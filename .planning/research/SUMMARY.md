# Project Research Summary

**Project:** VIPL Email Agent v2
**Domain:** AI-powered shared inbox management (internal tool, single company)
**Researched:** 2026-03-09
**Confidence:** HIGH

## Executive Summary

VIPL Email Agent v2 is a full rebuild of a production email triage system for a 3-person team at a single company. The v1 system (Cloud Run + Google Sheets as database + Claude AI) works but hits the ceiling of what Sheets can support as a data store. v2 moves to PostgreSQL and adds a web dashboard for email assignment, SLA tracking, and team oversight. The key research finding is a **stack pivot**: the originally proposed FastAPI + React architecture is massive over-engineering for a 5-user internal CRUD dashboard. The recommended stack is **Django 5.2 LTS + HTMX + Tailwind CSS** -- a single Python application with no JavaScript build toolchain, no separate frontend container, and batteries included for auth, ORM, migrations, and admin.

The architecture is a Django monolith deployed as a single Docker container behind the VM's existing Nginx reverse proxy, connecting to the VM's existing PostgreSQL instance (shared with Taiga). HTMX provides dynamic interactivity (filtering, inline assignment, live updates) without React, Vue, or any JavaScript framework. This eliminates Node.js, npm, CORS, JWT tokens, and an entire frontend build pipeline. The v1 agent modules (gmail_poller, ai_processor, sla_monitor, etc.) are pure Python and port directly into Django as service modules with the ORM replacing SheetLogger.

The primary risks are: (1) data corruption during Sheets-to-PostgreSQL migration from type coercion issues in 6+ months of production Sheet data; (2) duplicate email processing if v1 and v2 poll Gmail simultaneously during cutover; (3) APScheduler running duplicate jobs when Gunicorn forks multiple workers. All three have well-documented prevention strategies. The migration should use a hard cutover (or inbox-by-inbox rollover), not a parallel-run of both pollers.

## Key Findings

### Recommended Stack

Django 5.2 LTS replaces FastAPI as the web framework, providing ORM, migrations, auth, admin, and templating out of the box. HTMX + Tailwind CSS replace React for the frontend -- served as static files with zero JavaScript build step. The existing VM infrastructure (PostgreSQL, Nginx) is shared rather than duplicated.

**Core technologies:**
- **Django 5.2 LTS**: Web framework -- includes everything needed (ORM, auth, admin, migrations, templates). LTS until April 2028.
- **HTMX 2.0 + Tailwind CSS 3.4**: Frontend interactivity -- dynamic table filtering, inline editing, partial page updates via HTML attributes. No npm, no bundler, 14KB gzipped.
- **PostgreSQL (existing on VM)**: Primary database -- replaces Google Sheets. Already running for Taiga, zero incremental cost.
- **django-allauth 65.14.x**: Google OAuth SSO -- domain restriction to @vidarbhainfotech.com with server-side enforcement.
- **APScheduler 3.10.x**: Background job scheduling -- proven in v1. Runs email polling, SLA checks, EOD reports in a separate management command process.
- **Gunicorn + Nginx (existing)**: HTTP serving -- Gunicorn serves Django, Nginx reverse-proxies and serves static files. Both battle-tested.

**What this eliminates:** Node.js, npm, React, Vite/webpack, CORS, JWT tokens, Redis, Celery, SQLAlchemy, Alembic, a separate frontend container.

See `.planning/research/STACK.md` for full rationale, version details, and alternatives considered.

### Expected Features

**Must have (table stakes):**
- Manual email assignment + assignment visibility
- Status tracking (New / Acknowledged / Replied / Closed)
- Email table dashboard with filters (status, assignee, priority, date)
- Unassigned queue as default manager view
- SLA deadlines + breach alerts (migrated from v1)
- Google OAuth SSO restricted to @vidarbhainfotech.com
- Notification on assignment (Chat + email)
- Activity log / audit trail

**Should have (differentiators):**
- AI auto-assignment (category-to-person rules + AI fallback)
- Gmail thread auto-detection (auto-update status when assignee replies)
- Two-tier SLA (acknowledgement + response deadlines)
- Escalation to manager on breach
- Workload view (open items per person)

**Defer:**
- AI feedback loop from corrections
- Response time analytics / charts
- WhatsApp/SMS for CRITICAL escalations
- Configurable inbox management UI
- Google Sheets read-only mirror (build last, keep simple)

**Anti-features (do NOT build):** Reply from dashboard, round-robin assignment, CSAT surveys, canned responses, real-time collaboration, complex workflow states, mobile native app, email threading/conversation view.

See `.planning/research/FEATURES.md` for competitor analysis, dependency graph, and anti-feature rationale.

### Architecture Approach

A Django monolith with two Django apps (`dashboard` for the web UI, `inbox` for data models and business logic services). Views serve HTML directly; HTMX handles dynamic interactions via partial template swaps. APScheduler runs in a separate process via a management command alongside Gunicorn. One Docker container. Nginx on the VM host routes requests and serves static files.

**Major components:**
1. **Django Views + HTMX Templates** -- serve the dashboard (email table, assignment controls, filters)
2. **Inbox Services** -- gmail_poller, ai_processor, assignment_engine, sla_monitor, eod_reporter, notification_hub (adapted from v1)
3. **Thread Monitor** -- new service that watches Gmail threads for assignee responses
4. **Sheets Sync** -- one-way DB-to-Sheets mirror (fire-and-forget, non-critical)
5. **APScheduler (management command)** -- orchestrates all background jobs in a single dedicated process

**Key patterns:** Service layer separation (thin views, business logic in services), HTMX partial templates (same view serves full page or partial based on `request.htmx`), label-after-persist safety (Gmail label applied only after DB write succeeds).

See `.planning/research/ARCHITECTURE.md` for full component diagram, data flows, database schema, and Docker Compose layout.

### Critical Pitfalls

1. **Sheets-to-PostgreSQL migration data loss** -- Production Sheet has 6+ months of format drift (dates, SLA deadlines, "ERROR" markers). Export real Sheet, validate every column variant, run parallel comparison before cutover.
2. **Duplicate email processing during cutover** -- Never run both v1 and v2 polling simultaneously. Use inbox-by-inbox rollover or hard cutover with v2 in shadow mode for validation.
3. **APScheduler duplicates with Gunicorn workers** -- Gunicorn forks workers; each gets its own scheduler. Run scheduler as a separate management command process, not inside the WSGI app.
4. **Google OAuth domain restriction bypass** -- The `hd` parameter is client-side only. Enforce server-side via django-allauth adapter (`pre_social_login` hook). Test with non-VIPL accounts.
5. **Docker Compose conflicts with Taiga** -- Audit the VM first (`docker ps`, port usage, RAM, PostgreSQL connections). Share existing Nginx and PostgreSQL. Set memory limits on v2 container.

See `.planning/research/PITFALLS.md` for all 14 pitfalls with detection and prevention strategies, plus phase-specific warnings.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation (Django project + DB + Auth + Deployment)
**Rationale:** Everything depends on the Django project skeleton, database schema, authentication, and a working deployment pipeline. No feature can be built without these.
**Delivers:** Django project running on the VM, PostgreSQL schema with core models (Email, Assignment, SLAConfig, RuntimeConfig), Google OAuth SSO, Docker Compose deployment, Nginx config, health endpoint.
**Features:** Google OAuth SSO, basic project structure, Django admin for configuration.
**Avoids:** Docker/Taiga conflicts (Pitfall 4), OAuth domain bypass (Pitfall 2), static file serving issues (Pitfall 8), SA key management (Pitfall 10).

### Phase 2: Email Processing Pipeline (Migrate v1 agent modules)
**Rationale:** The email processing pipeline is the core product. v1 modules (gmail_poller, ai_processor, sla_monitor) port directly with ORM replacing SheetLogger. This must work before the dashboard has anything to display.
**Delivers:** Emails polled, triaged by AI, stored in PostgreSQL, Chat notifications sent, SLA tracked, EOD reports generated. Functional parity with v1.
**Features:** SLA deadlines + breach alerts, activity logging from day 1.
**Avoids:** APScheduler duplication (Pitfall 5), timezone bugs (Pitfall 9), PyMuPDF license issue (Pitfall 13 -- swap to pypdf).

### Phase 3: Dashboard Core (Email table + Manual assignment)
**Rationale:** With emails flowing into PostgreSQL, build the dashboard that makes them visible and actionable. This is the primary new capability v2 adds over v1.
**Delivers:** Email list view with filters (django-filter), manual assignment via HTMX forms, status tracking, unassigned queue as default view, assignment notifications via Chat + email.
**Features:** Manual assignment, assignment visibility, status tracking, email table dashboard, unassigned queue, notification on assignment.
**Avoids:** HTMX partial template errors (Pitfall 12 -- test both render paths).

### Phase 4: Smart Assignment + Thread Monitoring
**Rationale:** Once manual assignment works, add automation. AI auto-assignment uses the same triage output already in the database. Thread monitoring requires Gmail API integration that builds on Phase 2's poller.
**Delivers:** Category-to-person assignment rules, AI fallback for ambiguous emails, automatic status update when assignee replies in Gmail, two-tier SLA (ack + response), escalation to manager, workload view.
**Features:** AI auto-assignment, Gmail thread auto-detection, two-tier SLA, escalation, workload view.
**Avoids:** AI feedback bias (Pitfall 6 -- start with rules, not ML), Gmail History API gaps (Pitfall 11 -- hybrid push+poll, manual override button).

### Phase 5: Analytics + Polish + Sheets Mirror
**Rationale:** Analytics require accumulated data from Phases 2-4. Sheets mirror is non-critical and should be built last to avoid it becoming a maintenance burden.
**Delivers:** Response time charts, assignment analytics, Google Sheets read-only mirror (batch sync, simplified schema, locked Sheet), configurable inbox management UI.
**Features:** AI feedback loop, response time analytics, WhatsApp/SMS escalation (CRITICAL only), configurable inbox management, Sheets mirror.
**Avoids:** Sheets sync becoming a critical path (Pitfall 7 -- fire-and-forget, batch sync, build last).

### Phase 6: Migration + Cutover
**Rationale:** Cutover is a distinct operational phase, not a development phase. Requires v2 fully validated before v1 shutdown.
**Delivers:** Production data migrated from Sheets to PostgreSQL. v1 shut down. Cloud Run decommissioned.
**Avoids:** Duplicate processing during cutover (Pitfall 3 -- inbox-by-inbox or hard cutover), data loss from type coercion (Pitfall 1 -- export real Sheet, validate every variant).

### Phase Ordering Rationale

- **Foundation first** because every component depends on Django, PostgreSQL, auth, and deployment infrastructure.
- **Pipeline before dashboard** because the dashboard has nothing to show without emails in the database. The agent modules are proven v1 code -- porting them is lower risk than building new UI.
- **Manual assignment before AI assignment** because rules-based automation should only be added after the manual workflow is validated by the team.
- **Analytics and Sheets mirror last** because they are nice-to-haves that require accumulated data and add no core functionality.
- **Cutover as a separate phase** because it is an operational event with its own risks (data migration, dual-system coordination), distinct from feature development.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Foundation):** VM audit required -- current Taiga Docker setup, Nginx config, PostgreSQL version/config, available resources. Cannot write docker-compose.yml without inspecting the actual VM.
- **Phase 4 (Thread Monitoring):** Gmail API push notifications vs polling trade-offs need API-level research. Hiver documented production bugs with Gmail push. Hybrid approach (push + polling fallback) needs design.
- **Phase 6 (Migration/Cutover):** Production Sheet data audit required. Format variants, edge cases, empty cells, "ERROR" markers in SLA columns. Cannot write migration script without inspecting real data.

Phases with standard patterns (skip deeper research):
- **Phase 2 (Email Pipeline):** Direct port of proven v1 code with ORM swap. Well-understood.
- **Phase 3 (Dashboard):** Standard Django + HTMX CRUD dashboard. Extensively documented pattern with tutorials and production examples.
- **Phase 5 (Analytics):** Standard Django ORM aggregation queries. Well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Django + HTMX is a well-established pattern with extensive 2025-2026 documentation. All library versions verified. Django 5.2 LTS supported until 2028. |
| Features | HIGH | Competitor analysis (Front, Hiver, Help Scout, Missive, Gmelius, Drag) provides clear baseline. Feature prioritization aligns with v1 capabilities and 3-person team needs. |
| Architecture | HIGH | Single-container Django monolith is the most documented deployment pattern. v1 codebase directly inspected -- agent modules are framework-agnostic and portable. |
| Pitfalls | HIGH | Sourced from official docs (Django deployment checklist, Gmail API), production incident reports (Hiver's Gmail push bug), and direct v1 codebase analysis. 14 pitfalls identified with prevention strategies. |

**Overall confidence:** HIGH

### Gaps to Address

- **VM resource audit:** Need to inspect the actual VM before writing Docker Compose config -- current Taiga setup, available RAM/CPU, PostgreSQL version, Nginx config, port usage.
- **Production Sheet data inspection:** Need to export and audit the real Sheet before writing the migration script -- format variants in dates, SLA deadlines, ticket numbers, "ERROR" markers.
- **Tailwind CSS standalone CLI in Docker:** Verified macOS binary. Need to confirm Linux binary availability for VM/Docker build.
- **PyMuPDF license swap:** v1 uses PyMuPDF (AGPL). Need to validate that `pypdf` or `pdfminer.six` handles the same PDF extraction use cases (first 3 pages, max 1000 chars).
- **Subdomain setup:** `triage.vidarbhainfotech.com` DNS record and SSL certificate (Let's Encrypt via existing Nginx or certbot).

## Sources

### Primary (HIGH confidence)
- [Django 5.2 LTS release notes](https://www.djangoproject.com/weblog/2025/apr/02/django-52-released/)
- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [django-allauth Google provider docs](https://docs.allauth.org/en/dev/socialaccount/providers/google.html)
- [Gmail Push Notifications API](https://developers.google.com/workspace/gmail/api/guides/push)
- [django-apscheduler](https://pypi.org/project/django-apscheduler/)
- v1 codebase analysis (direct inspection of agent/ modules, CLAUDE.md, tests/)

### Secondary (MEDIUM confidence)
- [HTMX vs React dashboard comparison (2026)](https://medium.com/@the_atomic_architect/react-vs-htmx-i-built-the-same-dashboard-with-both-one-of-them-is-a-maintenance-nightmare-9f2ef3e84728)
- [Django Docker deployment guide (2026)](https://medium.com/@sizanmahmud08/production-ready-django-with-docker-in-2026-complete-guide-with-nginx-postgresql-and-best-1fb248e65983)
- [Hiver features and shared inbox comparison](https://hiverhq.com/features)
- [Help Scout shared inbox guide](https://www.helpscout.com/blog/shared-inbox/)
- [Gmail Push Notification bugs at Hiver](https://medium.com/hiver-engineering/gmail-apis-push-notifications-bug-and-how-we-worked-around-it-at-hiver-a0a114df47b4)
- [Google OAuth domain restriction](https://developers.google.com/identity/protocols/oauth2/web-server)

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes*
