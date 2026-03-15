---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: milestone
status: executing
stopped_at: Completed 02-04-PLAN.md
last_updated: "2026-03-15T13:55:16.000Z"
last_activity: 2026-03-15 -- Completed 02-04 (feedback distillation + prompt injection)
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
  percent: 30
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.
**Current focus:** Milestone v2.5.0 -- Intelligence + UX

## Current Position

Phase: 4 of 6 (Read/Unread Tracking)
Plan: 1 of 2 (04-01 complete)
Status: Executing
Last activity: 2026-03-15 -- Completed 02-04 (feedback distillation + prompt injection)

Progress: [███░░░░░░░] 30%

## Accumulated Context

### Decisions

- Override flags (category_overridden, priority_overridden) in Phase 1 models -- pipeline would overwrite user edits without them
- Auto-assign deploys disabled (threshold=100), enabled after confidence calibration
- Zero new Python deps, Chart.js 4.x CDN only for reports
- One migration batch for all new models to avoid migration chain conflicts
- Discrete confidence tiers (HIGH/MEDIUM/LOW) not float percentages -- Claude's self-reported confidence is uncalibrated
- Sender reputation (not ML) for spam learning -- volume too low for statistical approaches
- Confidence defaults to empty string (not None) -- consistent with existing DTO CharField pattern
- Confidence added to TRIAGE_TOOL required fields -- Claude must always provide it
- Spam badge annotation correct as-is -- SoftDeleteManager consistently filters in list + detail
- FIX-01 avatar: works correctly, URL expiry is Google-side signed URL TTL
- FIX-02 dedup: works correctly with proper window boundary and same-inbox exclusion
- No ThreadReadState row = treated as read -- avoids wall-of-bold on first deploy
- Unread detection via Exists subquery: is_read=False OR read_at < last_message_at
- All users can mark spam (not admin-only) -- SpamFeedback records user identity
- Pipeline block order: whitelist -> block check -> spam filter -> AI (cheapest path)
- Auto-block threshold: spam_ratio > 0.8 AND total_count >= 3
- Inline auto-assign uses optimistic locking (assigned_to__isnull=True filter) -- same pattern as batch
- Auto-assign threshold default "100" (disabled) -- no confidence tier matches string "100"
- Correction rules stored as STR in SystemConfig (not JSON) -- plain text for prompt injection
- Distillation wrapped in double try/except for defense-in-depth -- never crashes pipeline

### Pending Todos

10 todos captured in `.planning/todos/pending/` -- all scoped into this milestone.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-15T13:55:16.000Z
Stopped at: Completed 02-04-PLAN.md
Next: Continue with remaining plans
