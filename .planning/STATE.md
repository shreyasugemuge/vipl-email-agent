---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
stopped_at: Completed 06-01-PLAN.md
last_updated: "2026-03-13T17:59:18Z"
last_activity: 2026-03-13 -- Phase 6 Plan 01 complete (deploy.yml fix + CUTV-01 update)
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 18
  completed_plans: 17
  percent: 94
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-09)

**Core value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.
**Current focus:** Phase 6 in progress. Plan 01 (deploy.yml fix) complete, Plan 02 (first deploy) next.

## Current Position

Phase: 6 of 6 (Migration + Cutover) -- IN PROGRESS
Plan: 1 of 2 in current phase (1 complete)
Status: Plan 01 complete (deploy.yml fix + CUTV-01 update), Plan 02 next (first deploy)
Last activity: 2026-03-13 -- Phase 6 Plan 01 complete (deploy.yml fix + CUTV-01 update)

Progress: [#########-] 94%

## Performance Metrics

**Velocity:**
- Total plans completed: 15
- Average duration: 5.9 min
- Total execution time: ~1h 23m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 2 | 12 min | 6 min |
| 2. Email Pipeline | 3 | 17 min | 5.7 min |
| 3. Dashboard | 3 | 25 min | 8.3 min |
| 4. Assignment+SLA | 3/3 | 19 min | 6.3 min |
| 5. Reporting+Admin | 3/3 | 13 min | 4.3 min |

**Recent Trend:**
- Last 5 plans: 04-02 (7 min), 04-03 (4 min), 05-01 (3 min), 05-02 (6 min), 05-03 (4 min)
- Trend: Accelerating

*Updated after each plan completion*
| Phase 05 P03 | 4 | 2 tasks | 3 files |
| Phase 06 P01 | 1 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Stack: Django 5.2 LTS + HTMX + Tailwind CSS (single container, no React/Node)
- Auth: Simple password auth for v1 (Google OAuth deferred to v2)
- Scheduler: APScheduler as separate management command process (not inside Gunicorn)
- PDF: Swap PyMuPDF (AGPL) for pypdf (BSD)
- Python 3.13 venv required for Django 5.2 (system Python 3.9.6 too old)
- SQLite for local dev/tests, PostgreSQL via DATABASE_URL in production
- User model stub in Task 1 to set AUTH_USER_MODEL before first migration
- Single container (Django+Gunicorn) with host PostgreSQL via extra_hosts, port 8100:8000
- SSH deploy via appleboy/ssh-action, tag-triggered (same pattern as v1)
- Nginx listen 80 only, certbot adds SSL post-deploy
- SystemConfig inherits TimestampedModel only (not SoftDeleteModel)
- Spam filter category="Spam" (not "General Inquiry" like v1)
- TriageResult DTO simplified: dropped raw_response/success/error from v1
- StateManager SLA tracking deferred to Phase 4
- AIProcessor takes explicit api_key param (not env var) for testability
- Spam filter called by pipeline orchestrator, not AIProcessor (separation of concerns)
- Pipeline is the ONLY module with Django ORM imports (GmailPoller/AIProcessor Django-agnostic)
- Heartbeat not_started (no heartbeat) = healthy, stale (old heartbeat) = degraded
- ChatNotifier takes Django Email model instances (not dicts) for cleaner integration
- Tailwind v4 CDN + HTMX 2.0 CDN for zero build step (no Node.js)
- request.htmx partial detection for SPA-like behavior without SPA complexity
- Admin default=unassigned queue, member default=own emails
- ActivityLog model inherits TimestampedModel only (append-only, not soft-delete)
- nh3 (Rust-based) for HTML sanitization -- safe-by-default, explicit tag allowlist
- Fire-and-forget notifications: Chat and email never block or crash assignment
- 40/60 list-detail split layout per CONTEXT.md
- Service layer pattern: views call service functions, services handle ORM + notifications
- ai_suggested_assignee changed from CharField to JSONField (data migration for existing rows)
- Auto-assign uses optimistic locking (filter+update) to prevent race conditions
- SLA business hours: 8AM-8PM IST Mon-Sat, zoneinfo.ZoneInfo for timezone
- 24h dedup on SLA_BREACHED ActivityLog prevents re-bumping priority on every check cycle
- Personal breach alerts post to same Chat space (no per-user DM) -- true DMs need Chat API with user auth (deferred)
- CronTrigger for SLA summary (9,13,17 IST) separate from interval-based breach status updates
- TRIAGE_TOOL_SCHEMA suggested_assignee is now object {name, reason} (backward-compat parsing)
- Team workload injected into Claude prompt (~50 tokens per request)
- Settings sidebar link points to /emails/settings/ (app settings page) instead of Django admin
- Sortable.js CDN for drag-to-reorder assignment rules (zero build step)
- SLA color coding: emerald > 2h, amber 1-2h, orange 30m-1h, red < 30m, red+pulse breached
- [Phase 03]: Desktop-first responsive: default styles = desktop, responsive overrides for mobile
- [Phase 05]: Config editor saves per category group, not per individual key
- [Phase 05]: Bool configs use checkbox with unchecked=false convention
- [Phase 05]: Inboxes stored as comma-separated string in existing monitored_inboxes SystemConfig key
- [Phase 05]: Dual dedup: in-memory StateManager + persistent SystemConfig.last_eod_sent for cross-restart EOD dedup
- [Phase 05]: Message ID as 10th column in Sheet for programmatic row matching
- [Phase 05]: Conditional scheduler registration: sheets_sync only added when GOOGLE_SHEET_ID env var is set
- [Phase 06]: ROADMAP already had correct fresh-start wording for CUTV-01 -- only REQUIREMENTS.md needed update

### Pending Todos

None yet.

### Blockers/Concerns

- VM audit needed before Phase 1 deployment: Docker setup, Nginx config, PostgreSQL version, available resources
- Production Sheet data audit needed before migration (if migration phase added later)

## Session Continuity

Last session: 2026-03-13T17:59:18Z
Stopped at: Completed 06-01-PLAN.md
Resume file: .planning/phases/06-migration-cutover/06-01-SUMMARY.md
