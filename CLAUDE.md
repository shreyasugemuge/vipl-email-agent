# VIPL Email Agent

AI-powered shared inbox monitoring, triage, and response system for Vidarbha Infotech Private Limited.

## Version Status

| Version | Status | Platform |
|---------|--------|----------|
| **v1.x** (main branch) | Production — will be shut down after v2 migration | Google Cloud Run |
| **v2.0** (v2 branch) | **In Development** — full-stack rebuild | Self-hosted VM (Docker Compose) |

## v2 — What's Changing

Full-stack rebuild: Django backend with HTMX server-rendered frontend + PostgreSQL, deployed on the existing VIPL VM (already hosts Taiga + internal tools). Google Sheets becomes a read-only sync mirror, not the source of truth. Cloud Run will be shut down once v2 is live.

### v2 Target Stack
- **Backend**: Django 5.2 LTS + PostgreSQL (already on VM)
- **Frontend**: Django templates + HTMX + Tailwind CSS (server-rendered, no React/Node)
- **Deployment**: Docker Compose (single container: Django + Gunicorn), Nginx on host
- **Auth**: Simple password auth (Django built-in), Google OAuth deferred
- **Subdomain**: triage.vidarbhainfotech.com (configured, SSL via Let's Encrypt)

## v2 Architecture (Phase 1 Complete)

### v2 File Structure

```
manage.py
conftest.py
pytest.ini
gunicorn.conf.py
requirements.txt
requirements-dev.txt
.env.example
Dockerfile
docker-compose.yml
.dockerignore

config/
  __init__.py, settings/ (base.py, dev.py, prod.py), urls.py, wsgi.py, asgi.py

apps/
  __init__.py
  accounts/    # Custom User model (admin/member roles), auth views, admin
  emails/      # Email + AttachmentMetadata models (ready for Phase 2)
  core/        # SoftDeleteModel, TimestampedModel, health endpoint

templates/
  base.html, registration/login.html

nginx/
  triage.conf  # Reverse proxy for triage.vidarbhainfotech.com

.github/workflows/
  deploy.yml   # v2 CI/CD: tag → test → SSH deploy → docker compose up
```

### VM Details
- **VM**: `taiga` in GCP project `cm-sec-455407`, zone `asia-south1-b`, IP `35.207.237.47`
- **SSH user**: `shreyas_vidarbhainfotech_com` (gcloud compute ssh)
- **PostgreSQL**: Runs inside Taiga's Docker container (`taiga-docker-taiga-db-1`, postgres:12.3)
  - DB: `vipl_email_agent`, user: `vipl_agent`
  - Network: `taiga-docker_taiga` (172.18.0.0/16), DB IP: 172.18.0.6
- **Nginx**: Port 8100 → `triage.vidarbhainfotech.com` (SSL via Let's Encrypt)

### v2 Key Design Decisions (Phase 1)
- Python 3.13 venv required locally (system 3.9.6 too old for Django 5.2)
- SQLite for local dev/tests, PostgreSQL via `DATABASE_URL` in prod
- SoftDeleteModel base class (nothing ever truly deleted)
- APScheduler as separate management command (not inside Gunicorn)
- CI/CD: GitHub secrets set (`VM_HOST`, `VM_USER`, `VM_SSH_KEY` deploy key)

### v2 Testing

```bash
# Activate venv first
source .venv/bin/activate

# Run v2 tests
pytest -v
```

### v2 Common Tasks

```bash
source .venv/bin/activate
python manage.py runserver          # Local dev server
python manage.py createsuperuser    # Create admin user
python manage.py migrate            # Apply migrations
docker compose up -d                # Start production container
```

## v1 — Current Production (main branch)

Monitors Gmail shared inboxes (info@vidarbhainfotech.com, sales@vidarbhainfotech.com), triages emails using Claude AI, logs to a Google Sheet tracker, posts notifications to Google Chat, monitors SLA compliance, and sends daily EOD summary reports.

### v1 Architecture

```
Gmail Inboxes → GmailPoller (poll every 5 min)
    → AIProcessor (Haiku default, Sonnet for CRITICAL only)
    → SheetLogger (Google Sheets as database)
    → ChatNotifier (Google Chat webhook)
    → SLAMonitor (every 15 min, 3x daily summary)
    → EODReporter (daily 7 PM IST + startup during business hours)
```

Runs on Cloud Run with `--no-allow-unauthenticated`, `256Mi` memory, `min-instances=1`, `max-instances=1`.

## v1 File Structure

```
main.py                      # Entry point — scheduler, health server, JSON logging
config.yaml                  # Non-sensitive defaults (secrets from env vars)
Dockerfile                   # Python 3.11-slim, non-root user
requirements.txt
requirements-dev.txt         # Dev/test dependencies (pytest, pytest-cov)

agent/
  gmail_poller.py            # Polls Gmail via domain-wide delegation
  ai_processor.py            # Two-tier Claude AI with retry (tenacity), spam filter
  sheet_logger.py            # Google Sheets CRUD + config tab + dead letter (with retry)
  chat_notifier.py           # Google Chat Cards v2 webhook (poll, SLA summary, EOD)
  sla_monitor.py             # SLA breach detection — 3x daily summary (not per-ticket)
  eod_reporter.py            # Daily summary email + Chat card
  state.py                   # In-memory SLA cooldowns, failure tracking, EOD dedup
  utils.py                   # Shared utilities (parse_sheet_datetime, IST)

prompts/
  triage_prompt.txt          # System prompt for Claude triage (with injection defense)

templates/
  eod_email.html             # Jinja2 HTML template for EOD email

tests/
  conftest.py                # Shared fixtures (MockEmail, mock services, default config)
  test_*.py                  # 123 unit tests, all mocked (8 integration tests separate)
  sample_emails.json         # Fixture data for integration tests

scripts/
  run_local.sh               # Local dev runner (loads .env, validates SA key)

.github/workflows/
  deploy.yml                 # CI/CD: tag v*.*.* → test → build → deploy → GitHub Release
```

## Key Design Decisions

### Two-Tier AI (Cost Optimization)
- **Default**: Claude Haiku (`claude-haiku-4-5-20251001`) — ~$0.25/MTok
- **Escalation**: Claude Sonnet (`claude-sonnet-4-5-20250929`) — only for CRITICAL
- Prompt caching via `cache_control: {"type": "ephemeral"}` (~90% savings)
- Spam pre-filter: 13 regex patterns skip Claude entirely ($0 cost)
- Body truncation: max 1500 chars sent to Claude
- Retry: 3x with exponential backoff on transient errors (tenacity)
- Input sanitization: control chars stripped before AI processing
- Output validation: category/priority validated against allowed enums

### Email Safety
- Gmail "Agent/Processed" label applied AFTER successful Sheet log (not during poll)
- If Sheet write fails, email stays unlabeled and will be retried on next poll
- Sheet writes retry 3x with exponential backoff on transient API errors

### Circuit Breaker
- Tracks consecutive poll cycle failures via `StateManager`
- After `max_consecutive_failures` (default: 3), skips poll cycles to avoid hammering broken APIs
- Resets on first successful cycle
- Health endpoint reports failure count

### Dedup Strategy (Two Layers Only)
1. **Gmail query filter**: `-label:Agent/Processed` + `after:{startup_epoch}`
2. **Google Sheet thread ID cache**: `sheet_logger.is_thread_logged()` — 2 min TTL

No `state.json` — Cloud Run's ephemeral filesystem makes file persistence useless.

### Dynamic Config (Hot-Reload)
Config reloads from Agent Config sheet tab every poll cycle (thread-safe with lock):
- EOD recipients, poll interval, feature flags, quiet hours
- No redeploy needed for config changes
- Invalid values logged as warnings, previous config kept
- Override priority: env vars > Sheet > config.yaml

### Feature Flags (in Agent Config sheet)
- **AI Triage Enabled**: TRUE/FALSE — disable to skip Claude calls
- **Chat Notifications Enabled**: TRUE/FALSE — suppress all Chat alerts (including EOD Chat)
- **EOD Email Enabled**: TRUE/FALSE — skip EOD email only

### Quiet Hours
- Default: 8 PM – 8 AM IST (configurable in Sheet)
- Suppresses Chat notifications only — Sheet logging continues
- SLA breach summaries also suppressed during quiet hours

### SLA Monitoring
- **No per-ticket alert spam** — 3x daily summary at 9 AM, 1 PM, 5 PM IST
- Summary card shows breach count, worst-overdue-first, assignee info
- check() still runs every 15 min to keep Sheet SLA status current
- Unparseable deadlines marked as "ERROR" in Sheet for manual investigation
- Configurable via `sla.summary_hours` in config.yaml

### EOD Report
- Fires daily at 7 PM IST (configurable) + on startup (business hours 8 AM–9 PM IST only)
- Startup EOD deduplicated — won't send if already sent within 10 min
- Chat respects `Chat Notifications Enabled` flag, email respects `EOD Email Enabled` flag
- Recipients re-read from Agent Config sheet at send time
- Logs daily AI cost to Cost Tracker tab after each report

### Dead Letter & Retry
Failed triages logged to "Failed Triage" tab. Auto-retried every 30 min (max 3 attempts).
On exhaustion: marked "Exhausted" and Chat alert sent.

### Multi-Language Support
Emails in Hindi, Marathi, or Mixed are detected automatically. Summaries written in English for internal tracking. Draft replies composed in the original language.

### Attachment Analysis
PDF attachments extracted via pymupdf (first 3 pages, max 1000 chars, skip > 5 MB). Extracted text appended to Claude prompt for context-aware triage.

### Google Sheet Structure
- **Email Log** tab: All triaged emails with ticket numbers, priority, category, SLA deadlines, status
- **SLA Config** tab: Per-category SLA hours
- **Agent Config** tab: Runtime config + agent status display + error logs
- **Team** tab: Team member list for assignment suggestions
- **Cost Tracker** tab: Daily AI usage stats
- **Failed Triage** tab: Dead letter for failed processing
- **Change Log** tab: Audit trail of config changes

### Single-Instance Constraint
Ticket numbering uses an in-memory counter. This is safe with `max-instances=1` on Cloud Run.
If scaling to multiple instances, switch to a Sheet-based atomic counter.

## Configuration

### Environment Variables (set in Cloud Run)
```
GOOGLE_SHEET_ID              # Spreadsheet ID
MONITORED_INBOXES            # Comma-separated inboxes
ADMIN_EMAIL                  # shreyas@vidarbhainfotech.com
EOD_RECIPIENTS               # Comma-separated email recipients
EOD_SENDER_EMAIL             # (optional) Sender for EOD emails
```

### Secrets (Google Secret Manager)
```
ANTHROPIC_API_KEY            # Claude API key
GOOGLE_CHAT_WEBHOOK_URL      # Chat space webhook
/secrets/service-account.json # Service account key (file mount)
```

## Deployment

### CI/CD
Single workflow (`deploy.yml`) triggered by version tags only:
```
Tag v*.*.* → test → build → deploy to Cloud Run → GitHub Release
```
Push to `main` does NOT deploy. Pull requests run tests only.

### GCP Project
- Project: `utilities-vipl`
- Region: `asia-south1`
- Registry: `asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent`
- Service account: `vipl-email-agent@utilities-vipl.iam.gserviceaccount.com`

## Security

### Domain-Wide Delegation
Scopes: `gmail.readonly`, `gmail.labels`, `gmail.modify`, `gmail.send`, `spreadsheets`, `drive`

### Protections
- Cloud Run: `--no-allow-unauthenticated`, non-root Docker user
- SA key in Secret Manager only (gitignored)
- Prompt injection defense in system prompt (10 rules)
- Input sanitization before AI processing (control chars, null bytes)
- Workload Identity Federation for CI/CD (no SA key in GitHub)

## v1 Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run unit tests (no API keys needed) — 131 tests
pytest -m "not integration" -v

# Run integration tests (requires ANTHROPIC_API_KEY)
pytest -m integration -v

# Local dev run (requires .env + service-account.json)
./scripts/run_local.sh --once
```

## v1 Common Tasks

```bash
python main.py --once         # Single poll cycle
python main.py --eod          # Trigger EOD report
python main.py --sla          # Run SLA check
python main.py --retry        # Run dead letter retry
python main.py --init-sheet   # Initialize sheet headers + config tab
```

## Project Management (Taiga)

### Instance & Access
- **URL**: https://taiga.vidarbhainfotech.com/project/vipl-email-agent/
- **Credentials**: Stored locally in `.taiga-credentials` (gitignored, never committed)
- **API base**: `https://taiga.vidarbhainfotech.com/api/v1/`
- **Auth**: `POST /api/v1/auth` with `{"type": "normal", "username": "...", "password": "..."}` → returns `auth_token` → use as `Authorization: Bearer {token}`

### Project Structure
- **Methodology**: Scrum with Kanban board enabled
- **Project ID**: 14
- **Owner**: Shreyas (user ID 23)

### Current State (as of 2026-03-09)
- **v1.x history**: 13 epics (all Done), 99 stories (all Archived), 10 sprints (all Closed)
- **v2**: Phase 1 (Foundation) complete. Epics and stories being created for Phase 2+.

### Key IDs (for API calls)
```
User Story Statuses: New=120, Ready=121, In Progress=122, Ready for Test=123, Done=124, Archived=125
Epic Statuses:       New=64, Ready=65, In Progress=66, Ready for Test=67, Done=68
Task Statuses:       New=60, In Progress=61, Ready for Test=62, Closed=63, Needs Info=64
Issue Types:         Bug=37, Question=38, Enhancement=39, Task=40
Priorities:          Low=37, Normal=38, High=39, Critical=40
Points:              ½=147, 1=148, 2=149, 3=150, 5=151, 8=152, 10=153, 13=154
Roles:               UX=69, Design=70, Front=71, Back=72, PO=73, Stakeholder=74
```

### Wiki Pages
home, architecture, file-structure, configuration-guide, deployment-guide, development-guide, google-sheet-schema, version-history

### Tags
backend, ai, gmail, sheets, chat, sla, ci-cd, testing, security, docs, resilience, config

### Working with Taiga API
```bash
# Authenticate (credentials in .taiga-credentials)
curl -s -X POST "https://taiga.vidarbhainfotech.com/api/v1/auth" \
  -H "Content-Type: application/json" \
  -d '{"type": "normal", "username": "EMAIL", "password": "PASS"}'

# List stories
curl -s "https://taiga.vidarbhainfotech.com/api/v1/userstories?project=14" \
  -H "Authorization: Bearer {token}"

# Create story
curl -s -X POST "https://taiga.vidarbhainfotech.com/api/v1/userstories" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"project": 14, "subject": "...", "status": 120}'
```
