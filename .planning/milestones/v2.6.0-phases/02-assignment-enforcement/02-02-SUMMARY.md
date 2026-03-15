---
phase: 02-assignment-enforcement
plan: 02
subsystem: ui
tags: [django-templates, htmx, tailwind, assignment-ui, role-conditional]

requires:
  - phase: 01-role-permission-foundation
    provides: "User.can_assign, User.is_admin_only permission properties"
  - phase: 02-assignment-enforcement
    plan: 01
    provides: "REASSIGNED_BY_MEMBER action, reassign_thread() service, reassign_thread_view endpoint, server-side guards"
provides:
  - "Four-branch role-conditional assignment UI in detail panel"
  - "Inline reassign form with category-filtered candidates and mandatory reason"
  - "Read-only enforcement on editable priority/status/category dropdowns"
  - "Context menu Reassign item with R keyboard shortcut"
  - "REASSIGNED_BY_MEMBER styled activity timeline entry"
  - "Disabled claim button with tooltip for out-of-category threads"
affects: [04-alerts-bulk-actions]

tech-stack:
  added: []
  patterns:
    - "Four-branch template conditional: can_assign / assigned_to==user / can_claim / claim_disabled / read-only"
    - "Editable templates wrap content in permission check with read-only fallback"

key-files:
  created: []
  modified:
    - apps/emails/views.py
    - templates/emails/_thread_detail.html
    - templates/emails/_editable_priority.html
    - templates/emails/_editable_status.html
    - templates/emails/_editable_category.html
    - templates/emails/thread_list.html
    - apps/emails/tests/test_context_menu.py

key-decisions:
  - "claim_disabled computed in view context for disabled button rendering (not just absence of can_claim)"
  - "reassign_candidates filtered by CategoryVisibility in view context, not template"
  - "Context menu can_acknowledge/can_close gated on ownership-or-can_assign (not just status)"

patterns-established:
  - "Editable partials use {% if thread.assigned_to == request.user or user.can_assign %} gate with read-only fallback"
  - "Context menu keyboard shortcuts via data-action attribute + shortcutMap in thread_list.html"

requirements-completed: [ROLE-03, ROLE-04, ROLE-05]

duration: 21min
completed: 2026-03-15
---

# Phase 2 Plan 02: UI Gating Summary

**Four-branch role-conditional assignment UI with inline reassign form, disabled claim tooltip, read-only editable dropdowns, and visual verification approved**

## Performance

- **Duration:** 21 min (including human verification checkpoint)
- **Started:** 2026-03-15T19:38:04Z
- **Completed:** 2026-03-15T19:58:36Z
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 7

## Accomplishments
- Four-branch assignment section in detail panel: admin/gatekeeper assign dropdown, member reassign button + inline form, member claim button, disabled claim with tooltip, read-only assignee display
- Inline reassign form with exact UI-SPEC styling: amber-500 buttons, category-filtered candidates, mandatory reason textarea, "Reassign Thread" / "Keep Thread" buttons
- Read-only enforcement on all three editable dropdowns (priority, status, category) for members on others' threads
- Context menu "Reassign..." item with R keyboard shortcut for member on own thread
- REASSIGNED_BY_MEMBER styled activity timeline entry with reason display
- Fixed context menu can_claim to properly check CategoryVisibility + unassigned status
- Fixed context menu can_acknowledge/can_close to enforce ownership-or-can_assign

## Task Commits

Each task was committed atomically:

1. **Task 1: Role-conditional assignment UI + read-only enforcement** - `330db2a` (feat)
2. **Task 2: Visual verification** - approved by user (no commit)

## Files Created/Modified
- `apps/emails/views.py` - Added reassign_candidates, claim_disabled to _build_thread_detail_context; fixed context menu can_claim/can_acknowledge/can_close
- `templates/emails/_thread_detail.html` - Four-branch assignment UI, inline reassign form, REASSIGNED_BY_MEMBER timeline entry
- `templates/emails/_editable_priority.html` - Permission gate with read-only fallback
- `templates/emails/_editable_status.html` - Permission gate with read-only fallback
- `templates/emails/_editable_category.html` - Permission gate with read-only fallback
- `templates/emails/thread_list.html` - R keyboard shortcut in context menu handler
- `apps/emails/tests/test_context_menu.py` - Added CategoryVisibility setup for claim test

## Decisions Made
- `claim_disabled` is a separate context variable (not just the absence of `can_claim`) for explicit disabled button rendering
- `reassign_candidates` computed in view context to keep template logic simple
- Context menu `can_acknowledge`/`can_close` now enforce ownership-or-can_assign, preventing members from changing status on others' threads via context menu

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed context menu can_claim to require CategoryVisibility**
- **Found during:** Task 1 (test suite run)
- **Issue:** `test_member_sees_claim_instead_of_assign` failed because context menu `can_claim` didn't check CategoryVisibility or unassigned status
- **Fix:** Updated `thread_context_menu` view to properly check `thread.assigned_to is None` and `CategoryVisibility.objects.filter()`, matching the detail panel logic. Added CategoryVisibility setup to test.
- **Files modified:** apps/emails/views.py, apps/emails/tests/test_context_menu.py
- **Verification:** Full test suite passes (795 tests)
- **Committed in:** 330db2a (Task 1 commit)

**2. [Rule 1 - Bug] Fixed context menu can_acknowledge/can_close for role enforcement**
- **Found during:** Task 1 (code review during implementation)
- **Issue:** Context menu showed Acknowledge/Close to any user regardless of thread ownership
- **Fix:** Added `is_owner_or_assigner` gate to `can_acknowledge` and `can_close` in context menu view
- **Files modified:** apps/emails/views.py
- **Committed in:** 330db2a (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bug fixes)
**Impact on plan:** Both fixes necessary for correct role enforcement. The context menu view had looser permission checks than the detail panel.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (Assignment Enforcement) is fully complete
- All server-side guards + UI gating in place
- Ready for Phase 4 (Alerts + Bulk Actions) once Phase 3 is also complete
- No blockers

---
*Phase: 02-assignment-enforcement*
*Completed: 2026-03-15*
