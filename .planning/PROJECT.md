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
- ✓ AI suggested assignee XML tag cleanup at ingest + data migration — v2.3.6
- ✓ Mobile detail panel with history API, scroll lock, back button — v2.3.6
- ✓ Mobile filter stacking, activity chip wrap, toast positioning — v2.3.6
- ✓ Email count OOB update on view switch — v2.3.6
- ✓ Consistent page titles "VIPL Triage | {Page}" — v2.3.6
- ✓ Welcome banner with role-specific onboarding — v2.3.6
- ✓ Active filter indicators with count badge and clear-all — v2.3.6
- ✓ Scroll-snap stat cards for mobile — v2.3.6
- ✓ Keyboard navigation (Arrow keys + Escape) on email cards — v2.3.6
- ✓ Loading skeleton for detail panel HTMX fetches — v2.3.6

- ✓ AI confidence scoring (HIGH/MEDIUM/LOW) with visual dots on cards and detail — v2.5.0
- ✓ Auto-assign pipeline: HIGH confidence + AssignmentRule → auto-assignment with badge — v2.5.0
- ✓ Accept/reject AI suggestions with feedback distillation into correction rules — v2.5.0
- ✓ Spam learning: mark spam/not-spam, SenderReputation auto-block, whitelist on unblock — v2.5.0
- ✓ Per-user read/unread tracking with bold+dot indicators, sidebar badges, mark-as-unread — v2.5.0
- ✓ Right-click context menu on thread cards with role-aware quick actions — v2.5.0
- ✓ Inline editable category/priority/status with override flags preserved on new emails — v2.5.0
- ✓ Reports module: 4-tab analytics (Overview, Volume, Team, SLA) with Chart.js — v2.5.0
- ✓ Bug fixes: spam badge annotation, Gmail avatar edge cases, cross-inbox dedup — v2.5.0

- ✓ Bug fixes: welcome banner dedup, pipeline unread state, REOPENED status, AI assign OOB — v2.5.4
- ✓ Thread cards: expanded spacing, pill dropdowns, context menu readability, AI draft copy — v2.5.4
- ✓ Workflow: claim button with toast, spam toggle undo — v2.5.4
- ✓ Pages: retro-modern login, grouped settings tabs, thread-grouped activity, sidebar version badge — v2.5.4
- ✓ Dev inspector: force poll inline results, poll history with intervals/dimming/timestamps — v2.5.4
- ✓ QA fixes: thread count OOB, search view sync, mobile drawer, Escape close detail — v2.5.4
- ✓ Cosmetic: action button wrap, reports title format, SLA chart zero-value handling — v2.5.4

### Active

(No active milestone — run `/gsd:new-milestone` to start next)

### Out of Scope

- Reply from dashboard — team replies from Gmail directly, building compose UI is high effort low value
- Tender intelligence / MahaTender parsing — future milestone, research exists in `docs/mahatender/`
- Mobile native app — responsive web + Chat notifications is sufficient
- Multi-tenant / SaaS — single company tool
- Round-robin assignment — category rules more accurate for 3-person team
- Ticket numbering — nobody references ticket numbers, email subject is identifier

## Context

**Current state (v2.5.4 complete):** Production at triage.vidarbhainfotech.com. v2.5.0 deployed, v2.5.4 complete on `fixes` branch (24 UI/UX fixes, 734 tests). Django 4.2 LTS + PostgreSQL 12.3. 0 open GitHub issues.

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
| XML cleanup at ingest (not display layer) | Clean data at source, simpler templates | ✓ Good — v2.3.6 |
| OOB swap for email count updates | No page reload, HTMX out-of-band pattern | ✓ Good — v2.3.6 |
| pushState/popstate for mobile detail panel | Browser back button works naturally | ✓ Good — v2.3.6 |
| sessionStorage + localStorage for welcome banner | Session dismiss + permanent "don't show again" | ✓ Good — v2.3.6 |
| Discrete confidence tiers (HIGH/MEDIUM/LOW) | Claude's self-reported confidence is uncalibrated; discrete tiers are honest | ✓ Good — v2.5.0 |
| SenderReputation (not ML) for spam learning | Volume too low (50-100/day) for statistical approaches | ✓ Good — v2.5.0 |
| No ThreadReadState row = read | Avoids wall-of-bold on first deploy | ✓ Good — v2.5.0 |
| Chart.js CDN only on reports page | No build step, loaded lazily | ✓ Good — v2.5.0 |
| Override flags on Thread model | Pipeline preserves user-corrected category/priority | ✓ Good — v2.5.0 |
| Context menu fetched server-side (GET) | Role-aware rendering without duplicating permission logic in JS | ✓ Good — v2.5.0 |

---
*Last updated: 2026-03-15 after v2.5.4 milestone completed*
