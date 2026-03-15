---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: milestone
status: executing
stopped_at: Completed 04-02-PLAN.md
last_updated: "2026-03-15T13:59:49.984Z"
last_activity: 2026-03-15 -- Completed 04-02 (read/unread UI indicators)
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 13
  completed_plans: 8
  percent: 62
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.
**Current focus:** Milestone v2.5.0 -- Intelligence + UX

## Current Position

Phase: 4 of 6 (Read/Unread Tracking)
Plan: 2 of 2 (04-02 complete -- phase done)
Status: Executing
Last activity: 2026-03-15 -- Completed 04-02 (read/unread UI indicators)

Progress: [██████░░░░] 62%

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
- Replaced status=='new' with is_unread for bold/dot -- decouples visual state from thread status
- Mark as Unread outside admin guard -- all users can mark their own read state

### Pending Todos

10 todos captured in `.planning/todos/pending/` -- all scoped into this milestone.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-15T13:58:19Z
Stopped at: Completed 04-02-PLAN.md
Next: Continue with Phase 05 (Smart Notifications)
