# Phase 1: Foundation - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Django project running on the existing VM with PostgreSQL, user authentication, team management, Docker Compose deployment, CI/CD pipeline, and health endpoint. This is the skeleton everything else builds on — no email processing, no dashboard views, no assignment logic yet.

</domain>

<decisions>
## Implementation Decisions

### VM & Deployment
- VM already runs Taiga in Docker Compose behind Nginx with SSL (Let's Encrypt)
- Add Nginx server block for `triage.vidarbhainfotech.com` proxying to the email agent container
- Use same PostgreSQL instance as Taiga (separate database, not separate container)
- Single Docker container: Django + Gunicorn (no separate frontend container — HTMX is server-rendered)
- APScheduler runs as a separate Django management command process within the same container

### CI/CD
- Tag-based deployment via GitHub Actions (same pattern as v1)
- Claude's discretion on SSH deploy vs Docker registry pull — pick what's simplest and most reliable

### Database Schema
- Store full email body + headers + metadata (not just summary)
- Attachment metadata only (filename, size, MIME type) — actual files stay in Gmail
- Soft delete for all records (never lose data)
- Connect to host PostgreSQL via Docker network (same instance as Taiga, separate `vipl_email_agent` database)

### Auth & Roles
- Simple password auth (Django's built-in auth system)
- Two roles: Admin and Team Member
- Visibility is configurable per-user: admin can set whether a team member sees all emails or only their assigned ones
- Team member creation starts via Django admin panel (dashboard UI for this is a later phase)

### Project Structure
- Same repo, v2 branch — will merge to main once v2 is proven in production
- Claude's discretion on whether v1 agent modules live inside a Django app or as a separate importable package — pick the cleanest architecture
- v1 code on main branch stays untouched until cutover (Phase 6)

### Claude's Discretion
- CI/CD mechanism (SSH deploy vs registry pull)
- Agent module placement (Django app vs standalone package)
- Attachment handling approach (metadata-only for now)
- Django project layout (single app vs multi-app)
- Gunicorn worker count and configuration

</decisions>

<specifics>
## Specific Ideas

- Subdomain: `triage.vidarbhainfotech.com`
- Taiga is already on the VM in Docker Compose with Nginx + SSL — follow the same pattern
- PostgreSQL shared with Taiga (separate database) — no new DB infrastructure needed
- User explicitly said "not married to the stack" during init — Django + HTMX was research recommendation, confirmed

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent/gmail_poller.py`: Gmail API polling with domain-wide delegation — will be ported in Phase 2
- `agent/ai_processor.py`: Claude AI triage with two-tier model strategy — will be ported in Phase 2
- `agent/state.py`: StateManager pattern for ephemeral state — can inform Django equivalent
- `config.yaml`: Configuration structure — informs Django settings and dynamic config model
- `Dockerfile`: Python 3.11-slim base, non-root user — can be adapted for Django

### Established Patterns
- Service account authentication for Google APIs (domain-wide delegation)
- Three-tier config priority: env vars > database > config file
- Health endpoint returning JSON status

### Integration Points
- Django models will replace `SheetLogger` as the data access layer
- APScheduler integration via `django-apscheduler` or standalone management command
- Existing `.github/workflows/deploy.yml` needs rewriting for VM target (currently targets Cloud Run)
- Service account key must be available in the Docker container (Secret mount or env var)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-09*
