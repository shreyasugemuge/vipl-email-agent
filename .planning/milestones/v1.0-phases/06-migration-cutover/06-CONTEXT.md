# Phase 6: Migration + Cutover - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy v2 to the VM for the first time, verify it works, switch inboxes to production mode, clean up v1 GCP resources, and update CI/CD to include auto-migration. No historical data migration — v2 starts fresh.

</domain>

<decisions>
## Implementation Decisions

### Historical Data Migration
- **No data migration** — v2 starts with a clean database
- Production Google Sheet stays as-is (read-only archive of v1 history)
- Team members, SLA configs, and assignment rules seeded manually via v2 dashboard/admin after first deploy
- Update CUTV-01 requirement to reflect: "Sheet preserved as archive, v2 starts fresh, no migration script"

### Cutover Sequence
- v1 is already stopped (Cloud Run 0 services) — no parallel run needed
- Gap period emails (between v1 shutdown and v2 go-live) are ignored — not picked up by v2
- v2 starts polling from deployment time forward only
- Go-live progression: deploy with mode=off → quick smoke test (~30 min: test_pipeline --with-ai, one --once cycle on info@) → switch to mode=production
- Rollback plan: `docker compose down` — emails accumulate unlabeled in Gmail (safe, not lost), fix and redeploy. No need to keep v1 ready.

### Infrastructure Cleanup
- **Artifact Registry** (utilities-vipl, vipl-repo, 741 MB): Delete all v1 Docker images
- **Secret Manager** (utilities-vipl): Keep all 3 secrets (anthropic-api-key, chat-webhook-url, sa-key) — they're the canonical credential store, VM's .env was populated from them
- **v1 deploy workflow** (main branch): Leave as-is — frozen, harmless, serves as historical reference

### First Deploy + CI/CD
- First deploy triggered via CI/CD tag (not manual SSH) — push v2.0.0-rc1 tag
- deploy.yml needs update: add `docker compose exec web python manage.py migrate --noinput` after `up -d`
- createsuperuser done manually via SSH after first deploy (one-time)
- Subsequent deploys auto-migrate via the updated pipeline
- Bump to v2.0.0 once stable (after rc1 soak)

### Go-Live Announcement
- Post a Google Chat card to the team space after mode=production: "VIPL Email Agent v2 is live. Dashboard: triage.vidarbhainfotech.com"
- No email announcement — Chat is sufficient

### Claude's Discretion
- Exact smoke test checklist steps
- Order of GCP cleanup operations
- Whether to add a health check wait between `up -d` and `migrate` in deploy.yml
- Chat announcement card design

</decisions>

<specifics>
## Specific Ideas

- First tag: v2.0.0-rc1 (release candidate, signals "might need fixes")
- Quick smoke test, not day-long soak — trust the 257 tests
- Mode progression: off → dev (one cycle) → production

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy.yml`: Already does SSH → git checkout → docker compose build → up. Just needs migrate step added.
- `set_mode` command: Ready for off → dev → production progression
- `test_pipeline --with-ai`: Validates Claude integration without polling real inboxes
- `run_scheduler --once`: Single poll cycle for smoke testing
- `ChatNotifier`: Can post the go-live announcement card

### Established Patterns
- Docker Compose: web + scheduler services from same image, port 8100
- Nginx on host: triage.vidarbhainfotech.com → :8100, SSL via Let's Encrypt (already configured)
- SSH user not in docker group — must use `sudo docker` in deploy scripts
- `appleboy/ssh-action@v1` for CI/CD SSH execution

### Integration Points
- deploy.yml script block needs `sudo docker compose exec` (not plain docker)
- VM deploy dir: `/opt/vipl-email-agent/`
- Taiga network: `taiga-docker_taiga` (172.18.0.0/16) — v2 Docker Compose joins this for DB access
- PostgreSQL: `taiga-docker-taiga-db-1` container, DB `vipl_email_agent`, user `vipl_agent`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-migration-cutover*
*Context gathered: 2026-03-13*
