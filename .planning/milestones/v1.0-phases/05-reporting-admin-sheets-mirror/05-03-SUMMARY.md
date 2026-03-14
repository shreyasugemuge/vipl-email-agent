---
phase: 05-reporting-admin-sheets-mirror
plan: 03
subsystem: infra
tags: [google-sheets, sync, scheduler, apscheduler]

requires:
  - phase: 05-reporting-admin-sheets-mirror
    provides: "EOD reporter + scheduler integration (05-02)"
provides:
  - "SheetsSyncService: read-only mirror of completed emails to Google Sheets"
  - "Scheduler job: sheets_sync every 5 minutes (conditional on GOOGLE_SHEET_ID)"
affects: [06-migration-cutover]

tech-stack:
  added: []
  patterns: ["fire-and-forget sync with SystemConfig last-synced tracking"]

key-files:
  created:
    - apps/emails/services/sheets_sync.py
    - apps/emails/tests/test_sheets_sync.py
  modified:
    - apps/emails/management/commands/run_scheduler.py

key-decisions:
  - "Message ID as 10th column in Sheet for programmatic row matching"
  - "Conditional scheduler registration: sheets_sync only added when GOOGLE_SHEET_ID env var is set"

patterns-established:
  - "Fire-and-forget sync: outer try/except logs warning, never raises"
  - "Row index cache: message_id -> row_number built from column J on first sync"

requirements-completed: [INFR-04]

duration: 4min
completed: 2026-03-12
---

# Phase 5 Plan 3: Google Sheets Mirror Summary

**SheetsSyncService syncs completed emails to "v2 Mirror" Sheet tab every 5 minutes with fire-and-forget error handling**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-12T11:20:40Z
- **Completed:** 2026-03-12T11:24:29Z
- **Tasks:** 2 (Task 1 TDD: RED/GREEN)
- **Files modified:** 3

## Accomplishments
- SheetsSyncService appends new emails and updates changed rows in "v2 Mirror" tab
- Auto-creates tab with header row on first sync
- Sheets API errors are fire-and-forget (logged, never crash scheduler or pipeline)
- Scheduler integration: sheets_sync job every 5 minutes, only when GOOGLE_SHEET_ID is configured
- 8 tests covering tab creation, new/updated/mixed sync, error handling, row format, last_synced

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `988de2b` (test)
2. **Task 1 GREEN: SheetsSyncService implementation** - `f3fa0a9` (feat)
3. **Task 2: Scheduler integration** - `86055be` (feat)

## Files Created/Modified
- `apps/emails/services/sheets_sync.py` - SheetsSyncService with sync_changed_emails, _ensure_tab_exists, _build_row_index, _email_to_row, _append_rows, _batch_update_rows
- `apps/emails/tests/test_sheets_sync.py` - 8 tests with mocked Sheets API
- `apps/emails/management/commands/run_scheduler.py` - Added _sheets_sync_job + scheduler registration

## Decisions Made
- Message ID stored as 10th (last) column in Sheet for programmatic row lookup; humans can ignore it
- Conditional scheduler registration: sheets_sync job only added when GOOGLE_SHEET_ID env var is set, skipped silently otherwise
- Used datetime.timezone.utc instead of deprecated django.utils.timezone.utc

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Django deprecation warning for timezone.utc**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Using `django.utils.timezone.utc` triggers RemovedInDjango50Warning
- **Fix:** Imported `datetime.timezone` and used `dt_tz.utc` instead
- **Files modified:** apps/emails/services/sheets_sync.py
- **Verification:** Tests pass with no deprecation warnings

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor fix for forward compatibility. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. GOOGLE_SHEET_ID env var was already configured in production .env.

## Next Phase Readiness
- Phase 5 complete (all 3 plans: settings UI, EOD reporter, Sheets mirror)
- Ready for Phase 6: Migration + Cutover
- 257 tests passing across full suite

---
*Phase: 05-reporting-admin-sheets-mirror*
*Completed: 2026-03-12*
