# VIPL Email Agent v2

## What This Is

An AI-powered shared inbox management system for Vidarbha Infotech Private Limited. Monitors Gmail inboxes (info@ and sales@), triages incoming emails with Claude AI, auto-assigns them to team members based on category rules, tracks SLA compliance, and provides a branded dashboard with Google OAuth SSO for management oversight. Every email gets owned, acknowledged, and responded to.

## Core Value

Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks. The system is the safety net that prevents lost business from missed emails.

## Requirements

### Validated

- Gmail inbox polling with label-based processing — v2.1
- Claude AI two-tier triage: Haiku default, Sonnet for CRITICAL — v2.1
- Spam pre-filter via 13 regex patterns ($0 cost) — v2.1
- PDF attachment text extraction for triage context — v2.1
- Multi-language detection (Hindi, Marathi, English) — v2.1
- Dead letter queue with 3x retry for failed triages — v2.1
- Dashboard: card list with filters, sorting, pagination, HTMX — v2.1
- Manual assignment + reassignment with notifications — v2.1
- Auto-assignment engine: category rules + AI fallback — v2.1
- SLA tracking with business hours, breach detection, escalation — v2.1
- Per-category Google Chat webhook routing with quiet hours — v2.1
- Activity log for all assignment and status changes — v2.1
- EOD reports via email + Chat with database stats — v2.1
- SystemConfig admin for runtime configuration — v2.1
- Google Sheets read-only sync mirror — v2.1
- PostgreSQL as source of truth — v2.1
- Docker Compose deployment on VM — v2.1
- Release-triggered CI/CD via GitHub Actions — v2.1
- Simple password auth with admin/member roles — v2.1
- Health endpoint with system status — v2.1
- Configurable inbox management from Settings page — v2.1
- ✓ Google OAuth SSO with domain lock (@vidarbhainfotech.com) — v2.2
- ✓ Auto-provision new Google users as inactive (admin approval) — v2.2
- ✓ Type-aware settings inputs with pre-filled values — v2.2
- ✓ SpamWhitelist model with pipeline integration — v2.2
- ✓ Whitelist Sender button + management tab — v2.2
- ✓ Bool normalization migration — v2.2
- ✓ Inline save feedback on all settings tabs — v2.2
- ✓ VIPL brand identity (logo, palette, favicon, page titles) — v2.2
- ✓ Google Chat card branding (header icon + footer) — v2.2
- ✓ Inline Open buttons in Chat notification cards — v2.2
- ✓ Consistent SLA urgency labels across all card types — v2.2

### Active

- [ ] Thread/conversation model — group emails by `gmail_thread_id`, thread-level assignment + status
- [ ] Conversation UI — inbox shows threads, detail panel shows full message history
- [ ] Internal notes — team discusses emails internally with `@mentions`
- [ ] Contact history — see all threads from same sender in sidebar
- [ ] Snooze — temporarily hide a thread, resurface later
- [ ] Response templates — canned replies for repetitive emails
- [ ] Collision detection — "X is viewing this" indicator (polling-based)
- [ ] Keyboard shortcuts — `j/k` navigate, `a` assign, `e` close, `n` note
- [ ] Batch operations — select multiple threads, assign/close in bulk

### Out of Scope

- Reply from dashboard — team replies from Gmail directly, building compose UI is high effort low value
- Tender intelligence / MahaTender parsing — future milestone, research exists in `docs/mahatender/`
- Mobile native app — responsive web + Chat notifications is sufficient
- Multi-tenant / SaaS — single company tool
- Round-robin assignment — category rules more accurate for 3-person team
- Ticket numbering — nobody references ticket numbers, email subject is identifier
- Kanban board view — threads as cards on columns, overkill for 3-person team
- Analytics dashboards — volume/response time charts, defer to future milestone
- Shared drafts — collaborative reply editing, low value when team replies from Gmail

## Current Milestone: v2.3.5 Email Threads & Inbox

**Goal:** Transform the email triage experience from individual messages to threaded conversations, matching Gmelius/Hiver-level shared inbox UX.

**Target features:**
- Thread/conversation grouping with thread-level assignment + status
- Full conversation UI (inbox shows threads, detail shows message history)
- Internal notes with @mentions for team collaboration
- Contact history sidebar, snooze, response templates
- Collision detection, keyboard shortcuts, batch operations

## Context

**Current state (v2.2 shipped):** Production at triage.vidarbhainfotech.com since 2026-03-14. Full pipeline: Gmail polling → spam filter (13 regex + whitelist) → Claude AI triage → auto-assign → SLA tracking → Google Chat notifications (branded cards with deep links). Google OAuth SSO with domain lock. VIPL brand identity across all pages and Chat cards. 18,763 LOC Python, 349 tests passing, Django 4.2 LTS + PostgreSQL 12.3.

**Threading readiness:** `gmail_thread_id` already fetched and stored on every Email record. `fetch_thread_message()` method exists in gmail_poller. Foundation is there — just unused.

**Team:** 2-3 people handle the inboxes + 1 manager (Shreyas) who oversees.

**Infrastructure:** Self-hosted VM (`taiga` in GCP, asia-south1-b). Docker Compose with web + scheduler containers. Nginx reverse proxy with Let's Encrypt SSL. PostgreSQL shared with Taiga stack.

## Constraints

- **Hosting**: Self-hosted VM (Docker Compose). Must coexist with Taiga and other services.
- **Database**: PostgreSQL 12.3 (Taiga's container). Django 4.2 LTS required (5.2+ needs PG 13+).
- **Gmail access**: Domain-wide delegation via service account.
- **Budget**: Near-zero infrastructure cost. Claude API is the only ongoing expense.
- **Team size**: 4-5 users max.
- **Deployment**: Release-triggered CI/CD via GitHub Actions.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Django 4.2 LTS (not 5.2+) | PostgreSQL 12.3 on VM not supported by Django 5.2+ | ✓ Good — stable, LTS until 2026-04 |
| HTMX + Tailwind CDN (no React/Node) | Zero build step, server-rendered, simpler stack | ✓ Good — fast dev, no JS complexity |
| APScheduler as separate management command | Keeps scheduler out of Gunicorn workers | ✓ Good — clean separation |
| SystemConfig key-value store | Runtime config without redeploy, replaces Sheets config | ✓ Good — flexible, migration-seeded |
| Per-category Chat webhooks via SystemConfig | Categories = teams, configurable from Settings | ✓ Good — no Team model needed |
| Release-triggered deploy (not tag push) | Intentional deploys, documented via GitHub Releases | ✓ Good — prevents accidental deploys |
| Fire-and-forget notifications | Chat/email never block assignment flow | ✓ Good — resilient UX |
| nh3 for HTML sanitization | Rust-based, safe-by-default XSS protection | ✓ Good — zero vulnerabilities |
| SLA business hours 8AM-8PM IST Mon-Sat | Matches VIPL working hours | ✓ Good — accurate deadlines |
| Settings-based allauth APP config | Avoids DB SocialApp records, simpler deployment | ✓ Good — v2.2 |
| Whitelist check in pipeline.py (not spam_filter.py) | Keeps spam_filter pure/Django-free | ✓ Good — v2.2 |
| Plum brand palette (#a83362) | Derived from VIPL logo, consistent with corporate identity | ✓ Good — v2.2 |
| decoratedText.button for inline links | Cards v2 union field constraint, no endIcon conflict | ✓ Good — v2.2 |
| _sla_urgency_label module-level function | Cross-method reuse, consistent formatting | ✓ Good — v2.2 |

---
*Last updated: 2026-03-15 after v2.3.5 milestone started*
