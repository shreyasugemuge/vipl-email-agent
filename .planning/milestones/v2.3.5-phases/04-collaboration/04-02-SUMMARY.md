---
phase: 04-collaboration
plan: 02
subsystem: ui
tags: [presence, polling, htmx, django, viewing-indicator]

requires:
  - phase: 04-collaboration-01
    provides: Thread detail panel with sticky header, InternalNote model, timeline display
provides:
  - ThreadViewer model for tracking active thread viewers
  - Heartbeat endpoint for polling-based presence
  - Viewer badge partial with overlapping avatars
  - Idle detection and cleanup for viewer presence
affects: []

tech-stack:
  added: []
  patterns: [DB-backed polling presence, sendBeacon for cleanup, idle detection with heartbeat skip]

key-files:
  created:
    - apps/emails/migrations/0011_threadviewer.py
    - templates/emails/_viewer_badge.html
    - apps/emails/tests/test_viewing.py
  modified:
    - apps/emails/models.py
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/_thread_detail.html

key-decisions:
  - "ThreadViewer is ephemeral (plain Model, not SoftDeleteModel) -- viewer records are transient presence data"
  - "DB-backed polling (not WebSocket/Redis) -- 3-person team, 15s interval is more than adequate"
  - "Idle detection at 25s stops heartbeats before 30s server-side stale cutoff"
  - "navigator.sendBeacon for cleanup on page unload -- reliable even during navigation"

patterns-established:
  - "Ephemeral presence: DB polling with opportunistic stale cleanup on heartbeat"
  - "Viewer badge: overlapping avatar circles with +N overflow and tooltip"

requirements-completed: [COLLAB-04]

duration: 5min
completed: 2026-03-15
---

# Phase 4 Plan 2: Viewing Presence Summary

**DB-backed collision detection showing overlapping avatar badges when another user has the same thread open**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T07:30:33Z
- **Completed:** 2026-03-15T07:35:35Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- ThreadViewer model with unique (thread, user) constraint and auto-updating last_seen
- Heartbeat + clear-viewer endpoints with opportunistic stale record cleanup
- Viewer badge in thread detail sticky header with overlapping avatar circles and hover tooltip
- Heartbeat polling every 15s with idle detection (stops after 25s of inactivity)
- navigator.sendBeacon cleanup on page unload and htmx:beforeSwap on panel switch

## Task Commits

Each task was committed atomically:

1. **Task 1: ThreadViewer model, heartbeat endpoint, and cleanup logic**
   - `66dc4c8` (test) - Failing tests for viewing presence
   - `bdb1a67` (feat) - ThreadViewer model, heartbeat/clear-viewer endpoints, 11 tests pass
2. **Task 2: Viewer badge UI and heartbeat polling** - `f0ae153` (feat)

## Files Created/Modified
- `apps/emails/models.py` - Added ThreadViewer model (ephemeral, not SoftDeleteModel)
- `apps/emails/views.py` - get_active_viewers helper, viewer_heartbeat, clear_viewer endpoints
- `apps/emails/urls.py` - heartbeat and clear-viewer URL patterns
- `apps/emails/migrations/0011_threadviewer.py` - ThreadViewer migration
- `templates/emails/_viewer_badge.html` - Overlapping avatar badge partial with tooltip
- `templates/emails/_thread_detail.html` - Viewer badge in header, heartbeat polling JS, idle detection
- `apps/emails/tests/test_viewing.py` - 11 tests for model, helpers, and endpoints

## Decisions Made
- ThreadViewer is ephemeral (plain Model, not SoftDeleteModel) -- viewer records are transient presence data, cleanup is expected
- DB-backed polling rather than WebSocket/Redis -- 3-person team, 15s polling interval is more than adequate
- Idle detection threshold at 25s (5s before 30s server timeout) to avoid stale presence
- navigator.sendBeacon for reliable cleanup even during navigation/tab close

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 8 plans across 4 phases complete -- milestone v2.1 feature work done
- Ready for integration testing and deployment

---
*Phase: 04-collaboration*
*Completed: 2026-03-15*
