---
phase: 04-read-unread-tracking
plan: 02
subsystem: ui
tags: [htmx, django-templates, tailwind, read-unread, oob-swap]

# Dependency graph
requires:
  - phase: 04-read-unread-tracking/04-01
    provides: "ThreadReadState model, annotate_unread queryset, mark_thread_unread endpoint, OOB swap renders"
provides:
  - "Per-user unread visual indicators (bold text + blue dot) on thread cards"
  - "Sidebar unread count badges with conditional blue/muted styling"
  - "Mark as Unread button in thread detail action bar"
  - "Browser tab title with unread count prefix"
  - "Keyboard shortcut (U key) for mark-as-unread"
affects: [05-smart-notifications, 06-reports-module]

# Tech tracking
tech-stack:
  added: []
  patterns: ["OOB swap for real-time card state updates", "Conditional badge styling (blue pill vs muted count)"]

key-files:
  modified:
    - templates/emails/_thread_card.html
    - templates/emails/thread_list.html
    - templates/emails/_thread_detail.html
    - templates/emails/_thread_list_body.html
    - templates/base.html
    - apps/emails/views.py

key-decisions:
  - "Replaced status=='new' with is_unread for bold/dot — decouples visual state from thread status"
  - "OOB swap sets thread.is_unread attribute directly on object for consistent template rendering"

patterns-established:
  - "Conditional badge pattern: blue pill when unreads > 0, muted total when all read"
  - "OOB title updater script for HTMX partial swaps"

requirements-completed: [READ-03, READ-05]

# Metrics
duration: 12min
completed: 2026-03-15
---

# Phase 4 Plan 02: Read/Unread UI Summary

**Per-user unread indicators on thread cards (bold + blue dot), sidebar badges, mark-as-unread button, and browser tab title count**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-15T13:46:00Z
- **Completed:** 2026-03-15T13:58:19Z
- **Tasks:** 3 (2 auto + 1 checkpoint)
- **Files modified:** 6

## Accomplishments
- Thread cards now use per-user `is_unread` instead of `status == 'new'` for bold text and blue dot styling
- Sidebar view badges show blue pill with unread count when unreads exist, muted total otherwise
- Mark as Unread envelope button in thread detail action bar (accessible to all users)
- Browser tab title shows `(N) VIPL Triage` prefix when unreads exist, with OOB updater for HTMX partials
- Keyboard shortcut: U key triggers mark-as-unread from detail panel

## Task Commits

Each task was committed atomically:

1. **Task 1: Update thread card template for per-user unread styling** - `d939aeb` (feat)
2. **Task 2: Sidebar unread badges, mark-unread button, and browser tab title** - `847205b` (feat)
3. **Task 3: Visual verification checkpoint** - approved (no code changes)

## Files Created/Modified
- `templates/emails/_thread_card.html` - Replaced status=='new' with is_unread for bold, blue dot, font weight
- `templates/emails/thread_list.html` - Conditional sidebar badges (blue pill / muted count)
- `templates/emails/_thread_detail.html` - Mark as Unread button + U keyboard shortcut
- `templates/emails/_thread_list_body.html` - OOB title updater script for HTMX partials
- `templates/base.html` - Tab title with unread_total prefix
- `apps/emails/views.py` - OOB swap renders set thread.is_unread attribute

## Decisions Made
- Replaced `status == 'new'` with `is_unread` for bold/dot logic -- decouples visual unread state from thread lifecycle status
- OOB swap renders set `thread.is_unread` directly on the object before `render_to_string` for consistent template rendering
- Mark as Unread button placed outside admin guard -- all users can mark their own read state

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Read/unread tracking feature complete (model + UI)
- Ready for Phase 05 (Smart Notifications) and Phase 06 (Reports)

## Self-Check: PASSED

All 6 modified files verified on disk. Both task commits (d939aeb, 847205b) verified in git history.

---
*Phase: 04-read-unread-tracking*
*Completed: 2026-03-15*
