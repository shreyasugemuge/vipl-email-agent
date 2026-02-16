# VIPL Email Agent

**AI-powered shared inbox monitoring, triage & response system for [Vidarbha Infotech](https://vidarbhainfotech.com)**

Built with Claude AI · Google Workspace · Cloud Run

---

## How It Works

```
Gmail Inboxes     Claude AI          Google Sheets      Google Chat
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ info@vipl    │─▶│  Categorize  │─▶│  Log Ticket  │─▶│  Alert Team  │
│ sales@vipl   │  │  Prioritize  │  │  Track SLA   │  │  SLA Summary │
│              │  │  Draft Reply │  │  EOD Report  │  │  Daily Brief │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

Every **5 minutes**, the agent polls monitored inboxes. Each email is triaged by Claude AI into one of 8 categories with priority, summary, and draft reply — then logged to Google Sheets and announced in Google Chat.

---

## Features

| Feature | Description |
|---------|-------------|
| **AI Triage** | 8 categories: Government/Tender, Sales Lead, Support Request, Complaint, Partnership, Vendor, Internal, General Inquiry |
| **Two-Tier AI** | Haiku (cheap) for all emails, Sonnet only if CRITICAL — ~$1.50/mo vs $19/mo |
| **Priority Assessment** | CRITICAL → LOW based on business impact and urgency |
| **Draft Replies** | Professional acknowledgement drafts ready for team review |
| **SLA Tracking** | Per-category deadlines with 3x daily breach summary (9 AM, 1 PM, 5 PM) |
| **Quiet Hours** | No Chat alerts 8 PM – 8 AM IST (configurable) |
| **Feature Flags** | AI, Chat, EOD Email — all toggleable from Google Sheets |
| **Hot-Reload Config** | All settings reload every poll cycle — no redeploy needed |
| **EOD Reports** | Daily summary email + Chat card at 7 PM IST + on every deploy |
| **Dead Letter Tab** | Failed triages logged for manual review |
| **Structured Logging** | JSON logs for Cloud Logging with component, tokens, cost |
| **Health Endpoint** | JSON status with uptime, AI stats, failure count |
| **Resilience** | Claude API retries 3x with exponential backoff on transient errors |
| **Cost Tracker** | Daily AI usage logged to Google Sheets after each EOD report |
| **Prompt Injection Defense** | Email content treated as untrusted data |

---

## Architecture

```
vipl-email-agent/
├── main.py                  # Entry point, scheduler, health server
├── config.yaml              # Non-sensitive defaults
├── Dockerfile               # Python 3.11 slim container
├── requirements.txt
├── agent/
│   ├── gmail_poller.py      # Gmail API polling with domain-wide delegation
│   ├── ai_processor.py      # Claude AI with retry, spam filter, cost tracking
│   ├── sheet_logger.py      # Google Sheets CRUD + config tab + dead letter
│   ├── chat_notifier.py     # Google Chat webhook (Cards v2)
│   ├── sla_monitor.py       # SLA breach detection with 3x daily summary
│   ├── eod_reporter.py      # End-of-day summary (email + Chat)
│   ├── state.py             # In-memory SLA cooldowns (no file I/O)
│   └── utils.py             # Shared utilities (datetime parsing, IST)
├── prompts/
│   └── triage_prompt.txt    # System prompt with injection defense
├── templates/
│   └── eod_email.html       # Jinja2 HTML template for EOD email
└── .github/workflows/
    ├── deploy.yml           # CI/CD: push to main → Cloud Run
    └── release.yml          # Tag-triggered release + changelog
```

---

## Configuration

All runtime settings live in the **Agent Config** tab of the Google Sheet. Changes take effect on the next poll cycle (no redeploy needed):

| Setting | Default | Description |
|---------|---------|-------------|
| Poll Interval (seconds) | 300 | How often to check for new emails (60–3600) |
| SLA Alert Cooldown (hours) | 4 | Hours between repeated breach alerts |
| EOD Report Hour (IST) | 19 | Hour to send the daily summary |
| EOD Recipients | shreyas@ | Comma-separated — edit in Sheet, no redeploy |
| AI Triage Enabled | TRUE | Disable to skip AI (emails still logged) |
| Chat Notifications Enabled | TRUE | Disable to suppress Chat alerts |
| EOD Email Enabled | TRUE | Disable to skip EOD email (Chat still sent) |
| Quiet Hours Enabled | TRUE | Suppress Chat during off-hours |
| Quiet Hours Start/End | 20/8 | 8 PM – 8 AM IST |

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

### CI/CD (Recommended)

Push to `main` → GitHub Actions auto-deploys to Cloud Run via Workload Identity Federation.

### CLI Options

```bash
python main.py                # Full agent (scheduler + health server)
python main.py --once         # Single poll cycle and exit
python main.py --eod          # Trigger EOD report
python main.py --sla          # Run SLA check
python main.py --init-sheet   # Initialize sheet headers + config tab
```

---

## Google Sheet Tabs

| Tab | Purpose |
|-----|---------|
| **Email Log** | All triaged emails with ticket numbers, SLA status |
| **Agent Config** | Runtime config + live agent status + error logs |
| **SLA Config** | Per-category SLA hours and escalation emails |
| **Team** | Team members for assignment suggestions |
| **Cost Tracker** | Daily AI usage stats (auto-logged after EOD) |
| **Failed Triage** | Dead letter tab for emails that failed AI processing |

---

## Security

- **No public access** — Cloud Run requires IAM authentication
- **Service account** mounted from Secret Manager (never in git)
- **Prompt injection defense** — 10 rules in system prompt
- **Input sanitization** — control chars stripped before AI processing
- **Non-root container** — runs as `agent` user
- **Domain-wide delegation** scoped to minimum required Gmail/Sheets APIs
- **Workload Identity Federation** — no SA key stored in GitHub

---

## Logs

```bash
gcloud run services logs read vipl-email-agent \
  --region=asia-south1 --project=utilities-vipl --limit=30
```

Structured JSON logs flow to Cloud Logging. Live agent status is also visible in the Agent Config tab.

---

*Built for Vidarbha Infotech Private Limited, Nagpur*
