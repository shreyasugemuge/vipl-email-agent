---
phase: 03-mark-irrelevant
plan: 01
subsystem: api
tags: [django, views, models, permissions, tdd]

requires:
  - phase: 01-gatekeeper-role
    provides: "can_triage permission property on User model"
provides:
  - "Thread.Status.IRRELEVANT enum value"
  - "ActivityLog.Action.MARKED_IRRELEVANT and REVERTED_IRRELEVANT"
  - "mark_irrelevant and revert_irrelevant POST endpoints"
  - "Irrelevant count in sidebar_counts aggregate"
  - "Explicit status filter overrides view-level status constraints"
affects: [03-mark-irrelevant, 04-unassigned-alerts]

tech-stack:
  added: []
  patterns: ["can_triage permission gating on views", "explicit status filter bypasses view constraints"]

key-files:
  created:
    - apps/emails/migrations/0017_add_irrelevant_status.py
    - apps/emails/tests/test_mark_irrelevant.py
  modified:
    - apps/emails/models.py
    - apps/emails/views.py
    - apps/emails/urls.py

key-decisions:
  - "Explicit ?status= query param overrides view-level status filtering (e.g., ?status=irrelevant works even on all_open view)"
  - "Revert clears assignment fields (assigned_to, assigned_by, assigned_at) to reset thread fully"

patterns-established:
  - "Permission gating via user.can_triage property for triage-only actions"
  - "View filter override: has_explicit_status skips view-level status constraints when status query param is set"

requirements-completed: [TRIAGE-01, TRIAGE-02, TRIAGE-06]

duration: 6min
completed: 2026-03-16
---

# Phase 3 Plan 1: Mark Irrelevant Backend Summary

**IRRELEVANT thread status with mark/revert endpoints, can_triage permission gating, ActivityLog audit trail, and queryset filtering excluding irrelevant from active views**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-15T19:27:30Z
- **Completed:** 2026-03-15T19:33:49Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Thread.Status.IRRELEVANT + two new ActivityLog actions with migration
- mark_irrelevant and revert_irrelevant POST endpoints with permission gating, reason validation, and detail panel re-render
- Irrelevant threads excluded from Triage Queue, My Inbox, All Open; accessible via ?status=irrelevant
- 11 new tests across 3 test classes, all passing (TDD red/green)

## Task Commits

Each task was committed atomically:

1. **Task 1: Model changes + migration + test scaffold** - `d149535` (test: RED phase)
2. **Task 2: Views, URLs, queryset filtering** - `07e7d0d` (feat: GREEN phase)

_TDD: Task 1 = RED (11 tests, 10 failing), Task 2 = GREEN (all 11 passing)_

## Files Created/Modified
- `apps/emails/models.py` - Added IRRELEVANT status, MARKED_IRRELEVANT and REVERTED_IRRELEVANT ActivityLog actions
- `apps/emails/migrations/0017_add_irrelevant_status.py` - Schema migration for new choices
- `apps/emails/views.py` - mark_irrelevant, revert_irrelevant views + sidebar irrelevant count + explicit status filter override
- `apps/emails/urls.py` - mark-irrelevant and revert-irrelevant URL patterns
- `apps/emails/tests/test_mark_irrelevant.py` - 11 tests: permissions, activity log, filtering, revert

## Decisions Made
- Explicit `?status=` query param overrides view-level status filtering so `?status=irrelevant` works regardless of which sidebar view is active
- Revert clears all assignment fields (assigned_to, assigned_by, assigned_at) to fully reset the thread to unassigned NEW state

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Status filter conflict with view-level status constraints**
- **Found during:** Task 2 (GREEN phase)
- **Issue:** `?view=all_open&status=irrelevant` returned empty results because all_open pre-filters to `status__in=["new", "acknowledged"]`, then `status=irrelevant` ANDs on top yielding nothing
- **Fix:** Added `has_explicit_status` flag; when `?status=` param is set, view-level status constraints are skipped
- **Files modified:** apps/emails/views.py
- **Verification:** test_status_filter_shows_irrelevant passes
- **Committed in:** 07e7d0d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for ?status=irrelevant filtering to work. No scope creep.

## Issues Encountered
- Pre-existing Phase 2 RED test failures (test_assignment_enforcement, test_inline_edit) unrelated to our changes; confirmed by running tests on clean HEAD. Logged as out-of-scope.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend mark-irrelevant is complete and tested
- Ready for Phase 3 Plan 2 (UI/template work for irrelevant buttons)
- Sidebar count `irrelevant` is available in template context

---
*Phase: 03-mark-irrelevant*
*Completed: 2026-03-16*
