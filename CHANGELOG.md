# Changelog

All notable changes to the VIPL Email Agent are documented here.

## [2.7.0] — Mar 2026

Gatekeeper role with category-scoped permissions, irrelevant email handling, bulk actions, and member reassignment. 843 tests.

### Added
- **Triage Lead role** — New role between admin and member: `can_triage` (mark irrelevant, manage settings), category-scoped assignment permissions
- **Mark Irrelevant** — Gatekeeper/admin can dismiss threads with required reason, modal UI, keyboard shortcut (I), revert-to-new
- **Member Reassign** — Members can reassign their own threads with reason, category-filtered candidate list
- **Bulk Actions** — Checkbox multi-select on thread cards, sticky action bar: bulk assign, mark irrelevant, undo
- **Unassigned Alerts** — Scheduled check for threads unassigned beyond threshold, Chat notification
- **Corrections Digest** — Weekly AI feedback summary from user corrections, scheduled delivery
- **Irrelevant status** — New thread status with gold badge on cards, filtered from default views

### Changed
- Role-based sidebar visibility (`can_triage`, `can_assign`, `can_approve_users` helpers)
- Context menu actions gated by user permissions
- Editable status/priority/category badges show read-only for non-owners
- Activity timeline renders irrelevant/revert/reassign events with distinct styling
- `reassigned_by_member` action type in ActivityLog

## [2.6.1] — Mar 2026

### Changed
- **Prominent assignee badges** — Avatar images from Google OAuth shown on thread cards (w-5) and detail panel (w-6); solid rose-colored initial fallback with white text; `is_auto_assigned` badge shown inline
- **Gold "Unassigned" state** — Unassigned threads show amber/gold badge with "Unassigned" text and circular person icon instead of invisible grey "---"
- **Bolder status badges** — Background opacity increased from `/8` to `/15`, font bumped to `font-bold uppercase tracking-wider`, `reopened` status gets distinct gold color
- **Editable status badge bump** — Tailwind shades from `-50`/`-600` to `-100`/`-700`, larger dot indicator, increased padding
- **Editable priority badge bump** — Background `-50` to `-100`, text `-700` to `-800` for consistency

### Documentation
- CLAUDE.md: Added "Design System" section documenting hand-crafted CSS, theme tokens, class conventions
- README.md: Added "Design System" section, version history entries for v2.6.0 and v2.6.1, dark/light mode feature
- CHANGELOG.md: Added v2.6.0 and v2.6.1 entries
- Memory: Updated project state and design system origin

## [2.6.0] — Mar 2026

Full UI revamp — the retro v2 design becomes the default for all pages with dark/light theme support.

### Added
- **Dark/light theme toggle** — `data-theme` attribute on `<html>`, CSS variables scoped per theme, sun/moon toggle in sidebar footer, persisted in `localStorage('vipl-theme')`
- **Anti-FOUC script** — Inline `<script>` in `<head>` sets theme before render
- **Chart.js theme awareness** — `getChartThemeColors()` helper reads CSS variables; charts destroy and recreate on theme toggle via `window.onThemeChange` hook
- **VIPL logo** — Brand logo image in sidebar replaces text "V"

### Changed
- **All `--pxl-*` vars renamed to `--vipl-*`** — Brand rose palette (#e06a97 dark / #a83262 light) replaces green neon (#00FF88)
- **All `.pxl-*` classes renamed to `.vipl-*`** — `.vipl-card`, `.vipl-nav-active`, `.vipl-select`, etc.
- **v2 design becomes default** — v2 templates renamed to primary names (dropped `_v2` suffix)
- **All pages themed** — Activity log, reports (Chart.js), settings + 7 tab partials, team, login, dev inspector, shared partials
- **CRT/scanline effects** scoped to dark mode only
- **Grid background** — Dark = line grid; Light = subtle dot grid
- **Body font** — Dark = JetBrains Mono; Light = Plus Jakarta Sans

### Removed
- `thread_list_v2()` and `thread_detail_v2()` view functions
- `_V2_TEMPLATE_MAP`, `_is_v2()`, `_tpl()` helpers
- `/emails/v2/` URL routes (replaced with redirect to `/emails/`)
- v1 templates moved to `to_delete/`

## [1.1.3] — Mar 2026

Full code review and production hardening release. 22 issues identified and fixed across all severity levels.

### Added
- **Circuit breaker** — `StateManager` tracks consecutive failures; polling pauses after 3+ failures to stop hammering dead APIs
- **EOD send deduplication** — 10-minute cooldown window prevents double EOD reports on startup + CronTrigger collision
- **Sheet write retries** — `log_email()` and related writes retry 3x with exponential backoff on transient `HttpError`
- **Claude output validation** — category and priority validated against allowed enums; hallucinated values default to "General Inquiry" / "MEDIUM"
- **SLA parse error handling** — malformed SLA deadlines now set status to "ERROR — Invalid deadline" instead of silent skip
- **Config parse warnings** — invalid Sheet config values (e.g., non-numeric poll interval) now log WARNING with the invalid value and range
- **11 new unit tests** — circuit breaker, EOD dedup, mark_processed label flow, output validation (123 total)

### Fixed
- **Email loss prevention** (CRITICAL) — Gmail "Agent/Processed" label now applied AFTER successful Sheet log, not during poll. If Sheet write fails, email is retried next cycle instead of permanently lost.
- **Startup EOD spam** — startup EOD report guarded by business hours check (8 AM–9 PM IST) and 10-min dedup window
- **Double GitHub Actions** — merged `deploy.yml` + `release.yml` into single workflow (test → deploy → release)
- **Dead letter retry missing PDF context** — `retry_failed_triages()` now passes `gmail_poller` for attachment extraction
- **Ticket counter crash** — malformed ticket numbers (e.g., "INF-" or "INF-abc") no longer crash startup; logged and skipped
- **Thread cache header row** — dedup cache now skips header row (`values[1:]`), preventing false positive on "Gmail Thread ID" text
- **EOD Chat ignores feature flag** — EOD Chat summary now respects `Chat Notifications Enabled` flag
- **Health endpoint crash** — wrapped status builder in try-except; returns `{"status": "degraded"}` instead of 500 on failure
- **SIGTERM delay** — replaced `signal.pause()` with `time.sleep(10)` loop for faster graceful shutdown
- **HTML entity decoding** — `_strip_html()` now calls `html.unescape()` for cleaner email body extraction
- **Config hot-reload race** — added `threading.Lock()` to prevent concurrent config reads during retry jobs
- **Repo cleanup** — removed `to_delete/` from git tracking, added to `.gitignore`; updated docs

## [1.1.0] — Mar 2026

### Added
- **Unit test suite** — 112 tests covering all modules with mocked external services
- **Local dev environment** — `scripts/run_local.sh` + expanded `.env.example` for running against prod
- **CI test gate** — unit tests run on every push and PR before deploy
- **Dev dependencies** — `requirements-dev.txt` with pytest and pytest-cov
- **Test fixtures** — shared `conftest.py` with MockEmail, mock services, default config
- **PR trigger** — CI now runs tests on pull requests to main
- **Configurable EOD sender email** — `EOD_SENDER_EMAIL` env var with Sheet hot-reload override
- **Config change audit log** — detects config changes and logs diffs to Change Log tab
- **Dead letter retry** — auto-retries failed triages every 30 min (max 3 attempts), `--retry` CLI flag
- **Multi-language triage** — detects Hindi, Marathi, Mixed languages; replies in original language; Language column in Sheet
- **Attachment analysis** — extracts PDF text (first 3 pages, max 1000 chars) via pymupdf, included in Claude prompt

### Fixed
- **NUM_CONFIG_FIELDS off-by-one** — constant now matches actual CONFIG_FIELDS list length
- **SLA status never written** — `update_sla_status()` writes "Breached" to column M in Email Log
- **Timestamp labeled IST but was UTC** — `ai_processor.py` now converts to IST before formatting
- **Deploy spam** — test-only changes no longer trigger Cloud Run deploys

## [1.0.0] — Mar 2026

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
