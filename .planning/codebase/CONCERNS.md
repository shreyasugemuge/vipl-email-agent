# Codebase Concerns

**Analysis Date:** 2026-03-09

## Tech Debt

**Google Sheets as Database:**
- Issue: Google Sheets is used as the primary data store for all ticket management, SLA config, team data, cost tracking, dead letter queue, and config change auditing. Every read/write is an API call with rate limits, no transactions, no indexing, and no relational integrity.
- Files: `agent/sheet_logger.py` (992 lines — largest file in codebase)
- Impact: Sheets API rate limits (100 requests/100 seconds/user) will become a bottleneck as ticket volume grows. No atomic multi-cell updates means partial writes are possible. The entire `get_open_tickets()` / `get_all_tickets()` approach reads ALL rows every time (no pagination, no filtering server-side).
- Fix approach: v2 migration to PostgreSQL is already planned. Until then, this is a known limitation. Avoid adding more Sheet tabs or increasing poll frequency.

**SheetLogger God Class (992 lines):**
- Issue: `SheetLogger` handles email logging, SLA status updates, ticket reading, config tab management, formatting, dead letter management, cost tracking, agent status writing, and header initialization. It has 20+ public methods.
- Files: `agent/sheet_logger.py`
- Impact: Difficult to test individual concerns in isolation. Any change to Sheet structure risks breaking multiple unrelated features. New developers must understand the entire class to modify any part.
- Fix approach: For v2, split into domain-specific repositories (TicketRepository, ConfigRepository, etc.) backed by PostgreSQL.

**main.py Monolith (851 lines):**
- Issue: `main.py` contains config loading, config hot-reload logic, quiet hours check, component initialization, the entire email processing pipeline, dead letter retry logic, health server, scheduler setup, CLI parsing, and log buffering — all in one file.
- Files: `main.py`
- Impact: Hard to test individual pipeline steps. The `process_emails()` function is 140+ lines with deeply nested try/except blocks.
- Fix approach: Extract pipeline orchestration, config management, and health server into separate modules.

**In-Memory Ticket Counter:**
- Issue: Ticket numbering uses an in-memory counter (`self._ticket_counts`) that is safe only with `max-instances=1` on Cloud Run. The counter loads from Sheet on startup by scanning all rows in column A.
- Files: `agent/sheet_logger.py` (lines 53, 69-103)
- Impact: If Cloud Run scales to 2+ instances (misconfiguration), duplicate ticket numbers will be generated. The full-column scan on startup gets slower as ticket count grows.
- Fix approach: Use a Sheet-based atomic counter or (in v2) a database sequence.

**Class-Level Mutable State on AIProcessor:**
- Issue: Token counters (`_total_input_tokens`, `_total_output_tokens`, `_total_calls`, `_total_cache_hits`) are class variables, not instance variables. They accumulate across the entire process lifetime and are never reset.
- Files: `agent/ai_processor.py` (lines 132-134)
- Impact: The daily cost log in `log_daily_cost()` reports cumulative totals since last restart, not daily totals. After a long-running instance, the "daily" cost number becomes meaningless.
- Fix approach: Reset counters after each EOD report, or track per-day stats in a dict keyed by date.

**Business Hours SLA Calculation is a No-Op:**
- Issue: `SLAMonitor._business_hours_elapsed()` is supposed to calculate SLA time excluding non-business hours, but it just returns `dt.timestamp()` — identical to wall-clock time. The `business_hours_only` config flag exists but does nothing useful.
- Files: `agent/sla_monitor.py` (lines 155-157)
- Impact: If `business_hours_only` is enabled, SLA calculations silently behave identically to wall-clock mode. Users who enable this flag get no actual benefit.
- Fix approach: Implement actual business-hours-aware elapsed time calculation, or remove the flag and document that SLA is wall-clock only.

**Hardcoded NUM_CONFIG_FIELDS:**
- Issue: `NUM_CONFIG_FIELDS = 16` is hardcoded and must be manually kept in sync with the `CONFIG_FIELDS` list. A comment says "Keep in sync with CONFIG_FIELDS above" but there is no runtime check.
- Files: `agent/sheet_logger.py` (line 587)
- Impact: If a developer adds a config field to `CONFIG_FIELDS` without updating `NUM_CONFIG_FIELDS`, the Agent Status and Error Log sections in the Sheet will overlap with config rows, corrupting the display.
- Fix approach: Replace with `len(self.CONFIG_FIELDS)` everywhere.

## Known Bugs

**Cost Tracker Reports Cumulative, Not Daily:**
- Symptoms: The "daily" cost entry in the Cost Tracker tab shows cumulative token usage since the process last restarted, not the actual day's usage.
- Files: `agent/ai_processor.py` (lines 132-134), `agent/sheet_logger.py` (lines 800-847), `agent/eod_reporter.py` (lines 222-228)
- Trigger: Run the agent for multiple days without restart. Each day's cost entry will be higher than the last because counters never reset.
- Workaround: Cloud Run restarts frequently enough that this is approximately correct in practice. Not fixable without counter reset logic.

**SLA Summary Dedup is Hour-Granular:**
- Symptoms: If the SLA check runs at 8:59 AM and again at 9:01 AM, the 9:01 run sees `_last_summary_hour != 9` and sends a summary. But if the process restarts at 9:30, it will send another summary because `_last_summary_hour` is lost (in-memory only).
- Files: `agent/sla_monitor.py` (lines 46, 64-77)
- Trigger: Process restart during a summary hour.
- Workaround: Acceptable for v1 — at worst one duplicate SLA summary per restart.

## Security Considerations

**Broad OAuth Scopes:**
- Risk: The service account has `gmail.modify`, `gmail.send`, `spreadsheets`, and `drive` scopes. The `drive` scope is full access — far broader than needed for Sheets operations.
- Files: `agent/sheet_logger.py` (lines 24-27), `agent/gmail_poller.py` (lines 23-27)
- Current mitigation: Cloud Run uses `--no-allow-unauthenticated`, service account key is in Secret Manager, Docker runs as non-root.
- Recommendations: Narrow `drive` scope to `drive.file` or remove entirely (Sheets API should work with just `spreadsheets` scope). Audit whether `gmail.modify` can be narrowed to `gmail.labels` + `gmail.readonly`.

**Webhook URL in Config Without Validation:**
- Risk: The Chat webhook URL is accepted from environment variables and the Agent Config Sheet without cryptographic validation. A Sheet editor could redirect notifications to an attacker-controlled webhook.
- Files: `agent/chat_notifier.py` (lines 29-30), `main.py` (lines 130-132)
- Current mitigation: Only a prefix check (`https://chat.googleapis.com/`) is performed in `ChatNotifier.__init__`. The Sheet override in `load_sheet_config_overrides()` does not validate the webhook URL at all because webhook URL is not overridable from Sheet — only from env var. This is actually safe by design.
- Recommendations: No action needed. The current design correctly limits webhook URL to env vars only.

**Email Body Sent to External API:**
- Risk: Full email body content (up to 1500 chars) is sent to Anthropic's API for triage. This may include sensitive business information, customer PII, or confidential attachments (PDF text).
- Files: `agent/ai_processor.py` (lines 245-275)
- Current mitigation: Body truncated to 1500 chars, PDF text truncated to 1000 chars. Anthropic's data retention policy applies.
- Recommendations: Consider adding PII scrubbing before sending to Claude. Document the data flow in a privacy policy.

## Performance Bottlenecks

**Full Sheet Scan on Every Read:**
- Problem: `get_open_tickets()`, `get_all_tickets()`, and `get_all_tickets_today()` each read the ENTIRE Email Log tab (all rows, columns A-U) every time they are called. The EOD report calls all three.
- Files: `agent/sheet_logger.py` (lines 234-304)
- Cause: Google Sheets API has no server-side filtering. Every query returns all rows, and filtering happens in Python.
- Improvement path: v2 PostgreSQL will solve this. For v1, consider caching `get_all_tickets()` with a short TTL since EOD calls it and `get_all_tickets_today()` reads the same data.

**SLA Check Reads All Tickets Every 15 Minutes:**
- Problem: `SLAMonitor.check()` calls `sheet.get_open_tickets()` every 15 minutes, reading the entire Sheet each time. Then `update_sla_status()` reads column A again for EACH breached ticket to find its row number.
- Files: `agent/sla_monitor.py` (line 91), `agent/sheet_logger.py` (lines 740-762)
- Cause: No row-number cache. Each `update_sla_status()` call does a linear scan of column A.
- Improvement path: Cache ticket-to-row mapping during `get_open_tickets()` and pass it through, or batch updates.

**Thread ID Cache Reads Entire Column T:**
- Problem: Every 2 minutes, `_refresh_thread_id_cache()` reads ALL values from column T of the Email Log. As tickets accumulate (hundreds, thousands), this grows linearly.
- Files: `agent/sheet_logger.py` (lines 370-383)
- Cause: No way to incrementally update the cache from Sheets.
- Improvement path: Increase TTL for mature deployments, or only read the last N rows.

## Fragile Areas

**Agent Config Tab Row Calculations:**
- Files: `agent/sheet_logger.py` (lines 586-592)
- Why fragile: Row positions for the Status and Error Log sections are computed from `NUM_CONFIG_FIELDS` using arithmetic. Adding/removing config fields requires updating the hardcoded constant AND understanding the row layout. The `STATUS_HEADER_ROW`, `STATUS_DATA_ROW`, `LOG_HEADER_ROW` etc. are class-level constants computed at import time.
- Safe modification: Always use `len(CONFIG_FIELDS)` instead of `NUM_CONFIG_FIELDS`. Test by running `--init-sheet` after any change and visually inspecting the Sheet.
- Test coverage: No tests verify the row layout calculation. Only `ensure_agent_config_tab` is tested indirectly.

**Config Hot-Reload Mutation:**
- Files: `main.py` (lines 171-278)
- Why fragile: `load_sheet_config_overrides()` mutates the config dict in-place (via `setdefault` and direct assignment). The scheduler runs `process_emails()` which calls this function, and other scheduled jobs (SLA, EOD) read from the same config dict. While there is a `_config_lock`, only `process_emails()` acquires it — SLA and EOD jobs do not.
- Safe modification: Make config immutable (frozen dataclass or namedtuple). Create a new config dict on each reload instead of mutating.
- Test coverage: Config override logic has unit tests, but thread-safety is not tested.

**Gmail First-Poll vs Incremental Mode:**
- Files: `agent/gmail_poller.py` (lines 55, 240-313)
- Why fragile: `_first_poll_done` is an instance flag that changes the Gmail query from "latest 5" to "new since startup + unlabeled". If the first poll partially fails (e.g., one inbox succeeds, another throws), `_first_poll_done` is still set to True in `poll_all()`, potentially missing emails from the failed inbox.
- Safe modification: Track first-poll state per inbox, not globally.
- Test coverage: Basic poll tests exist but do not test partial-failure scenarios.

**Retry Decorator on Sheet Writes:**
- Files: `agent/sheet_logger.py` (lines 199-228)
- Why fragile: The `@retry` decorator retries on ALL `HttpError` exceptions, including 4xx client errors (bad request, permission denied). Only 5xx server errors should trigger retries. A malformed request will be retried 3 times before failing.
- Safe modification: Add a custom retry predicate that checks `e.resp.status >= 500`.
- Test coverage: Retry logic is not directly tested.

## Scaling Limits

**Google Sheets API Quota:**
- Current capacity: ~100 requests per 100 seconds per user (Google default)
- Limit: With 2 inboxes, 5-min poll interval, 15-min SLA check, and 30-min dead letter retry, the agent makes ~10-20 API calls per poll cycle. At high email volume (50+ emails/cycle), this could hit 100+ calls.
- Scaling path: v2 PostgreSQL eliminates this. For v1, increase poll interval or batch Sheet operations.

**Email Log Growth:**
- Current capacity: Google Sheets supports 10 million cells per spreadsheet
- Limit: With 22 columns, this is ~454,000 rows. At 50 emails/day, that is ~25 years. But full-column reads get slower well before that — expect degradation around 10,000-20,000 rows.
- Scaling path: Archive old tickets to a separate Sheet periodically.

**Single-Instance Constraint:**
- Current capacity: 1 Cloud Run instance processing all emails sequentially
- Limit: If email volume exceeds what one instance can process in a poll cycle (dependent on Claude API latency), emails will queue up.
- Scaling path: v2 with PostgreSQL and proper queue-based processing.

## Dependencies at Risk

**APScheduler 3.x (End of Life):**
- Risk: APScheduler 3.x is in maintenance mode. APScheduler 4.x is a complete rewrite with incompatible API.
- Impact: No new features or bug fixes. Migration to 4.x requires significant code changes.
- Migration plan: For v2, consider switching to Celery Beat or a simple cron-based approach.

**PyMuPDF Licensing:**
- Risk: PyMuPDF (pymupdf==1.24.3) changed to AGPL-3.0 license in recent versions, which has copyleft implications for commercial use.
- Impact: If the agent is considered a commercial product, AGPL may require open-sourcing the entire application.
- Migration plan: Evaluate license compliance. Alternative: use `pdfminer.six` (MIT) or `pypdf` (BSD) for PDF text extraction.

**Pinned Dependency Versions:**
- Risk: All dependencies are pinned to exact versions (no ranges). This prevents security patches from being applied automatically.
- Files: `requirements.txt`
- Impact: Known vulnerabilities in pinned versions won't be patched until manually updated.
- Migration plan: Use `~=` or `>=` with upper bounds for patch versions. Run `pip-audit` in CI.

## Missing Critical Features

**No Rate Limiting on Gmail API Calls:**
- Problem: The agent polls Gmail with `maxResults=10` per inbox but makes individual `messages.get()` calls for each message. No rate limiting or batching.
- Blocks: Nothing currently, but could cause quota exhaustion during high-volume periods.

**No Graceful Degradation When Sheet Is Full/Locked:**
- Problem: If the Google Sheet is locked for editing by another user, or reaches row limits, the agent will log errors and move to dead letter, but there is no circuit breaker specifically for Sheet failures.
- Blocks: Could result in all emails going to dead letter during a Sheet outage.

**No Alerting on Prolonged Failures:**
- Problem: The circuit breaker stops polling after 3 consecutive failures, but there is no external notification (PagerDuty, email alert) when this happens. The only indicator is the health endpoint's `consecutive_failures` field.
- Blocks: Agent could be silently broken for hours before anyone notices.

## Test Coverage Gaps

**No Tests for Config Hot-Reload Thread Safety:**
- What's not tested: Concurrent access to the config dict from multiple scheduler threads (process_emails, SLA check, EOD report).
- Files: `main.py` (lines 376-378)
- Risk: Race condition could cause partial config reads during hot-reload.
- Priority: Low (single-instance, Python GIL provides some protection)

**No Tests for Sheet Formatting Methods:**
- What's not tested: `format_email_log_columns()`, `_format_agent_config_tab()`, `ensure_agent_config_tab()` — these construct complex Sheets API batch requests.
- Files: `agent/sheet_logger.py` (lines 472-731)
- Risk: Formatting bugs won't be caught until deployment. Row calculation errors could corrupt the Sheet layout.
- Priority: Medium

**No Integration Test for Full Pipeline:**
- What's not tested: The complete flow from Gmail poll through AI triage to Sheet log to Chat notification. Unit tests mock each component individually.
- Files: `tests/test_main.py`
- Risk: Integration issues between components (e.g., data format mismatches) could slip through.
- Priority: Medium (8 integration tests exist but only test AI processor)

**No Tests for Dead Letter Retry Flow:**
- What's not tested: The `retry_failed_triages()` function in `main.py` and the `get_failed_triages_for_retry()` / `update_failed_triage_retry()` methods.
- Files: `main.py` (lines 522-589), `agent/sheet_logger.py` (lines 933-992)
- Risk: Retry logic bugs could cause infinite retries or lost emails.
- Priority: High

**No Tests for Error Recovery Paths:**
- What's not tested: What happens when `gmail.mark_processed()` fails AFTER `sheet.log_email()` succeeds. The email would be logged but not labeled, causing a duplicate on next poll (caught by `is_thread_logged` cache, but only if cache is fresh).
- Files: `main.py` (lines 451), `agent/gmail_poller.py` (lines 315-324)
- Risk: Edge case could cause duplicate ticket entries if Sheet cache TTL expires between polls.
- Priority: Medium

---

*Concerns audit: 2026-03-09*
