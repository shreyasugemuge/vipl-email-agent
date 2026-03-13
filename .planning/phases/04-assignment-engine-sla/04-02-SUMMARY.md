---
phase: 04-assignment-engine-sla
plan: 02
subsystem: ui, settings, sla-display
tags: [django, htmx, tailwind, sla, settings, claim, ai-suggestion, sortablejs]

requires:
  - phase: 04-assignment-engine-sla
    provides: AssignmentRule, SLAConfig, CategoryVisibility models, claim_email service, assign_email service
  - phase: 03-dashboard
    provides: Email card list, detail panel, base.html sidebar, template tags

provides:
  - Admin settings page with tabbed layout (assignment rules, category visibility, SLA config)
  - SLA countdown template filters (sla_color, sla_countdown, sla_ack_countdown)
  - Claim email endpoint with category visibility enforcement
  - AI suggestion accept/reject endpoints
  - Updated email cards with SLA countdown and AI suggestion badges
  - Updated detail panel with SLA bar, AI suggestion bar, claim button

affects: [04-03-breach-alerting, 05-reporting]

tech-stack:
  added: [sortablejs]
  patterns: [tab-switching-js, htmx-partial-swap-crud, sla-color-coding]

key-files:
  created:
    - templates/emails/settings.html
    - templates/emails/_assignment_rules.html
    - templates/emails/_category_visibility.html
    - templates/emails/_sla_config.html
    - apps/emails/tests/test_settings_views.py
  modified:
    - apps/emails/templatetags/email_tags.py
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/_email_card.html
    - templates/emails/_email_detail.html
    - templates/base.html

key-decisions:
  - "Settings link in sidebar now points to /emails/settings/ (app settings page) instead of Django admin"
  - "Rules partial re-rendered per category after CRUD operations for minimal HTMX swap"
  - "Sortable.js CDN for drag-to-reorder assignment rules (no build step)"
  - "SLA color filter returns Tailwind color family string with animate-pulse for breached state"
  - "Claim button shows on cards only when email.category is in user_visible_categories list"

patterns-established:
  - "Tab switching via JS show/hide with active tab state in URL param"
  - "HTMX partial swap for inline CRUD: POST to save endpoint, swap parent container"
  - "SLA color coding: emerald > 2h, amber 1-2h, orange 30m-1h, red < 30m, red+pulse breached"

requirements-completed: [ASGN-03, ASGN-04, INFR-09, INFR-10, SLA-02]

duration: 7min
completed: 2026-03-11
---

# Phase 4 Plan 02: Dashboard UI for Assignment Rules, SLA Config, and Claiming Summary

**Admin settings page with tabbed rules/visibility/SLA config, SLA countdown color-coded display on cards and detail panel, claim buttons, and AI suggestion accept/dismiss UI**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-11T17:59:12Z
- **Completed:** 2026-03-11T18:06:22Z
- **Tasks:** 2
- **Files modified:** 11
- **Tests added:** 31 (187 -> 218 total)

## Accomplishments
- Settings page at /emails/settings/ with three tabs: assignment rules (drag-reorder), category visibility (checkbox matrix), SLA config (editable matrix)
- SLA countdown display on email cards and detail panel with color-coded thresholds (green/amber/orange/red/flashing)
- Claim button on cards and detail panel for users with category visibility
- AI suggestion badge on cards, full suggestion bar with Accept/Dismiss buttons in detail panel
- 31 new tests covering settings CRUD, claim endpoint, AI suggestion endpoints, and SLA template filters

## Task Commits

Each task was committed atomically:

1. **Task 1: SLA template filters, claim/AI endpoints, card/detail updates** - `7f11db6` (feat)
2. **Task 2: Admin settings page with rules, visibility, SLA config + tests** - `04afd48` (feat)

## Files Created/Modified
- `apps/emails/templatetags/email_tags.py` - Added sla_color, sla_countdown, sla_ack_countdown filters
- `apps/emails/views.py` - Added claim_email_view, accept/reject_ai_suggestion, settings_view, settings save views
- `apps/emails/urls.py` - Added 7 new URL patterns (claim, accept-ai, reject-ai, settings, settings save endpoints)
- `templates/emails/_email_card.html` - SLA countdown display, AI suggestion badge, Claim button
- `templates/emails/_email_detail.html` - SLA bar, AI suggestion bar with Accept/Dismiss, Claim button for members
- `templates/emails/settings.html` - Full settings page with tabbed layout and Sortable.js
- `templates/emails/_assignment_rules.html` - Partial for per-category rule list with add/remove/reorder
- `templates/emails/_category_visibility.html` - Partial for team member x category checkbox matrix
- `templates/emails/_sla_config.html` - Partial for priority x category SLA hours table
- `templates/base.html` - Sidebar Settings link now points to /emails/settings/
- `apps/emails/tests/test_settings_views.py` - 31 tests for all new views and template filters

## Decisions Made
- Settings sidebar link points to app settings page rather than Django admin -- more integrated UX
- SLA color filter returns Tailwind color family names (not full classes) for composable usage in templates
- Sortable.js loaded from CDN to maintain zero-build-step pattern established in Phase 3
- Claim button visibility determined by `user_visible_categories` context variable (pre-fetched in list view)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All assignment + SLA UI wired into dashboard, ready for Plan 03 (breach alerting)
- Settings page provides admin control over all assignment and SLA configuration
- All 218 tests pass with zero regressions

---
*Phase: 04-assignment-engine-sla*
*Completed: 2026-03-11*
