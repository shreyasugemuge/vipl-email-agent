# VIPL Email Agent

AI-powered shared inbox monitoring, triage, and response system for Vidarbha Infotech Private Limited. Deployed on Google Cloud Run.

## What This Does

Monitors Gmail shared inboxes (info@vidarbhainfotech.com, sales@vidarbhainfotech.com), triages emails using Claude AI, logs to a Google Sheet tracker, posts notifications to Google Chat, monitors SLA compliance, and sends daily EOD summary reports.

## Architecture

```
Gmail Inboxes → GmailPoller (poll every 5 min)
    → AIProcessor (Haiku default, Sonnet for CRITICAL only)
    → SheetLogger (Google Sheets as database)
    → ChatNotifier (Google Chat webhook)
    → SLAMonitor (every 15 min, 3x daily summary)
    → EODReporter (daily 7 PM IST + on every startup)
```

Runs on Cloud Run with `--no-allow-unauthenticated`, `256Mi` memory, `min-instances=1`.

## File Structure

```
main.py                      # Entry point — scheduler, health server, JSON logging
config.yaml                  # Non-sensitive defaults (secrets from env vars)
Dockerfile                   # Python 3.11-slim, non-root user
requirements.txt
requirements-dev.txt             # Dev/test dependencies (pytest, pytest-cov)

agent/
  gmail_poller.py            # Polls Gmail via domain-wide delegation
  ai_processor.py            # Two-tier Claude AI with retry (tenacity), spam filter
  sheet_logger.py            # Google Sheets CRUD + config tab + dead letter
  chat_notifier.py           # Google Chat Cards v2 webhook (poll, SLA summary, EOD)
  sla_monitor.py             # SLA breach detection — 3x daily summary (not per-ticket)
  eod_reporter.py            # Daily summary email + Chat card
  state.py                   # In-memory SLA alert cooldowns (no file I/O)
  utils.py                   # Shared utilities (parse_sheet_datetime, IST)

prompts/
  triage_prompt.txt          # System prompt for Claude triage (with injection defense)

templates/
  eod_email.html             # Jinja2 HTML template for EOD email

tests/
  conftest.py                # Shared fixtures (MockEmail, mock services, default config)
  test_*.py                  # Unit tests for each module (92 tests, all mocked)
  sample_emails.json         # Fixture data for integration tests

scripts/
  run_local.sh               # Local dev runner (loads .env, validates SA key)

.github/workflows/
  deploy.yml                 # CI/CD: test → build → deploy to Cloud Run
  release.yml                # Tag-triggered release with auto-changelog
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

### Dedup Strategy (Two Layers Only)
1. **Gmail query filter**: `-label:Agent/Processed` + `after:{startup_epoch}`
2. **Google Sheet thread ID cache**: `sheet_logger.is_thread_logged()` — 2 min TTL

No `state.json` — Cloud Run's ephemeral filesystem makes file persistence useless.

### Dynamic Config (Hot-Reload)
Config reloads from Agent Config sheet tab every poll cycle:
- EOD recipients, poll interval, feature flags, quiet hours
- No redeploy needed for config changes
- Override priority: env vars > Sheet > config.yaml

### Feature Flags (in Agent Config sheet)
- **AI Triage Enabled**: TRUE/FALSE — disable to skip Claude calls
- **Chat Notifications Enabled**: TRUE/FALSE — suppress all Chat alerts
- **EOD Email Enabled**: TRUE/FALSE — skip email, keep Chat summary

### Quiet Hours
- Default: 8 PM – 8 AM IST (configurable in Sheet)
- Suppresses Chat notifications only — Sheet logging continues
- SLA breach summaries also suppressed during quiet hours

### SLA Monitoring
- **No per-ticket alert spam** — 3x daily summary at 9 AM, 1 PM, 5 PM IST
- Summary card shows breach count, worst-overdue-first, assignee info
- check() still runs every 15 min to keep Sheet SLA status current
- Configurable via `sla.summary_hours` in config.yaml

### EOD Report
- Fires daily at 7 PM IST (configurable) + on every startup/deploy
- Chat first (always), then email (independently)
- Recipients re-read from Agent Config sheet at send time
- Logs daily AI cost to Cost Tracker tab after each report

### Dead Letter
Failed triages logged to "Failed Triage" tab with timestamp, inbox, sender, subject, error, thread ID.

### Google Sheet Structure
- **Email Log** tab: All triaged emails with ticket numbers, priority, category, SLA deadlines, status
- **SLA Config** tab: Per-category SLA hours
- **Agent Config** tab: Runtime config + agent status display + error logs
- **Team** tab: Team member list for assignment suggestions
- **Cost Tracker** tab: Daily AI usage stats
- **Failed Triage** tab: Dead letter for failed processing

## Configuration

### Environment Variables (set in Cloud Run)
```
GOOGLE_SHEET_ID              # Spreadsheet ID
MONITORED_INBOXES            # Comma-separated inboxes
ADMIN_EMAIL                  # shreyas@vidarbhainfotech.com
EOD_RECIPIENTS               # Comma-separated email recipients
```

### Secrets (Google Secret Manager)
```
ANTHROPIC_API_KEY            # Claude API key
GOOGLE_CHAT_WEBHOOK_URL      # Chat space webhook
/secrets/service-account.json # Service account key (file mount)
```

## Deployment

### CI/CD (Primary)
Push to `main` → GitHub Actions auto-deploys via Workload Identity Federation.
Tag `v*.*.*` → creates GitHub Release with auto-changelog.

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

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run unit tests (no API keys needed)
pytest -m "not integration" -v

# Run integration tests (requires ANTHROPIC_API_KEY)
pytest -m integration -v

# Local dev run (requires .env + service-account.json)
./scripts/run_local.sh --once
```

## Common Tasks

```bash
python main.py --once         # Single poll cycle
python main.py --eod          # Trigger EOD report
python main.py --sla          # Run SLA check
python main.py --init-sheet   # Initialize sheet headers + config tab
```
