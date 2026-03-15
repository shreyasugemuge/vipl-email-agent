---
phase: 04-alerts-bulk-actions
plan: 02
subsystem: ui, api
tags: [htmx, bulk-actions, django-views, undo, floating-bar]

# Dependency graph
requires:
  - phase: 01-permission-model
    provides: can_assign permission property on User model
provides:
  - Bulk assign endpoint for multiple threads at once
  - Bulk mark-irrelevant endpoint with reason
  - Bulk undo endpoint restoring previous thread states
  - Floating action bar with checkbox selection UI
  - Undo toast with 10-second reversal window
affects: [04-alerts-bulk-actions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_render_thread_list_response helper for HTMX partial re-render from POST views"
    - "HX-Trigger showUndoToast pattern for client-side undo state"
    - "Serialized previous_states in undo payload for stateless reversal"

key-files:
  created:
    - templates/emails/_bulk_action_bar.html
    - apps/emails/tests/test_bulk_actions.py
  modified:
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/_thread_card.html
    - templates/emails/_thread_list_body.html
    - templates/emails/thread_list.html

key-decisions:
  - "Undo state serialized in HX-Trigger response (stateless server, no session storage)"
  - "Permission uses user.can_assign (admin + triage lead), not is_admin_only"
  - "Checkboxes opacity-0 on desktop with group-hover reveal, always visible on mobile"

patterns-established:
  - "_render_thread_list_response: reuses thread_list view logic by faking HTMX request"
  - "Bulk action bar at page bottom, hidden by default, slides up via Tailwind transitions"

requirements-completed: [TRIAGE-04, TRIAGE-05]

# Metrics
duration: 7min
completed: 2026-03-16
---

# Phase 4 Plan 02: Bulk Actions Summary

**Bulk assign/mark-irrelevant endpoints with floating action bar, checkbox selection, and 10-second undo toast**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-15T20:07:18Z
- **Completed:** 2026-03-15T20:14:17Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Three bulk action endpoints (assign, mark-irrelevant, undo) with permission enforcement and ActivityLog entries
- Floating bottom bar with assign dropdown, mark-irrelevant with reason input, and clear button
- Thread card checkboxes with hover-visible desktop / always-visible mobile behavior
- Select-all checkbox, Escape to clear, auto-clear on HTMX swap
- Undo toast with 10-second window using serialized previous states

## Task Commits

Each task was committed atomically:

1. **Task 1: Bulk action endpoints (TDD)** - `a9c4d7e` (test: RED), `b727c2f` (feat: GREEN -- URLs + views)
2. **Task 2: Bulk selection UI** - `5638942` (feat: templates + JS)

## Files Created/Modified
- `apps/emails/views.py` - bulk_assign, bulk_mark_irrelevant, bulk_undo views + _render_thread_list_response helper
- `apps/emails/urls.py` - 3 bulk action URL patterns before thread/<pk>/ patterns
- `apps/emails/tests/test_bulk_actions.py` - 11 tests covering permissions, validation, success, undo
- `templates/emails/_bulk_action_bar.html` - Floating bottom bar with assign form + irrelevant form
- `templates/emails/_thread_card.html` - Checkbox per card with group-hover opacity
- `templates/emails/_thread_list_body.html` - Select-all checkbox for admin/triage lead
- `templates/emails/thread_list.html` - Bulk state management JS + undo toast listener

## Decisions Made
- Undo uses serialized previous_states in HX-Trigger header (stateless server, no session/DB storage)
- Permission gate is user.can_assign (admin + triage lead), consistent with existing assignment system
- _render_thread_list_response fakes an HTMX request to reuse thread_list view logic
- Checkboxes use CSS opacity (not display:none) for smooth hover transitions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- views.py bulk action code was already present from a prior branch commit (04-03); only URL routes needed adding
- Virtual environment located in main worktree, not gatekeeper worktree

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Bulk actions fully functional and tested
- Ready for visual verification and integration with alert system

## Self-Check: PASSED

All 7 files verified present. All 3 commits verified in git log.

---
*Phase: 04-alerts-bulk-actions*
*Completed: 2026-03-16*
