---
phase: 05-reporting-admin-sheets-mirror
plan: 02
subsystem: infra
tags: [eod, email, chat, apscheduler, gmail-api, django-orm]

requires:
  - phase: 02-email-pipeline
    provides: ChatNotifier, StateManager, pipeline services
  - phase: 04-assignment-sla
    provides: SLA deadlines on Email model

provides:
  - EODReporter service with stats aggregation from Django ORM
  - ChatNotifier.notify_eod_summary for daily Chat card
  - Django HTML email template with inline CSS
  - Scheduler EOD cron job at 7 PM IST with startup catch-up
  - Persistent dedup via SystemConfig last_eod_sent

affects: [06-migration-cutover]

tech-stack:
  added: []
  patterns: [eod-reporter-service, cron-job-with-startup-catchup, persistent-dedup]

key-files:
  created:
    - apps/emails/services/eod_reporter.py
    - templates/emails/eod_email.html
    - apps/emails/tests/test_eod_reporter.py
  modified:
    - apps/emails/services/chat_notifier.py
    - apps/emails/management/commands/run_scheduler.py
    - apps/emails/tests/test_scheduler.py

key-decisions:
  - "Dual dedup: in-memory StateManager (10 min) + persistent SystemConfig.last_eod_sent (cross-restart)"
  - "Stats from Django ORM instead of Google Sheets (v2 architecture)"
  - "Startup catch-up fires missed EOD only during business hours (8AM-9PM IST)"

patterns-established:
  - "EOD reporter pattern: generate_stats -> render_email -> send via Gmail API + Chat card"
  - "Startup catch-up pattern: check persistent timestamp, fire if missed and within business hours"

requirements-completed: [INFR-05]

duration: 6min
completed: 2026-03-12
---

# Phase 5 Plan 02: EOD Reporter Summary

**Daily EOD report via Gmail API + Chat card with Django ORM stats, SLA metrics, feature flags, and 10-min dedup**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-12T11:12:41Z
- **Completed:** 2026-03-12T11:18:22Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- EODReporter service aggregates stats from Django ORM (received, closed, open, unassigned, SLA breaches, priority/category breakdown, avg ack/respond times, worst overdue)
- ChatNotifier.notify_eod_summary posts Cards v2 payload with stats grid, SLA metrics, worst overdue list
- Django HTML email template with inline CSS for Gmail/Outlook compatibility
- Feature flag respect: eod_email_enabled, chat_notifications_enabled
- Dual dedup: in-memory StateManager + persistent SystemConfig.last_eod_sent
- Scheduler EOD cron job at 7 PM IST with startup catch-up for missed reports

## Task Commits

Each task was committed atomically:

1. **Task 1: EOD reporter TDD RED** - `d12f41c` (test)
2. **Task 1: EOD reporter TDD GREEN** - `3529cdb` (feat)
3. **Task 2: Scheduler integration** - `10484bf` (feat)

## Files Created/Modified
- `apps/emails/services/eod_reporter.py` - EODReporter class with generate_stats, render_email, send_report, _send_email
- `templates/emails/eod_email.html` - Django HTML email template with inline CSS
- `apps/emails/services/chat_notifier.py` - Added notify_eod_summary method for daily Chat card
- `apps/emails/management/commands/run_scheduler.py` - Added _eod_job, CronTrigger at 19:00 IST, startup catch-up
- `apps/emails/tests/test_eod_reporter.py` - 8 tests covering stats, rendering, flags, dedup, Chat card
- `apps/emails/tests/test_scheduler.py` - Updated job count assertion (5 -> 6), added ADMIN_EMAIL env

## Decisions Made
- Dual dedup: in-memory StateManager (10 min window) + persistent SystemConfig.last_eod_sent key for cross-restart dedup
- Stats aggregated from Django ORM instead of Google Sheets (v2 architecture)
- Startup catch-up only fires within business hours (8AM-9PM IST) to avoid late-night reports
- Gmail API send via service account impersonation (same pattern as v1)
- avg_time_to_acknowledge uses assigned_at - received_at for ack'd/replied/closed emails

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed scheduler test DB access error**
- **Found during:** Task 2
- **Issue:** Existing scheduler test failed because new `_eod_startup_catchup` method accesses SystemConfig (DB) but test wasn't marked as django_db
- **Fix:** Mocked `_eod_startup_catchup` in test and added `ADMIN_EMAIL` env var to prevent `SystemConfig.get("admin_email")` fallback
- **Files modified:** apps/emails/tests/test_scheduler.py
- **Verification:** All 249 tests pass
- **Committed in:** 10484bf (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix to keep existing tests green. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- EOD reporting complete, ready for Plan 05-03 (Sheets Mirror)
- All 249 tests passing (8 new EOD tests + 241 existing)

---
*Phase: 05-reporting-admin-sheets-mirror*
*Completed: 2026-03-12*
