---
phase: 04-read-unread-tracking
plan: 01
subsystem: ui
tags: [django, htmx, read-tracking, queryset-annotation, oob-swap]

requires:
  - phase: 01-models-migrations
    provides: ThreadReadState model with unique_together(thread, user)
provides:
  - annotate_unread() queryset helper for per-user unread state
  - mark_thread_unread POST endpoint with OOB card swap
  - ThreadReadState upsert on thread_detail open
  - Assignment read-state reset for assignee
  - Sidebar unread counts (unread_mine, unread_unassigned, unread_open, unread_closed)
affects: [04-02-templates-ui]

tech-stack:
  added: []
  patterns: [ThreadReadState update_or_create for read/unread mutations, Exists subquery annotation for unread detection]

key-files:
  created:
    - apps/emails/tests/test_read_state.py
  modified:
    - apps/emails/views.py
    - apps/emails/urls.py

key-decisions:
  - "No ThreadReadState row = treated as read (avoids wall-of-bold on first deploy)"
  - "Unread detection via Exists subquery: is_read=False OR read_at < last_message_at"
  - "OOB card swap on thread_detail open and mark-unread to update card styling without full page reload"

patterns-established:
  - "annotate_unread(qs, user) pattern: reusable queryset annotation for any view needing unread state"
  - "Sidebar unread counts computed separately from aggregate (dict mutation after .aggregate())"

requirements-completed: [READ-01, READ-02, READ-04]

duration: 4min
completed: 2026-03-15
---

# Phase 4 Plan 1: Read/Unread Tracking Backend Summary

**Per-user read/unread tracking with ThreadReadState upsert on detail open, mark-unread endpoint, assignment reset, and Exists-subquery annotation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T13:46:30Z
- **Completed:** 2026-03-15T13:51:03Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 12 tests covering all read state backend behaviors (mark-as-read, mark-as-unread, annotation, assignment reset, sidebar counts)
- annotate_unread() helper annotates thread querysets with per-user is_unread boolean
- mark_thread_unread POST endpoint sets is_read=False and returns OOB card swap
- thread_detail upserts ThreadReadState to is_read=True on open
- assign_thread_view resets assignee read state to unread
- sidebar_counts includes unread_mine, unread_unassigned, unread_open, unread_closed

## Task Commits

Each task was committed atomically:

1. **Task 1: Tests for read state backend logic** - `1ad9ee9` (test - TDD RED)
2. **Task 2: Implement read state views, annotation helper, and URL wiring** - `e46ecd6` (feat - TDD GREEN)

## Files Created/Modified
- `apps/emails/tests/test_read_state.py` - 12 tests for all read state backend logic
- `apps/emails/views.py` - annotate_unread helper, ThreadReadState upsert in thread_detail, mark_thread_unread view, assignment reset, sidebar unread counts
- `apps/emails/urls.py` - mark-unread URL pattern

## Decisions Made
- No ThreadReadState row = treated as read (avoids wall-of-bold on first deploy where no rows exist yet)
- Unread detection uses Exists subquery with OR condition: is_read=False OR read_at < last_message_at
- OOB card swap included in both thread_detail and mark_thread_unread responses for instant UI feedback

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All backend logic ready for Plan 02 (templates/UI) to render unread indicators
- annotate_unread() is wired into thread_list queryset
- sidebar_counts dict has unread keys ready for badge rendering
- mark_thread_unread URL resolves at /emails/threads/<pk>/mark-unread/

---
*Phase: 04-read-unread-tracking*
*Completed: 2026-03-15*
