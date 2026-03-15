---
phase: 01-data-bug-fixes
plan: 01
subsystem: backend, ui
tags: [regex, xml-cleanup, htmx, oob-swap, data-migration, branding]

requires:
  - phase: none
    provides: existing ai_processor.py and views.py
provides:
  - XML-clean AI suggested assignee names at ingest
  - Data migration for existing XML-tainted records
  - OOB email count update on HTMX view switch
  - Consistent page titles across all pages
affects: [02-mobile-responsive]

tech-stack:
  added: []
  patterns: [OOB swap for out-of-band HTMX updates, regex XML tag stripping]

key-files:
  created:
    - apps/emails/migrations/0008_clean_xml_assignee.py
  modified:
    - apps/emails/services/ai_processor.py
    - apps/emails/views.py
    - templates/emails/email_list.html
    - templates/accounts/team.html
    - templates/emails/inspect.html
    - apps/emails/tests/test_ai_processor.py
    - apps/emails/tests/test_views.py
    - apps/emails/tests/test_branding.py

key-decisions:
  - "XML cleanup at ingest time in ai_processor.py, not display layer"
  - "OOB swap pattern for count updates avoids full page reload"

patterns-established:
  - "OOB swap: append hx-swap-oob elements to HTMX partial responses for out-of-band UI updates"
  - "_clean_xml_tags: reusable regex cleaner for Claude API response artifacts"

requirements-completed: [BUG-01, BUG-05, BUG-06]

duration: 5min
completed: 2026-03-15
---

# Phase 1 Plan 1: Data & Bug Fixes Summary

**XML tag cleanup at AI ingest + data migration, OOB email count on view switch, consistent page titles**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T06:45:18Z
- **Completed:** 2026-03-15T06:50:00Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- AI suggested assignee names cleaned of XML parameter tags at ingest time via _clean_xml_tags
- Data migration 0008 retroactively cleans existing records with XML markup
- Email count label updates via HTMX OOB swap when switching All/Unassigned/My Emails views
- All pages follow "VIPL Triage | {Page Name}" title pattern (team.html and inspect.html fixed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix AI XML markup cleanup** - `6a6089a` (test) + `597633b` (feat)
2. **Task 2: Fix email count OOB update** - `8b340d8` (test) + `d1ea2dc` (feat)
3. **Task 3: Fix page title consistency** - `7beff5a` (fix)

## Files Created/Modified
- `apps/emails/services/ai_processor.py` - Added _clean_xml_tags, updated _parse_suggested_assignee
- `apps/emails/migrations/0008_clean_xml_assignee.py` - Data migration to clean existing XML records
- `apps/emails/views.py` - OOB count span in HTMX response
- `templates/emails/email_list.html` - Added id="email-count" to count span
- `templates/accounts/team.html` - Added title block
- `templates/emails/inspect.html` - Updated title string
- `apps/emails/tests/test_ai_processor.py` - 8 new XML cleanup tests
- `apps/emails/tests/test_views.py` - 4 new OOB count tests
- `apps/emails/tests/test_branding.py` - 7 new title consistency tests

## Decisions Made
- XML cleanup at ingest time (ai_processor.py) per user decision, not at display layer
- OOB swap pattern chosen over full page reload for count updates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend data bugs fixed, ready for mobile responsive work (plan 01-02)
- All 399 tests passing, 0 regressions

---
*Phase: 01-data-bug-fixes*
*Completed: 2026-03-15*
