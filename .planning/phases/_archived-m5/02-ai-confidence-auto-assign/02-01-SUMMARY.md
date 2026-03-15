---
phase: 02-ai-confidence-auto-assign
plan: 01
subsystem: ai, pipeline
tags: [claude, triage, confidence, template-filters]

# Dependency graph
requires:
  - phase: 01-models-migrations
    provides: "Email.ai_confidence and Thread.ai_confidence model fields"
provides:
  - "TriageResult.confidence field in DTO"
  - "TRIAGE_TOOL schema with confidence enum (HIGH/MEDIUM/LOW)"
  - "Pipeline saves confidence to Email.ai_confidence"
  - "Thread preview copies ai_confidence from latest triaged email"
  - "confidence_base and confidence_tooltip template filters"
affects: [02-ai-confidence-auto-assign, dashboard-templates]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Confidence tier pattern: discrete HIGH/MEDIUM/LOW enum, not float"

key-files:
  created:
    - apps/emails/tests/test_ai_confidence.py
  modified:
    - apps/emails/services/dtos.py
    - apps/emails/services/ai_processor.py
    - apps/emails/services/pipeline.py
    - apps/emails/services/assignment.py
    - apps/emails/templatetags/email_tags.py

key-decisions:
  - "Confidence as empty string default (not None) -- consistent with existing DTO pattern"
  - "confidence added to TRIAGE_TOOL required fields -- Claude must always provide it"

patterns-established:
  - "Confidence color mapping: HIGH=emerald, MEDIUM=amber, LOW=red"

requirements-completed: [INTEL-01, INTEL-02]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 2 Plan 01: AI Confidence Tier Summary

**Discrete HIGH/MEDIUM/LOW confidence tier added to Claude triage output, persisted to Email and Thread models, with colored dot template filters**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T13:44:46Z
- **Completed:** 2026-03-15T13:50:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- TriageResult DTO extended with `confidence: str = ""` field
- TRIAGE_TOOL Claude schema includes confidence as required enum (HIGH/MEDIUM/LOW)
- Pipeline saves confidence through full chain: Claude response -> TriageResult -> Email.ai_confidence -> Thread.ai_confidence
- Template filters (confidence_base, confidence_tooltip) ready for dashboard display
- 19 tests covering DTO, schema, parsing, pipeline save, thread preview, and template filters

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for confidence tier** - `ebbd963` (test)
2. **Task 1 GREEN: Implement confidence in DTO, schema, pipeline, assignment, filters** - `130fa92` (feat)

_Note: Task 2 (template filters + full suite verification) was covered by Task 1 GREEN commit since all work overlapped._

## Files Created/Modified
- `apps/emails/services/dtos.py` - Added `confidence: str = ""` to TriageResult
- `apps/emails/services/ai_processor.py` - Added confidence to TRIAGE_TOOL schema and _call_claude parsing
- `apps/emails/services/pipeline.py` - Maps `triage.confidence` to `Email.ai_confidence` in save_email_to_db
- `apps/emails/services/assignment.py` - Copies `ai_confidence` in update_thread_preview
- `apps/emails/templatetags/email_tags.py` - Added confidence_base and confidence_tooltip filters
- `apps/emails/tests/test_ai_confidence.py` - 19 tests for all confidence functionality

## Decisions Made
- Confidence field defaults to empty string (not None) -- consistent with existing DTO pattern and model CharField
- Confidence added to TRIAGE_TOOL required fields so Claude always provides it
- Followed existing color mapping pattern: emerald=good, amber=caution, red=warning

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Confidence tier fully wired from AI output to DB to template filters
- Ready for dashboard template integration (confidence dots on thread cards)
- Ready for auto-assign gating on confidence tier (plan 02-02)

---
*Phase: 02-ai-confidence-auto-assign*
*Completed: 2026-03-15*
