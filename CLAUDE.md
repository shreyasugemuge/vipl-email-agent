# VIPL Email Agent

AI-powered shared inbox monitoring, triage, and response system for Vidarbha Infotech Private Limited.

## Version Status

| Version | Status | Platform |
|---------|--------|----------|
| **v1.x** (main branch) | Frozen at v1.1.3 — Cloud Run decommissioned | Google Cloud Run (shut down) |
| **v2.0** (v2 branch) | **In Development** — Phase 3 complete, Phase 4 (assignment engine + SLA) next | Self-hosted VM (Docker Compose) |

## v2 — What's Changing

Full-stack rebuild: Django backend with HTMX server-rendered frontend + PostgreSQL, deployed on the existing VIPL VM (already hosts Taiga + internal tools). Google Sheets becomes a read-only sync mirror, not the source of truth. Cloud Run will be shut down once v2 is live.

### v2 Target Stack
- **Backend**: Django 4.2 LTS + PostgreSQL 12.3 (Taiga's existing DB container)
- **Frontend**: Django templates + HTMX + Tailwind CSS (server-rendered, no React/Node)
- **Email Pipeline**: Gmail poller → spam filter → Claude AI triage → PostgreSQL → Gmail label
- **Scheduler**: APScheduler management command (poll 5min, retry 30min, heartbeat 1min)
- **Notifications**: Google Chat Cards v2 webhook with quiet hours
- **Deployment**: Docker Compose (web + scheduler containers), Nginx on host
- **Auth**: Simple password auth (Django built-in), Google OAuth deferred
- **Subdomain**: triage.vidarbhainfotech.com (configured, SSL via Let's Encrypt)

## v2 Architecture

### v2 File Structure

```
manage.py
conftest.py
pytest.ini
gunicorn.conf.py
requirements.txt
requirements-dev.txt
.env.example                # Dev-safe defaults + prod template
Dockerfile
docker-compose.yml          # web + scheduler services
.dockerignore

config/
  __init__.py, settings/ (base.py, dev.py, prod.py), urls.py, wsgi.py, asgi.py

apps/
  __init__.py
  accounts/                 # Custom User model (admin/member roles), auth views, admin
  emails/                   # Email + AttachmentMetadata models, services, management commands
    views.py                # Dev inspector view (/emails/inspect/)
    urls.py                 # Email app URL routes
    services/               # gmail_poller, ai_processor, chat_notifier, pipeline, spam_filter, pdf_extractor, dtos, state, fake_data
    management/commands/    # run_scheduler, test_pipeline
  core/                     # SoftDeleteModel, TimestampedModel, SystemConfig, health endpoint

prompts/
  triage_prompt.txt         # v1 system prompt
  triage_prompt_v2.txt      # v2 system prompt for Django pipeline

templates/
  base.html, registration/login.html, accounts/dashboard.html
  emails/inspect.html       # Dev inspector template (dark-themed, no login)

nginx/
  triage.conf               # Reverse proxy for triage.vidarbhainfotech.com

secrets/                    # Service account key (gitignored, mounted read-only in Docker)

.github/workflows/
  deploy.yml                # v2 CI/CD: tag → test → SSH deploy → docker compose up
```

### VM Details
- **VM**: `taiga` in GCP project `cm-sec-455407`, zone `asia-south1-b`, IP `35.207.237.47`
- **SSH**: `gcloud compute ssh shreyas_vidarbhainfotech_com@taiga --project=cm-sec-455407 --zone=asia-south1-b`
- **Direct SSH**: `ssh -i ~/.ssh/google_compute_engine shreyas_vidarbhainfotech_com@35.207.237.47`
- **PostgreSQL**: Runs inside Taiga's Docker container (`taiga-docker-taiga-db-1`, postgres:12.3)
  - DB: `vipl_email_agent`, user: `vipl_agent`
  - Network: `taiga-docker_taiga` (172.18.0.0/16)
  - Docker Compose joins this network so web/scheduler containers reach DB by hostname
- **Nginx**: Port 8100 → `triage.vidarbhainfotech.com` (SSL via Let's Encrypt, HTTP→HTTPS redirect)
- **Deploy dir**: `/opt/vipl-email-agent/` (cloned, v2 branch, .env ready)
- **Other containers on VM**: vipl-backend(:5000), vipl-frontend(:8080), full Taiga stack(:9000)
- **Resources**: 2 vCPU, 12 GiB RAM, 96 GB disk (23% used)

### v2 Key Design Decisions
- Django 4.2 LTS (downgraded from 5.2 — PostgreSQL 12.3 on VM not supported by Django 5.2+)
- Python 3.13 venv locally, 3.11 in Docker
- SQLite for local dev/tests, PostgreSQL via `DATABASE_URL` in prod
- SoftDeleteModel base class (nothing ever truly deleted)
- SystemConfig model for runtime config (replaces Google Sheets config tab)
- APScheduler as separate `run_scheduler` management command (not inside Gunicorn)
- Two Docker services from same image: `web` (Gunicorn) + `scheduler` (APScheduler)
- Secrets volume mount: `./secrets:/app/secrets:ro` for service account key
- CI/CD: GitHub secrets set (`VM_HOST`, `VM_USER`, `VM_SSH_KEY` deploy key)

### v2 Phase Status
- **Phase 1** (Foundation): Complete — Django skeleton, auth, models, Docker, CI/CD
- **Phase 2** (Email Pipeline): Complete — Gmail poller, AI processor, chat notifier, pipeline orchestrator, scheduler, 95 tests, UAT 6/6 passed
- **Phase 2.5** (Dev Safety): Complete — `--once`/`--dry-run`, `test_pipeline`, dev inspector, fake data, dev-safe defaults
- **Phase 3** (Dashboard): Complete — Email card list, assignment workflow, detail panel, activity log MIS, premium UI, 136 tests, UAT 9/9 passed
- **Phase 4** (Assignment + SLA): Not started
- **Phase 5** (Reporting + Admin + Sheets Mirror): Not started
- **Phase 6** (Migration + Cutover): Not started

### v2 Email Pipeline Architecture (Phase 2)
```
Gmail Inboxes → GmailPoller (domain-wide delegation)
    → SpamFilter (13 regex patterns, $0 cost)
    → AIProcessor (Haiku default, Sonnet for CRITICAL, prompt caching)
    → Pipeline (save to PostgreSQL → label Gmail — label-after-persist safety)
    → ChatNotifier (Google Chat Cards v2, quiet hours via SystemConfig)
    → Dead Letter Retry (every 30min, max 3 attempts → exhausted)
    → Circuit Breaker (3 consecutive failures → skip cycles)
```

### v2 Service Modules (`apps/emails/services/`)
| Module | Purpose | Django imports? |
|--------|---------|-----------------|
| `dtos.py` | EmailMessage + TriageResult dataclasses | No |
| `spam_filter.py` | 13 regex patterns, returns TriageResult | No |
| `pdf_extractor.py` | pypdf, 3 pages, 1000 chars, 5MB limit | No |
| `state.py` | Circuit breaker + EOD dedup | No |
| `gmail_poller.py` | Gmail API, domain-wide delegation, labels | No |
| `ai_processor.py` | Two-tier Claude (Haiku/Sonnet), tenacity retry | No |
| `chat_notifier.py` | Google Chat Cards v2, quiet hours | Yes (SystemConfig) |
| `pipeline.py` | Orchestrator: poll→filter→triage→save→label | Yes (ORM) |
| `fake_data.py` | 11 sample emails (EN/HI/MR) + matched triages for dev/test | No |

### v2 Management Commands
| Command | Purpose | External Calls |
|---------|---------|----------------|
| `run_scheduler` | Production scheduler (poll + retry + heartbeat) | Gmail, Claude, Chat |
| `run_scheduler --once` | Single poll cycle, then exit | Gmail, Claude, Chat |
| `run_scheduler --once --dry-run` | Simulated cycle with fake data | **None** |
| `test_pipeline` | Process fake emails through pipeline | **None** |
| `test_pipeline --with-ai` | Fake emails + real Claude triage | Claude only |
| `test_pipeline --with-chat` | Fake emails + real Chat webhook | Chat only |
| `test_pipeline --count N` | Process N fake emails | Depends on flags |
| `set_mode` | Show current operating mode + config table | **None** |
| `set_mode off` | All disabled: no Gmail, no AI, no Chat | **None** |
| `set_mode dev` | Local dev: info@ inbox, real AI, no Chat | Claude only |
| `set_mode production` | Full pipeline: both inboxes, AI, Chat | Gmail, Claude, Chat |

### v2 Operating Modes

Switch with `python manage.py set_mode <mode>`. Each mode atomically sets `operating_mode`, `ai_triage_enabled`, `chat_notifications_enabled`, and `monitored_inboxes` in SystemConfig.

| Config | `off` | `dev` | `production` |
|--------|-------|-------|-------------|
| `ai_triage_enabled` | `false` | `true` | `true` |
| `chat_notifications_enabled` | `false` | `false` | `true` |
| `monitored_inboxes` | _(empty)_ | `info@vidarbhainfotech.com` | `info@,sales@vidarbhainfotech.com` |

Fresh installs default to **off** mode (seeded via migration). Mode is visible in `/health/` JSON, `/emails/inspect/` badge, and poll cycle logs.

### v2 SystemConfig (Runtime Config)
Replaces v1's Google Sheets config tab. Key-value store with typed casting (str/int/bool/float/json).
Seeded defaults: `ai_triage_enabled`, `chat_notifications_enabled` (false), `eod_email_enabled`, `poll_interval_minutes`, `quiet_hours_start/end`, `business_hours_start/end`, `max_consecutive_failures`, `monitored_inboxes` (empty).

**Dev-safe defaults**: `monitored_inboxes` is empty and `chat_notifications_enabled` is false in the seed migration. A fresh `migrate` on dev will not poll real inboxes or post to Chat. Production values are set via SystemConfig admin or environment variables.

### v2 Testing

```bash
source .venv/bin/activate

# --- Unit Tests (no API keys needed) ---
pytest -v                           # All 95 tests (Phase 1: 33, Phase 2: 62)
pytest apps/accounts -v             # Account/auth tests (19)
pytest apps/emails -v               # Email pipeline tests (48)
pytest apps/core -v                 # Core model + health + config tests (28)

# --- Dev Pipeline Testing (no external calls by default) ---
python manage.py test_pipeline                  # 1 fake email, all mocked
python manage.py test_pipeline --count 5        # 5 fake emails, all mocked
python manage.py test_pipeline --with-ai        # Real Claude (~$0.001/email)
python manage.py run_scheduler --once --dry-run # Simulated cycle with fake data

# --- Dev Inspector (visual output) ---
python manage.py runserver 8100
# → http://localhost:8100/emails/inspect/   (read-only, shows simulated Chat/reply output)

# --- Docker ---
docker compose build                # Verify Docker image builds
```

### v2 Dev Safety (Mode-Based)

| Concern | `off` (default) | `dev` | `production` |
|---------|----------------|-------|-------------|
| Gmail polling | Nothing polled (no inboxes) | info@ only | Both inboxes |
| AI triage | Disabled (fallback result) | Claude Haiku/Sonnet | Claude Haiku/Sonnet |
| Chat notifications | Off | Off | Google Chat webhook |
| Database | SQLite (local) | SQLite (local) | PostgreSQL on VM |
| External API calls | **None** | Claude only | Gmail + Claude + Chat |
| Missing API keys | Warns, uses fallback | Warns, uses fallback | Required |

**Credentials** (GCP Secret Manager, project `utilities-vipl`):
```bash
gcloud secrets versions access latest --secret=anthropic-api-key --project=utilities-vipl
gcloud secrets versions access latest --secret=chat-webhook-url --project=utilities-vipl
gcloud secrets versions access latest --secret=sa-key --project=utilities-vipl > secrets/service-account.json
```

### v2 Dashboard (Phase 3)

```
/emails/              → Email card list (filters, sorting, pagination, HTMX)
/emails/?view=unassigned  → Default manager view (unassigned queue)
/emails/?view=mine    → Team member's assigned emails
/emails/<pk>/detail/  → Slide-out detail panel (email body, draft reply, activity)
/emails/<pk>/assign/  → POST: Assign/reassign email (admin only)
/emails/<pk>/status/  → POST: Change status (Acknowledge/Close)
/emails/activity/     → Activity log (assignments, status changes)
```

**Dashboard stack**: Django templates + HTMX 2.0 (CDN) + Tailwind CSS v4 (CDN play script)
- `django-htmx` middleware for `request.htmx` detection (partials vs full pages)
- `nh3` for HTML sanitization of email body content (XSS protection)
- Card-based layout (Linear/Trello style) with slide-out detail panel
- URL-based filter state (bookmarkable: `/emails/?status=new&priority=HIGH`)
- ActivityLog model tracks all assignment and status change events
- Assignment notifications via Google Chat + Django email

**Template structure:**
```
templates/
  base.html                    # Sidebar + topbar layout, Tailwind/HTMX CDN
  emails/
    email_list.html            # Full page: tabs + filters + card list + detail panel
    _email_card.html           # Partial: single email card
    _email_list_body.html      # Partial: card list + pagination (HTMX swap target)
    _email_detail.html         # Partial: slide-out detail panel
    _assign_dropdown.html      # Partial: assignee dropdown
    _activity_feed.html        # Partial: activity log entries
    activity_log.html          # Full page: activity log
    inspect.html               # Dev inspector (Phase 2.5)
```

### v2 Common Tasks

```bash
source .venv/bin/activate
python manage.py runserver 8100     # Local dev server + inspector at /emails/inspect/
python manage.py createsuperuser    # Create admin user
python manage.py migrate            # Apply migrations
python manage.py test_pipeline      # Quick pipeline smoke test (safe, no API calls)
python manage.py run_scheduler      # Start production scheduler (poll + retry + heartbeat)
python manage.py run_scheduler --once          # Single poll cycle then exit
python manage.py run_scheduler --once --dry-run # Simulate with fake data, no external calls
docker compose build                # Build locally
# Deploy only when ready — do NOT docker compose up on VM without approval
```

## v1 — Frozen (main branch, v1.1.3)

Cloud Run service has been decommissioned. v1 deploy workflow is frozen. Code preserved on `main` branch for reference during v2 migration.

Previously monitored Gmail shared inboxes (info@vidarbhainfotech.com, sales@vidarbhainfotech.com), triaged emails using Claude AI, logged to a Google Sheet tracker, posted notifications to Google Chat, monitored SLA compliance, and sent daily EOD summary reports.

### v1 Architecture

```
Gmail Inboxes → GmailPoller (poll every 5 min)
    → AIProcessor (Haiku default, Sonnet for CRITICAL only)
    → SheetLogger (Google Sheets as database)
    → ChatNotifier (Google Chat webhook)
    → SLAMonitor (every 15 min, 3x daily summary)
    → EODReporter (daily 7 PM IST + startup during business hours)
```

Ran on Cloud Run (now shut down) with `--no-allow-unauthenticated`, `256Mi` memory, `min-instances=1`, `max-instances=1`.

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

### v2 CI/CD (deploy.yml on v2 branch)
```
Tag v*.*.* → test → SSH deploy to VM → docker compose build → up → migrate
```
Pull requests to `v2` run tests only. No Cloud Run — all VM-based.

### v1 CI/CD (FROZEN on main branch)
v1 workflow `Deploy & Release (v1 - FROZEN)` — will not deploy. Cloud Run shut down.

### GCP Projects
- **cm-sec-455407** (cm-sec): VMs — taiga, cm-sec-app-server, cm-sec-db-server
- **utilities-vipl**: v1 artifacts (Artifact Registry `vipl-repo` 741MB, Secret Manager: anthropic-api-key, chat-webhook-url, sa-key)
- Service account: `vipl-email-agent@utilities-vipl.iam.gserviceaccount.com`

### GitHub Secrets (10)
VM_HOST, VM_USER, VM_SSH_KEY, WIF_PROVIDER, WIF_SERVICE_ACCOUNT,
GOOGLE_SHEET_ID, GOOGLE_CHAT_WEBHOOK_URL, MONITORED_INBOXES, ADMIN_EMAIL, EOD_RECIPIENTS

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

## Project Management

Tracked via GitHub issues and CLAUDE.md phase status. Taiga instance exists at taiga.vidarbhainfotech.com but is not actively used for v2 development.
