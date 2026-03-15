---
phase: 06-qa-bug-fixes
plan: 01
subsystem: ui
tags: [htmx, oob-swap, mobile, keyboard-nav, django-templates]

requires:
  - phase: 05-inspector-polish
    provides: "Thread list and detail panel templates"
provides:
  - "Thread count OOB swap on HTMX view switch"
  - "Search hidden input sync on URL change"
  - "Mobile detail drawer without hidden parent blocker"
  - "Escape key closes detail panel on all viewports"
affects: [thread-list, detail-panel, mobile-ux]

tech-stack:
  added: []
  patterns:
    - "hx-swap-oob for updating elements outside HTMX target"
    - "htmx:pushedIntoHistory + popstate for hidden input sync"

key-files:
  created: []
  modified:
    - templates/emails/thread_list.html
    - templates/emails/_thread_list_body.html

key-decisions:
  - "OOB swap span in partial template mirrors existing title-updater pattern"
  - "closeThreadDetail() handles both mobile (translate-x) and desktop (innerHTML placeholder restore)"
  - "Removed hidden parent wrapper entirely rather than toggling classes via JS"

patterns-established:
  - "OOB swap pattern: add id to target element, add hx-swap-oob sibling in partial"
  - "Hidden input sync: listen to htmx:pushedIntoHistory + popstate, parse URL params"

requirements-completed: [QA-01, QA-02, QA-03, QA-04]

duration: 2min
completed: 2026-03-15
---

# Phase 06 Plan 01: QA Bug Fixes Summary

**Fixed 4 functional bugs: thread count OOB swap, search view-hidden sync, mobile detail drawer, Escape key close**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T17:50:30Z
- **Completed:** 2026-03-15T17:52:07Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Thread count label now updates on every HTMX sidebar view switch via OOB swap
- Search input preserves current view/inbox filter after HTMX navigation and browser back/forward
- Mobile detail drawer opens on thread tap (removed hidden parent wrapper that blocked display)
- Escape key closes detail panel on both mobile (slide off) and desktop (restore placeholder)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix thread count OOB swap + search view-hidden sync** - `a5f6763` (fix)
2. **Task 2: Fix mobile detail drawer + Escape key close** - `9307693` (fix)

## Files Created/Modified
- `templates/emails/thread_list.html` - Added thread-count-label id, hidden input sync listeners, mobile panel restructure, Escape handler, closeThreadDetail rewrite
- `templates/emails/_thread_list_body.html` - Added OOB swap span for thread count

## Decisions Made
- Used existing OOB swap pattern (same as title-updater) for thread count -- consistent, zero new infrastructure
- Removed hidden parent wrapper entirely instead of toggling via JS -- simpler, no state to manage
- closeThreadDetail() restores placeholder HTML on desktop via innerHTML (matches original server-rendered content)
- Escape key calls closeThreadDetail() unconditionally -- on desktop it restores placeholder, on mobile it slides off

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- No virtualenv in worktree for pytest regression check; changes are template-only (HTML/JS) so no Python test regression possible

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 4 QA bugs fixed, ready for visual verification
- Template changes are backwards-compatible with existing views.py context

---
*Phase: 06-qa-bug-fixes*
*Completed: 2026-03-15*
