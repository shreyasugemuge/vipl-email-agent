---
phase: 06-migration-cutover
plan: 01
subsystem: infra
tags: [ci-cd, docker, github-actions, deploy]

requires:
  - phase: 01-foundation
    provides: "Original deploy.yml with SSH deploy pattern"
provides:
  - "Production-ready deploy.yml with sudo, sleep, no Cloud Run refs"
  - "Updated CUTV-01 requirement wording (fresh start, no data migration)"
affects: [06-02]

tech-stack:
  added: []
  patterns: ["sudo prefix for docker commands on VMs where user lacks docker group"]

key-files:
  created: []
  modified:
    - ".github/workflows/deploy.yml"
    - ".planning/REQUIREMENTS.md"

key-decisions:
  - "ROADMAP already had correct fresh-start wording -- only REQUIREMENTS.md needed update"

patterns-established: []

requirements-completed: [CUTV-04, CUTV-01]

duration: 1min
completed: 2026-03-13
---

# Phase 6 Plan 01: Deploy.yml Fix + Requirement Update Summary

**Production-ready deploy.yml with sudo docker commands, sleep 5 before migrate, all Cloud Run references removed, and CUTV-01 updated to fresh-start wording**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-13T17:58:05Z
- **Completed:** 2026-03-13T17:59:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- deploy.yml now uses `sudo docker compose` on all 3 commands (SSH user not in docker group)
- Added `sleep 5` between `up -d` and `migrate` so container boots before exec
- Removed Cloud Run comment (CUTV-04 compliance)
- CUTV-01 requirement updated to reflect fresh-start decision (no data migration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix deploy.yml for production VM deploy** - `de40129` (fix)
2. **Task 2: Update CUTV-01 requirement and ROADMAP success criteria** - `624d666` (docs)

## Files Created/Modified
- `.github/workflows/deploy.yml` - Added sudo prefix, sleep 5, replaced Cloud Run comment
- `.planning/REQUIREMENTS.md` - Updated CUTV-01 wording to fresh-start

## Decisions Made
- ROADMAP.md already had the correct fresh-start wording for Phase 6 success criteria item 1, so only REQUIREMENTS.md was changed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- 2 pre-existing test failures (test_notify_assignment_payload, test_notify_eod_summary) unrelated to this plan's changes -- logged but not fixed per scope boundary rules

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- deploy.yml is production-ready for first deploy
- Ready for 06-02: pre-deploy verification, first deploy (v2.0.0-rc1), smoke test, go-live

---
*Phase: 06-migration-cutover*
*Completed: 2026-03-13*
