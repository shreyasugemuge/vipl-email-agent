# Technology Stack

**Analysis Date:** 2026-03-09

## Languages

**Primary:**
- Python 3.11 (Docker) / 3.9.6 (local dev) - All application code

**Secondary:**
- HTML/CSS - EOD email template (`templates/eod_email.html`)
- YAML - Configuration (`config.yaml`, `.github/workflows/deploy.yml`)

## Runtime

**Environment:**
- Python 3.11-slim (Docker container on Cloud Run)
- Local dev: Python 3.9.6

**Package Manager:**
- pip (standard)
- Lockfile: None (pinned versions in `requirements.txt`)

## Frameworks

**Core:**
- No web framework - Uses `http.server.HTTPServer` from stdlib for health endpoint (`main.py:647`)
- APScheduler 3.10.4 - Background job scheduling for polling, SLA checks, EOD reports (`main.py:721`)

**Testing:**
- pytest 8.3.4 - Test runner (`requirements-dev.txt`)
- pytest-cov 5.0.0 - Coverage reporting (`requirements-dev.txt`)

**Build/Dev:**
- Docker (python:3.11-slim base image) - `Dockerfile`
- GitHub Actions - CI/CD (`.github/workflows/deploy.yml`)

## Key Dependencies

**Critical (core functionality):**
- `anthropic` 0.42.0 - Claude AI API client for email triage (`agent/ai_processor.py`)
- `google-api-python-client` 2.114.0 - Gmail API + Sheets API client (`agent/gmail_poller.py`, `agent/sheet_logger.py`, `agent/eod_reporter.py`)
- `google-auth` 2.27.0 - Service account auth with domain-wide delegation (`agent/gmail_poller.py:63`)
- `google-auth-httplib2` 0.2.0 - HTTP transport for Google API auth

**Infrastructure:**
- `httpx` 0.27.0 - HTTP client for Google Chat webhook posts (`agent/chat_notifier.py:39`)
- `apscheduler` 3.10.4 - Cron + interval job scheduling (`main.py:721-740`)
- `tenacity` 8.2.3 - Retry with exponential backoff on API calls (`agent/ai_processor.py:281`, `agent/sheet_logger.py`)
- `jinja2` 3.1.3 - HTML templating for EOD email reports (`agent/eod_reporter.py:53`)
- `pymupdf` 1.24.3 - PDF text extraction from email attachments (`agent/ai_processor.py:218`)

**Utility:**
- `pyyaml` 6.0.1 - YAML config file parsing (`main.py:113`)
- `python-dateutil` 2.8.2 - Date parsing utilities
- `pytz` 2024.1 - IST timezone handling throughout (`agent/utils.py:13`)

## Configuration

**Environment Variables (required at runtime):**
- `GOOGLE_SHEET_ID` - Spreadsheet ID for ticket tracking
- `MONITORED_INBOXES` - Comma-separated Gmail inbox addresses
- `ADMIN_EMAIL` - Admin email (shreyas@vidarbhainfotech.com)
- `EOD_RECIPIENTS` - Comma-separated EOD report recipients
- `EOD_SENDER_EMAIL` - (optional) Sender for EOD emails

**Secrets (Google Secret Manager, mounted at runtime):**
- `ANTHROPIC_API_KEY` - Claude API key
- `GOOGLE_CHAT_WEBHOOK_URL` - Google Chat space webhook
- `/secrets/service-account.json` - Google service account key (file mount)

**Configuration Files:**
- `config.yaml` - Non-sensitive defaults (poll intervals, SLA hours, model names, quiet hours)
- `.env.example` - Template for local development env vars (`.env` is gitignored)

**Config Priority (highest to lowest):**
1. Environment variables
2. Google Sheet "Agent Config" tab (hot-reload every poll cycle)
3. `config.yaml` defaults

**Build:**
- `Dockerfile` - Single-stage build, non-root user, health check on port 8080
- No build step beyond `pip install` (pure Python, no compilation)

## Platform Requirements

**Development:**
- Python 3.9+ (3.11 recommended)
- `service-account.json` with domain-wide delegation
- `ANTHROPIC_API_KEY` for Claude API access
- Google Workspace with Gmail + Sheets access

**Production:**
- Google Cloud Run (asia-south1 region)
  - 256Mi memory, 1 CPU
  - min-instances=1, max-instances=1 (single-instance constraint for ticket numbering)
  - `--no-allow-unauthenticated`
- Google Secret Manager for secrets
- Artifact Registry: `asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent`
- GCP Project: `utilities-vipl`

**v2 Target (in development on `v2` branch):**
- FastAPI + React + PostgreSQL on self-hosted VM
- Docker Compose (2 containers: backend + frontend)
- Google Sheets becomes read-only sync mirror

## AI Models

**Primary (cost tier):**
- Claude Haiku (`claude-haiku-4-5-20251001`) - Default for all emails, ~$0.25/MTok
- Config: `config.yaml` → `claude.model`

**Escalation (quality tier):**
- Claude Sonnet (`claude-sonnet-4-5-20250929`) - Only for CRITICAL priority emails
- Config: `config.yaml` → `claude.escalation_model`

**Cost Optimizations:**
- Prompt caching via `cache_control: {"type": "ephemeral"}` (~90% savings)
- Spam pre-filter: 13 regex patterns skip Claude entirely ($0 cost) (`agent/ai_processor.py:38-52`)
- Body truncation: max 1500 chars sent to Claude (`agent/ai_processor.py:56`)
- Tool use for structured output (no parsing needed) (`agent/ai_processor.py:79-124`)

---

*Stack analysis: 2026-03-09*
