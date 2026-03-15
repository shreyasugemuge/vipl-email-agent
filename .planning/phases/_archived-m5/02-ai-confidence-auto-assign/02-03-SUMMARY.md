---
phase: 02-ai-confidence-auto-assign
plan: 03
subsystem: ui, views
tags: [confidence, auto-assign, feedback, htmx, templates]

# Dependency graph
requires:
  - phase: 02-ai-confidence-auto-assign/01
    provides: "confidence_base and confidence_tooltip template filters, Thread.ai_confidence"
  - phase: 02-ai-confidence-auto-assign/02
    provides: "Thread.is_auto_assigned field, inline auto-assign in pipeline"
provides:
  - "accept_thread_suggestion and reject_thread_suggestion views"
  - "Confidence dots on thread cards and detail panel"
  - "Auto badge next to assignee name"
  - "Accept/reject suggestion bar with HTMX buttons"
  - "AssignmentFeedback recording on accept/reject"
affects: [02-ai-confidence-auto-assign, dashboard-templates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Suggestion bar pattern: show_suggestion_bar context flag from view, accept/reject HTMX buttons"
    - "Auto badge: muted 'auto' pill next to assignee, cleared on explicit accept"

key-files:
  created:
    - apps/emails/tests/test_feedback.py
  modified:
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/_thread_card.html
    - templates/emails/_thread_detail.html

key-decisions:
  - "Suggestion bar shows for both unassigned-with-suggestion AND auto-assigned threads"
  - "Accept/reject buttons use hx-post with HTMX, re-render entire detail panel partial"
  - "Reject clears ai_suggested_assignee on latest email so suggestion bar disappears"

patterns-established:
  - "Thread-level suggestion flow: view resolves suggestion from latest email's ai_suggested_assignee JSON"
  - "show_suggestion_bar computed in _build_thread_detail_context based on assignment state + suggestion presence"

requirements-completed: [INTEL-05, INTEL-06, INTEL-07]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 2 Plan 03: Confidence Dots, Auto Badge, and Accept/Reject UI Summary

**Confidence dots (green/amber/red) on thread cards and detail panel, auto badge for auto-assigned threads, and accept/reject suggestion bar with HTMX buttons and AssignmentFeedback recording**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T13:59:05Z
- **Completed:** 2026-03-15T14:04:01Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Thread-level accept/reject views with admin-only access, feedback recording, and HTMX partial rendering
- Confidence dots on thread cards (after priority chip) and in AI Summary area of detail panel
- Auto badge ("auto" pill) next to assignee name, disappears on explicit accept
- Suggestion bar with accept/reject buttons for both unassigned and auto-assigned threads
- 13 new tests, 677 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for accept/reject** - `779d9ec` (test)
2. **Task 1 GREEN: Implement accept/reject views + URL patterns** - `4a6a0e4` (feat)
3. **Task 2: Confidence dots, auto badge, suggestion bar** - `f03676c` (feat)

## Files Created/Modified
- `apps/emails/tests/test_feedback.py` - 13 tests for accept/reject suggestion flow and feedback recording
- `apps/emails/views.py` - accept_thread_suggestion, reject_thread_suggestion views + AssignmentFeedback import + show_suggestion_bar context
- `apps/emails/urls.py` - Thread-level accept-suggestion/ and reject-suggestion/ URL patterns
- `templates/emails/_thread_card.html` - Confidence dot after priority chip
- `templates/emails/_thread_detail.html` - Confidence in AI area, auto badge, accept/reject suggestion bar

## Decisions Made
- Suggestion bar shows for both unassigned-with-suggestion and auto-assigned threads (both cases need accept/reject)
- Reject clears ai_suggested_assignee on the latest email so the suggestion bar disappears permanently
- Accept/reject re-render full detail panel partial (same pattern as other thread actions)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All UI elements for confidence, auto-assign, and feedback in place
- AssignmentFeedback records ready for distillation service (Plan 04) to consume
- Full test suite green (677 passed)

---
*Phase: 02-ai-confidence-auto-assign*
*Completed: 2026-03-15*
