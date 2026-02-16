# Changelog

All notable changes to the VIPL Email Agent are documented here.

## [Unreleased] — v1.0.0 Release Candidate

### Added
- **Structured JSON logging** for Cloud Logging compatibility
- **Health endpoint** returns JSON with uptime, AI stats, component status
- **Startup self-test** verifies Sheets, Gmail, Claude, Chat connectivity on boot
- **Cost Tracker tab** — daily AI usage stats logged after each EOD report
- **Dynamic config reload** — Agent Config sheet re-read every poll cycle (no redeploy needed)
- **Feature flags** — AI Triage, Chat Notifications, EOD Email toggleable from Sheet
- **Quiet hours** — suppresses Chat alerts 8 PM – 8 AM IST (configurable)
- **SLA breach summary** — 3x daily (9 AM, 1 PM, 5 PM) replaces per-ticket spam
- **Dead letter tab** — "Failed Triage" tab logs emails that failed AI processing
- **Retry with backoff** — Claude API retries 3x on transient errors (tenacity)
- **Input sanitization** — control chars stripped from email content before AI
- **Shared utilities** — `agent/utils.py` with `parse_sheet_datetime()` and IST
- **CI/CD pipeline** — GitHub Actions auto-deploy on push to main (WIF, no SA key)
- **Release pipeline** — tag-triggered GitHub Release with auto-changelog

### Changed
- EOD recipients now re-read from Sheet at send time (add without redeploy)
- SLA monitor uses summary-based alerts instead of per-ticket Chat spam
- Agent Config tab expanded: 16 config fields (was 9) with feature flags + quiet hours
- All formatting row indices in Agent Config computed dynamically
- AI processor model default corrected to Haiku in Sheet config

### Fixed
- EOD email scope: removed `https://mail.google.com/` (only `gmail.send` needed)
- Chat and email send in independent try blocks (one failing doesn't kill the other)
- CI/CD env vars with @ characters handled via `--env-vars-file`

### Security
- Input sanitization strips null bytes and control chars before Claude
- Workload Identity Federation for CI/CD (no SA key stored in GitHub)

## [0.1.0] — Initial Development

- Gmail polling with domain-wide delegation
- Two-tier AI triage (Haiku + Sonnet escalation)
- Google Sheets as database with in-memory caching
- Google Chat Cards v2 notifications
- SLA monitoring with per-ticket breach alerts
- EOD summary email + Chat notification
- Sheet-based config with Agent Config tab
- Prompt injection defense in system prompt
- Spam pre-filter (13 regex patterns)
- Non-root Docker container on Cloud Run
