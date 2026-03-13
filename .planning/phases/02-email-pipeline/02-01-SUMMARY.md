---
phase: 02-email-pipeline
plan: 01
subsystem: database, api
tags: [django, models, migrations, spam-filter, pdf, pypdf, dataclass, systemconfig]

requires:
  - phase: 01-foundation
    provides: SoftDeleteModel, TimestampedModel, Email model, Django project structure
provides:
  - Email model with 14 new fields (AI metadata, dead letter tracking, processing status)
  - SystemConfig model with typed get() and get_all_by_category()
  - Seeded feature flags, polling config, quiet/business hours defaults
  - EmailMessage and TriageResult DTOs (dataclasses)
  - Spam regex pre-filter (13 patterns from v1)
  - PDF text extractor using pypdf (BSD license)
  - StateManager for circuit breaker and EOD dedup
  - Phase 2 dependencies in requirements.txt
  - v2 triage prompt (adapted from v1)
affects: [02-02, 02-03, 03-gmail-integration, 04-notifications]

tech-stack:
  added: [anthropic, google-api-python-client, google-auth, tenacity, APScheduler, httpx, pypdf, pytz]
  patterns: [SystemConfig typed key-value store, service module pattern under apps/emails/services/, DTO dataclasses]

key-files:
  created:
    - apps/core/admin.py
    - apps/core/migrations/0001_initial.py
    - apps/core/migrations/0002_seed_default_config.py
    - apps/emails/migrations/0002_email_ai_input_tokens_email_ai_model_used_and_more.py
    - apps/emails/services/__init__.py
    - apps/emails/services/dtos.py
    - apps/emails/services/spam_filter.py
    - apps/emails/services/pdf_extractor.py
    - apps/emails/services/state.py
    - apps/core/tests/test_system_config.py
    - apps/emails/tests/test_spam_filter.py
    - apps/emails/tests/test_pdf_extractor.py
    - prompts/triage_prompt_v2.txt
  modified:
    - apps/emails/models.py
    - apps/core/models.py
    - apps/emails/admin.py
    - requirements.txt

key-decisions:
  - "SystemConfig inherits TimestampedModel only (not SoftDeleteModel) -- config entries are simple key-values"
  - "Spam filter returns category='Spam' (not 'General Inquiry' like v1) for clearer identification"
  - "TriageResult DTO drops v1's raw_response/success/error fields -- those are v1 internal concerns"
  - "StateManager omits SLA alert tracking (deferred to Phase 4)"

patterns-established:
  - "Service modules live under apps/emails/services/ with no Django imports (pure Python)"
  - "SystemConfig.get(key, default) pattern for typed runtime config"
  - "DTOs are plain dataclasses -- no Django model coupling for pipeline data"

requirements-completed: [PROC-03, PROC-04, INFR-08, INFR-11]

duration: 6min
completed: 2026-03-11
---

# Phase 2 Plan 1: Pipeline Foundation Summary

**Email model with AI/retry fields, SystemConfig typed store with seeded feature flags, spam filter (13 patterns), PDF extractor (pypdf), and StateManager ported from v1**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-11T09:57:13Z
- **Completed:** 2026-03-11T10:03:09Z
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments
- Email model extended with 14 new fields: processing status, retry count, AI metadata, spam tracking
- SystemConfig model with typed casting (str/int/bool/float/json) and data migration seeding 10 default entries
- Four service modules ported from v1: DTOs, spam filter, PDF extractor, state manager
- 26 new tests (13 SystemConfig + 8 spam filter + 5 PDF extractor), all 59 total tests pass

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Email model migration + SystemConfig model + admin + deps + prompt**
   - `536bc8b` (test: failing tests for SystemConfig and Email model fields)
   - `3f60b3b` (feat: Email model fields + SystemConfig + admin + deps + triage prompt)

2. **Task 2: DTO module + spam filter + PDF extractor + state manager**
   - `0c9d432` (test: failing tests for spam filter and PDF extractor)
   - `8ba4225` (feat: DTOs, spam filter, PDF extractor, state manager)

## Files Created/Modified

- `apps/core/models.py` - Added SystemConfig model with typed_value, get(), get_all_by_category()
- `apps/core/admin.py` - SystemConfig admin with list_filter on category/value_type
- `apps/core/migrations/0001_initial.py` - SystemConfig table creation
- `apps/core/migrations/0002_seed_default_config.py` - Seeds 10 config entries (feature flags, polling, hours)
- `apps/emails/models.py` - 14 new fields: processing_status, retry_count, AI metadata, spam tracking
- `apps/emails/admin.py` - Added processing_status to list_display, is_spam to list_filter
- `apps/emails/migrations/0002_*.py` - Schema migration for 14 new Email fields
- `apps/emails/services/dtos.py` - EmailMessage and TriageResult dataclasses (ported from v1)
- `apps/emails/services/spam_filter.py` - 13 regex patterns, returns TriageResult on match
- `apps/emails/services/pdf_extractor.py` - pypdf-based extraction (3 pages, 1000 chars, 5MB limit)
- `apps/emails/services/state.py` - Circuit breaker + EOD dedup (SLA tracking deferred)
- `requirements.txt` - Added anthropic, google-api-python-client, tenacity, pypdf, etc.
- `prompts/triage_prompt_v2.txt` - v1 prompt adapted: stripped Sheet/ticket references, kept injection defense

## Decisions Made

- SystemConfig inherits TimestampedModel only (not SoftDeleteModel) -- config is simple key-values, no soft-delete needed
- Spam filter category changed from v1's "General Inquiry" to "Spam" for clearer identification in the database
- TriageResult DTO simplified from v1: dropped raw_response, success, and error fields (v1-specific concerns)
- StateManager SLA alert tracking omitted -- will be added in Phase 4 when SLA module is built

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_get_all_by_category collision with seed data**
- **Found during:** Task 1 (SystemConfig tests)
- **Issue:** Test created entries in "feature_flags" category which collided with seeded data migration entries
- **Fix:** Changed test to use "test_category" instead of "feature_flags"
- **Files modified:** apps/core/tests/test_system_config.py
- **Verification:** All 13 SystemConfig tests pass
- **Committed in:** 3f60b3b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test isolation fix. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Models, DTOs, and utility services are ready for Plan 02-02 (Gmail poller + AI processor)
- All dependencies installed, triage prompt adapted for v2
- StateManager ready for circuit breaker integration in the poll loop

## Self-Check: PASSED

All 16 files verified present. All 4 commit hashes verified in git log.

---
*Phase: 02-email-pipeline*
*Completed: 2026-03-11*
