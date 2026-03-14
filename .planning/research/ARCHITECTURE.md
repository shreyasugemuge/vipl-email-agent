# Architecture Research — v2.2 Integration Points

**Domain:** Django 4.2 LTS app — adding SSO, settings UI, branding, spam learning, Chat UX
**Researched:** 2026-03-14
**Confidence:** HIGH (firsthand codebase analysis + verified library docs)

---

## Context: What Already Exists

This is a subsequent milestone. The system is live. Research here answers only: "how do the new
features hook into what's already built?" Not what to build — where to attach it.

Existing anchors that every new feature must integrate with:

| Anchor | Location | Notes |
|--------|----------|-------|
| Custom User model | `apps/accounts/models.py:User` | `AbstractUser` + `role` + `can_see_all_emails` |
| Auth URL config | `config/settings/base.py` | `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` |
| Auth URL routing | `apps/accounts/urls.py` | Currently only `LoginView` + `LogoutView` |
| SystemConfig KV store | `apps/core/models.py:SystemConfig` | typed get/set, seeded via migrations, category-grouped |
| Settings view (multi-section) | `apps/emails/views.py:settings_view` + 6 save endpoints | Already exists — one page, multiple POST targets |
| Spam filter | `apps/emails/services/spam_filter.py` | Module-level compiled regex, returns `TriageResult` or `None` |
| ChatNotifier | `apps/emails/services/chat_notifier.py` | Cards v2 webhook, 4 notify methods, quiet hours via SystemConfig |
| Base template | `templates/base.html` | Tailwind v4 CDN, HTMX 2.0 CDN, Plus Jakarta Sans, sidebar nav |
| Pipeline entry | `apps/emails/services/pipeline.py` | Calls `spam_filter.is_spam()` before AI |

---

## Feature Integration Map

### 1. Google OAuth SSO

**What changes:** Authentication backend only. No model migrations required if using `social-auth-app-django`.

**Architecture decision:** Use `social-auth-app-django` (not `django-allauth`). Rationale:
- `social-auth-app-django` stores social tokens in its own tables — no migration to existing `User` model
- Domain restriction via `SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS` is a single settings line
- `django-allauth` v65+ requires `django.contrib.sites` and additional app installs; more surface area
- `social-auth-app-django` has a documented custom pipeline pattern for `hd` claim enforcement as a second safety layer

**Integration points:**

```
config/settings/base.py
  → INSTALLED_APPS: add 'social_django'
  → AUTHENTICATION_BACKENDS: add 'social_core.backends.google.GoogleOAuth2'
  → MIDDLEWARE: add 'social_django.middleware.SocialAuthExceptionMiddleware'
  → SOCIAL_AUTH_GOOGLE_OAUTH2_KEY / SECRET (from env)
  → SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = ['vidarbhainfotech.com']
  → SOCIAL_AUTH_PIPELINE: add custom domain enforcer after auth_allowed
  → SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {'hd': 'vidarbhainfotech.com'}

config/urls.py
  → path('social/', include('social_django.urls', namespace='social'))

apps/accounts/urls.py
  → No change (existing LoginView stays for fallback)
  → Optional: redirect login page to show Google button

apps/accounts/models.py
  → No change to User model (social-auth creates UserSocialAuth linked to existing User)

apps/accounts/
  → New: pipeline.py — custom pipeline step that enforces @vidarbhainfotech.com
  → New or modified: login template to show "Sign in with Google" button

templates/registration/login.html
  → Add Google SSO button linking to {% url 'social:begin' 'google-oauth2' %}
  → Keep password form as fallback (Shreyas may need it for emergency access)
```

**Data flow:**

```
User clicks "Sign in with Google"
  → /social/login/google-oauth2/   (social_django URL)
  → Google OAuth consent screen
  → Callback: /social/complete/google-oauth2/
  → social-auth pipeline runs:
      1. auth (fetch identity from Google)
      2. social_uid (build UID)
      3. auth_allowed (default check)
      4. custom enforce_domain() — blocks non-@vidarbhainfotech.com accounts
      5. social_user (find existing UserSocialAuth)
      6. get_username (derive username from email)
      7. create_user (create User if new) ← auto-creates member role
      8. associate_user / associate_by_email
      9. load_extra_data
      10. user_details (copy name/email from Google profile)
  → Django session created
  → Redirect to LOGIN_REDIRECT_URL (/emails/)
```

**New files:**
- `apps/accounts/pipeline.py` — `enforce_domain()` pipeline step
- Modified: `templates/registration/login.html` — Google button

**No new migrations required** (social_django creates its own tables via `python manage.py migrate`).

---

### 2. Settings Page Overhaul

**What changes:** The settings page already exists (`apps/emails/views.py:settings_view` + 6 save endpoints). This is a UI overhaul, not a new page.

**Current state:** Settings renders all SystemConfig entries. The overhaul groups them visually, adds type-aware inputs (toggle for bool, number for int, textarea for JSON), and pre-fills from DB.

**Integration points:**

```
apps/emails/views.py
  → settings_view(): already uses SystemConfig.get_all_by_category()
  → No new view functions likely needed — modify existing save endpoints if input types change
  → May add one new endpoint if a new category is added (e.g., for OAuth config display)

templates/emails/settings.html (or equivalent)
  → Full template rewrite — grouped sections per category
  → Type-aware inputs: <input type="number"> for int, <input type="checkbox"> for bool
  → Use HTMX for per-section saves (already the pattern from v2.1)

apps/core/models.py:SystemConfig
  → No model changes — category field already exists
  → May add new SystemConfig rows via migration for any new v2.2 settings
```

**Key constraint:** The settings view is admin-only (guarded by `user.is_staff or user.is_admin_role`). This does not change.

**New files:**
- Template update only (no new Python files)
- Possibly a new migration to seed additional SystemConfig rows (e.g., `branding_logo_url`)

---

### 3. VIPL Branding

**What changes:** Visual only — logo, colors, name. No model changes, no new views.

**Integration points:**

```
templates/base.html
  → Sidebar logo block (lines 72-91): replace SVG icon + "VIPL Triage" text with actual logo
  → Logo source: served from /static/ (download from Drive, commit to static/)
    OR served from a URL stored in SystemConfig('branding_logo_url')
  → Color theme: @theme block (lines 13-25) — change primary-* CSS custom properties
    to match VIPL brand colors (currently indigo/violet)

static/
  → New: vipl-logo.svg or vipl-logo.png

apps/core/models.py (optional)
  → Add SystemConfig row: branding_logo_url (str) — allows logo change without redeploy
```

**Recommendation:** Store logo in `static/img/vipl-logo.svg` (committed). Use SystemConfig for
the URL only if the logo needs to change without redeployment — for a 4-person internal tool,
a static file is simpler and avoids the Drive API dependency at render time.

**Build order note:** Branding depends on nothing — it can be done first or last. Defer until
the other features are working to avoid merge conflicts on base.html.

---

### 4. Spam Whitelisting / Learning

**What changes:** New model + modified spam filter + settings UI integration. Most substantial data model change in v2.2.

**Current spam filter:** `apps/emails/services/spam_filter.py` — module-level compiled regex
`_SPAM_RE`. Stateless. No DB interaction. Called from `pipeline.py`.

**New architecture:**

```
apps/emails/models.py
  → New: SpamWhitelist model
      sender_email (EmailField, unique, db_index)
      sender_domain (CharField, blank — derived from email on save)
      added_by (FK -> User, null=True)
      reason (CharField — 'user_action' | 'manual')
      created_at (auto)

apps/emails/services/spam_filter.py
  → Modify is_spam():
      1. Check SpamWhitelist FIRST (DB query): if sender in whitelist, return None (not spam)
      2. Then run regex patterns as before
  → New function: add_to_whitelist(email_address, added_by, reason)

apps/emails/views.py
  → Email detail panel POST handler (assign/status): when user marks "not spam" (new action),
    call add_to_whitelist(email.from_address, request.user, 'user_action')
  → Settings page: show whitelist table, allow manual add/remove

apps/emails/models.py:ActivityLog.Action
  → New choice: WHITELIST_ADDED = 'whitelist_added', 'Whitelisted'

templates/emails/_email_card.html or detail panel
  → "Not Spam / Whitelist Sender" button (only shown if email.is_spam=True)
  → HTMX POST to new endpoint: /emails/<pk>/whitelist/

apps/emails/urls.py
  → New: path('<int:pk>/whitelist/', views.whitelist_sender, name='whitelist_sender')
```

**Data flow:**

```
Pipeline poll cycle
  → spam_filter.is_spam(email_msg) called
  → [NEW] check SpamWhitelist.objects.filter(sender_email=from_address).exists()
      → if True: return None (skip spam filter entirely, go to AI)
  → [EXISTING] run _SPAM_RE regex
      → if match: return TriageResult(is_spam=True)
  → return None (clean email)

User marks email "not spam" in dashboard
  → POST /emails/<pk>/whitelist/
  → whitelist_sender view:
      1. SpamWhitelist.objects.get_or_create(sender_email=email.from_address, ...)
      2. ActivityLog.objects.create(action='whitelist_added', ...)
      3. HTMX partial response: remove "not spam" button, show "Whitelisted" badge
```

**Performance note:** The whitelist DB query on every email is safe at this scale (~50 emails/day,
whitelist likely <100 entries). Use `db_index=True` on `sender_email`. No caching needed.

**New migrations:** 1 (SpamWhitelist model)

---

### 5. Chat Notification UX Improvements

**What changes:** `apps/emails/services/chat_notifier.py` internals only. No model changes, no URL changes, no template changes. Purely service-layer work.

**Current state:** 4 notify methods, all building Cards v2 dicts manually inline. Cards are functional but sparse.

**Integration points:**

```
apps/emails/services/chat_notifier.py
  → Modify notify_new_emails(): richer card — add category breakdown widget, SLA urgency indicator
  → Modify notify_assignment(): add SLA deadline widget to card
  → Modify notify_personal_breach(): improve urgency formatting — hours/minutes, color coding via emoji
  → Modify notify_breach_summary(): add per-category breakdown section
  → Optional refactor: extract _build_email_widget() helper to DRY up repeated widget patterns
  → Optional: move card-building into separate builder functions for testability

SystemConfig (read path only — no new keys unless adding new notification triggers)
  → Existing: quiet_hours_start, quiet_hours_end, tracker_url — no change
  → New if needed: sla_alert_threshold_minutes (when to post SLA warnings)
```

**SLA alert notification (new trigger, if in scope):**

```
apps/emails/management/commands/run_scheduler.py
  → Existing SLA check job may call ChatNotifier.notify_breach_summary()
  → New: per-assignee breach alerts (notify_personal_breach) if not already wired up
  → No new scheduler jobs needed — attach to existing SLA check interval
```

**No new models, no new URLs, no migrations.**

---

## System Overview — v2.2 Component Map

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Browser (4-5 users)                          │
├──────────────────────────────────────────────────────────────────────┤
│  Login (password + Google SSO)   Dashboard   Settings   Email Detail │
└──────────────┬───────────────────────┬────────────┬──────────────────┘
               │ HTTPS                 │ HTMX       │ HTMX
┌──────────────▼───────────────────────▼────────────▼──────────────────┐
│                    Django 4.2 (Gunicorn, web container)               │
│                                                                       │
│  apps/accounts/         apps/emails/              apps/core/          │
│  ┌──────────────┐       ┌────────────────────┐    ┌───────────────┐  │
│  │ User model   │       │ Email, ActivityLog │    │ SystemConfig  │  │
│  │ pipeline.py  │       │ AssignmentRule     │    │ SoftDelete    │  │
│  │  (NEW: SSO   │       │ SpamWhitelist(NEW) │    │ TimestampedM  │  │
│  │  enforcer)   │       │ SLAConfig          │    └───────────────┘  │
│  └──────────────┘       └────────────────────┘                       │
│                                                                       │
│  social_django (NEW)    services/                                     │
│  ┌──────────────┐       ┌─────────────────────────────────────────┐  │
│  │ UserSocial   │       │ spam_filter.py  (+ whitelist check)     │  │
│  │ Auth tables  │       │ chat_notifier.py (richer cards)         │  │
│  └──────────────┘       │ pipeline.py     (unchanged)             │  │
│                          │ ai_processor.py (unchanged)             │  │
│                          │ gmail_poller.py (unchanged)             │  │
│                          └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────────────┐
│           PostgreSQL 12.3 (taiga-docker-taiga-db-1)                 │
│  + social_django tables (new)                                        │
│  + emails_spamwhitelist (new)                                        │
│  + existing: emails_email, core_systemconfig, accounts_user, etc.   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities — New vs Modified

| Component | Status | Responsibility |
|-----------|--------|----------------|
| `apps/accounts/pipeline.py` | NEW | Social-auth pipeline step — enforce @vidarbhainfotech.com |
| `apps/emails/models.py:SpamWhitelist` | NEW | Per-sender whitelist, FK to User |
| `apps/emails/views.py:whitelist_sender` | NEW | POST endpoint for "not spam" action |
| `social_django` tables | NEW (via migrate) | Store Google OAuth tokens, link to User |
| `templates/registration/login.html` | MODIFIED | Add Google SSO button |
| `templates/base.html` | MODIFIED | Logo + brand colors |
| `templates/emails/settings.html` | MODIFIED | Grouped sections, type-aware inputs |
| `apps/emails/services/spam_filter.py:is_spam()` | MODIFIED | Check whitelist before regex |
| `apps/emails/services/chat_notifier.py` | MODIFIED | Richer card widgets, better SLA display |
| `config/settings/base.py` | MODIFIED | social_django apps + OAuth settings |
| `config/urls.py` | MODIFIED | Add social_django URL include |
| `apps/emails/views.py:settings_view` | MODIFIED | New settings sections / inputs |
| All other files | UNCHANGED | Pipeline, gmail_poller, ai_processor, etc. |

---

## Build Order and Dependencies

Dependencies drive order. Features that require no other v2.2 feature can go first.

```
Phase 1 — Foundation (no inter-feature dependencies)
  ├── Google OAuth SSO
  │     → Blocks nothing, but other features depend on having real users to test
  │     → Must be first: team will use SSO from day 1 of v2.2
  └── VIPL Branding
        → Zero dependencies, purely visual
        → Can overlap with Phase 1 (different files)

Phase 2 — Data + UX
  ├── Spam Whitelisting
  │     → Depends on: User model (for added_by FK) — already exists
  │     → New model + migration + view + template change
  │     → Can be built independently of SSO (doesn't need OAuth users)
  └── Settings Page Overhaul
        → Depends on: knowing what new SystemConfig keys v2.2 adds (whitelist settings?)
        → Build after spam whitelist model is defined (if whitelist settings surface here)

Phase 3 — Polish
  └── Chat Notification UX
        → Zero dependencies on other v2.2 features
        → Pure internal service refactor
        → Best done last: least risk, can ship incrementally
```

**Recommended build order:**

1. SSO (OAuth plumbing + domain enforcement + login template)
2. Branding (logo + color swap in base.html — parallel with SSO if different developer)
3. Spam Whitelist model + migration + spam_filter.py integration
4. Whitelist "not spam" action in dashboard detail panel
5. Settings page overhaul (now knows all new config keys from steps 1-4)
6. Chat notification card improvements

---

## Integration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| social-auth pipeline order misconfiguration allows non-VIPL Google accounts | MEDIUM | HIGH | Add `enforce_domain` pipeline step AND `WHITELISTED_DOMAINS` setting — belt + suspenders |
| SpamWhitelist DB query adds latency to poll cycle | LOW | LOW | Indexed query, <100 rows, negligible |
| settings_view template rewrite breaks existing save endpoints | MEDIUM | MEDIUM | Each save endpoint is an independent POST — rewrite template section by section, test each |
| base.html brand color change breaks existing component styles | LOW | LOW | Colors defined as CSS custom properties in @theme block — change once, propagates everywhere |
| Google OAuth redirect_uri mismatch in production | MEDIUM | HIGH | Set `SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI` explicitly; add to GCP OAuth consent screen authorized URIs |

---

## External Service Integration

| Service | Integration Pattern | Files Touched | Notes |
|---------|---------------------|---------------|-------|
| Google OAuth 2.0 | social-auth pipeline via `social_django` | settings, urls, accounts/pipeline.py | `hd` param hints domain; whitelist enforces it |
| Google Chat | Existing webhook, card dict modification | chat_notifier.py | No new webhook URLs; modify card structure only |
| Gmail API | Unchanged | gmail_poller.py | Domain-wide delegation not affected by SSO |
| Claude AI | Unchanged | ai_processor.py | Not affected by any v2.2 feature |

---

## Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `spam_filter.is_spam()` ↔ `SpamWhitelist` | Django ORM (DB read) | New dependency: spam_filter.py gains a Django import for the first time |
| `social_django` ↔ `accounts.User` | social-auth pipeline creates User via `get_or_create` | New users get `role=MEMBER` by default — admin must manually set role=ADMIN post-login |
| `whitelist_sender` view ↔ `spam_filter.py` | Function call: `add_to_whitelist()` | Keep whitelist mutation logic in spam_filter.py, not in the view |
| Settings view ↔ `SystemConfig` | ORM read/write (existing pattern) | No change to boundary — only template changes |

**Critical note on spam_filter.py:** This module currently has no Django imports (`# No Django imports` per CLAUDE.md service table). Adding a `SpamWhitelist` ORM query will change that. This is acceptable — the module is called only from `pipeline.py` which already runs inside Django — but the module-level comment and service table in CLAUDE.md should be updated.

---

## Anti-Patterns to Avoid

### Storing OAuth credentials in SystemConfig

**What:** Putting GOOGLE_OAUTH_CLIENT_ID or CLIENT_SECRET in the SystemConfig DB table.
**Why bad:** Secrets in the database are hard to rotate, visible to Django admin users, and not encrypted at rest.
**Instead:** Environment variables in `.env` (prod) or Docker Compose env section. Same pattern as ANTHROPIC_API_KEY.

### Blocking the pipeline on whitelist DB queries

**What:** Making `is_spam()` raise or return errors when the DB is unavailable.
**Why bad:** The pipeline already handles failures gracefully. A whitelist lookup failure should be non-fatal.
**Instead:** Wrap the whitelist query in try/except, log the error, and fall through to regex check.

### Rebuilding the settings page as a new URL

**What:** Creating `/settings/` as a new app or view instead of modifying `emails:settings`.
**Why bad:** Breaks existing sidebar nav link, existing URL references, and the existing save endpoint pattern.
**Instead:** Modify the template and view in place. The existing URL `/emails/settings/` stays.

### Requiring SSO exclusively (removing password login)

**What:** Removing `LoginView` from `accounts/urls.py` after SSO is deployed.
**Why bad:** If Google OAuth is misconfigured or Google has an outage, there is no recovery path. Shreyas cannot log in to fix it.
**Instead:** Keep password login on the existing form. SSO button is additive.

---

## Sources

- Firsthand codebase analysis: `apps/accounts/`, `apps/emails/services/`, `apps/core/models.py`, `templates/base.html`, `config/settings/base.py` — HIGH confidence
- [social-auth-app-django: SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html) — MEDIUM confidence (docs verified via search)
- [django-allauth Google provider docs](https://docs.allauth.org/en/latest/socialaccount/providers/google.html) — reviewed and rejected in favor of social-auth
- Google Chat Cards v2 widget structure: verified from existing `chat_notifier.py` implementation — HIGH confidence

---

*Architecture research for: VIPL Email Agent v2.2 Polish & Hardening*
*Researched: 2026-03-14*
