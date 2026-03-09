# External Integrations

**Analysis Date:** 2026-03-09

## APIs & External Services

**Anthropic Claude API:**
- Purpose: AI-powered email triage (categorize, prioritize, summarize, draft reply)
- SDK: `anthropic` 0.42.0 (`agent/ai_processor.py:163`)
- Auth: `ANTHROPIC_API_KEY` env var
- Models used: Haiku (default), Sonnet (CRITICAL escalation only)
- Features: Tool use for structured output, prompt caching, retry with tenacity
- Retry: 3x exponential backoff on `APIConnectionError`, `RateLimitError`, `InternalServerError` (`agent/ai_processor.py:281-286`)

**Gmail API (v1):**
- Purpose: Poll shared inboxes, read emails, label processed emails, send EOD reports
- SDK: `google-api-python-client` via `build("gmail", "v1", ...)` (`agent/gmail_poller.py:68`, `agent/eod_reporter.py:65`)
- Auth: Service account with domain-wide delegation
- Scopes (polling): `gmail.readonly`, `gmail.labels`, `gmail.modify` (`agent/gmail_poller.py:23-27`)
- Scopes (sending): `gmail.send` (`agent/eod_reporter.py:25-27`)
- Key operations:
  - `messages.list` + `messages.get` for polling (`agent/gmail_poller.py:266-285`)
  - `messages.modify` for labeling processed emails (`agent/gmail_poller.py:97-103`)
  - `messages.attachments.get` for PDF downloads (`agent/gmail_poller.py:211-223`)
  - `messages.send` for EOD email reports (`agent/eod_reporter.py:246-248`)
  - `labels.list` + `labels.create` for "Agent/Processed" label (`agent/gmail_poller.py:74-89`)

**Google Sheets API (v4):**
- Purpose: Ticket database (source of truth), SLA config, team roster, agent config, cost tracking
- SDK: `google-api-python-client` via `build("sheets", "v4", ...)` (`agent/sheet_logger.py:44-47`)
- Auth: Service account
- Scopes: `spreadsheets`, `drive` (`agent/sheet_logger.py:24-27`)
- Spreadsheet ID: `GOOGLE_SHEET_ID` env var
- Tabs: Email Log, SLA Config, Team, Change Log, Agent Config, Cost Tracker, Failed Triage
- Key operations:
  - `values().get/append/update` for CRUD (`agent/sheet_logger.py`)
  - `batchUpdate` for formatting (`agent/sheet_logger.py`)
  - Retry: 3x exponential backoff on `HttpError` with 429/500/503 status codes

**Google Chat API (Webhooks):**
- Purpose: Real-time notifications (poll summaries, SLA breaches, EOD summaries, deployments)
- Client: `httpx` HTTP POST to incoming webhook URL (`agent/chat_notifier.py:39`)
- Auth: `GOOGLE_CHAT_WEBHOOK_URL` env var (secret)
- Format: Cards v2 with `decoratedText` widgets (`agent/chat_notifier.py:111-132`)
- Message types:
  - Startup notification (plain text) (`agent/chat_notifier.py:62-73`)
  - Poll summary card (batch, max 10 items shown) (`agent/chat_notifier.py:79-132`)
  - SLA breach summary card (3x daily) (`agent/chat_notifier.py:138-185`)
  - EOD summary card (`agent/chat_notifier.py:196-229`)
  - Simple text messages (dead letter alerts) (`agent/chat_notifier.py:54-56`)

## Data Storage

**Databases:**
- Google Sheets (primary, v1 source of truth)
  - Connection: `GOOGLE_SHEET_ID` env var
  - Client: `google-api-python-client` (Sheets API v4)
  - Thread ID cache: in-memory with 2-min TTL for dedup (`agent/sheet_logger.py`)

**File Storage:**
- Local filesystem only (no cloud storage)
- Service account key mounted at `/secrets/service-account.json` in Cloud Run

**Caching:**
- In-memory only (no Redis/Memcached)
  - Gmail service instances cached per inbox (`agent/gmail_poller.py:53`)
  - Label IDs cached per inbox (`agent/gmail_poller.py:54`)
  - Thread ID cache with TTL for dedup in SheetLogger
  - SLA alert cooldowns in StateManager (`agent/state.py:24`)
  - Config snapshot for change detection (`agent/state.py:26`)

## Authentication & Identity

**Auth Provider:**
- Google Workspace service account with domain-wide delegation
  - Key file: `/secrets/service-account.json` (mounted from Secret Manager)
  - Impersonates inbox users for Gmail access (`agent/gmail_poller.py:63-68`)
  - Impersonates admin email for sending EOD reports (`agent/eod_reporter.py:60-65`)
  - Direct credentials for Sheets API (`agent/sheet_logger.py:44-47`)
  - Service account email: `vipl-email-agent@utilities-vipl.iam.gserviceaccount.com`

**CI/CD Auth:**
- Workload Identity Federation (no SA key in GitHub)
  - Provider: `secrets.WIF_PROVIDER` GitHub secret
  - Service account: `secrets.WIF_SERVICE_ACCOUNT` GitHub secret
  - Used in: `.github/workflows/deploy.yml:64-66`

## Monitoring & Observability

**Error Tracking:**
- No external service (Sentry, etc.)
- In-memory `AgentLogBuffer` stores last 50 error/highlight entries (`main.py:74-97`)
- Errors written to "Agent Config" sheet tab via `sheet.write_agent_status()` (`main.py:496`)
- Failed triages logged to "Failed Triage" sheet tab (`main.py:479`)

**Logs:**
- JSON structured logging to stdout (`main.py:42-57`)
- Format: `{"timestamp", "severity", "component", "message", ...extra fields}`
- Extra fields: `inbox`, `thread_id`, `cost_usd`, `model`, `tokens`, `ticket`
- Consumed by Cloud Run / Cloud Logging (GCP)

**Health Check:**
- HTTP endpoint on port 8080 at `/health` (`main.py:600-653`)
- Returns JSON with: status, uptime, started_at, current_time, ai_usage stats, consecutive_failures
- Docker HEALTHCHECK every 30s (`Dockerfile:22-23`)

**Cost Tracking:**
- In-memory token counters in `AIProcessor` class variables (`agent/ai_processor.py:131-134`)
- Daily cost logged to "Cost Tracker" sheet tab after EOD report (`agent/eod_reporter.py:223-228`)
- Cache hit rate tracked for prompt caching effectiveness

## CI/CD & Deployment

**Hosting:**
- Google Cloud Run (v1 production)
  - Region: `asia-south1`
  - Project: `utilities-vipl`
  - Single instance (min=1, max=1)
  - 256Mi memory, 1 CPU

**Container Registry:**
- Google Artifact Registry: `asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent`
- Tags: `{sha}`, `{version}`, `latest`

**CI Pipeline:**
- GitHub Actions (`.github/workflows/deploy.yml`)
- Trigger: Version tags (`v*.*.*`) for deploy, PRs for test only
- Jobs: test -> deploy -> release (sequential)
- Test: pytest on Python 3.11, unit tests only (`-m "not integration"`)
- Deploy: Build Docker image, push to Artifact Registry, deploy to Cloud Run
- Release: Auto-generate changelog, create GitHub Release

**Deployment Notifications:**
- Success: Cards v2 message to Google Chat with version, image, actor, inboxes
- Failure: Plain text alert to Google Chat

## Environment Configuration

**Required env vars (Cloud Run):**
- `GOOGLE_SHEET_ID` - Spreadsheet for ticket tracking
- `MONITORED_INBOXES` - Comma-separated inbox addresses (info@, sales@)
- `ADMIN_EMAIL` - Admin email address
- `EOD_RECIPIENTS` - Comma-separated EOD email recipients

**Required secrets (Google Secret Manager):**
- `anthropic-api-key` - Mapped to `ANTHROPIC_API_KEY`
- `chat-webhook-url` - Mapped to `GOOGLE_CHAT_WEBHOOK_URL`
- `sa-key` - Mounted at `/secrets/service-account.json`

**Optional env vars:**
- `EOD_SENDER_EMAIL` - Override sender for EOD emails (defaults to ADMIN_EMAIL)
- `PORT` - Health server port (defaults to 8080)

**Secrets location:**
- Production: Google Secret Manager (mounted into Cloud Run)
- Local dev: `.env` file (gitignored) + `service-account.json` (gitignored)
- CI/CD: GitHub Secrets (WIF_PROVIDER, WIF_SERVICE_ACCOUNT, plus env vars)

## Webhooks & Callbacks

**Incoming:**
- None (agent polls Gmail on a schedule, does not receive webhooks)

**Outgoing:**
- Google Chat webhook: Real-time notifications for new emails, SLA breaches, EOD summaries, deployments
  - URL pattern: `https://chat.googleapis.com/v1/spaces/*/messages?key=*&token=*`
  - Method: HTTP POST with JSON payload
  - Client: `httpx` (`agent/chat_notifier.py:39`)

## Startup Self-Test

The agent runs integration checks on startup (`main.py:660-712`):
1. Google Sheets API - Tests `spreadsheets.get()` call
2. Gmail API - Tests `users().getProfile()` on first inbox
3. Claude API - Verifies `ANTHROPIC_API_KEY` is set
4. Chat webhook - Validates URL starts with `https://chat.googleapis.com/`

All checks are non-blocking (agent starts regardless, logs warnings).

---

*Integration audit: 2026-03-09*
