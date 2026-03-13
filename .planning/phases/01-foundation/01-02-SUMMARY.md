---
phase: 01-foundation
plan: 02
subsystem: infra
tags: [docker, nginx, gunicorn, ci-cd, github-actions, ssh-deploy]

# Dependency graph
requires:
  - phase: 01-foundation/01-01
    provides: Django project skeleton with settings, models, and health endpoint
provides:
  - Dockerfile with Python 3.11-slim, Gunicorn, collectstatic, non-root user
  - docker-compose.yml with single web service, host PostgreSQL access via host.docker.internal
  - Nginx reverse proxy config for triage.vidarbhainfotech.com
  - CI/CD pipeline -- test on PR to v2, SSH deploy to VM on version tag
  - .dockerignore excluding .git, .env, .planning, docs, __pycache__
affects: [02-email-pipeline, 06-migration-cutover]

# Tech tracking
tech-stack:
  added: [gunicorn, docker-compose, appleboy/ssh-action]
  patterns: [tag-triggered-deploy, single-container-with-host-db, nginx-reverse-proxy]

key-files:
  created: [Dockerfile, docker-compose.yml, nginx/triage.conf]
  modified: [.github/workflows/deploy.yml, .dockerignore]

key-decisions:
  - "Single container (Django+Gunicorn) with host PostgreSQL via extra_hosts"
  - "Port 8100 on host mapped to 8000 in container for Nginx proxy"
  - "Nginx listen 80 only -- certbot adds SSL post-deploy"
  - "SSH deploy via appleboy/ssh-action, same tag-trigger pattern as v1"

patterns-established:
  - "Docker build: collectstatic at build time with placeholder SECRET_KEY"
  - "Deploy flow: tag v*.*.* -> test -> SSH -> git checkout tag -> docker compose up"
  - "Health check: urllib-based in docker-compose healthcheck"

requirements-completed: [INFR-02, INFR-03]

# Metrics
duration: 3min
completed: 2026-03-09
---

# Phase 1 Plan 2: Deployment Infrastructure Summary

**Dockerfile, Docker Compose, Nginx reverse proxy, and GitHub Actions CI/CD for VM deployment via SSH**

## Performance

- **Duration:** 3 min (continuation after checkpoint approval)
- **Started:** 2026-03-09T08:00:00Z
- **Completed:** 2026-03-09T08:03:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint)
- **Files modified:** 5

## Accomplishments
- Dockerfile with Python 3.11-slim, non-root user, collectstatic at build, Gunicorn CMD
- docker-compose.yml with single web service, host PostgreSQL via host.docker.internal, port 8100:8000, healthcheck
- Nginx server block for triage.vidarbhainfotech.com proxying to container port
- CI/CD workflow: pytest on PR to v2, SSH deploy to VM on version tags
- .dockerignore excludes .git, .env, .planning, docs, __pycache__

## Task Commits

Each task was committed atomically:

1. **Task 1: Dockerfile, Docker Compose, Nginx config, CI/CD workflow** - `53d67d9` (feat)
2. **Task 2: Verify deployment configuration** - checkpoint approved, no commit needed

## Files Created/Modified
- `Dockerfile` - Python 3.11-slim container with Gunicorn, collectstatic, non-root user
- `docker-compose.yml` - Single web service with host PostgreSQL access and healthcheck
- `nginx/triage.conf` - Nginx reverse proxy for triage.vidarbhainfotech.com
- `.github/workflows/deploy.yml` - CI/CD: test on PR, SSH deploy on version tag
- `.dockerignore` - Excludes non-essential files from Docker build context

## Decisions Made
- Single container architecture: Django + Gunicorn in one container, PostgreSQL on host
- Port mapping 8100:8000 avoids conflicts with existing services on VM
- Nginx listens on port 80 only; certbot --nginx adds SSL after initial deploy
- SSH deploy with appleboy/ssh-action matches v1 deployment pattern

## Deviations from Plan

None - plan executed exactly as written.

## User Setup Required

External services require manual configuration before first deploy:

**VM PostgreSQL:**
- Create database `vipl_email_agent` and user `vipl_agent`
- Add pg_hba.conf entry for Docker subnet
- Ensure PostgreSQL listens on Docker bridge IP

**VM SSH Access:**
- GitHub repo secrets: `VM_HOST`, `VM_USER`, `VM_SSH_KEY`
- Clone repo at `/opt/vipl-email-agent` on VM, checkout v2 branch
- Create `.env` file with `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `APP_VERSION`

**DNS:**
- A record for `triage.vidarbhainfotech.com` pointing to VM IP (already configured per MEMORY.md)

## Issues Encountered
None

## Next Phase Readiness
- Deployment infrastructure complete; Phase 2 can begin building email pipeline features
- VM setup tasks must be completed before first actual deploy (documented in user_setup)
- DNS and SSL already configured per project memory

---
*Phase: 01-foundation*
*Completed: 2026-03-09*

## Self-Check: PASSED
- All 5 files verified present
- Commit 53d67d9 verified in git log
