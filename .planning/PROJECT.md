# VIPL Email Agent v2

## What This Is

An AI-powered shared inbox management system for Vidarbha Infotech Private Limited. Monitors unmanned Gmail inboxes, triages incoming emails with Claude AI, auto-assigns them to team members, tracks SLA compliance, and gives management a dashboard for oversight. Replaces the v1 monitoring-only system with an active workflow that ensures every email gets owned, acknowledged, and responded to.

## Core Value

Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks. The system is the safety net that prevents lost business from missed emails.

## Requirements

### Validated

<!-- Carried from v1 — these work and are proven in production -->

- Gmail inbox polling with label-based processing (v1)
- Claude AI two-tier triage: category, priority, summary, draft reply (v1)
- Spam pre-filter via regex patterns (v1)
- Google Chat webhook notifications (v1)
- SLA deadline calculation per category (v1)
- EOD summary report via email + Chat (v1)
- Dead letter queue with retry for failed triages (v1)
- Multi-language detection (Hindi, Marathi, English) (v1)
- PDF attachment extraction for triage context (v1)
- Dynamic config hot-reload from external source (v1)

### Active

<!-- v2 scope — building toward these -->

- [ ] Email assignment engine: rules-based (category -> person) + AI fallback (content/workload analysis)
- [ ] Manual reassignment with AI correction feedback loop (corrections improve future assignments)
- [ ] SLA workflow: acknowledgement deadline + response deadline per priority
- [ ] Gmail thread monitoring to auto-detect when assignee responds
- [ ] Dashboard: table view with email details, filters, assignment controls, status tracking
- [ ] Google OAuth SSO restricted to @vidarbhainfotech.com
- [ ] Live dashboard analytics: response times, volume trends, assignee performance
- [ ] Configurable inbox management: add/remove monitored inboxes without code changes
- [ ] Notification multi-channel: Google Chat + Email + WhatsApp/SMS for urgent escalations
- [ ] SLA escalation: alert manager when assignee misses deadline
- [ ] Google Sheets read-only sync mirror (simplified: date, from, subject, assignee, status)
- [ ] Daily EOD report (email + Chat) with enhanced stats from real database
- [ ] PostgreSQL as source of truth (replaces Sheets-as-DB)
- [ ] Docker Compose deployment on existing VM
- [ ] Tag-based CI/CD via GitHub Actions targeting VM

### Out of Scope

- Reply from dashboard (team replies from Gmail directly) — complexity vs value
- Tender intelligence / MahaTender parsing — future milestone, not v2 core
- Web scraping for tender documents — future milestone
- Mobile native app — responsive web is sufficient
- Real-time chat/messaging — not needed for email workflow
- Multi-tenant / SaaS — single company tool

## Context

**Current state (v1):** Production on Cloud Run since v1.0. Monitors info@ and sales@ inboxes, triages with Claude AI, logs to Google Sheets, posts to Google Chat. Works as an alerting/monitoring system but is purely passive — nobody is assigned to act on emails, so they still get missed. 112 unit tests, 8 integration tests.

**The business problem:** VIPL receives sales inquiries, tender notifications, and general correspondence across shared inboxes. With no ownership model, emails sit unread. By the time someone checks, the prospect has moved on. This directly costs revenue.

**Team:** 2-3 people handle the inboxes + 1 manager (Shreyas) who oversees. Small team, needs simple workflow not enterprise complexity.

**Infrastructure:** An existing VM hosts Taiga and other internal tools. PostgreSQL already runs there. The VM is paid for regardless, so deploying v2 there keeps costs zero.

**Tender intelligence research:** Extensive research exists in `docs/mahatender/` covering MahaTender email parsing (8 notification types, regex patterns, field extraction) and portal scraping feasibility (Playwright-based, CAPTCHA handling). This is documented and ready for a future milestone but explicitly deferred from v2 core.

**v1 codebase:** Python 3.11, pure-Python with no web framework (just stdlib HTTPServer for health checks). APScheduler for background jobs. Google APIs for Gmail + Sheets. Anthropic SDK for Claude. Well-tested with 131 tests. Key patterns to preserve: label-after-persist safety, circuit breaker, retry with backoff, spam pre-filter, two-tier AI model strategy.

## Constraints

- **Auth**: Google OAuth only — restricted to @vidarbhainfotech.com domain. No separate user management.
- **Hosting**: Self-hosted VM (Docker Compose). Must coexist with Taiga and other services on same machine.
- **Database**: PostgreSQL (already running on VM for Taiga).
- **Gmail access**: Domain-wide delegation via service account (existing pattern from v1).
- **Budget**: Near-zero infrastructure cost. Claude API is the only ongoing expense.
- **Team size**: 4-5 users max. Don't over-engineer for scale.
- **Deployment**: Tag-based CI/CD via GitHub Actions. No auto-deploy on push.
- **Subdomain**: `triage.vidarbhainfotech.com` (or similar — to be configured).
- **Browser support**: Desktop-first, mobile-usable. No IE/legacy requirements.

## Key Decisions

<!-- Decisions made during project initialization -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PostgreSQL over Sheets as primary DB | Sheets hit API rate limits, can't do joins/queries, no referential integrity | -- Pending |
| Keep Sheets as read-only mirror | Team is used to Sheets for quick lookups, low effort to sync | -- Pending |
| Google OAuth (not password auth) | Everyone already has @vipl Google accounts, zero password management | -- Pending |
| Self-host on existing VM | Already paying for the VM, PostgreSQL already there, zero incremental cost | -- Pending |
| Triage + assign only (no reply from dashboard) | Team already knows Gmail, adding reply UX is high effort low value | -- Pending |
| AI feedback loop from corrections | Corrections logged to improve assignment accuracy over time | -- Pending |
| Tender intelligence deferred to future milestone | Get core inbox management right first, tender features are additive | -- Pending |
| Taiga sync agent for development | Dedicated agent keeps Taiga stories/tasks updated as we build v2 (dev process, not product feature) | -- Pending |
| Stack TBD — not married to FastAPI+React | Research phase should propose best-fit stack for this use case | -- Pending |

---
*Last updated: 2026-03-09 after initialization*
