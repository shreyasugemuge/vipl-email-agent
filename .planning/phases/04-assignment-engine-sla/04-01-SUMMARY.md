---
phase: 04-assignment-engine-sla
plan: 01
subsystem: assignment, sla, ai
tags: [django, sla, business-hours, auto-assign, claiming, workload, jsonfield]

requires:
  - phase: 03-dashboard
    provides: ActivityLog model, assignment service, email list/detail views
  - phase: 02-email-pipeline
    provides: Email model, pipeline orchestrator, AIProcessor, TriageResult DTO

provides:
  - AssignmentRule, SLAConfig, CategoryVisibility models with migrations
  - Business-hours SLA deadline calculator (8AM-8PM IST, Mon-Sat)
  - Auto-assign batch job with optimistic locking
  - Claim email service with category visibility validation
  - SLA breach detection query
  - AI workload-aware assignee suggestions with structured output
  - Pipeline integration for SLA deadline setting on every saved email

affects: [04-02-ui-settings, 04-03-breach-alerting, 05-reporting]

tech-stack:
  added: [zoneinfo]
  patterns: [optimistic-locking, business-hours-calculation, structured-ai-output]

key-files:
  created:
    - apps/emails/services/sla.py
    - apps/emails/tests/test_sla.py
    - apps/emails/tests/test_auto_assignment.py
    - apps/emails/tests/test_claiming.py
    - apps/emails/tests/test_ai_suggestion.py
    - apps/emails/migrations/0004_convert_ai_suggested_assignee_to_json.py
    - apps/emails/migrations/0005_email_sla_ack_deadline_email_sla_respond_deadline_and_more.py
  modified:
    - apps/emails/models.py
    - apps/emails/services/assignment.py
    - apps/emails/services/pipeline.py
    - apps/emails/services/ai_processor.py
    - apps/emails/services/dtos.py

key-decisions:
  - "ai_suggested_assignee changed from CharField to JSONField with data migration for existing rows"
  - "SLA business hours use zoneinfo.ZoneInfo instead of pytz for IST timezone"
  - "Auto-assign uses optimistic locking (filter+update) to prevent race conditions"
  - "Claim overwrites ActivityLog action from ASSIGNED to CLAIMED for accurate audit trail"
  - "Team workload injected into Claude prompt adds ~50 tokens per request (negligible cost)"
  - "TRIAGE_TOOL_SCHEMA suggested_assignee changed from string to object with name+reason"
  - "Pipeline resolves user_id from suggested name for richer AI suggestion storage"

patterns-established:
  - "Optimistic locking: filter(pk=X, condition).update() for concurrent-safe writes"
  - "Business hours calculation: snap-to-open + day-block subtraction (not minute-by-minute)"
  - "Structured AI output: tool schema objects with backward-compat parsing for plain strings"

requirements-completed: [ASGN-03, ASGN-04, SLA-02, INFR-09, INFR-10]

duration: 8min
completed: 2026-03-11
---

# Phase 4 Plan 01: Assignment Engine + SLA Foundation Summary

**AssignmentRule/SLAConfig/CategoryVisibility models, business-hours SLA calculator, auto-assign batch with optimistic locking, claim service, and AI workload-aware structured assignee suggestions**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-11T17:47:05Z
- **Completed:** 2026-03-11T17:55:45Z
- **Tasks:** 3
- **Files modified:** 12
- **Tests added:** 51 (136 -> 187 total)

## Accomplishments
- Three new models (AssignmentRule, SLAConfig, CategoryVisibility) with proper constraints and migrations
- Business-hours SLA calculator handling overnight crossing, weekend skipping, fractional hours
- Auto-assign batch job with optimistic locking to prevent race conditions on concurrent assignment
- Claim service with category visibility enforcement (admin bypass)
- AI triage prompt now includes team workload context for smarter assignee suggestions
- Structured assignee suggestion (name + reason) with backward compatibility for plain strings
- Pipeline sets SLA deadlines on every saved email, maps structured suggestions to JSONField

## Task Commits

Each task was committed atomically:

1. **Task 1: New models, Email SLA fields, ActivityLog actions, migration** - `a130b1a` (feat)
2. **Task 2: Auto-assign batch job, claim service, pipeline SLA integration** - `02d71ee` (feat)
3. **Task 3: AI processor workload-aware assignee suggestion** - `c5b6c8a` (feat)

## Files Created/Modified

- `apps/emails/models.py` - Added AssignmentRule, SLAConfig, CategoryVisibility models; SLA deadline fields on Email; JSONField for ai_suggested_assignee; 4 new ActivityLog actions
- `apps/emails/services/sla.py` - Business-hours SLA calculator, breach detection query, deadline setter
- `apps/emails/services/assignment.py` - Extended with auto_assign_batch() and claim_email()
- `apps/emails/services/pipeline.py` - SLA deadline integration, structured assignee mapping with user_id resolution
- `apps/emails/services/ai_processor.py` - Team workload injection, structured tool schema, backward-compat parsing
- `apps/emails/services/dtos.py` - Added suggested_assignee_detail dict field to TriageResult
- `apps/emails/migrations/0004_*.py` - Data migration converting CharField values to JSON
- `apps/emails/migrations/0005_*.py` - Schema migration for new models and fields
- `apps/emails/tests/test_sla.py` - 21 tests for SLA calculator, business hours, deadlines, breach detection
- `apps/emails/tests/test_auto_assignment.py` - 15 tests for models and auto-assign batch
- `apps/emails/tests/test_claiming.py` - 5 tests for claim service
- `apps/emails/tests/test_ai_suggestion.py` - 10 tests for workload, message building, suggestion parsing

## Decisions Made

- **CharField to JSONField migration**: Created a two-step migration (data conversion in 0004, schema change in 0005) to handle existing string values like "Aniket" in the ai_suggested_assignee column
- **zoneinfo over pytz**: Used zoneinfo.ZoneInfo for new IST timezone code (Python 3.9+ stdlib) while existing AIProcessor code still uses pytz
- **Optimistic locking pattern**: auto_assign_batch uses `Email.objects.filter(pk=email.pk, assigned_to__isnull=True).update()` to prevent overwriting manual assignments that happen between query and write
- **ActivityLog action override**: claim_email creates an ASSIGNED log via assign_email(), then updates it to CLAIMED, reusing the existing assignment infrastructure

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CharField to JSONField data migration**
- **Found during:** Task 1 (migration)
- **Issue:** Existing ai_suggested_assignee column contained plain strings ("Aniket", "Shreyas") which are not valid JSON, causing SQLite CHECK constraint failure
- **Fix:** Created separate data migration (0004) to convert strings to JSON objects before schema migration (0005)
- **Files modified:** apps/emails/migrations/0004_convert_ai_suggested_assignee_to_json.py
- **Verification:** Migration applies cleanly, all 187 tests pass

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Migration split was necessary for data integrity. No scope creep.

## Issues Encountered
None beyond the migration issue documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Models and services ready for Plan 02 (UI + settings page)
- SLA breach detection query ready for Plan 03 (breach alerting)
- Auto-assign batch function ready to be wired into APScheduler management command
- All 187 tests pass with zero regressions

---
*Phase: 04-assignment-engine-sla*
*Completed: 2026-03-11*
