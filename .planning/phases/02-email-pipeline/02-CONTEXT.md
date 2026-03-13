# Phase 2: Email Pipeline - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Port the v1 email processing pipeline to Django with PostgreSQL as the data store. Emails flow from Gmail into the Email model — polled, spam-filtered, triaged by AI, with dead letter retry and Chat notifications. Feature flags and runtime config are hot-reloadable from the database. Reaches functional parity with v1's email processing capabilities.

Requirements: PROC-01, PROC-02, PROC-03, PROC-04, PROC-05, PROC-06, INFR-08, INFR-11

</domain>

<decisions>
## Implementation Decisions

### Module Porting Strategy
- Adapt v1 classes into Django service modules — keep class structure, swap Sheets calls for Django ORM
- Services live in `apps/emails/services/` (gmail_poller.py, ai_processor.py, chat_notifier.py, etc.)
- Keep v1 dataclasses (EmailMessage, TriageResult) as DTOs — GmailPoller returns EmailMessage, a save step maps it to the Email model. Clean separation: poller doesn't need Django imports.
- Adapt v1 triage prompt for v2 — strip Sheet/ticket references, keep triage logic, categories, priorities, and output format intact. Store in `prompts/` directory.

### Scheduler & Background Jobs
- Single management command (`python manage.py run_scheduler`) running APScheduler with all jobs (poll, retry, SLA check)
- Runs as a second service in Docker Compose — same image, different command. Two containers: web (Gunicorn) + scheduler.
- In-memory StateManager for ephemeral state (cooldowns, failure tracking, EOD dedup) — same as v1, resets on restart (acceptable)
- Scheduler writes a heartbeat timestamp to DB every minute; health endpoint checks it — if stale > 5 min, report degraded

### Feature Flags & Config Storage
- SystemConfig model in `apps/core/` with key-value pairs (key, value, type, description)
- Scheduler reloads config every poll cycle — same hot-reload pattern as v1 Sheets
- Port v1's 3 feature flags (AI Triage, Chat Notifications, EOD Email) AND expand with v2 flags (auto-assignment toggle, dashboard notifications, etc.) as they become relevant
- Django admin for config editing now; dashboard settings page added later (Phase 5)

### Dead Letter & Error Handling
- Claude's discretion on implementation — either a separate FailedTriage model or a status/retry_count field on the Email model
- Retry pattern should match v1: max 3 attempts, scheduler job triggers retries
- Fallback triage result pattern preserved from v1 (return safe defaults on AI failure)

### Claude's Discretion
- Dead letter model design (separate model vs fields on Email)
- Exact SystemConfig model schema (beyond key/value/type/description)
- How config validation works (range checks, type coercion)
- Scheduler job intervals and timing
- Error handling patterns for ORM operations
- Test structure and fixture design

</decisions>

<specifics>
## Specific Ideas

- v1's label-after-persist safety pattern MUST be preserved: Gmail "Agent/Processed" label applied only AFTER successful DB save
- v1's circuit breaker pattern should carry over: pause polling after consecutive failures
- v1's two-tier AI (Haiku default, Sonnet for CRITICAL) and spam pre-filter (13 regex patterns) are proven — port as-is
- Config should be expandable — new phases will add their own flags without schema changes

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/emails/models.py`: Email model already has all needed fields (message_id, gmail_id, category, priority, ai_summary, status, assigned_to)
- `apps/core/models.py`: SoftDeleteModel and TimestampedModel base classes ready
- `agent/gmail_poller.py`: GmailPoller class with EmailMessage dataclass — adapt, don't rewrite
- `agent/ai_processor.py`: AIProcessor with TriageResult dataclass, spam filter, two-tier AI — adapt
- `agent/chat_notifier.py`: ChatNotifier with Cards v2 webhook — adapt
- `agent/state.py`: StateManager — can be reused almost as-is (no external dependencies)
- `agent/utils.py`: IST timezone, parse_sheet_datetime — port datetime utils
- `prompts/triage_prompt.txt`: Triage system prompt — adapt for v2

### Established Patterns
- Dependency injection via constructor (v1 pattern, carry forward)
- tenacity retry decorator for external API calls
- Structured JSON logging with `logging.getLogger(__name__)`
- Dataclass DTOs for inter-module communication

### Integration Points
- Email model (apps/emails/models.py) — target for all pipeline writes
- Health endpoint (apps/core/views.py) — add scheduler heartbeat check
- Django admin — register SystemConfig model
- docker-compose.yml — add scheduler service
- requirements.txt — add anthropic, google-api-python-client, google-auth, tenacity, apscheduler, pypdf

</code_context>

<deferred>
## Deferred Ideas

- Dashboard settings page for config editing — Phase 5 (Admin)
- Auto-assignment toggle flag — will be added to SystemConfig when Phase 4 is built
- SLA config per category/priority — Phase 4

</deferred>

---

*Phase: 02-email-pipeline*
*Context gathered: 2026-03-09*
