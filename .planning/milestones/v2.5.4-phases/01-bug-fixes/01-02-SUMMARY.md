---
phase: 01-bug-fixes
plan: 02
subsystem: ui, views
tags: [htmx, oob-swap, sessionStorage, welcome-banner, django-views]

requires:
  - phase: none
    provides: existing accept/reject suggestion views and welcome banner JS
provides:
  - Welcome banner dedup via sessionStorage (vipl_welcome_shown flag)
  - OOB card swap on accept/reject AI suggestion (thread card updates in list)
affects: [frontend, thread-detail, thread-list]

tech-stack:
  added: []
  patterns:
    - "OOB card swap pattern now consistent across ALL action views"
    - "sessionStorage shown-flag pattern for deduplicating UI on redirect flows"

key-files:
  created: []
  modified:
    - templates/emails/email_list.html
    - apps/emails/views.py
    - apps/emails/tests/test_feedback.py

key-decisions:
  - "Used _render_thread_detail_with_oob_card helper (already exists) instead of duplicating OOB logic"
  - "Added vipl_welcome_shown flag set BEFORE showing banner to prevent race condition on OAuth redirect"

patterns-established:
  - "All thread action views must return OOB card swap via _render_thread_detail_with_oob_card"

requirements-completed: [BUG-01, BUG-05]

duration: 5min
completed: 2026-03-15
---

# Phase 1 Plan 2: Frontend & View Bug Fixes Summary

**Welcome banner dedup via sessionStorage shown-flag, plus OOB card swap on accept/reject AI suggestion views**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T17:08:29Z
- **Completed:** 2026-03-15T17:13:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Welcome banner now shows at most once per session, preventing double-show on OAuth redirect flow
- accept_thread_suggestion and reject_thread_suggestion views return OOB card swap, matching all other action views
- 4 new tests verify OOB swap behavior on accept/reject

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix welcome banner double-show on OAuth login** - `43ac117` (fix)
2. **Task 2 RED: Add failing OOB swap tests** - `ef6918a` (test)
3. **Task 2 GREEN: Add OOB card swap to accept/reject views** - `bd7d33f` (feat)

## Files Created/Modified
- `templates/emails/email_list.html` - Added vipl_welcome_shown sessionStorage check before showing banner
- `apps/emails/views.py` - Replaced manual render with _render_thread_detail_with_oob_card in accept/reject views
- `apps/emails/tests/test_feedback.py` - 4 new tests for OOB swap in accept/reject responses

## Decisions Made
- Used existing `_render_thread_detail_with_oob_card` helper rather than duplicating OOB logic inline
- Set `vipl_welcome_shown` flag before removing `hidden` class to prevent race condition

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in `test_pipeline.py::TestPipelineThreading::test_save_reopens_closed_thread` (unrelated to this plan, caused by other uncommitted changes in this worktree). Logged to deferred items.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both BUG-01 and BUG-05 resolved
- All feedback tests passing (17/17)
- Ready for next plan in phase

---
*Phase: 01-bug-fixes*
*Completed: 2026-03-15*
