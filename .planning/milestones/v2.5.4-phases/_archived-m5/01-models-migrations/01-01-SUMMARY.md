---
phase: 01-models-migrations
plan: 01
subsystem: emails/models
tags: [models, migrations, v250]
dependency_graph:
  requires: []
  provides: [ThreadReadState, SpamFeedback, SenderReputation, AssignmentFeedback, Thread.ai_confidence, Email.ai_confidence, Thread.category_overridden, Thread.priority_overridden]
  affects: [apps/emails/models.py]
tech_stack:
  added: []
  patterns: [SoftDeleteModel+TimestampedModel inheritance, unique_together constraints, TextChoices enums]
key_files:
  created:
    - apps/emails/migrations/0015_v250_models.py
    - apps/emails/tests/test_v250_models.py
  modified:
    - apps/emails/models.py
decisions:
  - All 4 new models inherit SoftDeleteModel + TimestampedModel (consistent with existing patterns)
  - ai_confidence as CharField(max_length=10) for discrete tiers (HIGH/MEDIUM/LOW), not float
  - AssignmentFeedback.confidence_at_time is nullable CharField (captures tier at decision time)
metrics:
  duration: ~3 min
  completed: "2026-03-15"
  tests_added: 30
  tests_total: 586
---

# Phase 01 Plan 01: v2.5.0 Models + Migration Summary

All new database models and fields for v2.5.0 in a single migration batch -- foundation for AI confidence, spam learning, read/unread tracking, and editable attributes.

## What Was Done

### Task 1: Add new models, fields, and ActivityLog actions

Added to `apps/emails/models.py`:

**4 new models:**
- `ThreadReadState` -- per-user read/unread state with unique_together(thread, user)
- `SpamFeedback` -- records spam/not-spam corrections with original and user verdicts
- `SenderReputation` -- per-sender spam ratio tracking with auto-block flag and spam_ratio property
- `AssignmentFeedback` -- records user feedback on AI assignment suggestions (accepted/rejected/reassigned/auto_assigned)

**5 new fields on existing models:**
- `Thread.category_overridden` (BooleanField, default=False)
- `Thread.priority_overridden` (BooleanField, default=False)
- `Thread.ai_confidence` (CharField, max_length=10, blank, default="")
- `Email.ai_confidence` (CharField, max_length=10, blank, default="")

**4 new ActivityLog actions:**
- SPAM_MARKED, SPAM_UNMARKED, PRIORITY_CHANGED, CATEGORY_CHANGED

### Task 2: Migration + tests

- Generated single migration `0015_v250_models.py` covering all changes
- Migration applied cleanly on SQLite
- Created 30 tests covering all new models, fields, constraints, and actions
- All 586 tests pass (30 new + 556 existing)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed User fixture missing username**
- **Found during:** Task 2 (test execution)
- **Issue:** `User.objects.create_user()` requires `username` positional argument in this project's custom User model
- **Fix:** Added `username="testuser_v250"` to the user fixture
- **Files modified:** apps/emails/tests/test_v250_models.py

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | 5e995bc | feat(01-01): add v2.5.0 models, fields, and ActivityLog actions |
| 2 | 8c89fb0 | test(01-01): add migration and tests for v2.5.0 models |

## Self-Check: PASSED
