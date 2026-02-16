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
    → SLAMonitor (every 15 min, checks deadlines)
    → EODReporter (daily 7 PM IST + on every startup)
```

Runs on Cloud Run with `--no-allow-unauthenticated`, `256Mi` memory, `min-instances=1`.

## File Structure

```
main.py                      # Entry point — scheduler, health server, pipeline
config.yaml                  # Non-sensitive defaults (secrets come from env vars)
deploy.sh                    # One-command deploy to Cloud Run
Dockerfile                   # Python 3.11-slim, non-root user
requirements.txt             # Dependencies

agent/
  gmail_poller.py            # Polls Gmail via domain-wide delegation
  ai_processor.py            # Two-tier Claude AI (Haiku + Sonnet escalation)
  sheet_logger.py            # Google Sheets read/write with in-memory caching
  chat_notifier.py           # Google Chat Cards v2 webhook notifications
  sla_monitor.py             # SLA breach detection and alerts
  eod_reporter.py            # Daily summary email + Chat card
  state.py                   # In-memory SLA alert cooldowns (no file I/O)

prompts/
  triage_prompt.txt          # System prompt for Claude triage (with injection defense)

templates/
  eod_email.html             # Jinja2 HTML template for EOD email

scripts/
  deploy_cloudrun.sh         # Alternate deploy script
  sheet_changelog.gs         # Google Apps Script for Sheet change logging

tests/
  test_ai_processor.py
  test_sla_monitor.py
  sample_emails.json
```

## Key Design Decisions

### Two-Tier AI (Cost Optimization)
- **Default**: Claude Haiku (`claude-haiku-4-5-20251001`) — ~$0.25/MTok
- **Escalation**: Claude Sonnet (`claude-sonnet-4-5-20250929`) — only for CRITICAL priority emails
- Prompt caching via `cache_control: {"type": "ephemeral"}` on system prompt (~90% savings on repeated calls)
- Spam pre-filter: 13 regex patterns skip Claude entirely ($0 cost)
- Body truncation: max 1500 chars sent to Claude
- Target cost: ~$8-10/month (down from ~$54/month with Sonnet for everything)

### Dedup Strategy (Two Layers Only)
1. **Gmail query filter**: `-label:Agent/Processed` + `after:{startup_epoch}` — prevents old emails from being fetched
2. **Google Sheet thread ID cache**: `sheet_logger.is_thread_logged()` — in-memory set refreshed every 2 minutes

There is NO `state.json` — Cloud Run's ephemeral filesystem makes file-based persistence useless.

### State Management
`StateManager` is pure in-memory. It only tracks:
- SLA alert cooldowns (which tickets were already alerted, to prevent spam)
- These reset on restart — worst case is one duplicate alert, which is acceptable

### Email Polling Flow
- **First poll on startup**: Fetches latest 5 emails from inbox (`query="in:inbox"`, `maxResults=5`)
- **Subsequent polls**: Only emails received AFTER agent started + not labeled (`after:{epoch} -label:Agent/Processed`, `maxResults=10`)
- Gmail label `Agent/Processed` is applied immediately after fetching
- Poller does NOT do any dedup — it just fetches and labels. Dedup is in `main.py` via the Sheet cache.

### EOD Report
- Fires daily at 7 PM IST (configurable via config.yaml or Agent Config sheet)
- Also fires on every startup/deploy
- Sends to **Google Chat first** (always works), then **email** (requires gmail.send scope)
- Chat and email are independent try blocks — one failing doesn't kill the other
- Recipients come from `EOD_RECIPIENTS` env var

### Google Sheet Structure
- **Email Log** tab: All triaged emails with ticket numbers, priority, category, SLA deadlines, status
- **SLA Config** tab: Per-category SLA hours (overrides config.yaml defaults)
- **Agent Config** tab: Runtime config overrides (poll interval, EOD time, etc.) + agent status display
- **Team** tab: Team member list for assignment suggestions
- Timestamps use `valueInputOption="RAW"` to prevent Google Sheets date serial conversion
- Sheet thread ID cache: refreshed every 2 min; SLA config cache: refreshed every 1 hour

## Configuration

### Environment Variables (set in Cloud Run)
```
GOOGLE_SHEET_ID              # Spreadsheet ID
MONITORED_INBOXES            # Comma-separated: info@vidarbhainfotech.com,sales@vidarbhainfotech.com
ADMIN_EMAIL                  # shreyas@vidarbhainfotech.com
EOD_RECIPIENTS               # Comma-separated email recipients for EOD report
```

### Secrets (Google Secret Manager)
```
ANTHROPIC_API_KEY            # Claude API key
GOOGLE_CHAT_WEBHOOK_URL      # Chat space webhook
/secrets/service-account.json # Service account key (file mount)
```

### Config Override Priority
1. Environment variables (highest)
2. Google Sheet "Agent Config" tab (read once on startup)
3. config.yaml (lowest — non-sensitive defaults)

## Deployment

```bash
cd ~/vipl-email-agent && ./deploy.sh
```

This pulls latest from `main`, builds the container via Cloud Build, deploys to Cloud Run in `asia-south1`.

### GCP Project
- Project: `utilities-vipl`
- Region: `asia-south1`
- Container registry: `asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent`
- Service account: `vipl-email-agent@utilities-vipl.iam.gserviceaccount.com`

## Security

### Domain-Wide Delegation
The service account uses Google Workspace domain-wide delegation to impersonate inbox users (info@, sales@) and the admin user (shreyas@) for sending EOD emails. Authorized scopes in Google Workspace Admin:
- `gmail.readonly`, `gmail.labels`, `gmail.modify` — for reading/labeling inbox emails
- `gmail.send` — for sending EOD email reports
- `spreadsheets` — for Google Sheets access
- `drive` — for Sheet access

### Service Account Key
- Stored in Google Secret Manager, mounted at `/secrets/service-account.json` on Cloud Run
- NOT in the git repo (gitignored)
- Two keys exist — only one should be active. Delete the unused one.

### Prompt Injection Defense
`triage_prompt.txt` has 10 rules telling Claude to ignore instructions embedded in email content. This prevents malicious emails from manipulating triage output. The worst case with a successful injection is wrong categorization — not code execution.

### Cloud Run Security
- `--no-allow-unauthenticated` — no public access
- Non-root Docker user (`agent`)
- Health endpoint at `/health` returns "OK" — no sensitive data exposed

## Known Issues / Pending

- **EOD email** may fail if `gmail.send` scope hasn't propagated in domain-wide delegation. Chat notification works independently.
- **Agent Config sheet overrides** are only read on startup, not dynamically. Changing values requires redeploy.
- **"Closed Today" stat** in EOD depends on someone manually setting Status to "Closed" in the Sheet. No auto-close mechanism exists.
- **SLA business hours mode** is stubbed — `_business_hours_elapsed()` just returns wall-clock timestamp. Only wall-clock SLA works currently.

## Common Tasks

### Run one poll cycle locally
```bash
python main.py --once --config config.yaml
```

### Trigger EOD report manually
```bash
python main.py --eod --config config.yaml
```

### Initialize/reset Sheet headers
```bash
python main.py --init-sheet --config config.yaml
```

### Check logs after deploy
```bash
gcloud run services logs read vipl-email-agent --region=asia-south1 --project=utilities-vipl --limit=50
```

### View token usage stats
`AIProcessor.get_usage_stats()` returns total input/output tokens, call count, and cache hits for cost monitoring.
