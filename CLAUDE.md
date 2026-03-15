# VIPL Email Agent

AI-powered shared inbox monitoring, triage, and response system for Vidarbha Infotech Private Limited.

## Status

| Version | Status | Platform |
|---------|--------|----------|
| **v2.6.1** (main branch) | **Complete** — prominent assignee/status badges | Self-hosted VM (Docker Compose) |
| **v2.6.0** (main branch) | **Complete** — full UI revamp, dark/light mode | Self-hosted VM (Docker Compose) |
| **v2.5.4** (merged) | **Complete** — 24 UI/UX fixes | Self-hosted VM (Docker Compose) |
| **v1.x** (archived in git history) | Frozen at v1.1.3 — Cloud Run decommissioned | Google Cloud Run (shut down) |

**Live URL**: https://triage.vidarbhainfotech.com
**GitHub Release**: v2.5.11 (latest deployed)

## Active Branches

| Branch | Worktree | Purpose | Status |
|--------|----------|---------|--------|
| `main` | `.` | Production branch, deployed to VM | v2.5.4 deployed |
| `feature/analytics-dashboard` | `../vipl-email-agent-analytics` | Analytics & reporting dashboard | Not started |
| `feature/gatekeeper-role` | `../vipl-email-agent-gatekeeper` | Gatekeeper role feature | In progress |

## Stack
- **Backend**: Django 4.2 LTS + PostgreSQL 12.3 (Taiga's existing DB container)
- **Frontend**: Django templates + HTMX 2.0 + Tailwind CSS v4 (server-rendered, no React/Node)
- **Email Pipeline**: Gmail poller → spam filter → Claude AI triage → PostgreSQL → Gmail label
- **Scheduler**: APScheduler management command (poll 5min, retry 30min, heartbeat 1min)
- **Notifications**: Google Chat Cards v2 webhook with quiet hours
- **Deployment**: Docker Compose (web + scheduler containers), Nginx on host
- **Local Dev**: `runserver` + native Caddy (`triage.local` → `localhost:8000`)
- **Auth**: Google OAuth SSO (django-allauth) — @vidarbhainfotech.com only
- **CI/CD**: Release-triggered → test → SSH deploy to VM

## Architecture

### File Structure

```
manage.py
conftest.py
pytest.ini
gunicorn.conf.py
requirements.txt
requirements-dev.txt
.env.example                # Dev-safe defaults + prod template
Dockerfile
docker-compose.yml          # Production: web + scheduler services
.dockerignore

config/
  __init__.py, settings/ (base.py, dev.py, prod.py), urls.py, wsgi.py, asgi.py

apps/
  __init__.py
  accounts/                 # Custom User model (admin/member roles), auth views, admin
  emails/                   # Email + AttachmentMetadata models, services, management commands
    views.py                # Dashboard views + dev inspector (/emails/inspect/)
    urls.py                 # Email app URL routes
    services/               # gmail_poller, ai_processor, chat_notifier, pipeline, spam_filter, pdf_extractor, dtos, state, fake_data, assignment, eod_reporter, sheets_sync, reports, distillation
    management/commands/    # run_scheduler, test_pipeline, set_mode
  core/                     # SoftDeleteModel, TimestampedModel, SystemConfig, health endpoint

prompts/
  triage_prompt.txt         # v1 system prompt (archived)
  triage_prompt_v2.txt      # v2 system prompt for Django pipeline

templates/
  base.html, registration/login.html, accounts/dashboard.html
  emails/                   # Card list, detail panel, activity log, partials, inspector

nginx/
  triage.conf               # Production reverse proxy for triage.vidarbhainfotech.com

secrets/                    # Service account key (gitignored, mounted read-only in Docker)

.github/workflows/
  ci.yml                    # CI: test on push/PR to main
  deploy.yml                # CD: deploy on GitHub Release published
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
- **Deploy dir**: `/opt/vipl-email-agent/` (cloned, main branch, .env configured)
- **Other containers on VM**: vipl-backend(:5000), vipl-frontend(:8080), full Taiga stack(:9000)
- **Resources**: 2 vCPU, 12 GiB RAM, 96 GB disk (23% used)
- **SSH user**: NOT in docker group — must use `sudo docker`

### Key Design Decisions
- Django 4.2 LTS (downgraded from 5.2 — PostgreSQL 12.3 on VM not supported by Django 5.2+)
- Python 3.13 venv locally, 3.11 in Docker
- SQLite for local dev/tests, PostgreSQL via `DATABASE_URL` in prod
- SoftDeleteModel base class (nothing ever truly deleted)
- SystemConfig model for runtime config (replaces Google Sheets config tab)
- APScheduler as separate `run_scheduler` management command (not inside Gunicorn)
- Two Docker services from same image: `web` (Gunicorn) + `scheduler` (APScheduler)
- Local dev: native Caddy proxies `triage.local` → `localhost:8000` (same pattern as vipms.local)
- Production: `docker-compose.yml` exposes port 8100 directly, Nginx on host handles SSL
- Secrets volume mount: `./secrets:/app/secrets:ro` for service account key
- CI/CD: GitHub secrets set (`VM_HOST`, `VM_USER`, `VM_SSH_KEY` deploy key)
- `ALLOWED_HOSTS` must include `localhost` for Docker healthcheck to pass

### Phase History
- **Phase 1** (Foundation): Django skeleton, auth, models, Docker, CI/CD
- **Phase 2** (Email Pipeline): Gmail poller, AI processor, chat notifier, pipeline orchestrator, scheduler
- **Phase 2.5** (Dev Safety): `--once`/`--dry-run`, `test_pipeline`, dev inspector, fake data, dev-safe defaults
- **Phase 3** (Dashboard): Email card list, assignment workflow, detail panel, activity log MIS, premium UI
- **Phase 4** (Assignment + SLA): Assignment engine, SLA tracking, Chat notifications
- **Phase 4.5** (Polish): Quiet hours fix, settings cleanup
- **Phase 5** (Reporting + Admin): EOD reporter, SystemConfig admin, Sheets sync mirror
- **Phase 6** (Migration + Cutover): Deploy to VM, merge v2→main, go live
- **Phase 7** (UI/UX Polish): HTMX loading indicator, button loading states, accessibility (skip-to-content, aria-labels, keyboard nav, focus-visible), mobile responsive (detail drawer, filter toggle, settings tab scroll, team table), toast improvements, visual polish
- **Phase 8** (OAuth Hardening): Google avatar fetch fix, `_update_avatar()` helper, structured OAuth logging, 22 edge case tests
- **Phase 9** (UI/UX v2 — PR #6): XML assignee cleanup, mobile detail panel with history API, clickable stat cards, welcome banner, collapsible filter panel with badge, keyboard nav (arrow keys), loading skeleton, scroll-snap, underline tabs, search icon
- **Phase 10** (Email Threads — PR #8): Thread model + data migration, cross-inbox dedup, pipeline thread integration, conversation UI with thread list/detail, internal notes, viewer tracking, thread assignment + collaboration
- **Phase 11** (UI/UX v3 — PR #9): QA verification (13/13 pass), inline bug fixes, milestone v2.3.6 archive
- **Phase 12** (Dashboard UX Overhaul — v2.4.0): Single sidebar merge (eliminated 220px inner sidebar), JS-based active state indicators (fixes HTMX partial swap bug), sender email on cards, poll epoch persistence (deploy safety), dev inspector poll countdown, settings UX (webhook masking, tab descriptions, SLA presets, config validation), timezone fix
- **Phase 13** (Production Hardening — v2.4.1): Inspect endpoint auth, SECRET_KEY crash-if-missing, HSTS/SSL/session headers, nh3 XSS fix, health endpoint auth, SOCIALACCOUNT_LOGIN_ON_GET=False, Gmail retry narrowing, @require_POST on clear_viewer, deploy migration ordering, Docker log rotation + resource limits, Gunicorn worker recycling, HTMX SRI hash, Nginx security headers + rate limiting, DB indexes (8 fields), N+1 query fixes (thread counts, sidebar/dash aggregates, inbox badges, team workload), SystemConfig TTL cache, SoftDeleteQuerySet
- **Phase 14** (UI/UX v4 — Holistic Overhaul): Expanded thread cards (AI summary, spam badge, AI suggestion on cards), separated AI sections in detail (summary always visible, reasoning/draft collapsible), AI summary inline editing with activity log, Triage Queue / My Inbox sidebar separation, clickable stat cards on all screens (thread list, activity, team), status/priority chip tooltips, PollLog model + pipeline MIS table + poll history in inspector, force poll button, team table JS filtering, stat card active states
- **v2.5.0 Phase 1** (Models + Migrations): ThreadReadState, SpamFeedback, SenderReputation models; ai_confidence field on Email + Thread; is_auto_assigned on Thread; category_overridden + priority_overridden override flags
- **v2.5.0 Phase 2** (AI Confidence + Auto-Assign): Three-tier confidence scoring (HIGH/MEDIUM/LOW), auto-assign when confidence >80%, confidence dots on thread cards, accept/reject AI suggestion UI, inline auto-assign in pipeline, feedback distillation into correction rules
- **v2.5.0 Phase 3** (Spam Learning + Bug Fixes): Mark spam/not-spam buttons, SenderReputation tracking, spam badge on cards, whitelist/blocked sender management, undo spam feedback, force poll fix, avatar dedup fix
- **v2.5.0 Phase 4** (Read/Unread Tracking): Per-user ThreadReadState, unread badge in sidebar, mark-as-unread button, unread card styling, keyboard shortcut (U), tab title with unread count
- **v2.5.0 Phase 5** (Editable Attrs + Context Menu): Inline dropdown editing for category/priority/status on thread detail, right-click context menu on thread cards with quick actions
- **v2.5.0 Phase 6** (Reports Module): Reports page with 4 tabs (Overview, Volume, Team, SLA), Chart.js charts, date range picker, aggregation service
- **v2.5.0 Phase 7** (Pipeline Override Guards): Override flag enforcement in update_thread_preview, auto_assign_confidence_tier config rename with data migration
- **v2.5.4 Phase 1** (Bug Fixes): Welcome banner dedup, pipeline unread state, REOPENED status, avatar sync, AI assign OOB swap
- **v2.5.4 Phase 2** (Thread Card & Detail UX): Expanded card spacing, pill-style dropdowns, context menu readability, AI draft copy button
- **v2.5.4 Phase 3** (Workflow Actions): Claim button with toast, spam toggle undo
- **v2.5.4 Phase 4** (Page Polish): Retro-modern login, grouped settings tabs, thread-grouped activity, sidebar version badge
- **v2.5.4 Phase 5** (Dev Inspector): Force poll inline results, poll history with intervals/dimming/timestamps
- **v2.5.4 Phase 6** (QA Bug Fixes): Thread count OOB filter sync, search view preservation, mobile drawer close, Escape key detail close
- **v2.5.4 Phase 7** (QA Cosmetic): Action button flex-wrap, reports title format, SLA chart zero-value handling
- **v2.6.0** (Full UI Revamp): V2 retro design becomes default for all pages, dark/light theme toggle (`data-theme` + localStorage), VIPL brand rose palette (`--vipl-*` CSS variables), CRT/scanline/glow effects dark-only, Chart.js theme-aware re-render, all templates themed (activity, reports, settings, team, login, inspector, partials), v1 templates moved to `to_delete/`, v2 views/routes removed
- **v2.6.1** (Prominent Badges): Bolder assignee badges with avatar image support and solid colored initials, gold "Unassigned" state, status badges with increased opacity/font weight/uppercase, `reopened` status gets gold color, editable status/priority badges bumped to `-100`/`-700` Tailwind shades

### Design System

The UI is a **100% hand-crafted CSS design system** — there is no external PxlKit or design framework dependency. The retro aesthetic (scanlines, CRT vignette, pixel corners, glow effects, custom color palette) is pure CSS written inline in `templates/base.html` (~220 lines of `<style>` block).

**Stack**: Django templates + HTMX 2.0 + Tailwind CSS v4 (utility classes only) + hand-crafted theme CSS.

**Theme system**: Dual dark/light mode via `data-theme="dark|light"` on `<html>`, CSS variables scoped per theme (`[data-theme="dark"] { --vipl-*: ... }`), persisted in `localStorage('vipl-theme')`, anti-FOUC script in `<head>`.

**Color tokens** (CSS variables in `base.html`): `--vipl-bg`, `--vipl-surface`, `--vipl-card`, `--vipl-card-hover`, `--vipl-border`, `--vipl-primary` (brand rose), `--vipl-primary-dim`, `--vipl-cyan`, `--vipl-gold`, `--vipl-red`, `--vipl-purple`, `--vipl-text`, `--vipl-text-dim`, `--vipl-text-muted`.

**Class conventions**: `.vipl-card` (card hover), `.vipl-card-selected`, `.vipl-nav-active`, `.vipl-view-active`, `.vipl-pill-active`/`.vipl-pill-inactive`, `.vipl-select`, `.vipl-stat-active`, `.vipl-filter-toggle`.

**Fonts**: Press Start 2P (pixel headings), JetBrains Mono (dark mode body), Plus Jakarta Sans (light mode body).

### Email Pipeline Architecture
```
Gmail Inboxes → GmailPoller (domain-wide delegation)
    → SpamFilter (13 regex patterns + SenderReputation blocked list, $0 cost)
    → AIProcessor (Haiku default, Sonnet for CRITICAL, prompt caching, confidence scoring)
    → Auto-Assign (HIGH confidence >80% → auto-assign by category rules)
    → Pipeline (save to PostgreSQL → label Gmail — label-after-persist safety)
    → ChatNotifier (Google Chat Cards v2, quiet hours via SystemConfig)
    → Feedback Loop (spam corrections → SenderReputation, AI corrections → distillation)
    → Dead Letter Retry (every 30min, max 3 attempts → exhausted)
    → Circuit Breaker (3 consecutive failures → skip cycles)
```

### Service Modules (`apps/emails/services/`)
| Module | Purpose | Django imports? |
|--------|---------|-----------------|
| `dtos.py` | EmailMessage + TriageResult dataclasses | No |
| `spam_filter.py` | 13 regex patterns, returns TriageResult | No |
| `pdf_extractor.py` | pypdf, 3 pages, 1000 chars, 5MB limit | No |
| `state.py` | Circuit breaker + EOD dedup | No |
| `gmail_poller.py` | Gmail API, domain-wide delegation, labels, UTC-aware epochs | No |
| `ai_processor.py` | Two-tier Claude (Haiku/Sonnet), tenacity retry | No |
| `chat_notifier.py` | Google Chat Cards v2, quiet hours | Yes (SystemConfig) |
| `pipeline.py` | Orchestrator: poll→filter→triage→save→label→persist epoch | Yes (ORM) |
| `fake_data.py` | 11 sample emails (EN/HI/MR) + matched triages for dev/test | No |
| `assignment.py` | Email assignment, status changes, notifications | Yes (ORM) |
| `eod_reporter.py` | Daily summary email + Chat card | Yes (ORM) |
| `sheets_sync.py` | Read-only Google Sheets mirror | Yes (ORM) |
| `reports.py` | Aggregation service for reports dashboard (categories, SLA, performance) | Yes (ORM) |
| `distillation.py` | Feedback distillation: user corrections → AI prompt correction rules | Yes (ORM) |

### Management Commands
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

### Operating Modes

Switch with `python manage.py set_mode <mode>`. Each mode atomically sets `operating_mode`, `ai_triage_enabled`, `chat_notifications_enabled`, and `monitored_inboxes` in SystemConfig.

| Config | `off` | `dev` | `production` |
|--------|-------|-------|-------------|
| `ai_triage_enabled` | `false` | `true` | `true` |
| `chat_notifications_enabled` | `false` | `false` | `true` |
| `monitored_inboxes` | _(empty)_ | `info@vidarbhainfotech.com` | `info@,sales@vidarbhainfotech.com` |

Fresh installs default to **off** mode (seeded via migration). Mode is visible in `/health/` JSON, `/emails/inspect/` badge, and poll cycle logs.

### SystemConfig (Runtime Config)
Replaces v1's Google Sheets config tab. Key-value store with typed casting (str/int/bool/float/json).
Seeded defaults: `ai_triage_enabled`, `chat_notifications_enabled` (false), `eod_email_enabled`, `poll_interval_minutes`, `quiet_hours_start/end`, `business_hours_start/end`, `max_consecutive_failures`, `monitored_inboxes` (empty).
Runtime keys: `last_poll_epoch` (INT, persisted after each poll cycle for deploy safety — prevents re-triaging emails on restart).

**Dev-safe defaults**: `monitored_inboxes` is empty and `chat_notifications_enabled` is false in the seed migration. A fresh `migrate` on dev will not poll real inboxes or post to Chat. Production values are set via SystemConfig admin or environment variables.

### Testing

```bash
source .venv/bin/activate

# --- Unit Tests (no API keys needed) ---
pytest -v                           # All tests (~734)
pytest apps/accounts -v             # Account/auth tests
pytest apps/emails -v               # Email + dashboard + assignment + EOD tests
pytest apps/core -v                 # Core model + health + config tests

# --- Dev Pipeline Testing (no external calls by default) ---
python manage.py test_pipeline                  # 1 fake email, all mocked
python manage.py test_pipeline --count 5        # 5 fake emails, all mocked
python manage.py test_pipeline --with-ai        # Real Claude (~$0.001/email)
python manage.py run_scheduler --once --dry-run # Simulated cycle with fake data

# --- Dev Inspector (visual output) ---
python manage.py runserver 8000
# → http://triage.local/emails/inspect/   (read-only, shows simulated Chat/reply output)

# --- Docker ---
docker compose build                # Verify Docker image builds
```

### Dev Safety (Mode-Based)

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

### Dashboard

```
/emails/              → Thread list dashboard (Triage Queue / My Inbox / Views)
/emails/?view=unassigned  → Triage queue (unassigned threads)
/emails/?view=mine    → My inbox (assigned to current user)
/emails/threads/<pk>/detail/  → Thread detail panel (messages, AI triage, notes)
/emails/threads/<pk>/edit-summary/  → POST: Edit AI summary (inline correction)
/emails/threads/<pk>/edit-category/  → POST: Inline edit category (dropdown)
/emails/threads/<pk>/edit-priority/  → POST: Inline edit priority (dropdown)
/emails/threads/<pk>/edit-status/  → POST: Inline edit status (dropdown)
/emails/threads/<pk>/assign/  → POST: Assign/reassign thread (admin only)
/emails/threads/<pk>/status/  → POST: Change thread status
/emails/threads/<pk>/accept-suggestion/  → POST: Accept AI suggestion (auto-assign)
/emails/threads/<pk>/reject-suggestion/  → POST: Reject AI suggestion
/emails/threads/<pk>/mark-unread/  → POST: Mark thread as unread for current user
/emails/threads/<pk>/context-menu/  → GET: Right-click context menu partial
/emails/threads/<pk>/mark-spam/  → POST: Mark thread as spam (updates SenderReputation)
/emails/threads/<pk>/mark-not-spam/  → POST: Mark thread as not-spam
/emails/reports/      → Reports dashboard (Overview, Categories, Performance, SLA tabs)
/emails/activity/     → Activity log (assignments, status changes, AI edits)
/emails/inspect/      → Dev inspector (poll history, MIS stats, force poll)
/emails/inspect/force-poll/  → POST: Trigger single poll cycle (dev/off mode only)
```

**Dashboard stack**: Django templates + HTMX 2.0 (CDN) + Tailwind CSS v4 (pre-built CSS)
- `django-htmx` middleware for `request.htmx` detection (partials vs full pages)
- `nh3` for HTML sanitization of email body content (XSS protection)
- **Single sidebar layout**: Views, inbox pills, and filters in main dark sidebar via `{% block sidebar_extra %}`; email content gets full remaining width
- **JS-based active state**: `updateActiveStates()` in base.html handles `data-view`/`data-inbox` attributes on HTMX navigation and browser back/forward (`htmx:pushedIntoHistory` + `popstate`)
- Card-based layout (Linear/Trello style) with slide-out detail panel
- Email/thread cards show sender name + email address
- URL-based filter state (bookmarkable: `/emails/?status=new&priority=HIGH`)
- ActivityLog model tracks all assignment and status change events
- Assignment notifications via Google Chat + Django email
- Global HTMX progress bar (top-of-page, auto show/hide on requests)
- Button loading states (`hx-disabled-elt`) prevent double-submission
- Accessibility: skip-to-content, aria-labels, keyboard nav on cards, focus-visible rings, aria-current
- Mobile responsive: detail panel as slide-over drawer with history API, scrollable settings tabs, responsive team table
- Toast notifications: stacked, auto-dismiss with stagger, close buttons, swipe-to-dismiss on mobile
- Clickable stat cards on all screens: thread list (Total/Unassigned/Urgent/New), activity log (Total/Today/Assignments/Status), team (Total/Active/Pending/Admins)
- Collapsible filter panel with badge count, search icon, "Clear all" link
- Sidebar: Triage Queue (Unassigned) / My Inbox (Mine) / Views (All Open, Closed) — clear inbox separation
- Welcome banner with role-specific guidance (dismissible, persistent via localStorage)
- Keyboard navigation: arrow keys between cards, Escape closes detail
- Loading skeleton in detail panel during HTMX fetch
- Settings UX: webhook URL masking with reveal toggle, tab descriptions, SLA presets (Standard/Aggressive/Relaxed), inline config validation
- Thread cards: expanded 3-line cards with AI summary, spam badge, AI suggested assignee
- Thread detail: AI summary (always visible, inline-editable), AI reasoning + draft reply (collapsible), AI suggestion bar, spam badge
- AI summary inline editing: pencil icon → textarea → save/cancel, creates ActivityLog entry
- Status/priority chip tooltips: hover descriptions on all badges across all screens
- Team table: JS-based filtering by stat card clicks (all/active/pending/admin)
- Dev inspector: poll countdown, force poll button, PollLog history table, pipeline MIS stats (7-day aggregates)
- AI confidence dots: visual HIGH/MEDIUM/LOW indicator on thread cards + detail
- Accept/reject AI suggestion bar: one-click auto-assign or dismiss
- Inline auto-assign badge: "Auto" badge on auto-assigned threads
- Spam feedback: mark spam/not-spam buttons in detail panel, undo support
- SenderReputation: per-sender spam ratio tracking, auto-block at threshold
- Blocked sender management: unblock button in whitelist/blocked settings tab
- Read/unread tracking: per-user state, unread badge in sidebar, bold unread cards, mark-as-unread button
- Unread count in browser tab title
- Keyboard shortcut: U to mark thread unread
- Inline editable attributes: category, priority, status dropdowns in detail panel (overrides pipeline)
- Right-click context menu: quick actions on thread cards (assign, status, priority, spam, unread)
- Reports module: 4-tab dashboard (Overview, Categories, Performance, SLA) with Chart.js charts, date range picker
- Feedback distillation: user corrections aggregated into AI prompt correction rules via scheduler
- Dark/light theme toggle: sun/moon button in sidebar footer, persisted in localStorage, anti-FOUC
- Assignee badges: Google avatar image (w-5 card / w-6 detail), solid rose initial fallback, gold "Unassigned" state
- Status badges: bolder colors (bg/15 opacity, uppercase, font-bold), reopened=gold, glow dots
- Editable priority/status: bumped to Tailwind -100/-700 shades for more visual weight

### Common Tasks

```bash
source .venv/bin/activate
python manage.py runserver 8000     # Local dev server
python manage.py createsuperuser    # Create admin user
python manage.py migrate            # Apply migrations
python manage.py test_pipeline      # Quick pipeline smoke test (safe, no API calls)
python manage.py run_scheduler      # Start production scheduler (poll + retry + heartbeat)
python manage.py run_scheduler --once          # Single poll cycle then exit
python manage.py run_scheduler --once --dry-run # Simulate with fake data, no external calls
python manage.py set_mode production           # Switch to production mode
docker compose build                              # Build locally
caddy reverse-proxy --from triage.local:80 --to localhost:8000  # Local Caddy proxy
```

## Deployment

### CI/CD

Two separate workflows:
- **`ci.yml`**: Runs tests on every push to `main` and on pull requests
- **`deploy.yml`**: Deploys to VM when a GitHub Release is published

```
Push/PR to main → CI tests only
GitHub Release published → test → SSH deploy to VM
```

**To deploy a new version:**
```bash
gh release create v2.0.1 --title "v2.0.1" --generate-notes
# Creates tag + release → triggers deploy workflow automatically
```

Pull requests and direct pushes to `main` run tests only — no deploy.

### GCP Projects
- **cm-sec-455407** (cm-sec): VMs — taiga, cm-sec-app-server, cm-sec-db-server
- **utilities-vipl**: Secrets (Secret Manager: anthropic-api-key, chat-webhook-url, sa-key, google-oauth-client-id, google-oauth-client-secret)
- Service account: `vipl-email-agent@utilities-vipl.iam.gserviceaccount.com`

### GitHub Secrets (10)
VM_HOST, VM_USER, VM_SSH_KEY, WIF_PROVIDER, WIF_SERVICE_ACCOUNT,
GOOGLE_SHEET_ID, GOOGLE_CHAT_WEBHOOK_URL, MONITORED_INBOXES, ADMIN_EMAIL, EOD_RECIPIENTS

### VM Production Environment
```
# Django
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=<generated>
ALLOWED_HOSTS=triage.vidarbhainfotech.com,localhost
DATABASE_URL=postgres://vipl_agent:vipl_agent_2026@taiga-docker-taiga-db-1:5432/vipl_email_agent

# Google OAuth SSO
GOOGLE_OAUTH_CLIENT_ID=<from GCP Console>
GOOGLE_OAUTH_CLIENT_SECRET=<from GCP Console>
SUPERADMIN_EMAILS=shreyas@vidarbhainfotech.com

# Google Workspace
GOOGLE_SERVICE_ACCOUNT_KEY_PATH=/app/secrets/service-account.json
MONITORED_INBOXES=info@vidarbhainfotech.com,sales@vidarbhainfotech.com

# AI + Notifications
ANTHROPIC_API_KEY=<from Secret Manager>
GOOGLE_CHAT_WEBHOOK_URL=<from Secret Manager>
ADMIN_EMAIL=shreyas@vidarbhainfotech.com
EOD_RECIPIENTS=shreyas@vidarbhainfotech.com
GOOGLE_SHEET_ID=<from Google Sheets>
```

## Security

### Google OAuth SSO
- **Provider**: Google OAuth 2.0 via django-allauth
- **Domain lock**: Only `@vidarbhainfotech.com` emails (enforced server-side via `hd` claim in adapter)
- **Superadmin**: `SUPERADMIN_EMAILS` env var (comma-separated) — auto-approved as admin on first login
- **New users**: Created as inactive `member`, pending admin approval at `/accounts/team/`
- **Auto-link**: Existing users auto-linked to Google account on first SSO login (safe — domain verified)
- **Manual signup**: Disabled (`ACCOUNT_SIGNUP_ENABLED = False`)
- **OAuth credentials**: Stored in GCP Secret Manager (`google-oauth-client-id`, `google-oauth-client-secret` in `utilities-vipl`)
- **Adapter**: `apps/accounts/adapters.py` — `VIPLSocialAccountAdapter`
- **Callback URL**: `https://triage.vidarbhainfotech.com/accounts/google/login/callback/`
- **Template overrides**: `templates/account/` and `templates/socialaccount/` (styled, no ugly defaults)

### Domain-Wide Delegation
Scopes: `gmail.readonly`, `gmail.labels`, `gmail.modify`, `gmail.send`, `spreadsheets`, `drive`

### Protections
- Non-root Docker user
- SA key in Secret Manager only (gitignored)
- OAuth credentials in env vars (never in code)
- Superadmin emails in env vars (never hardcoded)
- Prompt injection defense in system prompt (10 rules)
- Input sanitization before AI processing (control chars, null bytes)
- HTML sanitization via `nh3` (XSS protection in email body display)
- Workload Identity Federation for CI/CD (no SA key in GitHub)
- Cloudflare handles HTTP→HTTPS redirect; Nginx hardcodes `X-Forwarded-Proto: https`

## Two-Tier AI (Cost Optimization)
- **Default**: Claude Haiku (`claude-haiku-4-5-20251001`) — ~$0.25/MTok
- **Escalation**: Claude Sonnet (`claude-sonnet-4-5-20250929`) — only for CRITICAL
- Prompt caching via `cache_control: {"type": "ephemeral"}` (~90% savings)
- Spam pre-filter: 13 regex patterns skip Claude entirely ($0 cost)
- Body truncation: max 1500 chars sent to Claude
- Retry: 3x with exponential backoff on transient errors (tenacity)

## v1 — Archived

v1 code is preserved in git history (tags v1.0.0 through v1.1.3). Cloud Run service has been decommissioned. The v1 architecture used Google Sheets as the database with a Python scheduler on Cloud Run. All v1 functionality has been rebuilt in v2 with Django + PostgreSQL.

## Project Management

Tracked via GitHub issues and CLAUDE.md. Development happens on `main` branch directly or via feature branches merged to `main`.
