<div align="center">

# VIPL Email Agent

### AI-Powered Email Monitoring & Triage System

[![Version](https://img.shields.io/badge/v2.8.1-latest-e06a97?style=for-the-badge)](https://github.com/shreyasugemuge/vipl-email-agent/releases)
[![Tests](https://img.shields.io/badge/Tests-829_passing-4ECDC4?style=for-the-badge)](https://github.com/shreyasugemuge/vipl-email-agent/actions)
[![AI](https://img.shields.io/badge/Claude_AI-Haiku_%2B_Sonnet-cc785c?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)

[![Django](https://img.shields.io/badge/Django-4.2_LTS-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![HTMX](https://img.shields.io/badge/HTMX-2.0-3366CC?style=flat-square)](https://htmx.org)
[![Tailwind](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12.3-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker_Compose-blue?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-Private-555?style=flat-square)](LICENSE)

**Autonomous email classification, SLA tracking, and team alerting**
**for [Vidarbha Infotech Pvt. Ltd.](https://vidarbhainfotech.com)**

[Live Dashboard](https://triage.vidarbhainfotech.com) &middot; [Wiki](https://github.com/shreyasugemuge/vipl-email-agent/wiki) &middot; [Changelog](CHANGELOG.md) &middot; [Releases](https://github.com/shreyasugemuge/vipl-email-agent/releases)

</div>

---

## What It Does

VIPL Email Agent watches your team's shared inboxes (`info@`, `sales@`) 24/7, classifies every email with Claude AI, assigns them to the right person, tracks SLA deadlines, and alerts the team — all from a retro-themed real-time dashboard with dark/light mode.

Every email gets a category, priority, SLA deadline, summary, draft reply, and suggested assignee — in under 3 seconds, for ~$0.001 per email.

---

## The Problem

> *"We kept missing government tender emails buried under vendor spam. By the time someone noticed, the deadline had passed."*

**Before**: 30-80 emails/day across shared inboxes. Missed tenders, inconsistent triage, no SLA tracking, zero visibility into communication state.

**After**: Zero missed emails. AI classifies everything. SLA breaches caught automatically. Team sees one dashboard.

---

## Pipeline

```
Gmail Inboxes (info@, sales@)
    → SpamFilter (13 regex + blocked senders — $0)
    → AIProcessor (Haiku ~$0.001/ea, Sonnet for CRITICAL ~$0.01/ea)
    → Auto-Assign (HIGH confidence >80% → assign by category rules)
    → Pipeline (save PostgreSQL → label Gmail → notify Chat)
    → Feedback Loop (spam corrections → SenderReputation, AI corrections → distillation)
    → Dead Letter Retry (30min intervals, max 3 attempts)
    → Circuit Breaker (3 failures → pause polling)
```

> Deep dive: **[Email Pipeline](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Email-Pipeline)** &middot; **[AI Triage](https://github.com/shreyasugemuge/vipl-email-agent/wiki/AI-Triage)**

---

## Features

### AI Intelligence

| Feature | Detail |
|---------|--------|
| **Two-Tier AI** | Haiku for routine, Sonnet for CRITICAL — prompt caching saves ~90% |
| **Confidence Scoring** | HIGH/MEDIUM/LOW with visual dots; HIGH triggers auto-assign |
| **Spam Learning** | Feedback loop: mark spam → SenderReputation → auto-block repeat offenders |
| **Feedback Distillation** | User corrections aggregated into AI prompt rules nightly |
| **Multi-Language** | Hindi, Marathi, Mixed — summaries in English, replies in original language |
| **PDF Analysis** | Extracts first 3 pages of PDF attachments for context-aware triage |

### Dashboard

| Feature | Detail |
|---------|--------|
| **Dark/Light Mode** | Retro CRT aesthetic (dark) or clean modern (light) — toggle persists |
| **Thread Cards** | Filterable queue with avatar badges, status dots, AI summary, confidence |
| **Detail Panel** | Slide-out with inline editing (category, priority, status, AI summary) |
| **Assignee Badges** | Google avatar images, solid rose initials, gold "Unassigned" state |
| **Context Menu** | Right-click cards for quick assign, status, priority, spam actions |
| **Reports** | 4-tab analytics with Chart.js (theme-aware, re-renders on toggle) |
| **Activity Log** | Full audit trail: assignments, status changes, notes, AI edits |
| **Keyboard Nav** | Arrow keys, Enter, Escape, U (mark unread) |

> Full walkthrough: **[Dashboard Guide](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Dashboard-Guide)**

### Monitoring

| Feature | Detail |
|---------|--------|
| **Chat Alerts** | Google Chat Cards v2 for HIGH/CRITICAL emails |
| **SLA Alerts** | 3x daily breach summary (9 AM, 1 PM, 5 PM IST) |
| **Quiet Hours** | Alerts suppressed 8 PM – 8 AM IST |
| **EOD Report** | Daily summary email + Chat card at 7 PM IST |
| **Health** | `/health/` JSON endpoint for Docker healthcheck |

---

## Tech Stack

```
Frontend    Django Templates + HTMX 2.0 + Tailwind CSS v4
            + Hand-crafted retro theme system (no external design library)
Backend     Django 4.2 LTS + PostgreSQL 12.3
AI          Claude Haiku (default) + Sonnet (escalation) via Anthropic API
Email       Gmail API with Domain-Wide Delegation
Notify      Google Chat Cards v2 Webhooks
Auth        Google OAuth SSO (django-allauth, domain-locked)
Deploy      Docker Compose + Nginx + Let's Encrypt
CI/CD       GitHub Actions: release-triggered deploy
```

> Architecture details: **[Architecture](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Architecture)**

---

## Design System

The UI is a **100% hand-crafted CSS design system** — no PxlKit, no external framework. Retro effects (scanlines, CRT vignette, pixel corners, glow) are pure CSS in `templates/base.html`.

| | Dark Mode | Light Mode |
|-|-----------|------------|
| **Background** | Deep dark `#0a0a0f` | Slate-50 `#f8fafc` |
| **Body Font** | JetBrains Mono | Plus Jakarta Sans |
| **Effects** | CRT scanlines, vignette, neon glow | Subtle dot grid, soft shadows |
| **Accent** | Rose `#e06a97` | Rose `#a83262` |
| **Headings** | Press Start 2P (pixel font) | Press Start 2P (pixel font) |

Color tokens: `--vipl-primary` (rose), `--vipl-cyan` (info), `--vipl-gold` (warning), `--vipl-red` (error), `--vipl-purple` (AI).

> Complete guide: **[Design System](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Design-System)**

---

## Quick Start

```bash
git clone https://github.com/shreyasugemuge/vipl-email-agent.git
cd vipl-email-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 8000
```

Fresh installs default to **off** mode — zero external API calls.

```bash
pytest -v                                        # 843 tests (no API keys)
python manage.py test_pipeline                   # Smoke test with fake data
python manage.py run_scheduler --once --dry-run  # Simulated poll cycle
```

> Full setup: **[Getting Started](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Getting-Started)** &middot; **[Configuration](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Configuration)**

---

## Deployment

```bash
gh release create v2.8.1 --title "v2.8.1" --generate-notes
# → CI tests → SSH deploy to VM → done
```

Push to `main` runs tests only. Deploy only on GitHub Release — intentional, documented, reversible.

> Full guide: **[Deployment](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Deployment)** &middot; **[Security](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Security)**

---

## Cost

| Component | Monthly |
|-----------|:------:|
| GCP VM (shared with Taiga) | ~$0 |
| Claude AI (Haiku + Sonnet) | ~$5-15 |
| Google APIs (Gmail, Sheets) | Free |
| **Total** | **< $20/mo** |

---

## Version History

| Version | Highlights |
|:-------:|------------|
| **v2.8.1** | To/Cc display on thread detail, AI performance calibration dashboard |
| **v2.8.0** | Codebase cleanup, split views, consolidated tests, deploy fix |
| **v2.7.1** | QA bug fixes (6 bugs), GitHub Wiki user manual |
| **v2.7.0** | Gatekeeper role, irrelevant email handling, bulk actions, member reassign, alerts |
| **v2.6.1** | Prominent assignee/status badges, Google avatar support, gold "Unassigned" state |
| **v2.6.0** | Full UI revamp: dark/light theme, VIPL brand rose palette, hand-crafted design system |
| **v2.5.4** | 24 UI/UX fixes: expanded cards, pill dropdowns, retro login, dev inspector overhaul |
| **v2.5.0** | AI confidence scoring, auto-assign, spam learning, read/unread, reports module |
| **v2.4.0** | Dashboard UX overhaul: single sidebar, settings validation, poll persistence |
| **v2.0.0** | Full-stack rebuild: Django + PostgreSQL + HTMX. Deployed to VM |
| **v1.0.0** | Initial: Gmail polling, Claude triage, Google Sheets, Chat alerts |

> Full changelog: **[CHANGELOG.md](CHANGELOG.md)** &middot; **[Releases](https://github.com/shreyasugemuge/vipl-email-agent/releases)**

---

## Documentation

| Resource | Description |
|----------|-------------|
| **[Wiki](https://github.com/shreyasugemuge/vipl-email-agent/wiki)** | Complete documentation — architecture, guides, API, operations |
| **[CLAUDE.md](CLAUDE.md)** | Architecture reference for AI-assisted development |
| **[CHANGELOG.md](CHANGELOG.md)** | Detailed version history |
| **[API Endpoints](https://github.com/shreyasugemuge/vipl-email-agent/wiki/API-Endpoints)** | All URL routes and HTMX endpoints |
| **[Testing](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Testing)** | Test suite, dev pipeline, QA |
| **[Troubleshooting](https://github.com/shreyasugemuge/vipl-email-agent/wiki/Troubleshooting)** | Common issues and solutions |

---

<div align="center">

**Built for Vidarbha Infotech Pvt. Ltd., Nagpur**

*Saving 10+ hours/week of manual email triage since January 2026*

</div>
