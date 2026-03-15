---
phase: 03-conversation-ui
plan: 01
subsystem: ui
tags: [django-templates, htmx, tailwind, three-panel, thread-list, sidebar]

# Dependency graph
requires:
  - phase: 01-thread-model-data-migration
    provides: Thread model with status, assignment, triage fields
provides:
  - thread_list view with filtering, sidebar counts, inbox filter
  - Three-panel layout template (sidebar + thread list + detail placeholder)
  - Compact 2-line thread card template
  - Thread list body with pagination
affects: [03-02-PLAN, 03-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: [inner-sidebar-within-content, view-based-filtering, inbox-pill-toggles]

key-files:
  created:
    - templates/emails/thread_list.html
    - templates/emails/_thread_card.html
    - templates/emails/_thread_list_body.html
  modified:
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/base.html

key-decisions:
  - "Inner sidebar is within content area (not replacing base.html dark sidebar) -- white/light panel for views+filters"
  - "thread_list replaces email_list as default at /emails/, legacy view moved to /emails/legacy/"
  - "Default view: all_open for admins, mine for members"
  - "Thread card uses 2-line compact layout for 15-20 visible threads without scrolling"

patterns-established:
  - "View-based sidebar: Unassigned/Mine/All Open/Closed with count badges and HTMX swap"
  - "Inbox pill toggles: single-select filter that persists across view changes"
  - "Collapsible filter section: priority/category/status dropdowns hidden by default"

requirements-completed: [UI-01, UI-02, UI-05, INBOX-04]

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 3 Plan 1: Thread List & Three-Panel Layout Summary

**Three-panel conversation UI with sidebar views, inbox filter pills, and compact 2-line thread cards replacing the email card list**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T07:04:05Z
- **Completed:** 2026-03-15T07:08:18Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Thread list view with full filtering (view/inbox/priority/category/status/search) and sidebar counts
- Three-panel layout: inner sidebar (220px) + thread list (~35%) + detail placeholder (~65%)
- Compact 2-line thread cards with sender, time, message count, assignee avatar, subject, priority dot, status badge, inbox badges
- All 382 existing tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Thread list view and URL routing** - `e98aa5d` (feat)
2. **Task 2: Three-panel layout template, thread cards, and sidebar** - `b707e5c` (feat)

## Files Created/Modified
- `apps/emails/views.py` - Added thread_list view with filtering, sidebar counts, pagination
- `apps/emails/urls.py` - thread_list as default route, email_list moved to /legacy/
- `templates/base.html` - Nav link updated to point to thread_list
- `templates/emails/thread_list.html` - Three-panel layout with inner sidebar, search, detail placeholder
- `templates/emails/_thread_card.html` - Compact 2-line thread card with all metadata
- `templates/emails/_thread_list_body.html` - Thread list body with empty state and pagination

## Decisions Made
- Inner sidebar is a content-area panel (white bg, right border), not a replacement for base.html's dark navigation sidebar
- thread_list replaces email_list as the default route at /emails/; legacy email_list remains accessible at /emails/legacy/
- Default view is "all_open" for admins, "mine" for members (matching the context decisions)
- Thread card hx-get currently points to email_detail as placeholder -- will be updated when thread_detail view is created in Plan 02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Thread list UI is complete and functional
- Detail panel is an empty placeholder ready for Plan 02 (thread detail with message history)
- Thread card click targets need updating when thread_detail endpoint is created

---
*Phase: 03-conversation-ui*
*Completed: 2026-03-15*
