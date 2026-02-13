# 📧 VIPL Email Agent

**AI-powered shared inbox monitoring, triage & response system for [Vidarbha Infotech](https://vidarbhainfotech.com)**

Built with Claude AI · Google Workspace · Cloud Run

---

## How It Works

```
📬 Gmail Inboxes     🤖 Claude AI        📊 Google Sheets     💬 Google Chat
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ info@vipl    │───▶│  Categorize  │───▶│  Log Ticket  │───▶│  Alert Team  │
│ sales@vipl   │    │  Prioritize  │    │  Track SLA   │    │  SLA Breach  │
│              │    │  Draft Reply │    │  EOD Report  │    │  Daily Brief │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

Every **5 minutes**, the agent polls monitored inboxes for new emails. Each email is triaged by Claude AI into one of 8 categories with a priority level, summary, and draft reply — then logged to Google Sheets and announced in Google Chat.

---

## Features

| Feature | Description |
|---------|-------------|
| **AI Triage** | Categorizes emails into Government/Tender, Sales Lead, Support Request, Complaint, Partnership, Vendor, Internal, General Inquiry |
| **Priority Assessment** | CRITICAL → LOW based on business impact, sender importance, and urgency |
| **Draft Replies** | Professional acknowledgement drafts ready for team review |
| **SLA Tracking** | Per-category deadlines with automatic breach alerts |
| **Google Chat Cards** | Rich notifications with buttons to open Gmail and the tracker |
| **EOD Reports** | Daily summary email + Chat notification at 7 PM IST |
| **Sheet-Based Config** | All settings editable in Google Sheets — no code changes needed |
| **Live Agent Logs** | Latest 5 log entries visible in the config sheet |
| **Prompt Injection Defense** | Email content treated as untrusted data, never followed as instructions |

---

## Architecture

```
vipl-email-agent/
├── main.py                  # Entry point, scheduler, health server
├── config.yaml              # Non-sensitive defaults
├── deploy.sh                # One-command deploy to Cloud Run
├── Dockerfile               # Python 3.11 slim container
├── cloudbuild.yaml          # CI/CD via Cloud Build
├── agent/
│   ├── gmail_poller.py      # Gmail API polling with domain-wide delegation
│   ├── ai_processor.py      # Claude API integration (tool-use)
│   ├── sheet_logger.py      # Google Sheets read/write + config tab
│   ├── chat_notifier.py     # Google Chat webhook notifications
│   ├── sla_monitor.py       # SLA deadline checker with breach alerts
│   ├── eod_reporter.py      # End-of-day summary generator
│   └── state.py             # Persistent state (processed threads, failures)
└── prompts/
    └── triage_prompt.txt    # System prompt with injection defense
```

---

## Configuration

All runtime settings live in the **"Agent Config"** tab of the Google Sheet:

| Setting | Default | Description |
|---------|---------|-------------|
| Poll Interval (seconds) | 300 | How often to check for new emails |
| SLA Alert Cooldown (hours) | 4 | Hours between repeated breach alerts |
| EOD Report Hour (IST) | 19 | Hour to send the daily summary |
| EOD Report Minute | 0 | Minute for the EOD report |
| Admin Email | shreyas@vidarbhainfotech.com | Primary admin |
| EOD Recipients | shreyas@vidarbhainfotech.com | Daily report recipients |
| Monitored Inboxes | info@, sales@ | Inboxes being watched |
| Claude Model | claude-sonnet-4-5 | AI model for triage |

The config tab includes data validation, color formatting, and instructions for each field. The agent reads these values on startup.

---

## Secrets & Environment

| Secret | Source | Description |
|--------|--------|-------------|
| `ANTHROPIC_API_KEY` | Secret Manager | Claude API key |
| `GOOGLE_CHAT_WEBHOOK_URL` | Secret Manager | Chat space webhook |
| `sa-key` | Secret Manager (file mount) | Service account JSON |
| `GOOGLE_SHEET_ID` | Environment variable | Tracker spreadsheet ID |
| `MONITORED_INBOXES` | Environment variable | Comma-separated inboxes |
| `ADMIN_EMAIL` | Environment variable | Admin email address |
| `EOD_RECIPIENTS` | Environment variable | EOD report recipients |

---

## Deploy

### One-Command Deploy (Cloud Shell)

```bash
./deploy.sh
```

This pulls the latest code, builds the container, deploys to Cloud Run, and shows recent logs.

### Manual Deploy

```bash
# Build
gcloud builds submit \
  --tag asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent:latest \
  --project=utilities-vipl

# Deploy
gcloud run deploy vipl-email-agent \
  --image=asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent:latest \
  --region=asia-south1 \
  --project=utilities-vipl
```

### CLI Options

```bash
python main.py                # Full agent (scheduler + health server)
python main.py --once         # Single poll cycle and exit
python main.py --eod          # Trigger EOD report
python main.py --sla          # Run SLA check
python main.py --init-sheet   # Initialize sheet headers + config tab
```

---

## Google Sheet Structure

| Tab | Purpose |
|-----|---------|
| **Email Log** | All triaged emails with ticket numbers, SLA status, formulas |
| **Agent Config** | Runtime configuration with validation and live logs |
| **SLA Config** | Per-category SLA hours and escalation emails |
| **Team** | Team members for assignment suggestions |

---

## SLA Defaults

| Category | Hours |
|----------|-------|
| Government/Tender | 4 |
| Complaint | 4 |
| Sales Lead | 4 |
| Support Request | 8 |
| General Inquiry | 24 |
| Partnership | 24 |
| Internal | 24 |
| Vendor | 48 |

---

## Security

- **No public access** — Cloud Run requires IAM authentication
- **Service account** mounted from Secret Manager (never in git)
- **Prompt injection defense** — emails are treated as untrusted data
- **Non-root container** — runs as `agent` user
- **Draft replies** never echo URLs, account numbers, or email data
- **Domain-wide delegation** scoped to Gmail read/modify only

---

## Logs

View recent logs:
```bash
gcloud run services logs read vipl-email-agent \
  --region=asia-south1 --project=utilities-vipl --limit=30
```

Live agent logs are also written to the **Agent Config** tab in the Google Sheet after every poll cycle.

---

*Built for Vidarbha Infotech Private Limited, Nagpur*
