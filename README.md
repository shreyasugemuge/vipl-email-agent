<div align="center">

# VIPL Email Agent

### AI-Powered Email Monitoring & Triage System

[![AI](https://img.shields.io/badge/Powered%20by-Claude%20AI-cc785c?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)
[![Django](https://img.shields.io/badge/Django-4.2%20LTS-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-Private-red?style=for-the-badge)](LICENSE)

**Autonomous email classification, SLA tracking, and team alerting**
**for [Vidarbha Infotech Pvt. Ltd.](https://vidarbhainfotech.com)**

</div>

---

## Overview

VIPL Email Agent monitors Gmail shared inboxes 24/7, triages every email with Claude AI, tracks SLA compliance, and alerts the team via Google Chat and a web dashboard.

**Live at**: `triage.vidarbhainfotech.com`

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 4.2 LTS + PostgreSQL 12.3 |
| **Frontend** | Django templates + HTMX 2.0 + Tailwind CSS v4 |
| **AI** | Claude Haiku (default) + Sonnet (CRITICAL escalation) |
| **Email** | Gmail API with domain-wide delegation |
| **Notifications** | Google Chat Cards v2 webhooks |
| **Deployment** | Docker Compose on self-hosted GCP VM |
| **CI/CD** | GitHub Actions: release → test → deploy |

---

## The Problem

> *"We kept missing government tender emails buried under vendor spam. By the time someone noticed, the deadline had passed."*

Vidarbha Infotech receives 30-80 emails daily across shared inboxes. Before this system:

- **Missed emails** — High-priority tenders and complaints buried under noise
- **Inconsistent triage** — Same email categorized differently depending on who saw it
- **No SLA tracking** — A 4-hour tender deadline treated the same as a routine vendor email
- **Zero visibility** — No daily summary, no dashboard, no way to know the state of customer communications

---

## How It Works

```
Gmail Inboxes → GmailPoller (domain-wide delegation)
    → SpamFilter (13 regex patterns, $0 cost)
    → AIProcessor (Haiku default, Sonnet for CRITICAL, prompt caching)
    → Pipeline (save to PostgreSQL → label Gmail)
    → ChatNotifier (Google Chat Cards v2, quiet hours)
    → Dead Letter Retry (every 30min, max 3 attempts)
    → Circuit Breaker (3 consecutive failures → skip cycles)
```

Every email is classified into 8 categories with priority, SLA deadline, summary, and suggested assignee — in under 3 seconds.

---

## Features

### Core Intelligence

| Feature | Description |
|---------|-------------|
| **AI Email Triage** | Every email classified with category, priority, SLA deadline, summary, and draft reply |
| **Two-Tier AI** | Haiku for routine emails (~$0.001/ea), Sonnet only for CRITICAL (~$0.01/ea) |
| **Spam Pre-Filter** | 13 regex patterns skip Claude entirely ($0 cost) |
| **Multi-Language** | Detects Hindi, Marathi, Mixed emails; summaries in English; replies in original language |
| **PDF Analysis** | Extracts text from PDF attachments (first 3 pages) for context-aware triage |

### Dashboard

| Feature | Description |
|---------|-------------|
| **Email Card List** | Filterable, sortable email queue with status badges and priority indicators |
| **Assignment Workflow** | Admins assign emails to team members; members acknowledge and close |
| **Detail Panel** | Slide-out panel with email body, draft reply, and activity timeline |
| **Activity Log** | Full audit trail of assignments, status changes, and notes |
| **SLA Tracking** | Visual SLA indicators with breach detection and deadline monitoring |

### Monitoring & Alerts

| Feature | Description |
|---------|-------------|
| **Real-Time Chat Alerts** | Google Chat cards for HIGH and CRITICAL emails |
| **SLA Breach Summary** | 3x daily consolidated alert (9 AM, 1 PM, 5 PM IST) |
| **Quiet Hours** | Chat alerts suppressed 8 PM – 8 AM IST |
| **EOD Reports** | HTML email + Chat card at 7 PM IST with day's stats |
| **Sheets Sync Mirror** | Read-only Google Sheets mirror for reporting continuity |

### Operations

| Feature | Description |
|---------|-------------|
| **Operating Modes** | `off` / `dev` / `production` — dev-safe defaults on fresh install |
| **Hot-Reload Config** | SystemConfig model — change settings without redeploying |
| **Retry with Backoff** | 3x exponential backoff on transient Claude API errors |
| **Dead Letter Queue** | Failed triages auto-retried, then marked Exhausted with Chat alert |
| **Health Endpoint** | `/health/` returns JSON with uptime, mode, AI stats, failure count |

---

## Development

### Prerequisites

- Python 3.11+
- Django 4.2

### Local Setup

```bash
# Clone and install
git clone https://github.com/shreyasugemuge/vipl-email-agent.git
cd vipl-email-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Configure
cp .env.example .env   # Edit with your values (or leave defaults for safe dev mode)

# Run
python manage.py migrate
python manage.py runserver 8000
```

Fresh installs default to **off** mode — no external API calls, no Gmail polling, no Chat notifications.

### Testing

```bash
pytest -v                              # All 257 tests (no API keys needed)
python manage.py test_pipeline         # Smoke test with fake data (no external calls)
python manage.py test_pipeline --with-ai   # Real Claude triage (~$0.001/email)
python manage.py run_scheduler --once --dry-run  # Simulated poll cycle
```

### Dev Inspector

```bash
python manage.py runserver 8000
# Visit http://localhost:8000/emails/inspect/
# Read-only view of simulated Chat/reply output — no login required
```

---

## Deployment

### CI/CD

Two workflows keep CI and CD separate:

- **`ci.yml`** — Runs tests on every push to `main` and on pull requests
- **`deploy.yml`** — Deploys to VM when a GitHub Release is published

**To deploy:**
```bash
gh release create v2.0.1 --title "v2.0.1" --generate-notes
# Creates tag + release → triggers deploy automatically
```

This ensures every deploy is intentional, documented, and reversible. Pushing to `main` runs tests only — never deploys.

### Manual Deploy

```bash
ssh user@vm
cd /opt/vipl-email-agent
git fetch --tags && git checkout v2.0.1
sudo docker compose build --no-cache
sudo docker compose up -d
sleep 5
sudo docker compose exec -T web python manage.py migrate --noinput
```

### Operating Modes

```bash
# On VM (inside container)
sudo docker compose exec web python manage.py set_mode off          # Safe: nothing runs
sudo docker compose exec web python manage.py set_mode dev          # AI only, info@ inbox
sudo docker compose exec web python manage.py set_mode production   # Full pipeline
```

---

## Cost

| Component | Monthly Cost |
|-----------|:---:|
| GCP VM (shared with Taiga) | ~$0 incremental |
| Claude AI (Haiku + Sonnet) | ~$5-15 |
| Google APIs (Gmail, Sheets) | Free |
| **Total** | **< $20/mo** |

---

## Version History

| Version | Date | Highlights |
|:---:|:---:|------------|
| **v2.0.0-rc1** | Mar 2026 | Full-stack rebuild: Django + PostgreSQL + HTMX dashboard. 6 phases complete. Deployed to VM. |
| **v1.1.3** | Mar 2026 | Final v1: circuit breaker, email-loss prevention, 123 tests. Cloud Run decommissioned. |
| **v1.0.0** | Feb 2026 | Initial production: Gmail polling, Claude triage, Google Sheets, Chat alerts |

---

## Documentation

| Document | Description |
|----------|-------------|
| [`CLAUDE.md`](CLAUDE.md) | Architecture reference and development guide |

---

<div align="center">

**Built for Vidarbha Infotech Pvt. Ltd., Nagpur**

*Saving 10+ hours/week of manual email triage since January 2026*

</div>
