---
phase: 02-ai-confidence-auto-assign
plan: 04
subsystem: ai
tags: [distillation, haiku, correction-rules, prompt-injection, systemconfig]

requires:
  - phase: 02-01
    provides: "AssignmentFeedback model for recording corrections"
provides:
  - "distill_correction_rules() function for learning from user corrections"
  - "Correction rules injected into AI system prompt as <correction_rules> block"
  - "Scheduler integration: distillation runs before each poll cycle"
affects: [ai-processor, scheduler, prompt-tuning]

tech-stack:
  added: []
  patterns: ["Non-critical service pattern: try/except swallow with logger.exception"]

key-files:
  created:
    - apps/emails/services/distillation.py
    - apps/emails/tests/test_distillation.py
  modified:
    - apps/emails/services/ai_processor.py
    - apps/emails/management/commands/run_scheduler.py

key-decisions:
  - "Store correction_rules as STR type in SystemConfig (not JSON) -- rules are plain text for prompt injection"
  - "Exclude 'No correction rules yet.' placeholder from prompt injection -- avoids wasting tokens on no-ops"
  - "Distillation wrapped in double try/except -- inner (_do_distill) and outer (distill_correction_rules) for defense-in-depth"

patterns-established:
  - "Non-critical service pattern: wrap in try/except, log exception, never crash pipeline"
  - "SystemConfig as AI memory store: key-value pairs for runtime prompt augmentation"

requirements-completed: [INTEL-08]

duration: 5min
completed: 2026-03-15
---

# Phase 02 Plan 04: Feedback Distillation Summary

**Distillation service that converts user assignment corrections into compact Haiku-generated rules injected into AI system prompt**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T13:50:26Z
- **Completed:** 2026-03-15T13:55:16Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Distillation service queries rejected/reassigned AssignmentFeedback, calls Haiku to produce compact rules
- Rules stored in SystemConfig and injected into AI system prompt as `<correction_rules>` block
- Scheduler calls distillation before each poll cycle, with failure isolation
- 13 tests covering no-op, feedback, staleness, failure handling, formatting, storage, and prompt injection

## Task Commits

Each task was committed atomically:

1. **Task 1: Create distillation service and tests** - `9de6125` (feat -- pre-existing in repo)
2. **Task 2: Inject correction rules into AI prompt + scheduler** - `ac985ca` (feat)

_Note: Task 1 files were found already committed in a prior commit (accidentally bundled). Task 2 added prompt injection and scheduler wiring._

## Files Created/Modified
- `apps/emails/services/distillation.py` - Distillation service: queries feedback, calls Haiku, stores rules
- `apps/emails/tests/test_distillation.py` - 13 tests covering all distillation + prompt injection behavior
- `apps/emails/services/ai_processor.py` - Loads correction_rules from SystemConfig into system prompt
- `apps/emails/management/commands/run_scheduler.py` - Calls distill_correction_rules() before each poll cycle

## Decisions Made
- Store correction_rules as STR (not JSON) since rules are plain text for prompt injection
- Exclude "No correction rules yet." placeholder from injection to avoid wasting tokens
- Double try/except defense-in-depth: inner distillation logic + outer wrapper both catch exceptions
- Import SystemConfig inside try/except in ai_processor (matches existing _get_team_workload pattern)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed User.create_user() requires username parameter**
- **Found during:** Task 1 (test fixture)
- **Issue:** Custom User model requires username arg, plan's fixture omitted it
- **Fix:** Added username parameter to test fixture create_user calls
- **Files modified:** apps/emails/tests/test_distillation.py
- **Verification:** All tests pass
- **Committed in:** 9de6125 (pre-existing)

**2. [Rule 1 - Bug] Fixed deprecated timezone.utc usage**
- **Found during:** Task 1 (distillation.py)
- **Issue:** `django.utils.timezone.utc` deprecated in Django 5.0+, triggers RemovedInDjango50Warning
- **Fix:** Used `datetime.timezone.utc` (stdlib) instead
- **Files modified:** apps/emails/services/distillation.py
- **Committed in:** 9de6125 (pre-existing)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for test correctness and deprecation compliance. No scope creep.

## Issues Encountered
- Task 1 files were already committed in a prior unrelated commit (9de6125). No re-commit needed; verified content matches plan spec.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Correction feedback loop complete: user corrections -> distillation -> prompt injection -> better AI suggestions
- System learns from each rejected/reassigned assignment automatically
- No blockers for subsequent phases

---
*Phase: 02-ai-confidence-auto-assign*
*Completed: 2026-03-15*
