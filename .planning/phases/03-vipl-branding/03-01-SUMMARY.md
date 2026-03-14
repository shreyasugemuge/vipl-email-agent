---
phase: 03-vipl-branding
plan: 01
subsystem: ui
tags: [tailwind-css-v4, django-static, branding, favicon, logo]

requires:
  - phase: 02-settings-spam-whitelist
    provides: Settings templates and whitelist tab that need brand color updates

provides:
  - VIPL logo assets committed to static/img/ (vipl-icon.jpg, vipl-logo-full.jpg, vipl-logo-white.jpg, favicon.ico)
  - Brand plum/purple @theme palette replacing indigo across all templates
  - Page titles in "VIPL Triage | Page" format
  - Copyright footer on dashboard
  - 7 automated branding tests

affects: [04-chat-polish]

tech-stack:
  added: []
  patterns:
    - "primary-* Tailwind classes for brand colors (resolved via @theme tokens)"
    - "{% load static %} + {% static 'img/...' %} for logo references"

key-files:
  created:
    - static/img/vipl-icon.jpg
    - static/img/vipl-logo-full.jpg
    - static/img/vipl-logo-white.jpg
    - static/img/favicon.ico
    - apps/emails/tests/test_branding.py
  modified:
    - templates/base.html
    - templates/registration/login.html
    - templates/registration/dev_login.html
    - templates/emails/email_list.html
    - templates/emails/activity_log.html
    - templates/emails/settings.html
    - templates/emails/_email_detail.html
    - templates/emails/_config_editor.html
    - templates/emails/_whitelist_tab.html
    - templates/emails/_inboxes_tab.html
    - templates/emails/_sla_config.html
    - templates/emails/_category_visibility.html
    - templates/emails/_webhooks_tab.html
    - templates/emails/_email_card.html
    - templates/emails/_assign_dropdown.html
    - templates/emails/_assignment_rules.html
    - templates/emails/_activity_feed.html

key-decisions:
  - "Brand palette: plum 600=#a83362 derived from logo Vi mark, 50-900 scale built around it"
  - "favicon.ico generated via macOS sips (zero dependencies, 32x32 ICO format)"
  - "Login/dev_login standalone @theme blocks updated independently (they don't extend base.html)"
  - "Dev inspector (inspect.html) left as-is -- no indigo/violet classes, separate dark theme"

patterns-established:
  - "Use primary-* classes for all brand/accent colors, never hardcode indigo/violet"
  - "Standalone templates (login, dev_login) need their own @theme block with full palette"

requirements-completed: [R3.1, R3.2, R3.3, R3.4]

duration: 10min
completed: 2026-03-14
---

# Phase 3 Plan 1: VIPL Branding Summary

**Plum/purple brand palette from VIPL logo applied across all 17 templates, with Vi mark sidebar logo, full logo on login, favicon, page titles, and copyright footer**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-14T16:53:11Z
- **Completed:** 2026-03-14T17:03:36Z
- **Tasks:** 2
- **Files modified:** 22 (5 created + 17 modified)

## Accomplishments
- Copied 3 VIPL logo variants to static/img/ and generated 32x32 favicon.ico
- Replaced indigo @theme palette with plum/purple (600=#a83362) across base.html, login.html, dev_login.html
- Updated all 17 template files: zero indigo/violet occurrences remain (except dev inspector)
- Added sidebar Vi mark logo, login page full logo, favicon link, page titles, copyright footer
- Created 7 automated branding tests covering assets, logos, color replacement, titles, and favicon
- Full test suite: 334 tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Copy logo assets, generate favicon, create branding test scaffold** - `49a103a` (feat)
2. **Task 2: Apply brand palette and update all templates** - `ef29655` (feat)

## Files Created/Modified
- `static/img/vipl-icon.jpg` - Vi mark logo for sidebar and favicon source
- `static/img/vipl-logo-full.jpg` - Full logo with company name for login page
- `static/img/vipl-logo-white.jpg` - White variant for dark backgrounds
- `static/img/favicon.ico` - 32x32 browser tab icon
- `apps/emails/tests/test_branding.py` - 7 branding verification tests
- `templates/base.html` - Brand @theme palette, sidebar logo, favicon, footer
- `templates/registration/login.html` - Full logo, plum gradient, brand classes
- `templates/registration/dev_login.html` - Brand classes, plum gradient
- `templates/emails/*.html` (14 files) - All indigo/violet replaced with primary-*

## Decisions Made
- Brand palette uses #a83362 as primary-600 (derived from logo plum, accessible on white)
- favicon.ico generated via macOS sips (zero-dependency, native ICO format)
- Login/dev_login get independent @theme blocks (standalone templates)
- Dev inspector left as-is (no indigo/violet classes, separate dark UI)
- Gradient backgrounds updated from indigo-tinted (#1a1635/#251d4d) to plum-tinted (#1a0f1a/#2d1525)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All branding complete for templates
- Phase 4 (Chat Polish) can proceed -- chat_notifier.py branding is in plan 03-02
- Visual verification recommended via `python manage.py runserver 8000` at triage.local

## Self-Check: PASSED

- All 6 created files exist on disk
- Both task commits (49a103a, ef29655) found in git log
- 334 tests pass, 7 branding tests green
- Zero indigo/violet in templates (verified by grep)

---
*Phase: 03-vipl-branding*
*Completed: 2026-03-14*
