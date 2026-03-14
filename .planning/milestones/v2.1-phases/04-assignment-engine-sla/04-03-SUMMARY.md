---
phase: 04-assignment-engine-sla
plan: 03
subsystem: sla, notifications, scheduler
tags: [sla, chat-notifier, apscheduler, breach-detection, escalation]

# Dependency graph
requires:
  - phase: 04-assignment-engine-sla/01
    provides: SLA calculator, breach detection, assignment rules, auto-assign
  - phase: 04-assignment-engine-sla/02
    provides: ChatNotifier base class, settings UI, SLA display
provides:
  - SLA breach auto-escalation (priority bump on breach)
  - Manager breach summary Chat notification (Cards v2)
  - Per-assignee personal breach Chat alerts
  - Scheduler jobs: auto-assign every 3min, SLA summary at 9/13/17 IST
affects: [05-reporting-admin, 06-migration]

# Tech tracking
tech-stack:
  added: [CronTrigger]
  patterns: [breach-escalation-with-24h-dedup, manager-plus-personal-alerts]

key-files:
  created: []
  modified:
    - apps/emails/services/sla.py
    - apps/emails/services/chat_notifier.py
    - apps/emails/management/commands/run_scheduler.py
    - apps/emails/tests/test_sla.py
    - apps/emails/tests/test_scheduler.py

key-decisions:
  - "24h dedup on SLA_BREACHED ActivityLog prevents re-bumping priority on every check cycle"
  - "Personal breach alerts post to same Chat space (no per-user DM) -- true DMs need Chat API with user-scoped auth (deferred)"
  - "CronTrigger for SLA summary (9,13,17 IST) separate from interval-based breach status updates"

patterns-established:
  - "Breach escalation pattern: check 24h ActivityLog before bumping to avoid cascading escalation"
  - "Manager summary + per-assignee personal alerts pattern for Chat notifications"

requirements-completed: [SLA-03, SLA-04]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 4 Plan 3: SLA Breach Alerting Summary

**SLA breach auto-escalation with priority bumping, manager Cards v2 summary, per-assignee personal Chat alerts, and scheduler integration (auto-assign 3min + SLA summary 9/13/17 IST)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T18:09:13Z
- **Completed:** 2026-03-11T18:13:25Z
- **Tasks:** 1 of 2 (Task 2 is human-verify checkpoint)
- **Files modified:** 5

## Accomplishments
- SLA breach detection finds overdue emails (ack + respond) and auto-escalates priority one level
- 24-hour dedup prevents re-bumping on repeated check cycles
- Manager gets full breach summary via Chat (total counts, top 3 offenders, per-assignee breakdown)
- Each assignee gets a separate personal breach alert listing only their breached emails
- Scheduler now runs 5 jobs: heartbeat (1min), poll (5min), retry (30min), auto-assign (3min), SLA summary (9/13/17 IST)
- 232 tests passing (35 SLA-specific, up from 21)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for breach escalation** - `d016e46` (test)
2. **Task 1 (GREEN): SLA breach escalation, Chat alerts, scheduler jobs** - `0cff536` (feat)

_TDD: RED->GREEN pattern, no refactor needed_

## Files Created/Modified
- `apps/emails/services/sla.py` - Added check_and_escalate_breaches, build_breach_summary, PRIORITY_ESCALATION map
- `apps/emails/services/chat_notifier.py` - Added notify_breach_summary (manager) and notify_personal_breach (per-assignee)
- `apps/emails/management/commands/run_scheduler.py` - Added auto_assign_job (3min) and sla_summary_job (CronTrigger 9,13,17)
- `apps/emails/tests/test_sla.py` - 14 new tests: breach summary, escalation, Chat alerts, notification flow
- `apps/emails/tests/test_scheduler.py` - Updated job count assertion from 3 to 5

## Decisions Made
- 24h dedup on SLA_BREACHED ActivityLog prevents re-bumping priority on every check cycle
- Personal breach alerts post to same Chat space (webhook-only, no per-user DM) -- true DMs deferred to Chat API
- CronTrigger for SLA summary at fixed times (9,13,17 IST), separate from interval-based checks

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated scheduler test job count assertion**
- **Found during:** Task 1 (full test suite verification)
- **Issue:** test_scheduler.py expected 3 add_job calls but we added 2 new jobs (5 total)
- **Fix:** Updated assertion from 3 to 5
- **Files modified:** apps/emails/tests/test_scheduler.py
- **Verification:** Full test suite passes (232 tests)
- **Committed in:** 0cff536 (part of GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary test update for new scheduler jobs. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 4 automation layer complete: auto-assignment, SLA tracking, breach detection, escalation, Chat alerts
- Task 2 (human-verify checkpoint) pending: visual verification of end-to-end Phase 4 flow
- Ready for Phase 5 (Reporting + Admin + Sheets Mirror) after checkpoint approval

---
*Phase: 04-assignment-engine-sla*
*Completed: 2026-03-11*
