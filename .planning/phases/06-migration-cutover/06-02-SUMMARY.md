---
phase: 06-migration-cutover
plan: 02
subsystem: infra
tags: [deploy, go-live, cleanup, ci-cd, nginx]

requires:
  - phase: 06-migration-cutover
    plan: 01
    provides: "Production-ready deploy.yml"
provides:
  - "v2 deployed and running in production on taiga VM"
  - "Superuser created, dashboard accessible"
  - "CI/CD split: ci.yml (test) + deploy.yml (release-triggered deploy)"
  - "GitHub Release v2.0.0-rc1 created"
  - "v2 branch merged to main and deleted"
  - "CLAUDE.md and README.md fully rewritten for v2-as-production"
affects: []

tech-stack:
  added: []
  patterns:
    - "Deploy on GitHub Release published (not tag push) — intentional deploys"
    - "Nginx: listen on both 80+443 in same block when behind Cloudflare Flexible SSL"
    - "ALLOWED_HOSTS must include localhost for Docker healthcheck"
    - "docker compose restart does NOT reload env_file — need down+up"

key-files:
  created:
    - ".github/workflows/ci.yml"
  modified:
    - ".github/workflows/deploy.yml"
    - "CLAUDE.md"
    - "README.md"
    - "config/urls.py"
    - "apps/emails/tests/test_eod_reporter.py"

key-decisions:
  - "Deploy triggered by GitHub Release, not tag push — best practice for intentional deploys"
  - "CI and CD split into separate workflow files"
  - "Nginx config changed to match taiga pattern (listen 80+443) to work with Cloudflare Flexible SSL"
  - "Root URL / redirects to /emails/ dashboard"
  - "Time-dependent tests frozen to noon IST to avoid midnight boundary failures"

patterns-established:
  - "Release-triggered deploy: gh release create → CI tests → SSH deploy"

requirements-completed: [CUTV-01, CUTV-02, CUTV-03]

duration: 90min
completed: 2026-03-14
---

# Phase 6 Plan 02: Deploy, Go-Live, and Cleanup Summary

**v2 deployed to production VM, superuser created, smoke test passed, mode=production active, CI/CD restructured for release-triggered deploys, all docs updated**

## Performance

- **Duration:** ~90 min (manual operational work)
- **Started:** 2026-03-13
- **Completed:** 2026-03-14
- **Tasks:** 4 planned + 5 unplanned fixes
- **Files modified:** 6

## Accomplishments

### Planned Work
- Pre-deploy VM verification: .env, SA key, DB, network all confirmed
- v2 deployed via direct SSH (CI/CD tag had already been pushed)
- Superuser created: `admin` / `shreyas@vidarbhainfotech.com`
- Smoke test passed: `test_pipeline` (mocked), `test_pipeline --with-ai` (real Claude)
- Mode switched: off → dev → production
- Both inboxes monitored: info@ + sales@vidarbhainfotech.com
- Health endpoint returning: healthy, production, scheduler running

### Unplanned Fixes (discovered during deploy)
1. **ALLOWED_HOSTS**: Docker healthcheck hits `localhost:8000` inside container — added `localhost` to ALLOWED_HOSTS in .env
2. **docker compose restart**: Does NOT reload env_file — discovered the hard way, used `down && up -d`
3. **Nginx redirect loop**: Cloudflare Flexible SSL + Nginx HTTP→HTTPS redirect = infinite loop. Fixed by matching taiga's pattern (listen 80+443 in same block, no redirect)
4. **Root URL 404**: `/` returned 404 — added RedirectView to `/emails/`
5. **Time-dependent test**: EOD reporter test failed at midnight IST — froze time to noon IST

### Repo Cleanup
- CI/CD split: `ci.yml` (test on push/PR) + `deploy.yml` (deploy on release published)
- GitHub Release v2.0.0-rc1 created with full changelog
- v2 branch deleted (remote + local)
- CLAUDE.md fully rewritten — v2 is production, main is active branch
- README.md fully rewritten — current stack, CI/CD flow, development guide

## Task Commits

1. `a3800b3` — fix(tests): mock _is_quiet_hours in Chat notification tests
2. `3062bf8` — refactor: release-triggered deploy, split CI/CD, update docs for v2 launch
3. `006f734` — fix: add root URL redirect to /emails/ dashboard

## Files Created/Modified
- `.github/workflows/ci.yml` — New: CI tests on push/PR
- `.github/workflows/deploy.yml` — Rewritten: release-triggered deploy
- `CLAUDE.md` — Rewritten: v2 as production
- `README.md` — Rewritten: current stack and guide
- `config/urls.py` — Added root redirect
- `apps/emails/tests/test_eod_reporter.py` — Fixed time-dependent test

## Deviations from Plan

- Plan specified CI/CD tag-triggered deploy; changed to release-triggered (user's explicit request, best practice)
- Plan specified `gcloud artifacts repositories delete`; deferred (gcloud auth expired on VM)
- Plan specified go-live Chat announcement; deferred (can be done anytime)
- Nginx fix and root redirect were not in the plan (discovered during manual testing)

## Issues Encountered

- SA key on VM was initially a gcloud error message (356 bytes) — re-pulled from local machine via SCP
- gcloud auth expired on both local and VM — user re-authenticated locally
- Cloudflare Flexible SSL incompatible with HTTP→HTTPS redirect in Nginx

## Remaining Items (deferred, non-blocking)

- [ ] Delete Artifact Registry: `gcloud artifacts repositories delete vipl-repo --project=utilities-vipl --location=asia-south1 --quiet`
- [ ] Post go-live Chat announcement

## Next Phase Readiness

All phases complete. Milestone v1.0 ready for completion.

---
*Phase: 06-migration-cutover*
*Completed: 2026-03-14*
