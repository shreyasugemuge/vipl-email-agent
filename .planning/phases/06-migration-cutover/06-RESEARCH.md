# Phase 6: Migration + Cutover - Research

**Researched:** 2026-03-13
**Domain:** DevOps / deployment / infrastructure cleanup
**Confidence:** HIGH

## Summary

Phase 6 is an operational phase, not a feature-building phase. The goal is to deploy v2 to the VM for the first time via CI/CD, run a smoke test, switch to production mode, clean up v1 GCP resources, and fix the deploy.yml to use `sudo docker` (SSH user is not in the docker group). No historical data migration is needed -- v2 starts fresh.

The existing deploy.yml already has `docker compose build`, `up -d`, and `migrate --noinput` steps, but it is missing `sudo` prefixes on all docker commands (critical -- the SSH user `shreyas_vidarbhainfotech_com` is not in the docker group on the VM). The go-live announcement is a simple Chat webhook card using the existing ChatNotifier pattern.

**Primary recommendation:** Fix deploy.yml's `sudo` issue, push v2.0.0-rc1 tag, run smoke test checklist, switch to production mode, then clean up Artifact Registry images.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **No data migration** -- v2 starts with a clean database
- Production Google Sheet stays as-is (read-only archive of v1 history)
- Team members, SLA configs, and assignment rules seeded manually via v2 dashboard/admin after first deploy
- v1 is already stopped (Cloud Run 0 services) -- no parallel run needed
- Gap period emails (between v1 shutdown and v2 go-live) are ignored
- v2 starts polling from deployment time forward only
- Go-live progression: deploy with mode=off -> quick smoke test (~30 min) -> switch to mode=production
- Rollback plan: `docker compose down` -- emails accumulate unlabeled in Gmail (safe, not lost)
- **Artifact Registry** (utilities-vipl, vipl-repo, 741 MB): Delete all v1 Docker images
- **Secret Manager** (utilities-vipl): Keep all 3 secrets (canonical credential store)
- **v1 deploy workflow** (main branch): Leave as-is -- frozen, harmless
- First deploy triggered via CI/CD tag (v2.0.0-rc1), not manual SSH
- deploy.yml needs `migrate --noinput` after `up -d` (already present in current file)
- createsuperuser done manually via SSH after first deploy (one-time)
- Post a Google Chat card to the team space after mode=production

### Claude's Discretion
- Exact smoke test checklist steps
- Order of GCP cleanup operations
- Whether to add a health check wait between `up -d` and `migrate` in deploy.yml
- Chat announcement card design

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CUTV-01 | All historical email data migrated from production Sheet to PostgreSQL with zero data loss | **Redefined per CONTEXT.md**: No migration -- v2 starts fresh, Sheet stays as archive |
| CUTV-02 | Both inboxes cut over from v1 to v2 with v1 fully stopped | `set_mode production` enables both inboxes; v1 already stopped (Cloud Run 0 services) |
| CUTV-03 | Cloud Run service decommissioned (no cost, no running instances) | Already done (0 services). Cleanup = delete Artifact Registry images (741 MB) |
| CUTV-04 | CI/CD pipeline targets VM only -- no Cloud Run references remain | v2 deploy.yml already targets VM; only comment reference to remove. v1 workflow on main stays frozen. |
</phase_requirements>

## Standard Stack

No new libraries or dependencies needed. This phase uses existing infrastructure exclusively.

### Existing Tools Used
| Tool | Purpose | Notes |
|------|---------|-------|
| `appleboy/ssh-action@v1` | CI/CD SSH deploy to VM | Already in deploy.yml |
| `gcloud` CLI | Artifact Registry cleanup | Local machine or Cloud Shell |
| `docker compose` | Container orchestration on VM | Via `sudo` -- user not in docker group |
| `set_mode` management command | Mode switching (off/dev/production) | Already implemented |
| `ChatNotifier._post()` | Go-live announcement card | Existing webhook pattern |

## Architecture Patterns

### deploy.yml Fix Pattern

The current deploy.yml uses `docker compose` without `sudo`. The SSH user (`shreyas_vidarbhainfotech_com`) is NOT in the docker group. Every docker command in the SSH script block must be prefixed with `sudo`.

**Current (broken):**
```yaml
script: |
  cd /opt/vipl-email-agent
  git fetch --tags
  git checkout ${{ github.ref_name }}
  docker compose build --no-cache
  docker compose up -d
  docker compose exec -T web python manage.py migrate --noinput
```

**Fixed:**
```yaml
script: |
  cd /opt/vipl-email-agent
  git fetch --tags
  git checkout ${{ github.ref_name }}
  sudo docker compose build --no-cache
  sudo docker compose up -d
  sleep 5
  sudo docker compose exec -T web python manage.py migrate --noinput
  echo "Deployed ${{ github.ref_name }}"
```

The `sleep 5` between `up -d` and `migrate` gives the web container time to start (healthcheck is 30s interval, but the container needs a few seconds to boot Python/Gunicorn before exec works). This is a simple, reliable approach.

### Smoke Test Checklist Pattern

The go-live uses a staged mode progression with specific verification at each step:

```
1. Tag v2.0.0-rc1 -> CI/CD deploys to VM (mode defaults to "off")
2. SSH to VM -> createsuperuser
3. Verify: curl https://triage.vidarbhainfotech.com/health/ (should return JSON)
4. Verify: login to dashboard at https://triage.vidarbhainfotech.com/
5. Run: sudo docker compose exec -T web python manage.py test_pipeline --with-ai
6. Switch to dev: sudo docker compose exec -T web python manage.py set_mode dev
7. Run: sudo docker compose exec -T web python manage.py run_scheduler --once
8. Verify: check /emails/ shows the polled email(s)
9. Switch to production: sudo docker compose exec -T web python manage.py set_mode production
10. Verify: wait for one scheduler poll cycle (~5 min), check new emails appear
11. Post go-live Chat announcement
```

### Go-Live Chat Card Pattern

Use `ChatNotifier._post()` directly or a one-off management command. Simplest approach: a small script or inline `docker compose exec` call.

```python
# Can be run as a Django shell one-liner via docker exec
from apps.emails.services.chat_notifier import ChatNotifier
import os
notifier = ChatNotifier(os.environ["GOOGLE_CHAT_WEBHOOK_URL"])
notifier._post({
    "cardsV2": [{
        "cardId": "go-live",
        "card": {
            "header": {
                "title": "VIPL Email Agent v2 is Live",
                "subtitle": "All inboxes now monitored by v2",
            },
            "sections": [{
                "widgets": [
                    {"decoratedText": {"topLabel": "Dashboard", "text": "triage.vidarbhainfotech.com"}},
                    {"buttonList": {"buttons": [{"text": "Open Dashboard", "onClick": {"openLink": {"url": "https://triage.vidarbhainfotech.com"}}}]}}
                ]
            }]
        }
    }]
})
```

### Artifact Registry Cleanup Pattern

```bash
# List all images first (verify before delete)
gcloud artifacts docker images list \
  asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo \
  --include-tags --project=utilities-vipl

# Delete the entire repository (cleaner than per-image deletion)
gcloud artifacts repositories delete vipl-repo \
  --project=utilities-vipl \
  --location=asia-south1 \
  --quiet
```

Deleting the repository is cleaner than deleting individual images -- it removes all images, tags, and the repo itself. This is safe because v2 builds images locally on the VM (no Artifact Registry needed).

### Anti-Patterns to Avoid

- **Running docker without sudo on VM:** Will fail with permission denied. Every docker/docker-compose command needs `sudo`.
- **Manual SSH deploy for first deploy:** User explicitly wants CI/CD tag-triggered deploy, not manual `git pull && docker compose up`.
- **Attempting v1 rollback:** Rollback is `docker compose down`, not resurrecting Cloud Run. v1 is dead.
- **Migrating historical data:** Explicitly scoped out. No migration script needed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Go-live announcement | New management command | Inline Django shell via `docker exec` | One-time operation, not worth a permanent command |
| Health check wait | Complex readiness probe in CI | `sleep 5` after `up -d` | Docker healthcheck exists; sleep is sufficient for exec |
| Artifact cleanup | Custom script | `gcloud artifacts repositories delete` | Single command, one-time operation |

## Common Pitfalls

### Pitfall 1: docker without sudo
**What goes wrong:** SSH user not in docker group; all docker commands fail with permission denied.
**How to avoid:** Prefix every docker/docker-compose command with `sudo` in deploy.yml and manual SSH commands.

### Pitfall 2: migrate before container is ready
**What goes wrong:** `docker compose exec` fails if the web container hasn't started its entrypoint yet.
**How to avoid:** Add `sleep 5` between `up -d` and `exec ... migrate`. The Docker healthcheck (30s interval, 3 retries) is for the scheduler dependency, but a brief sleep is sufficient for exec.

### Pitfall 3: Forgetting to create superuser
**What goes wrong:** Dashboard login is impossible without a user. `createsuperuser` is interactive and cannot be in CI/CD.
**How to avoid:** Document as explicit manual step after first deploy. Use `sudo docker compose exec -T web python manage.py createsuperuser` via SSH.
**Note:** `-T` disables pseudo-TTY but createsuperuser needs interactive input. Use `--noinput` with `DJANGO_SUPERUSER_*` env vars, or drop `-T` when running manually.

### Pitfall 4: .env file not on VM
**What goes wrong:** Containers start but crash because .env is missing or incomplete.
**What we know:** `/opt/vipl-email-agent/.env` should already exist from earlier setup (per CLAUDE.md: ".env ready"). Verify before tagging.
**How to avoid:** SSH to VM and verify .env exists with all required vars before pushing the tag.

### Pitfall 5: secrets/ directory not on VM
**What goes wrong:** Gmail poller and Sheets sync fail because service-account.json is missing.
**How to avoid:** Verify `/opt/vipl-email-agent/secrets/service-account.json` exists on VM before tagging.

### Pitfall 6: Taiga Docker network not accessible
**What goes wrong:** web/scheduler containers can't reach PostgreSQL because they're not on the taiga network.
**What we know:** docker-compose.yml references external network `taiga-docker_taiga`. This network must exist (created by Taiga's docker-compose).
**How to avoid:** Verify with `sudo docker network ls | grep taiga` on VM before tagging.

### Pitfall 7: Port 8100 conflict
**What goes wrong:** Another service already using port 8100 on the VM.
**How to avoid:** Check `sudo ss -tlnp | grep 8100` or `sudo docker ps` before deploying.

## Code Examples

### deploy.yml with sudo fix
```yaml
# Source: existing deploy.yml + sudo fix for VM SSH user
- name: Deploy via SSH
  uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.VM_HOST }}
    username: ${{ secrets.VM_USER }}
    key: ${{ secrets.VM_SSH_KEY }}
    script: |
      cd /opt/vipl-email-agent
      git fetch --tags
      git checkout ${{ github.ref_name }}
      sudo docker compose build --no-cache
      sudo docker compose up -d
      sleep 5
      sudo docker compose exec -T web python manage.py migrate --noinput
      echo "Deployed ${{ github.ref_name }}"
```

### createsuperuser via SSH (manual, one-time)
```bash
# SSH to VM first
ssh -i ~/.ssh/google_compute_engine shreyas_vidarbhainfotech_com@35.207.237.47

# Option A: Interactive (prompts for password)
cd /opt/vipl-email-agent
sudo docker compose exec web python manage.py createsuperuser

# Option B: Non-interactive (set env vars in command)
sudo docker compose exec \
  -e DJANGO_SUPERUSER_USERNAME=shreyas \
  -e DJANGO_SUPERUSER_EMAIL=shreyas@vidarbhainfotech.com \
  -e DJANGO_SUPERUSER_PASSWORD=<password> \
  web python manage.py createsuperuser --noinput
```

### Go-live announcement via docker exec
```bash
sudo docker compose exec -T web python manage.py shell -c "
from apps.emails.services.chat_notifier import ChatNotifier
import os
n = ChatNotifier(os.environ.get('GOOGLE_CHAT_WEBHOOK_URL', ''))
n._post({'cardsV2': [{'cardId': 'go-live', 'card': {
    'header': {'title': 'VIPL Email Agent v2 is Live', 'subtitle': 'All inboxes now monitored by v2'},
    'sections': [{'widgets': [
        {'decoratedText': {'topLabel': 'Dashboard', 'text': 'triage.vidarbhainfotech.com'}},
        {'buttonList': {'buttons': [{'text': 'Open Dashboard', 'onClick': {'openLink': {'url': 'https://triage.vidarbhainfotech.com'}}}]}}
    ]}]
}}]})
print('Go-live announcement sent!')
"
```

## State of the Art

This phase uses no new technology. Everything is existing, proven infrastructure.

| Component | Current State | Action Needed |
|-----------|---------------|---------------|
| deploy.yml (v2) | Has docker commands without sudo | Add `sudo` prefix to all docker commands |
| deploy.yml (v1/main) | Frozen, triggers only on PR to main (test only) | Leave as-is |
| Cloud Run | 0 services, already decommissioned | No action needed |
| Artifact Registry | 741 MB of v1 images in `vipl-repo` | Delete repository |
| Secret Manager | 3 secrets (anthropic-api-key, chat-webhook-url, sa-key) | Keep (canonical store) |
| VM deploy dir | `/opt/vipl-email-agent/` cloned, v2 branch, .env ready | Verify .env + secrets before tagging |
| Nginx | triage.vidarbhainfotech.com -> :8100, SSL configured | No changes needed |
| PostgreSQL | `vipl_email_agent` DB exists on Taiga's PG 12.3 | Verify DB + user exist |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + Django test client |
| Config file | `pytest.ini` |
| Quick run command | `pytest --tb=short -q` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CUTV-01 | Sheet stays as archive, v2 starts fresh | manual-only | N/A -- verify Sheet untouched, DB empty at startup | N/A |
| CUTV-02 | Both inboxes monitored by v2 | smoke | `sudo docker compose exec -T web python manage.py set_mode production` then verify poll cycle | N/A (manual smoke) |
| CUTV-03 | Cloud Run decommissioned | manual-only | `gcloud run services list --project=utilities-vipl` should return empty | N/A |
| CUTV-04 | CI/CD targets VM only, no Cloud Run refs | unit | `grep -r "cloud.run\|cloudrun\|gcloud run" .github/workflows/deploy.yml` should find nothing | N/A |

**Note:** This phase is primarily operational. Verification is through manual smoke tests and infrastructure checks, not automated test suites. The existing 257 tests validate the application itself; this phase validates deployment and operations.

### Sampling Rate
- **Per task commit:** `pytest --tb=short -q` (ensure no regressions from deploy.yml changes)
- **Per wave merge:** Full smoke test checklist on VM
- **Phase gate:** All smoke tests pass, both inboxes processing, Artifact Registry deleted

### Wave 0 Gaps
None -- no new test files needed. This phase modifies deploy.yml and performs operational tasks.

## Pre-Deploy Verification Checklist

Before pushing v2.0.0-rc1 tag, verify on VM via SSH:

```bash
# 1. .env file exists and has required vars
ssh shreyas_vidarbhainfotech_com@35.207.237.47 \
  "ls -la /opt/vipl-email-agent/.env"

# 2. Service account key exists
ssh shreyas_vidarbhainfotech_com@35.207.237.47 \
  "ls -la /opt/vipl-email-agent/secrets/service-account.json"

# 3. Taiga Docker network exists
ssh shreyas_vidarbhainfotech_com@35.207.237.47 \
  "sudo docker network ls | grep taiga"

# 4. PostgreSQL DB and user exist
ssh shreyas_vidarbhainfotech_com@35.207.237.47 \
  "sudo docker exec taiga-docker-taiga-db-1 psql -U postgres -c '\\l' | grep vipl"

# 5. Port 8100 is free
ssh shreyas_vidarbhainfotech_com@35.207.237.47 \
  "sudo ss -tlnp | grep 8100"

# 6. Git repo is on v2 branch
ssh shreyas_vidarbhainfotech_com@35.207.237.47 \
  "cd /opt/vipl-email-agent && git branch --show-current"
```

## Open Questions

1. **createsuperuser password management**
   - What we know: Must be done manually after first deploy
   - What's unclear: Whether to use interactive mode or pass via env vars
   - Recommendation: Use non-interactive with env vars passed inline (not stored), then immediately change password via dashboard

2. **Comment-only Cloud Run reference in deploy.yml**
   - What we know: Line 8 has `# Replaces v1 Cloud Run deployment with VM SSH deploy.`
   - What's unclear: Whether CUTV-04 "no Cloud Run references" includes comments
   - Recommendation: Remove the comment to be thorough -- replace with clean header comment

## Sources

### Primary (HIGH confidence)
- Existing codebase: `deploy.yml`, `docker-compose.yml`, `run_scheduler.py`, `set_mode.py`, `chat_notifier.py`
- `CLAUDE.md` project instructions (VM details, SSH access, docker group issue)
- `MEMORY.md` (SSH user not in docker group, must use `sudo docker`)
- `06-CONTEXT.md` (all locked decisions)

### Secondary (MEDIUM confidence)
- `appleboy/ssh-action@v1` behavior (well-known GitHub Action, standard SSH execution)
- `gcloud artifacts repositories delete` command (standard gcloud CLI)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing tools
- Architecture: HIGH -- deploy.yml fix is straightforward, patterns are established
- Pitfalls: HIGH -- known from MEMORY.md (sudo docker) and project experience

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable -- no fast-moving dependencies)
