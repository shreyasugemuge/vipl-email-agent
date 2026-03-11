<div align="center">

# VIPL Email Agent

### AI-Powered Email Monitoring & Triage System

[![AI](https://img.shields.io/badge/Powered%20by-Claude%20AI-cc785c?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-Private-red?style=for-the-badge)](LICENSE)

**Autonomous email classification, SLA tracking, and team alerting**
**for [Vidarbha Infotech Pvt. Ltd.](https://vidarbhainfotech.com)**

</div>

---

## Version Status

| Version | Branch | Status | Platform |
|---------|--------|--------|----------|
| **v1.x** | `main` | Frozen at v1.1.3 — Cloud Run decommissioned | Google Cloud Run (shut down) |
| **v2.0** | `v2` | **In Development** — Phase 3 complete, Phase 4 next | Self-hosted VM (Docker Compose) |

### v2 — What's Changing

Full-stack rebuild: Django backend with HTMX server-rendered frontend + PostgreSQL, deployed on the existing VIPL VM. Google Sheets becomes a read-only sync mirror, not the source of truth. Cloud Run will be shut down once v2 is live.

| Layer | v1 | v2 |
|-------|----|----|
| **Backend** | Python scripts + Google Sheets as DB | Django 4.2 LTS + PostgreSQL |
| **Frontend** | Google Sheets + Chat cards | Django templates + HTMX + Tailwind CSS |
| **Deployment** | Cloud Run (serverless) | Docker Compose on self-hosted VM |
| **Auth** | Service account only | Django built-in auth (domain-restricted) |
| **URL** | Cloud Run endpoint | `triage.vidarbhainfotech.com` |

**v2 Progress** — Phases 1-3 complete (Foundation, Email Pipeline, Dashboard). 136 tests passing. Phase 4 (Assignment Engine + SLA) is next.

---

## The Problem

> *"We kept missing government tender emails buried under vendor spam. By the time someone noticed, the deadline had passed."*

Vidarbha Infotech receives 30-80 emails daily across shared inboxes. Before this system:

- **Missed emails** &mdash; High-priority tenders and complaints buried under noise
- **Inconsistent triage** &mdash; Same email categorized differently depending on who saw it
- **No SLA tracking** &mdash; A 4-hour tender deadline treated the same as a routine vendor email
- **Zero visibility** &mdash; No daily summary, no dashboard, no way to know the state of customer communications

---

## The Solution

VIPL Email Agent runs 24/7 on Google Cloud Run, polling Gmail every 5 minutes. Every email is classified by Claude AI, logged to Google Sheets, and announced in Google Chat &mdash; in under 3 seconds.

```
                          VIPL Email Agent
                          ================

   Gmail Inboxes              Claude AI                Google Sheets
  ┌─────────────┐         ┌──────────────┐          ┌──────────────┐
  │  info@vipl  │────────▶│  Categorize  │─────────▶│  Email Log   │
  │  sales@vipl │  poll   │  Prioritize  │  log     │  SLA Config  │
  └─────────────┘  every  │  Assign SLA  │  ticket  │  Dashboard   │
                   5 min  │  Summarize   │          │  Cost Track  │
                          └──────┬───────┘          └──────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              Google Chat    EOD Email    SLA Monitor
             ┌──────────┐  ┌──────────┐  ┌──────────┐
             │ Real-time │  │ 7 PM IST │  │ 3x Daily │
             │  Alerts   │  │  Summary │  │  Summary │
             │ HIGH/CRIT │  │  Report  │  │ 9,1,5 PM │
             └──────────┘  └──────────┘  └──────────┘
```

---

## Features

### Core Intelligence

| | Feature | Description |
|---|---------|-------------|
| :brain: | **AI Email Triage** | Every email classified into 8 categories with priority, SLA deadline, summary, and suggested assignee |
| :moneybag: | **Two-Tier AI** | Haiku for routine emails (~$0.001/ea), Sonnet only for CRITICAL (~$0.01/ea). Monthly cost: ~$5-15 |
| :dart: | **Smart Assignment** | AI matches emails to team members based on the Team roster in Google Sheets |
| :shield: | **Input Sanitization** | Control characters stripped before AI processing; prompt injection defense built into system prompt |
| :globe_with_meridians: | **Multi-Language** | Detects Hindi, Marathi, Mixed emails; summaries in English; replies in original language |
| :paperclip: | **PDF Analysis** | Extracts text from PDF attachments (first 3 pages) for context-aware triage |

### Monitoring & Alerts

| | Feature | Description |
|---|---------|-------------|
| :bell: | **Real-Time Chat Alerts** | Google Chat cards for HIGH and CRITICAL emails with subject, sender, priority, and Gmail link |
| :clock3: | **SLA Breach Summary** | Consolidated alert 3x daily (9 AM, 1 PM, 5 PM) instead of per-ticket spam |
| :crescent_moon: | **Quiet Hours** | Chat alerts suppressed 8 PM &ndash; 8 AM IST. Emails still triaged and logged. |
| :email: | **EOD Reports** | HTML email + Chat card at 7 PM IST with day's stats, breaches, and unassigned tickets |

### Operations & Resilience

| | Feature | Description |
|---|---------|-------------|
| :gear: | **Hot-Reload Config** | Agent Config sheet re-read every poll cycle. Change settings without redeploying. |
| :triangular_flag_on_post: | **Feature Flags** | AI Triage, Chat Notifications, EOD Email &mdash; all toggleable from the Sheet |
| :repeat: | **Retry with Backoff** | Claude API retries 3x with exponential backoff (2s, 4s, 8s) on transient errors |
| :coffin: | **Dead Letter + Retry** | Failed triages auto-retried every 30 min (max 3 attempts), then marked Exhausted |
| :chart_with_upwards_trend: | **Cost Tracker** | Daily AI usage (calls, tokens, cost) logged to Sheet after each EOD report |
| :green_heart: | **Health Endpoint** | `/health` returns JSON with uptime, AI stats, failure count, last poll time |
| :page_facing_up: | **Structured Logging** | JSON logs for Cloud Logging with severity, component, tokens, and cost fields |

---

## Architecture

### v2 File Structure (v2 branch — in development)

```
manage.py                        # Django management
conftest.py                      # Root test config
gunicorn.conf.py                 # Production WSGI server
Dockerfile                       # Django + Gunicorn container
docker-compose.yml               # Production: web + scheduler services
docker-compose.dev.yml           # Local dev: adds Caddy reverse proxy
Caddyfile                        # Caddy config for local dev

config/                          # Django project config
  settings/ (base.py, dev.py, prod.py), urls.py, wsgi.py, asgi.py

apps/
  accounts/                      # Custom User model (admin/member roles), auth views
  emails/                        # Email pipeline, dashboard views, assignment service
    services/                    # gmail_poller, ai_processor, chat_notifier, pipeline, spam_filter
    management/commands/         # run_scheduler, test_pipeline, set_mode
    templatetags/email_tags.py   # Priority/status color helpers
  core/                          # SoftDeleteModel, TimestampedModel, SystemConfig, health

templates/
  base.html                      # Dark sidebar layout, Tailwind v4 + HTMX 2.0 CDN
  registration/login.html        # Glassmorphism login
  emails/
    email_list.html              # Dashboard: stats bar, tabs, filters, card list + detail panel
    activity_log.html            # MIS activity log with stats and filters
    _email_card.html             # Email card partial (HTMX OOB swap support)
    _email_detail.html           # Detail panel partial (timeline activity, draft reply)
    _email_list_body.html        # Card list + pagination partial
    _activity_feed.html          # Activity feed entries partial
    inspect.html                 # Dev inspector (Phase 2.5)

nginx/triage.conf                # Production reverse proxy for triage.vidarbhainfotech.com
.github/workflows/deploy.yml     # v2 CI/CD: tag → test → SSH deploy → docker compose up
```

### v1 File Structure (main branch — production)

```
main.py                          # Entry point: scheduler, health server
config.yaml                      # Non-sensitive defaults
agent/                           # Gmail poller, AI processor, Sheet logger, Chat notifier,
                                 #   SLA monitor, EOD reporter, state, utils
prompts/triage_prompt.txt        # System prompt with injection defense
templates/eod_email.html         # Jinja2 HTML template for EOD report
tests/                           # 123 unit tests + 8 integration tests
scripts/run_local.sh             # Local dev runner
.github/workflows/deploy.yml     # Tag v*.*.* → test → build → deploy to Cloud Run
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.11 on Google Cloud Run (`asia-south1`, 256Mi, min-instances=1) |
| **AI** | Anthropic Claude: Haiku 4.5 (default) + Sonnet 4.5 (CRITICAL escalation) |
| **Email** | Gmail API with domain-wide delegation via service account |
| **Database** | Google Sheets API v4 with in-memory caching |
| **Alerts** | Google Chat Incoming Webhooks (Cards v2 format) |
| **Scheduling** | APScheduler (CronTrigger for EOD, IntervalTrigger for SLA) |
| **CI/CD** | GitHub Actions with Workload Identity Federation (keyless) |
| **Secrets** | GCP Secret Manager (API keys, webhook URL, service account JSON) |
| **Resilience** | tenacity (retry with exponential backoff) |

---

## Configuration

All runtime settings live in the **Agent Config** tab of the Google Sheet. Changes take effect on the next poll cycle &mdash; no redeploy needed.

### Dynamic Settings (Hot-Reload)

| Setting | Default | Description |
|---------|---------|-------------|
| Poll Interval (seconds) | `300` | How often to check for new emails (60&ndash;3600) |
| Monitored Inboxes | `info@, sales@` | Comma-separated inbox addresses |
| EOD Recipients | *(from env)* | Comma-separated &mdash; edit in Sheet, no redeploy |
| Claude Model | `claude-haiku-4-5` | Default AI model for triage |
| Escalation Model | `claude-sonnet-4-5` | Model used when Haiku returns CRITICAL |
| Max Tokens | `512` | AI response token limit |
| SLA Check Interval | `900` | Seconds between SLA breach scans |

### Feature Flags

| Flag | Default | Effect |
|------|---------|--------|
| AI Triage Enabled | `TRUE` | When OFF, emails are logged but not AI-triaged |
| Chat Notifications Enabled | `TRUE` | When OFF, no Chat alerts (Sheet logging continues) |
| EOD Email Enabled | `TRUE` | When OFF, skip EOD email (Chat summary still sent) |
| Quiet Hours Enabled | `TRUE` | When OFF, Chat alerts fire 24/7 |
| Quiet Hours Start/End | `20:00 / 08:00` | IST window for Chat suppression |

### Environment Variables & Secrets

| Variable | Source | Description |
|----------|--------|-------------|
| `GOOGLE_SHEET_ID` | Cloud Run env | Google Sheets spreadsheet ID |
| `MONITORED_INBOXES` | Cloud Run env | Comma-separated inbox emails |
| `ADMIN_EMAIL` | Cloud Run env | Admin email (used for Gmail impersonation) |
| `EOD_RECIPIENTS` | Cloud Run env | Comma-separated report recipients |
| `EOD_SENDER_EMAIL` | Cloud Run env | Sender for EOD emails (defaults to ADMIN_EMAIL) |
| `ANTHROPIC_API_KEY` | Secret Manager | Claude API key |
| `GOOGLE_CHAT_WEBHOOK_URL` | Secret Manager | Chat space webhook URL |
| `/secrets/service-account.json` | Secret Manager (file) | GCP service account credentials |

---

## Google Sheet Tabs

The Google Sheet serves as both database and configuration panel:

| Tab | Purpose | Auto-Created |
|-----|---------|:---:|
| **Email Log** | All triaged emails: ticket #, category, priority, SLA, summary, Gmail link | On first email |
| **Agent Config** | 16-field live config panel + agent status + error logs | On startup |
| **SLA Config** | Per-category SLA hour overrides (editable by team) | On startup |
| **Team** | Team roster for AI assignee matching (names, emails, specializations) | Manual setup |
| **Dashboard** | Real-time stats: open tickets, SLA compliance, category distribution | On startup |
| **Change Log** | Audit trail of system events and configuration changes | On startup |
| **Cost Tracker** | Daily AI usage: API calls by model, estimated cost, monthly total | On first EOD |
| **Failed Triage** | Dead letter tab: failed emails with error details for manual review | On first failure |

---

## Deployment

### CI/CD (Recommended)

Deploys are triggered by version tags only &mdash; pushing to `main` does NOT deploy:

```bash
git tag -a v1.2.0 -m "Description of release"
git push origin main --tags
```

This triggers a single workflow (`deploy.yml`) with three sequential jobs:
1. **Test**: Run unit tests
2. **Deploy**: Docker build &rarr; Push to Artifact Registry &rarr; Deploy to Cloud Run &rarr; Chat notification
3. **Release**: GitHub Release with auto-generated changelog

Pull requests to `main` run tests only (no deploy).

### CLI Options

```bash
python main.py                # Full agent (scheduler + health server)
python main.py --once         # Single poll cycle and exit
python main.py --eod          # Trigger EOD report immediately
python main.py --sla          # Run SLA check immediately
python main.py --retry        # Run dead letter retry immediately
python main.py --init-sheet   # Initialize sheet headers + config tab
```

---

## Development & Testing

### Local Dev Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with real values (Sheet ID, inboxes, admin email, etc.)
   ```

3. **Place service account key:**
   ```bash
   # Copy your SA key JSON to the project root (already in .gitignore)
   cp ~/path/to/sa-key.json ./service-account.json
   ```

4. **Run locally:**
   ```bash
   ./scripts/run_local.sh --once    # Single poll cycle
   ./scripts/run_local.sh --eod     # Test EOD report
   ./scripts/run_local.sh --sla     # Test SLA check
   ./scripts/run_local.sh           # Continuous mode
   ```

### Running Tests

```bash
# Unit tests (no API keys or external services needed)
pytest -m "not integration" -v

# Integration tests (requires ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY=sk-... pytest -m integration -v

# With coverage
pytest -m "not integration" --cov=agent --cov-report=term-missing
```

123 unit tests use mocks for all external services (Gmail, Sheets, Chat, Claude). The CI pipeline runs unit tests on every version tag push and PR before deploying.

---

## Security

| Layer | Implementation |
|-------|---------------|
| **Network** | Cloud Run with `--no-allow-unauthenticated` (IAM-only access) |
| **Credentials** | All secrets in GCP Secret Manager, mounted at runtime. Never in code. |
| **CI/CD Auth** | Workload Identity Federation &mdash; no long-lived service account keys in GitHub |
| **AI Safety** | 10-rule prompt injection defense in system prompt; email content treated as untrusted |
| **Input** | Control characters and null bytes stripped before AI processing |
| **Container** | Non-root `agent` user; Python 3.11 slim base image |
| **Gmail** | Domain-wide delegation scoped to minimum required APIs (read, labels, modify, send) |
| **Data** | All data stays in `asia-south1` (Mumbai) for Indian data residency compliance |

---

## Monitoring

### Logs

```bash
# Recent logs
gcloud run services logs read vipl-email-agent \
  --region=asia-south1 --project=utilities-vipl --limit=30

# Filter for errors
gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR' \
  --project=utilities-vipl --limit=20
```

### Health Check

The `/health` endpoint returns:

```json
{
  "status": "healthy",
  "uptime_seconds": 86412,
  "ai_stats": {
    "total_calls": 147,
    "failures": 2,
    "haiku_calls": 142,
    "sonnet_calls": 5
  },
  "last_poll": "2026-02-16T14:30:00+05:30"
}
```

### Key Metrics to Watch

| Metric | Where | Alert Threshold |
|--------|-------|----------------|
| AI failure rate | Health endpoint, Cost Tracker | > 5% of calls |
| SLA breach count | EOD report, SLA summary | Any CRITICAL breach |
| Daily email volume | EOD report | Sudden drop (poller may be stuck) |
| Monthly AI cost | Cost Tracker tab | > $25 (investigate volume spike) |
| Container restarts | Cloud Run console | > 2/day (memory or crash issue) |

---

## Cost Breakdown

| Component | Monthly Cost | Notes |
|-----------|:---:|-------|
| Cloud Run | ~$3-5 | 256Mi, min-instances=1, asia-south1 |
| Claude AI (Haiku) | ~$3-10 | 30-80 emails/day @ ~$0.001/email |
| Claude AI (Sonnet) | ~$1-5 | Only CRITICAL emails @ ~$0.01/email |
| Google Sheets API | Free | Within default quotas |
| Gmail API | Free | Within default quotas |
| Secret Manager | ~$0.06 | 3 secrets, negligible |
| **Total** | **< $25/mo** | **Full autonomous email agent** |

---

## Version History

| Version | Date | Highlights |
|:---:|:---:|------------|
| **1.1.3** | Mar 2026 | Production hardening: circuit breaker, email-loss prevention (label after log), Sheet write retries, Claude output validation, config locking, 123 tests |
| **1.1.0** | Mar 2026 | Reliability + intelligence: dead letter retry, multi-language triage, PDF attachment analysis, config audit log, configurable sender email |
| **1.0.0** | Feb 2026 | Production release: dynamic config, feature flags, quiet hours, SLA summaries, retry/resilience, dead letter, structured logging, cost tracking, CI/CD hardening |
| 0.7.0 | Feb 2026 | CI/CD with GitHub Actions + Workload Identity Federation |
| 0.6.0 | Feb 2026 | Dedup simplification, thread cache, first-poll backfill |
| 0.5.0 | Feb 2026 | Two-tier AI (Haiku + Sonnet), cost optimization |
| 0.4.0 | Feb 2026 | EOD email report with Jinja2 HTML template |
| 0.3.0 | Jan 2026 | Google Chat alerts, SLA breach monitoring |
| 0.2.0 | Jan 2026 | Claude AI triage, categorization, priority |
| 0.1.0 | Jan 2026 | Initial prototype: Gmail polling, Sheet logging |

---

## Documentation

| Document | Description |
|----------|-------------|
| [`CLAUDE.md`](CLAUDE.md) | Architecture reference for AI-assisted development |
| [`CHANGELOG.md`](CHANGELOG.md) | Full changelog with all versions |

---

<div align="center">

**Built for Vidarbha Infotech Pvt. Ltd., Nagpur**

*Saving 10+ hours/week of manual email triage since January 2026*

</div>
