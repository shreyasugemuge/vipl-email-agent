---
phase: 01-bug-fixes
plan: 01
subsystem: emails
tags: [pipeline, thread-read-state, reopened-status, template-tags, avatar]

requires: []
provides:
  - ThreadReadState creation on new thread and reopen in pipeline
  - REOPENED status on Thread.Status
  - Amber color and tooltip for reopened status in template tags
  - Verified avatar sync on OAuth login
affects: [02-thread-card-detail-ux, 03-sidebar-navigation]

tech-stack:
  added: []
  patterns:
    - "_create_unread_states_for_all_users helper: bulk reset + create missing read states"

key-files:
  created: []
  modified:
    - apps/emails/models.py
    - apps/emails/services/pipeline.py
    - apps/emails/templatetags/email_tags.py
    - apps/emails/views.py
    - apps/emails/tests/test_pipeline.py

key-decisions:
  - "REOPENED as TextChoices addition -- no migration needed (CharField max_length=20)"
  - "Reopen resets ALL existing read states to unread + creates missing ones"
  - "Avatar sync verified working -- no code changes needed (BUG-04)"

patterns-established:
  - "_create_unread_states_for_all_users: update existing + bulk_create missing pattern for idempotent read state management"

requirements-completed: [BUG-02, BUG-03, BUG-04]

duration: 5min
completed: 2026-03-15
---

# Phase 1 Plan 1: Backend Bug Fixes Summary

**Pipeline creates ThreadReadState(is_read=False) for new/reopened threads, sets REOPENED status on reopen, avatar sync verified working**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T17:08:50Z
- **Completed:** 2026-03-15T17:13:53Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Pipeline creates ThreadReadState(is_read=False) for all active users when a new thread is created
- Pipeline sets status to REOPENED (not NEW) when a closed/acknowledged thread gets a new email
- Reopened threads reset all users' read states to unread
- Template tags return amber color and descriptive tooltip for reopened status
- Views include "reopened" in all open-status filter queries
- Avatar sync verified working with 8 existing tests covering all edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix pipeline -- unread state + REOPENED status** (TDD)
   - `eb3de86` (test: failing tests for unread state, reopened status, template tags)
   - `03e3896` (feat: pipeline unread state, REOPENED status, template tags)
2. **Task 2: Verify avatar sync** -- No code changes needed; 8 existing tests pass

## Files Created/Modified
- `apps/emails/models.py` -- Added REOPENED to Thread.Status
- `apps/emails/services/pipeline.py` -- ThreadReadState creation on new/reopened threads, REOPENED status
- `apps/emails/templatetags/email_tags.py` -- Amber color, tooltip, status_color for reopened
- `apps/emails/views.py` -- Include "reopened" in all status__in filter lists
- `apps/emails/tests/test_pipeline.py` -- 9 new tests (read state, reopened status, template tags)

## Decisions Made
- REOPENED is a TextChoices addition on CharField(max_length=20) -- no migration needed
- Reopen resets ALL existing read states to unread (not just creating new ones) to ensure everyone sees the reopened thread
- Avatar sync (BUG-04) verified working as-is -- adapter code and 8 tests cover all edge cases

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing reopen tests to expect REOPENED status**
- **Found during:** Task 1
- **Issue:** Three existing tests asserted `Thread.Status.NEW` on reopen; now status is REOPENED
- **Fix:** Updated assertions in test_save_reopens_closed_thread, test_save_reopens_acknowledged_thread, test_reopen_creates_reopened_activity_log
- **Files modified:** apps/emails/tests/test_pipeline.py
- **Committed in:** 03e3896

---

**Total deviations:** 1 auto-fixed (1 bug fix in tests)
**Impact on plan:** Expected -- changing reopen status from NEW to REOPENED requires updating existing test assertions.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- REOPENED status is added to Thread model; templates can render amber badges
- ThreadReadState rows now exist for new threads; unread indicators will work correctly
- Ready for thread card and detail UX plans that display these states

---
*Phase: 01-bug-fixes*
*Completed: 2026-03-15*

## Self-Check: PASSED
