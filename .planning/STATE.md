---
gsd_state_version: 1.0
milestone: v2.2
milestone_name: — Polish & Hardening
status: in-progress
stopped_at: Completed 04-01-PLAN.md (checkpoint:human-verify pending)
last_updated: "2026-03-14T17:32:57Z"
last_activity: 2026-03-14 — Phase 4 Plan 1 complete (urgency labels + Open buttons + pk in breach dicts)
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 6
  completed_plans: 6
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.
**Current focus:** v2.2 — Polish & Hardening

## Current Position

Phase: 4 of 4 — Chat Notification Polish
Plan: 1 of 1 (done)
Status: Phase 4 Plan 1 complete -- checkpoint:human-verify pending
Last activity: 2026-03-14 — Phase 4 Plan 1 complete (urgency labels + Open buttons + pk in breach dicts)

Progress: [##########] 100%

## Accumulated Context

### Decisions

- 4-phase structure: OAuth → Settings+Whitelist → Branding → Chat Polish
- OAuth first: team should use SSO from start; introduces only hard dependency (allauth migrations)
- Settings + Whitelist grouped: both touch settings template, avoids double-pass
- Branding after OAuth: both touch login.html, sequential avoids conflicts
- Chat last: pure service-layer, no dependencies
- Settings-based allauth APP config instead of DB SocialApp records
- Migration helper module outside migrations/ to avoid Django loader conflict
- Signal-based welcome toast with try/except for test resilience
- [Phase 01]: Dev-login role picker bypass for local development without OAuth
- [Phase 02-01]: Whitelist check in pipeline.py (not spam_filter.py) to keep spam_filter pure/Django-free
- [Phase 02-01]: Case-insensitive matching via __iexact for email and domain whitelist entries
- [Phase 02-01]: Hidden input fallback for checkbox (browser sends false when unchecked)
- [Phase 02-02]: Removed draft reply feature entirely -- not useful, cluttered detail view
- [Phase 02-02]: Whitelist sender un-spams all existing emails from that sender
- [Phase 02-02]: No delete confirmation on whitelist entries -- immediate delete for snappier UX
- [Phase 02-02]: OOB swap pattern for whitelist action (refreshes detail + all cards from sender)
- [Phase 03-02]: Cached tracker_url in ChatNotifier.__init__ to avoid duplicate SystemConfig.get calls
- [Phase 03-02]: VIPL_FOOTER_SECTION as module-level constant (never varies per instance)
- [Phase 03-02]: Defensive None fallback for SystemConfig.get returning None in tests/empty DB
- [Phase 03-01]: Brand palette: plum 600=#a83362 derived from logo, 50-900 scale
- [Phase 03-01]: favicon.ico via macOS sips (zero-dependency, native ICO)
- [Phase 03-01]: Dev inspector left as-is (separate dark theme, no indigo/violet)
- [Phase 04-01]: decoratedText.button for inline Open buttons (Cards v2 union field constraint)
- [Phase 04-01]: pk passed through data dicts, not ORM import in chat_notifier
- [Phase 04-01]: _sla_urgency_label as module-level function for cross-method reuse

### Pending Todos

None.

### Blockers/Concerns

None.

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01 | 01 | 7min | 3 | 21 |
| 02 | 01 | 4min | 2 | 7 |
| 02 | 02 | multi-session | 3 | 17 |
| 03 | 01 | 10min | 2 | 22 |
| 03 | 02 | 4min | 1 | 2 |
| 04 | 01 | 4min | 2 | 4 |

## Session Continuity

Last session: 2026-03-14T17:32:57Z
Stopped at: Completed 04-01-PLAN.md (checkpoint:human-verify pending)
Next: Validate card payloads in Google Chat Card Builder
