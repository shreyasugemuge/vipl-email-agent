---
phase: 04-alerts-bulk-actions
plan: 01
subsystem: notifications
tags: [google-chat, alerts, systemconfig, rising-edge, sidebar-badge]

requires:
  - phase: 01-permission-model
    provides: "User role model and can_assign/can_triage permissions"
provides:
  - "Rising-edge unassigned alert via Chat webhook"
  - "Threshold-based sidebar badge coloring (green/amber/red)"
  - "Configurable alert threshold and cooldown in Settings"
  - "SystemConfig keys for alert state tracking"
affects: [04-02, 04-03]

tech-stack:
  added: []
  patterns: ["Rising-edge detection with SystemConfig flag", "Cooldown via timestamp comparison"]

key-files:
  created:
    - apps/core/migrations/0007_seed_alert_config.py
    - apps/emails/tests/test_unassigned_alerts.py
  modified:
    - apps/emails/services/chat_notifier.py
    - apps/emails/management/commands/run_scheduler.py
    - templates/emails/thread_list.html
    - templates/emails/settings.html
    - apps/emails/views.py
    - apps/emails/urls.py

key-decisions:
  - "Alert fires regardless of quiet hours (proactive, not suppressible)"
  - "Rising-edge flag stored in SystemConfig for persistence across restarts"
  - "Badge thresholds hardcoded in template (5+ red, 3-4 amber, 1-2 green) matching default SystemConfig"
  - "Alert config in SLA tab of Settings page (not a separate tab)"

patterns-established:
  - "Rising-edge detection: SystemConfig flag tracks was-below state, prevents re-fire"
  - "Cooldown via ISO timestamp in SystemConfig with minute-based comparison"

requirements-completed: [ALERT-01, ALERT-02, ALERT-03]

duration: 6min
completed: 2026-03-16
---

# Phase 04 Plan 01: Unassigned Alert System Summary

**Rising-edge Chat alert on threshold crossing with cooldown, threshold-based sidebar badge coloring, and configurable alert settings**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-15T20:06:46Z
- **Completed:** 2026-03-15T20:13:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Rising-edge Chat alert fires exactly once when unassigned count crosses threshold upward
- Cooldown prevents alert storms (configurable, default 30 min)
- Sidebar badge uses threshold-based colors: green (1-2), amber (3-4), red (5+)
- Alert threshold and cooldown configurable from Settings SLA tab
- 11 new tests covering all edge cases (disabled, below, rising-edge, no-refire, reset, cooldown)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `00f8ee6` (test)
2. **Task 1 GREEN: Alert backend implementation** - `39e28a6` (feat)
3. **Task 2: Sidebar badge + settings config** - `af3fcaa` (feat)

## Files Created/Modified
- `apps/core/migrations/0007_seed_alert_config.py` - Seeds 4 SystemConfig keys for alerts
- `apps/emails/services/chat_notifier.py` - Added notify_unassigned_alert() with Cards v2 payload
- `apps/emails/management/commands/run_scheduler.py` - Added _check_unassigned_alert() + heartbeat integration
- `apps/emails/tests/test_unassigned_alerts.py` - 11 tests for alert system
- `templates/emails/thread_list.html` - Threshold-based badge coloring
- `templates/emails/settings.html` - Alert config section in SLA tab
- `apps/emails/views.py` - settings_alert_save view + context vars
- `apps/emails/urls.py` - settings/alerts/ endpoint

## Decisions Made
- Alert fires regardless of quiet hours -- triage queue alerts are proactive, not suppressible
- Rising-edge flag stored in SystemConfig for persistence across scheduler restarts
- Badge thresholds hardcoded in template (matching default SystemConfig value of 5)
- Alert config placed in SLA tab alongside other operational settings

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Alert system ready; bulk actions and corrections digest plans can proceed independently
- SystemConfig keys seeded by migration, no manual setup needed

---
*Phase: 04-alerts-bulk-actions*
*Completed: 2026-03-16*
