---
phase: 03-workflow-actions
plan: 01
subsystem: ui
tags: [django, htmx, context-menu, claim, toast, spam-toggle]

requires:
  - phase: 01-bug-fixes
    provides: "Thread model with assignment, CategoryVisibility"
provides:
  - "Fixed can_claim logic in context menu (admin + member + visibility check)"
  - "Toast notification on thread claim"
  - "Verified spam toggle working correctly"
affects: []

tech-stack:
  added: []
  patterns: ["can_claim permission check pattern: assigned_to=None + CategoryVisibility"]

key-files:
  created: []
  modified:
    - apps/emails/views.py
    - apps/emails/tests/test_context_menu.py
    - apps/emails/tests/test_settings_views.py

key-decisions:
  - "Context menu can_claim now matches detail panel logic: requires assigned_to=None + CategoryVisibility for members, always True for admins"
  - "Spam toggle verified working as-is -- no changes needed"

patterns-established:
  - "Claim permission: admins can always claim unassigned threads; members need CategoryVisibility for thread category"

requirements-completed: [FLOW-01, FLOW-02]

duration: 4min
completed: 2026-03-15
---

# Phase 3 Plan 1: Fix Claim Button + Spam Toggle Summary

**Fixed context menu Claim visibility (admin/member/visibility), added "Thread claimed" toast, verified spam toggle**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T17:22:54Z
- **Completed:** 2026-03-15T17:26:39Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed context menu `can_claim` to require `assigned_to is None` + CategoryVisibility check (was broken: excluded admins, showed Claim for assigned threads)
- Added "Thread claimed" toast message to `claim_thread_view` response
- Verified spam toggle works correctly (mark_spam/mark_not_spam both set proper state and toast)
- Added 6 new tests covering all fixed claim scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix Claim button bugs and add toast** - `c4cd044` (fix)
2. **Task 2: Add/update tests for fixed claim logic** - `0190bf5` (test)

## Files Created/Modified
- `apps/emails/views.py` - Fixed `thread_context_menu` can_claim logic + added toast_msg to `claim_thread_view`
- `apps/emails/tests/test_context_menu.py` - Added CategoryVisibility import, fixed existing test, added 4 new tests
- `apps/emails/tests/test_settings_views.py` - Added `TestThreadClaimEndpoint` class with 2 toast tests

## Decisions Made
- Context menu `can_claim` now matches `_build_thread_detail_context` logic exactly: admins always see Claim for unassigned threads, members need CategoryVisibility
- Spam toggle verified working correctly -- no code changes needed (both views set toast_msg and toggle is_spam properly)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed existing test_member_sees_claim_instead_of_assign**
- **Found during:** Task 1 verification
- **Issue:** Test was passing with broken can_claim logic (no CategoryVisibility check). After fix, test failed because member had no CategoryVisibility record.
- **Fix:** Added `CategoryVisibility.objects.create(user=member_user, category=thread.category)` to test setup
- **Files modified:** apps/emails/tests/test_context_menu.py
- **Verification:** All 18 targeted tests pass
- **Committed in:** c4cd044 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test)
**Impact on plan:** Test was only passing due to broken logic. Fix is necessary for correctness.

## Issues Encountered
- Pre-existing test failure in `test_activity.py::test_shows_activity_entries` -- unrelated to changes, logged as deferred item

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Claim button and spam toggle working correctly
- Ready for remaining workflow action plans

---
*Phase: 03-workflow-actions*
*Completed: 2026-03-15*
