---
phase: 02-email-pipeline
plan: 02
subsystem: email-processing
tags: [gmail-api, anthropic, claude, triage, pipeline, tenacity, two-tier-ai]

# Dependency graph
requires:
  - phase: 02-email-pipeline/01
    provides: "DTOs (EmailMessage, TriageResult), spam_filter, pdf_extractor, StateManager, Email/AttachmentMetadata models, SystemConfig"
provides:
  - "GmailPoller service (Gmail API polling with domain-wide delegation)"
  - "AIProcessor service (Claude AI triage with two-tier model selection)"
  - "Pipeline orchestrator (process_poll_cycle, save_email_to_db, retry_failed_emails)"
affects: [02-email-pipeline/03, 03-notifications, 04-sla]

# Tech tracking
tech-stack:
  added: [google-api-python-client, google-auth, anthropic, tenacity, pytz]
  patterns: [two-tier-ai, label-after-persist, circuit-breaker, dead-letter-retry]

key-files:
  created:
    - apps/emails/services/gmail_poller.py
    - apps/emails/services/ai_processor.py
    - apps/emails/services/pipeline.py
    - apps/emails/tests/test_gmail_poller.py
    - apps/emails/tests/test_ai_processor.py
    - apps/emails/tests/test_pipeline.py
  modified:
    - conftest.py

key-decisions:
  - "AIProcessor accepts anthropic_api_key param instead of reading ANTHROPIC_API_KEY env var directly (testable without env)"
  - "Spam filter called by pipeline orchestrator, not by AIProcessor (separation of concerns)"
  - "Pipeline is the ONLY module with Django ORM imports (GmailPoller and AIProcessor remain Django-agnostic)"

patterns-established:
  - "Label-after-persist: Gmail label applied only after successful DB write"
  - "Django-agnostic services: GmailPoller/AIProcessor have zero Django imports"
  - "Factory fixtures: make_email_message() and make_triage_result() in conftest.py"

requirements-completed: [PROC-01, PROC-02, PROC-05, INFR-11]

# Metrics
duration: 7min
completed: 2026-03-11
---

# Phase 2 Plan 2: Email Pipeline Core Summary

**Gmail poller and Claude AI triage ported from v1, wired through pipeline orchestrator with label-after-persist safety, circuit breaker, and dead letter retry**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-11T10:06:57Z
- **Completed:** 2026-03-11T10:14:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- GmailPoller ported from v1 with identical behavior (domain-wide delegation, label management, dedup query, attachment parsing)
- AIProcessor ported with two-tier model selection (Haiku default, Sonnet for CRITICAL), prompt caching, body truncation, input sanitization
- Pipeline orchestrator wires poll-filter-triage-save-label with label-after-persist safety pattern
- Dead letter retry processes failed emails up to 3 attempts with exhausted terminal state
- 22 new tests covering all services with mocked external APIs
- Full test suite passes (81 tests, zero regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Port GmailPoller + AIProcessor** - `7fda455` (feat)
2. **Task 2: Pipeline orchestrator** - `cf8fa9d` (feat)

_Both tasks followed TDD: tests written first (RED), then implementation (GREEN)._

## Files Created/Modified
- `apps/emails/services/gmail_poller.py` - Gmail API polling with domain-wide delegation, returns EmailMessage DTOs
- `apps/emails/services/ai_processor.py` - Two-tier Claude AI triage with prompt caching and tenacity retry
- `apps/emails/services/pipeline.py` - Pipeline orchestrator: save_email_to_db, process_single_email, process_poll_cycle, retry_failed_emails
- `apps/emails/tests/test_gmail_poller.py` - 5 tests for GmailPoller (poll, parse, label, link)
- `apps/emails/tests/test_ai_processor.py` - 5 tests for AIProcessor (triage, model selection, fallback, truncation, sanitization)
- `apps/emails/tests/test_pipeline.py` - 12 tests for pipeline (save, dedup, label order, spam, circuit breaker, retry)
- `conftest.py` - Added make_email_message() and make_triage_result() factory fixtures

## Decisions Made
- AIProcessor constructor takes explicit `anthropic_api_key` parameter instead of reading from env var directly (more testable)
- Spam filter is called by pipeline orchestrator, not by AIProcessor (v1 had spam filter inside AIProcessor; v2 separates concerns)
- Pipeline module is the only service with Django ORM imports; GmailPoller and AIProcessor remain Django-agnostic per locked decision

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing Python packages in venv**
- **Found during:** Task 1 (running tests)
- **Issue:** pytz, google-api-python-client, google-auth, tenacity, anthropic not installed in .venv despite being in requirements.txt
- **Fix:** Installed all required packages via pip
- **Files modified:** None (venv only, not committed)
- **Verification:** All imports succeed, tests pass
- **Committed in:** N/A (runtime environment fix)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Package installation was necessary for tests to run. No scope creep.

## Issues Encountered
None beyond the package installation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GmailPoller, AIProcessor, and pipeline orchestrator are ready for Plan 03 (scheduler management command)
- Chat notifier placeholder in pipeline ready for Phase 3 integration
- Dead letter retry ready for scheduler wiring

---
*Phase: 02-email-pipeline*
*Completed: 2026-03-11*
