---
phase: 02-assignment-enforcement
plan: 01
subsystem: auth
tags: [django, permissions, assignment, reassign, activitylog]

requires:
  - phase: 01-role-permission-foundation
    provides: "User.can_assign, User.is_admin_only permission properties, triage_lead_user fixture"
provides:
  - "REASSIGNED_BY_MEMBER ActivityLog action type with migration"
  - "reassign_thread() service function with mandatory reason enforcement"
  - "reassign_thread_view endpoint for member self-reassignment"
  - "Server-side guards on assign/edit_category/edit_priority views"
  - "Gatekeeper bypass on claim_thread CategoryVisibility check"
affects: [02-02-ui-gating, 03-triage-queue]

tech-stack:
  added: []
  patterns:
    - "reassign_thread() service enforces ownership + reason + CategoryVisibility"
    - "Server-side 403 on assign endpoint for members with exact message"

key-files:
  created:
    - apps/emails/migrations/0018_add_reassigned_by_member_action.py
    - apps/emails/tests/test_assignment_enforcement.py
  modified:
    - apps/emails/models.py
    - apps/emails/services/assignment.py
    - apps/emails/tests/test_inline_edit.py

key-decisions:
  - "Separate reassign endpoint (/reassign/) rather than overloading /assign/ -- cleaner separation"
  - "REASSIGNED_BY_MEMBER distinct from REASSIGNED for filtering/reporting"
  - "reassign_thread_view returns 403 for can_assign users (they should use /assign/ instead)"

patterns-established:
  - "Member self-reassignment requires mandatory non-empty reason stored in ActivityLog.detail"
  - "Server-side permission guards: can_assign OR assigned_to == user for edit endpoints"

requirements-completed: [ROLE-03, ROLE-04, ROLE-05]

duration: 7min
completed: 2026-03-15
---

# Phase 2 Plan 01: Assignment Enforcement Summary

**REASSIGNED_BY_MEMBER action type, reassign_thread() service with mandatory reason/ownership/CategoryVisibility checks, server-side 403 guards on assign and edit endpoints, 14 permission tests**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-15T19:28:00Z
- **Completed:** 2026-03-15T19:35:19Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments
- REASSIGNED_BY_MEMBER added to ActivityLog.Action with migration
- reassign_thread() service validates ownership, non-empty reason, and CategoryVisibility
- reassign_thread_view endpoint handles member self-reassignment with full response pattern
- assign_thread_view returns 403 with exact message per CONTEXT.md locked decision
- edit_category and edit_priority views now enforce ownership-or-can_assign guard
- claim_thread() updated to use can_assign for gatekeeper bypass (was admin/staff only)
- 14 new permission enforcement tests all passing, 795 total tests green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing tests for assignment enforcement** - `b0b9abd` (test)
2. **Task 1 GREEN: Implement assignment enforcement** - `e16829f` (feat)

## Files Created/Modified
- `apps/emails/models.py` - Added REASSIGNED_BY_MEMBER to ActivityLog.Action choices
- `apps/emails/migrations/0018_add_reassigned_by_member_action.py` - AlterField migration
- `apps/emails/services/assignment.py` - reassign_thread() service + claim_thread can_assign bypass
- `apps/emails/tests/test_assignment_enforcement.py` - 14 permission enforcement tests
- `apps/emails/tests/test_inline_edit.py` - Fixed tests for new edit guards (assign thread to member)

## Decisions Made
- Separate /reassign/ endpoint keeps member self-reassignment cleanly separated from admin/gatekeeper /assign/
- reassign_thread_view returns 403 for can_assign users, directing them to the standard assign endpoint

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed inline edit tests for new permission guards**
- **Found during:** Task 1 GREEN phase (full suite run)
- **Issue:** test_member_can_edit_category and test_member_can_edit_priority created threads not assigned to the member, which now correctly get 403
- **Fix:** Updated tests to assign thread to member_user before editing
- **Files modified:** apps/emails/tests/test_inline_edit.py
- **Verification:** Full test suite passes (795 tests)
- **Committed in:** e16829f (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Test fix was necessary for correctness -- the old tests were testing the wrong behavior (any user could edit any thread).

## Issues Encountered
- views.py and urls.py changes (reassign_thread_view, reassign URL, edit guards, 403 message) were already committed by Phase 1 Plan 02 (permission refactor). No duplicate work needed.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All server-side permission enforcement in place
- Ready for Plan 02 (UI gating: template changes for role-conditional assignment UI)
- No blockers

---
*Phase: 02-assignment-enforcement*
*Completed: 2026-03-15*
