---
phase: 05-editable-attrs-context-menu
plan: 02
subsystem: ui
tags: [context-menu, htmx, vanilla-js, long-press, keyboard-nav]

requires:
  - phase: 05-01
    provides: "Inline editable dropdowns for category, priority, status"
provides:
  - "Right-click context menu on thread cards with grouped quick actions"
  - "Mobile long-press (500ms) trigger for same context menu"
  - "Role-aware menu rendering (admin vs member)"
  - "Keyboard navigation within menu (arrow keys, Escape)"
affects: [04-read-unread-tracking, phase-3-spam]

tech-stack:
  added: []
  patterns:
    - "Server-rendered context menu via HTMX GET + JS positioning"
    - "Long-press via touchstart/touchend timers"

key-files:
  created:
    - templates/emails/_context_menu.html
    - apps/emails/tests/test_context_menu.py
  modified:
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/_thread_card.html
    - templates/emails/thread_list.html

key-decisions:
  - "Context menu fetched server-side (GET) for role-aware rendering -- avoids duplicating permission logic in JS"
  - "Placeholder URLs for Phase 3/4 endpoints (mark spam, toggle read) with graceful fallback"

patterns-established:
  - "Server-rendered context menus: fetch partial via GET, position with JS, process with htmx.process()"

requirements-completed: [MENU-01, MENU-02, MENU-03, MENU-04, MENU-05]

duration: 8min
completed: 2026-03-15
---

# Phase 5 Plan 2: Context Menu Summary

**Right-click and long-press context menu on thread cards with grouped actions, role-aware visibility, and keyboard navigation**

## Performance

- **Duration:** 8 min (continuation -- task 1 completed by prior agent)
- **Started:** 2026-03-15T14:27:52Z
- **Completed:** 2026-03-15T14:36:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Context menu endpoint returns role-aware HTML partial with 4 action groups
- Thread cards respond to right-click (desktop) and long-press (mobile, 500ms)
- Menu closes on click outside, Escape, or scroll; arrow key navigation within menu
- Human verified: inline edit dropdowns and context menu working on desktop and mobile

## Task Commits

Each task was committed atomically:

1. **Task 1: Context menu endpoint and JS component (TDD)** - `ad6ccce` (test) + `7a78490` (feat)
2. **Task 2: Visual and functional verification** - checkpoint:human-verify, approved by user

**Plan metadata:** `d83bac8` (docs: complete context menu plan)

## Files Created/Modified
- `templates/emails/_context_menu.html` - Floating menu partial with grouped actions and keyboard shortcut hints
- `apps/emails/tests/test_context_menu.py` - Tests for context menu endpoint and role-based visibility
- `apps/emails/views.py` - Added thread_context_menu view
- `apps/emails/urls.py` - Added context-menu URL route
- `templates/emails/_thread_card.html` - Added contextmenu + long-press event handlers
- `templates/emails/thread_list.html` - Added context menu container div and JS component

## Decisions Made
- Context menu fetched server-side (GET) for role-aware rendering -- avoids duplicating permission logic in JS
- Placeholder URLs for Phase 3/4 endpoints (mark spam, toggle read) with graceful fallback

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 5 complete (both plans 01 and 02 done)
- Context menu references Phase 3 (mark spam) and Phase 4 (toggle read) endpoints via placeholders
- Ready for Phase 6 (reports module) continuation

## Self-Check: PASSED

All files and commits verified:
- _context_menu.html: FOUND
- test_context_menu.py: FOUND
- SUMMARY.md: FOUND
- Commit ad6ccce: FOUND
- Commit 7a78490: FOUND

---
*Phase: 05-editable-attrs-context-menu*
*Completed: 2026-03-15*
