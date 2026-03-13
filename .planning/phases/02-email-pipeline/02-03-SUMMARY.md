---
phase: 02-email-pipeline
plan: 03
subsystem: infra
tags: [apscheduler, google-chat, webhook, docker-compose, health-check, scheduler]

# Dependency graph
requires:
  - phase: 02-email-pipeline/02
    provides: "Pipeline orchestrator (process_poll_cycle, retry_failed_emails)"
provides:
  - "ChatNotifier service for Google Chat webhook notifications"
  - "APScheduler management command (poll, retry, heartbeat)"
  - "Health endpoint with scheduler liveness monitoring"
  - "Docker Compose scheduler service with secrets volume"
affects: [03-dashboard, 04-sla, deployment]

# Tech tracking
tech-stack:
  added: [APScheduler 3.x, httpx]
  patterns: [management-command-scheduler, heartbeat-liveness, secrets-volume-mount]

key-files:
  created:
    - apps/emails/services/chat_notifier.py
    - apps/emails/management/commands/run_scheduler.py
    - apps/emails/management/__init__.py
    - apps/emails/management/commands/__init__.py
    - apps/emails/tests/test_chat_notifier.py
    - apps/emails/tests/test_scheduler.py
  modified:
    - apps/core/views.py
    - apps/core/tests/test_health.py
    - docker-compose.yml
    - .env.example

key-decisions:
  - "Heartbeat not_started (no heartbeat) = healthy, stale (old heartbeat) = degraded -- avoids false degraded before scheduler starts"
  - "ChatNotifier takes Django Email model instances (not dicts) for cleaner interface"

patterns-established:
  - "Management command scheduler: APScheduler BlockingScheduler in separate Docker container"
  - "Heartbeat liveness: SystemConfig key with ISO timestamp, health endpoint checks freshness"
  - "Secrets volume: ./secrets:/app/secrets:ro mounted on both web and scheduler"

requirements-completed: [PROC-06, INFR-08, INFR-11]

# Metrics
duration: 4min
completed: 2026-03-11
---

# Phase 2 Plan 3: Chat Notifier, Scheduler, and Docker Compose Summary

**Google Chat webhook notifier with quiet hours, APScheduler management command (poll/retry/heartbeat), health endpoint liveness, and Docker Compose dual-service config**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T10:16:45Z
- **Completed:** 2026-03-11T10:20:45Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Ported ChatNotifier from v1 with Cards v2 format, quiet hours via SystemConfig, and batch email summaries
- Created APScheduler management command with 3 jobs: poll (5min), retry (30min), heartbeat (1min)
- Updated health endpoint with scheduler liveness status based on heartbeat freshness
- Docker Compose now runs web + scheduler as separate containers from same image with secrets volume

## Task Commits

Each task was committed atomically:

1. **Task 1: Chat notifier + scheduler + health** (TDD)
   - `4506055` (test) - failing tests for chat notifier, scheduler, health
   - `7d4bb72` (feat) - chat notifier, scheduler command, health heartbeat
2. **Task 2: Docker Compose + secrets** - `8bcaf1d` (feat)

## Files Created/Modified
- `apps/emails/services/chat_notifier.py` - Google Chat Cards v2 webhook with quiet hours
- `apps/emails/management/commands/run_scheduler.py` - APScheduler BlockingScheduler with poll, retry, heartbeat
- `apps/emails/management/__init__.py` - Package init
- `apps/emails/management/commands/__init__.py` - Package init
- `apps/core/views.py` - Health endpoint with scheduler heartbeat check
- `apps/core/tests/test_health.py` - Updated with scheduler status tests
- `apps/emails/tests/test_chat_notifier.py` - 8 tests for ChatNotifier
- `apps/emails/tests/test_scheduler.py` - 3 tests for scheduler command
- `docker-compose.yml` - Added scheduler service and secrets volume
- `.env.example` - Phase 2 env vars (API keys, service account path)

## Decisions Made
- No heartbeat = "not_started" status (healthy), old heartbeat = "stale" (degraded). This avoids the web container always reporting degraded before the scheduler starts.
- ChatNotifier takes Django Email model instances directly instead of dicts, for cleaner integration with the pipeline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed APScheduler in venv**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** APScheduler was in requirements.txt but not installed in local .venv
- **Fix:** `pip install APScheduler>=3.10,<4.0`
- **Verification:** Tests pass, command loads

**2. [Rule 1 - Bug] Health endpoint status logic for missing heartbeat**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Plan specified missing heartbeat = "stale" = degraded, but this would make web-only container always report 503 (no scheduler running in tests or before scheduler starts)
- **Fix:** Changed missing heartbeat to "not_started" (healthy), only existing-but-old heartbeat = "stale" (degraded)
- **Files modified:** apps/core/views.py
- **Verification:** All 8 health tests pass including new scheduler-specific tests

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required

The plan specifies three external services that will need configuration before production use:
1. **Google Service Account key** -- place `service-account.json` in `secrets/` directory on VM
2. **Anthropic API key** -- set `ANTHROPIC_API_KEY` in `.env`
3. **Google Chat webhook URL** -- set `GOOGLE_CHAT_WEBHOOK_URL` in `.env`

These are the same credentials used in v1 and are already available.

## Next Phase Readiness
- Phase 2 Email Pipeline is now COMPLETE: all 3 plans executed
- Email polling, AI triage, spam filter, dead letter retry, Chat notifications, and scheduler are all in place
- 95 tests pass across the full suite
- Ready for Phase 3 (Dashboard) or deployment

---
*Phase: 02-email-pipeline*
*Completed: 2026-03-11*
