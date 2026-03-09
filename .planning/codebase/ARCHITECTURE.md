# Architecture

**Analysis Date:** 2026-03-09

## Pattern Overview

**Overall:** Pipeline-based background service with scheduler-driven event loops

**Key Characteristics:**
- Single-process Python application running on Cloud Run (single instance)
- Background scheduler (APScheduler) drives all recurring tasks: email polling, SLA checks, EOD reports, dead letter retry
- Pipeline pattern: Gmail poll -> AI triage -> Sheet log -> Chat notify
- Google Sheets as the sole persistent data store (source of truth for tickets, config, SLA)
- In-memory state only for ephemeral data (cooldowns, failure counts, dedup caches)
- Hot-reloadable config: config.yaml < env vars < Google Sheet Agent Config tab

## Layers

**Entry Point / Orchestration (`main.py`):**
- Purpose: CLI parsing, config loading, component wiring, scheduler setup, health server
- Location: `main.py`
- Contains: `load_config()`, `init_components()`, `process_emails()`, `retry_failed_triages()`, `run_agent()`, `HealthHandler`, `AgentLogBuffer`, JSON logging setup
- Depends on: All `agent/` modules, APScheduler, PyYAML
- Used by: Docker ENTRYPOINT, CLI

**Data Ingestion (`agent/gmail_poller.py`):**
- Purpose: Poll Gmail inboxes for new emails via domain-wide delegation
- Location: `agent/gmail_poller.py`
- Contains: `GmailPoller` class, `EmailMessage` dataclass
- Depends on: Google Auth (service account), Gmail API v1
- Used by: `main.py:process_emails()`, `main.py:retry_failed_triages()`

**AI Processing (`agent/ai_processor.py`):**
- Purpose: Two-tier Claude AI triage with spam pre-filter, PDF extraction, cost optimization
- Location: `agent/ai_processor.py`
- Contains: `AIProcessor` class, `TriageResult` dataclass, `TRIAGE_TOOL` schema, spam regex patterns
- Depends on: Anthropic Python SDK, tenacity (retry), pymupdf (PDF extraction), `agent/utils.py`
- Used by: `main.py:process_emails()`, `main.py:retry_failed_triages()`

**Persistence (`agent/sheet_logger.py`):**
- Purpose: All CRUD operations against Google Sheets (ticket logging, SLA config, team data, dead letter, cost tracking, agent status)
- Location: `agent/sheet_logger.py`
- Contains: `SheetLogger` class with methods for 7+ sheet tabs
- Depends on: Google Sheets API v4, Google Auth (service account), tenacity (retry)
- Used by: All other agent modules (central data layer)

**Notifications (`agent/chat_notifier.py`):**
- Purpose: Post formatted Cards v2 messages to Google Chat via webhook
- Location: `agent/chat_notifier.py`
- Contains: `ChatNotifier` class with methods for poll summary, SLA breach summary, EOD summary, startup notification
- Depends on: httpx (HTTP client)
- Used by: `main.py:process_emails()`, `agent/sla_monitor.py`, `agent/eod_reporter.py`

**SLA Monitoring (`agent/sla_monitor.py`):**
- Purpose: Check open tickets for SLA breaches, update Sheet status, post 3x daily summary
- Location: `agent/sla_monitor.py`
- Contains: `SLAMonitor` class
- Depends on: `agent/sheet_logger.py`, `agent/chat_notifier.py`, `agent/state.py`, `agent/utils.py`
- Used by: APScheduler (every 15 min), `agent/eod_reporter.py`

**Reporting (`agent/eod_reporter.py`):**
- Purpose: Generate daily end-of-day summary email + Chat card + cost tracking
- Location: `agent/eod_reporter.py`
- Contains: `EODReporter` class
- Depends on: `agent/sheet_logger.py`, `agent/sla_monitor.py`, `agent/chat_notifier.py`, Gmail API (send), Jinja2
- Used by: APScheduler (daily cron), startup logic in `main.py`

**State Management (`agent/state.py`):**
- Purpose: In-memory ephemeral state (SLA alert cooldowns, failure tracking, EOD dedup, config change detection)
- Location: `agent/state.py`
- Contains: `StateManager` class
- Depends on: Nothing (pure Python)
- Used by: `main.py`, `agent/sla_monitor.py`

**Utilities (`agent/utils.py`):**
- Purpose: Shared helpers (datetime parsing, IST timezone constant)
- Location: `agent/utils.py`
- Contains: `parse_sheet_datetime()`, `IST` timezone, `SHEET_DATETIME_FORMAT`
- Depends on: pytz
- Used by: `agent/sla_monitor.py`, `agent/eod_reporter.py`, `agent/ai_processor.py`

## Data Flow

**Email Processing Pipeline (every 5 min):**

1. `main.py:process_emails()` hot-reloads config from Google Sheet Agent Config tab
2. `GmailPoller.poll_all()` queries Gmail API for unprocessed emails across all inboxes
3. `SheetLogger.is_thread_logged()` dedup check against cached Sheet thread IDs (2 min TTL)
4. `AIProcessor.is_spam()` runs regex pre-filter (free, skips Claude)
5. `AIProcessor.process()` calls Claude Haiku via tool_use; escalates to Sonnet if CRITICAL
6. `SheetLogger.log_email()` writes ticket row to Email Log tab (generates ticket number)
7. `GmailPoller.mark_processed()` applies "Agent/Processed" Gmail label (AFTER Sheet write succeeds)
8. `ChatNotifier.notify_poll_summary()` posts ONE summary card for all emails in the cycle
9. `SheetLogger.write_agent_status()` updates agent status + error logs in Agent Config tab

**SLA Monitoring (every 15 min + 3x daily summary):**

1. `SLAMonitor.check()` reads all open tickets from Sheet
2. Parses SLA deadlines, identifies breaches, updates Sheet SLA status column
3. At summary hours (9 AM, 1 PM, 5 PM IST), posts ONE breach summary card to Chat
4. Quiet hours suppress Chat notifications but Sheet updates continue

**EOD Report (daily 7 PM IST + startup):**

1. `EODReporter.generate_stats()` aggregates ticket data from Sheet (received, closed, open, breaches, unassigned)
2. `EODReporter.render_email()` renders Jinja2 HTML template
3. Sends HTML email via Gmail API to fresh recipients (re-read from Sheet)
4. Posts summary card to Chat
5. Logs daily AI cost to Cost Tracker tab

**Dead Letter Retry (every 30 min):**

1. `SheetLogger.get_failed_triages_for_retry()` reads Failed Triage tab
2. `GmailPoller.fetch_thread_message()` re-fetches the original email
3. Re-runs AI triage pipeline
4. On success: logs to Email Log, marks retry as "Success"
5. After 3 failures: marks "Exhausted", alerts on Chat

**State Management:**
- All persistent state lives in Google Sheets (tickets, config, SLA, cost tracking)
- In-memory state (`StateManager`) tracks only ephemeral data: SLA alert cooldowns, consecutive failure count, EOD dedup timestamp, config change baseline
- No file-based persistence (Cloud Run ephemeral filesystem)

## Key Abstractions

**EmailMessage:**
- Purpose: Parsed email data passed through the pipeline
- Defined in: `agent/gmail_poller.py`
- Pattern: Python dataclass with fields for thread_id, message_id, inbox, sender, subject, body, timestamp, attachments, gmail_link

**TriageResult:**
- Purpose: Structured output from AI triage (or spam filter / fallback)
- Defined in: `agent/ai_processor.py`
- Pattern: Python dataclass with category, priority, summary, draft_reply, reasoning, tags, language, token usage, model_used, success/error

**SheetLogger:**
- Purpose: Central data access layer for all Google Sheets operations
- Defined in: `agent/sheet_logger.py`
- Pattern: Single class managing 7+ sheet tabs with retry logic (tenacity), thread-safe caching, and header auto-initialization

**StateManager:**
- Purpose: Ephemeral runtime state that does not survive restarts
- Defined in: `agent/state.py`
- Pattern: Pure in-memory Python class with dict-based cooldown tracking

## Entry Points

**`main.py` (CLI):**
- Location: `main.py:main()`
- Triggers: Docker ENTRYPOINT `python main.py`, or manual CLI
- Responsibilities: Parse args, load config, init components, dispatch to scheduler or one-shot mode
- CLI modes: `--once` (single poll), `--eod` (EOD report), `--sla` (SLA check), `--init-sheet` (setup headers), `--retry` (dead letter retry), default (full scheduler)

**Health Endpoint:**
- Location: `main.py:HealthHandler`
- Triggers: HTTP GET to `/health` or `/` on port 8080 (configurable via `PORT` env var)
- Responsibilities: Return JSON status with uptime, AI usage stats, failure count

## Error Handling

**Strategy:** Defensive try/except at every boundary with graceful degradation

**Patterns:**
- **Circuit breaker**: `StateManager` tracks consecutive poll failures; after `max_consecutive_failures` (default 3), poll cycles are skipped entirely. Resets on first success. (`main.py:process_emails()`)
- **Retry with backoff**: Claude API calls retry 3x with exponential backoff on transient errors (APIConnectionError, RateLimitError, InternalServerError) via tenacity (`agent/ai_processor.py:_call_claude()`)
- **Sheet write retry**: Google Sheets API writes retry 3x with exponential backoff on HttpError 429/500/503 via tenacity (`agent/sheet_logger.py`)
- **Fallback triage**: If AI fails completely, returns a safe `TriageResult` with "General Inquiry" / "MEDIUM" and flags for manual review (`agent/ai_processor.py:_fallback_result()`)
- **Dead letter queue**: Failed triages logged to "Failed Triage" sheet tab for automated retry (max 3 attempts, then "Exhausted" with Chat alert) (`main.py:retry_failed_triages()`)
- **Label-after-persist**: Gmail "Agent/Processed" label is applied ONLY after successful Sheet write. If Sheet write fails, the email stays unlabeled and will be retried on next poll cycle (`main.py:process_emails()`)
- **Per-email isolation**: Each email in a poll batch is processed independently; one failure does not block others (`main.py:process_emails()`)

## Cross-Cutting Concerns

**Logging:**
- JSON structured logging via custom `JSONFormatter` in `main.py`
- Outputs to stdout for Cloud Logging ingestion
- Fields: timestamp (IST), severity, component, message, plus optional extras (inbox, thread_id, cost_usd, model, tokens, ticket)
- In-memory `AgentLogBuffer` stores last 50 ERROR/HIGHLIGHT entries for Sheet status display

**Validation:**
- AI output validation: category and priority checked against `VALID_CATEGORIES` and `VALID_PRIORITIES` enums; invalid values default to safe fallbacks (`agent/ai_processor.py`)
- Input sanitization: control chars and null bytes stripped before AI processing (`agent/ai_processor.py:_sanitize()`)
- Config validation: Sheet overrides validated for range (poll interval 60-3600s, SLA cooldown 1-48h, hours 0-23); invalid values logged as warnings, previous config kept (`main.py:load_sheet_config_overrides()`)

**Authentication:**
- Google Workspace service account with domain-wide delegation (scopes: gmail.readonly, gmail.labels, gmail.modify, gmail.send, spreadsheets, drive)
- Service account key file at `/secrets/service-account.json` (Secret Manager mount) with local fallback to `service-account.json`
- Anthropic API key from `ANTHROPIC_API_KEY` env var
- Chat webhook URL from `GOOGLE_CHAT_WEBHOOK_URL` env var (Secret Manager)

**Configuration:**
- Three-tier priority: env vars > Google Sheet Agent Config tab > `config.yaml`
- Hot-reload: Agent Config tab re-read every poll cycle (thread-safe with `_config_lock`)
- Feature flags: AI Triage Enabled, Chat Notifications Enabled, EOD Email Enabled (all from Sheet)
- Config change audit: changes detected by `StateManager.detect_config_changes()` and logged to Change Log sheet tab

**Scheduling:**
- APScheduler `BackgroundScheduler` with IST timezone
- Jobs: email poll (interval), SLA check (interval), EOD report (cron), dead letter retry (interval 30 min)
- All jobs: `max_instances=1`, `coalesce=True` (prevents overlap and catches up missed runs)

---

*Architecture analysis: 2026-03-09*
