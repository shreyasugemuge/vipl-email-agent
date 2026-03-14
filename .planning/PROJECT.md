# VIPL Email Agent v2

## What This Is

An AI-powered shared inbox management system for Vidarbha Infotech Private Limited. Monitors Gmail inboxes (info@ and sales@), triages incoming emails with Claude AI, auto-assigns them to team members based on category rules, tracks SLA compliance, and provides a dashboard for management oversight. Every email gets owned, acknowledged, and responded to.

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

## Current Milestone: v2.2 Polish & Hardening

**Goal:** Improve UX, add SSO, upgrade settings page, brand with VIPL identity, smarter spam filtering, and better notifications.

**Target features:**
- Google OAuth SSO (domain-locked to @vidarbhainfotech.com)
- Settings page overhaul (grouped form UI, pre-filled values, type-aware inputs)
- VIPL branding (logo from Drive, theme colors throughout)
- Spam learning (whitelist from "not spam" actions, adaptive filtering)
- Chat notification UX improvements (better card design, SLA alerts)
- General UX/UI polish across dashboard

### Active

- R1.1: django-allauth[socialaccount] integration — v2.2 Phase 1
- R1.2: Server-side @vidarbhainfotech.com domain enforcement — v2.2 Phase 1
- R1.3: Google Sign-In button on login page (password form preserved) — v2.2 Phase 1
- R1.4: Auto-provision new Google users as MEMBER role — v2.2 Phase 1
- R1.5: Data migration for existing superuser email fields — v2.2 Phase 1
- R1.6: GCP OAuth consent screen + credentials — v2.2 Phase 1
- R2.1: Type-aware settings input widgets (checkbox/number/text) — v2.2 Phase 2
- R2.2: Pre-fill settings inputs with current DB values — v2.2 Phase 2
- R2.3: SpamWhitelist model (email/domain entries) — v2.2 Phase 2
- R2.4: Whitelist-aware spam filter (AI triage always runs) — v2.2 Phase 2
- R2.5: "Whitelist Sender" button in email detail panel — v2.2 Phase 2
- R2.6: Spam whitelist management tab in settings — v2.2 Phase 2
- R2.7: Normalize existing SystemConfig bool values — v2.2 Phase 2
- R2.8: Inline save feedback on SLA Config tab — v2.2 Phase 2
- R3.1: VIPL logo asset in static/img/ — v2.2 Phase 3
- R3.2: Logo in sidebar and login page — v2.2 Phase 3
- R3.3: Brand color palette in @theme — v2.2 Phase 3
- R3.4: HTMX partial audit for brand color consistency — v2.2 Phase 3
- R4.1: Email pk in breach data structure — v2.2 Phase 4
- R4.2: Per-email "Open" link in breach alerts — v2.2 Phase 4
- R4.3: Consistent SLA urgency display across card types — v2.2 Phase 4
- R4.4: Card payload validation in Card Builder — v2.2 Phase 4

### Out of Scope

- Reply from dashboard — team replies from Gmail directly, building compose UI is high effort low value
- Tender intelligence / MahaTender parsing — future milestone, research exists in `docs/mahatender/`
- Mobile native app — responsive web + Chat notifications is sufficient
- Multi-tenant / SaaS — single company tool
- Round-robin assignment — category rules more accurate for 3-person team
- Ticket numbering — nobody references ticket numbers, email subject is identifier

## Context

**Current state (v2.1 shipped):** Production at triage.vidarbhainfotech.com since 2026-03-14. Monitors info@ and sales@ inboxes, triages with Claude AI (Haiku/Sonnet), auto-assigns by category, tracks SLA deadlines, notifies via Google Chat per-category webhooks. 16,572 LOC Python, 257 tests passing, Django 4.2 LTS + PostgreSQL 12.3.

**Team:** 2-3 people handle the inboxes + 1 manager (Shreyas) who oversees.

**Infrastructure:** Self-hosted VM (`taiga` in GCP, asia-south1-b). Docker Compose with web + scheduler containers. Nginx reverse proxy with Cloudflare SSL. PostgreSQL shared with Taiga stack.

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
| Django 4.2 LTS (not 5.2+) | PostgreSQL 12.3 on VM not supported by Django 5.2+ | Good — stable, LTS until 2026-04 |
| Simple password auth (not Google OAuth) | Faster to ship, OAuth deferred to v2 requirements | Good — works for 4 users |
| HTMX + Tailwind CDN (no React/Node) | Zero build step, server-rendered, simpler stack | Good — fast dev, no JS complexity |
| APScheduler as separate management command | Keeps scheduler out of Gunicorn workers | Good — clean separation |
| SystemConfig key-value store | Runtime config without redeploy, replaces Sheets config | Good — flexible, migration-seeded |
| Per-category Chat webhooks via SystemConfig | Categories = teams, configurable from Settings | Good — no Team model needed |
| Release-triggered deploy (not tag push) | Intentional deploys, documented via GitHub Releases | Good — prevents accidental deploys |
| Fire-and-forget notifications | Chat/email never block assignment flow | Good — resilient UX |
| nh3 for HTML sanitization | Rust-based, safe-by-default XSS protection | Good — zero vulnerabilities |
| SLA business hours 8AM-8PM IST Mon-Sat | Matches VIPL working hours | Good — accurate deadlines |

---
*Last updated: 2026-03-14 after v2.2 milestone started*
