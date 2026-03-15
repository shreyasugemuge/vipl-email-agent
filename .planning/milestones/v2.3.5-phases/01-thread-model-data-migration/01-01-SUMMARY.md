---
phase: 01-thread-model-data-migration
plan: 01
subsystem: database
tags: [django, models, migrations, threading, soft-delete]

requires:
  - phase: none
    provides: greenfield — first plan in milestone
provides:
  - Thread model with status, assignment, SLA, triage fields
  - Email.thread FK linking emails to threads
  - ActivityLog refactored with thread FK and new action types
  - Data wipe migration for clean slate
  - Thread admin registration with email inlines
affects: [01-02-assignment-migration, 02-pipeline-integration, 03-thread-ui]

tech-stack:
  added: []
  patterns: [thread-groups-emails, denormalized-preview-fields, thread-level-status]

key-files:
  created:
    - apps/emails/migrations/0008_thread_model.py
    - apps/emails/migrations/0009_wipe_existing_data.py
  modified:
    - apps/emails/models.py
    - apps/emails/admin.py
    - apps/emails/tests/test_models.py

key-decisions:
  - "ActivityLog.thread FK made nullable at DB level — application logic ensures it is always set, but nullable avoids migration issues with existing data"
  - "Thread.latest_message_at is both a denormalized field and a computed property — field for DB ordering, property for accurate queries"
  - "Thread.Status excludes REPLIED (email-level concern, not thread-level)"

patterns-established:
  - "Thread wraps emails: Email.thread FK, thread-level status/assignment/triage"
  - "Denormalized preview fields on Thread (last_message_at, last_sender) for list display performance"
  - "ActivityLog points to Thread (required) + Email (optional) for thread-level activity tracking"

requirements-completed: [THRD-01, THRD-02, THRD-05]

duration: 8min
completed: 2026-03-15
---

# Phase 1 Plan 1: Thread Model + Data Migration Summary

**Thread model grouping emails by gmail_thread_id with thread-level status, assignment, SLA, triage, and denormalized preview fields**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-15T05:35:37Z
- **Completed:** 2026-03-15T05:43:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Thread model with NEW/ACKNOWLEDGED/CLOSED status, assignment, SLA, and triage fields
- Email.thread FK links emails to threads; multiple emails per thread supported
- ActivityLog refactored: thread FK (nullable at DB, required in practice), email FK optional, 3 new action types
- Data wipe migration clears all existing Email/ActivityLog/AttachmentMetadata records (clean slate)
- ThreadAdmin registered with email inlines, message count display, filters and search
- 400 tests passing (26 new Thread model tests, 0 regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Thread model tests** - `37a7f5a` (test)
2. **Task 1 (GREEN): Thread model implementation** - `8c10833` (feat)
3. **Task 2: Data wipe migration + admin** - `2c5f43d` (feat)

_TDD: Task 1 used RED/GREEN flow with separate commits_

## Files Created/Modified
- `apps/emails/models.py` - Thread model, Email.thread FK, ActivityLog thread FK + new actions
- `apps/emails/migrations/0008_thread_model.py` - Thread creation, FK additions, ActivityLog changes
- `apps/emails/migrations/0009_wipe_existing_data.py` - Hard delete all existing records
- `apps/emails/admin.py` - ThreadAdmin with EmailInline, message count, filters
- `apps/emails/tests/test_models.py` - 19 Thread model tests + 3 ActivityLog thread tests

## Decisions Made
- ActivityLog.thread FK nullable at DB level to avoid migration conflicts with existing data; application logic ensures always set
- Thread.Status excludes REPLIED — reply tracking is email-level, not thread-level
- Thread ordering by `-last_message_at` (most recently active threads first)
- Data wipe uses hard delete (bypasses SoftDeleteModel) for true clean slate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ActivityLog.thread FK made nullable for migration compatibility**
- **Found during:** Task 1 (Thread model implementation)
- **Issue:** Non-nullable thread FK on ActivityLog requires a default for existing rows; makemigrations blocked
- **Fix:** Made thread FK nullable at DB level (null=True, blank=True). Data wipe migration clears all existing rows. Application logic will always set thread.
- **Files modified:** apps/emails/models.py
- **Verification:** makemigrations succeeds, migrate applies cleanly, all tests pass
- **Committed in:** 8c10833 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Pragmatic DB-level nullability to unblock migration. No functional impact — all new ActivityLog records will have thread set.

## Issues Encountered
- Python 3.13 venv needed to be created (no existing .venv in project). Created and installed dependencies before execution.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Thread model ready for Plan 01-02 (assignment migration: backfill threads from existing emails)
- Thread model ready for Phase 2 (pipeline integration: create/update threads on email receipt)
- All 400 tests passing, migrations apply cleanly

## Self-Check: PASSED

All 5 files verified present. All 3 commit hashes verified in git log.

---
*Phase: 01-thread-model-data-migration*
*Completed: 2026-03-15*
