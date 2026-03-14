---
phase: 01-google-oauth-sso
plan: 01
subsystem: auth
tags: [allauth, google-oauth, sso, django, social-auth]

# Dependency graph
requires: []
provides:
  - django-allauth integration with Google provider
  - VIPLSocialAccountAdapter with domain enforcement + auto-inactive + avatar
  - User.avatar_url field for Google profile photos
  - Redesigned login page with Google Sign-In button
  - Welcome toast on login with avatar
  - Password login preserved at ?password=1
affects: [03-vipl-branding]

# Tech tracking
tech-stack:
  added: [django-allauth 65.15]
  patterns: [settings-based allauth APP config, custom SocialAccountAdapter, signal-based welcome toast]

key-files:
  created:
    - apps/accounts/adapters.py
    - apps/accounts/signals.py
    - apps/accounts/migration_helpers.py
    - apps/accounts/migrations/0002_user_avatar_url.py
    - apps/accounts/migrations/0003_set_superuser_emails.py
    - apps/accounts/tests/test_oauth.py
  modified:
    - requirements.txt
    - config/settings/base.py
    - config/urls.py
    - apps/accounts/models.py
    - apps/accounts/admin.py
    - apps/accounts/apps.py
    - templates/registration/login.html
    - templates/base.html

key-decisions:
  - "Settings-based allauth APP config instead of DB SocialApp records"
  - "ImmediateHttpResponse redirect for inactive new users instead of 500"
  - "Signal-based welcome toast with try/except for test resilience"
  - "Migration helper module outside migrations/ to avoid Django loader conflict"

patterns-established:
  - "Custom adapter pattern: VIPLSocialAccountAdapter for domain enforcement"
  - "Dual-mode login page: Google-only default, password at ?password=1"
  - "Avatar-aware sidebar: img tag for OAuth users, initials for password users"
  - "Toast animation: CSS keyframe in/out with JS auto-remove after 4s"

requirements-completed: [R1.1, R1.2, R1.3, R1.4, R1.5, R1.6]

# Metrics
duration: 7min
completed: 2026-03-14
---

# Phase 1 Plan 01: Google OAuth SSO Summary

**django-allauth with Google provider, @vidarbhainfotech.com domain enforcement adapter, dual-mode login page, sidebar avatar, and welcome toast**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-14T11:26:14Z
- **Completed:** 2026-03-14T11:33:18Z
- **Tasks:** 3 of 3 (2 auto + 1 checkpoint approved)
- **Files modified:** 21

## Accomplishments
- Google OAuth SSO via django-allauth with server-side domain enforcement (email + hd claim)
- Login page redesigned: Google Sign-In button default, password form hidden at ?password=1
- New Google users auto-created as inactive MEMBER, admin notified via email
- Avatar stored from Google profile, displayed in sidebar with initials fallback
- Welcome toast on login with name and avatar, auto-dismiss 4s, once per session
- All 271 tests pass (14 new OAuth tests + 257 existing, zero regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: OAuth test scaffolding** - `766c871` (test)
2. **Task 1 GREEN: allauth, adapter, avatar_url, data migration** - `234bd8e` (feat)
3. **Task 2: Login page, sidebar avatar, welcome toast** - `0cd2497` (feat)
4. **Task 3: Checkpoint human-verify** - approved (GCP OAuth credentials configured)
5. **Post-checkpoint: Dev-login role picker** - `56359f1` (feat)

## Files Created/Modified
- `apps/accounts/adapters.py` - VIPLSocialAccountAdapter: domain enforcement, inactive new users, avatar update
- `apps/accounts/signals.py` - Welcome toast via user_logged_in signal
- `apps/accounts/migration_helpers.py` - Reusable superuser email setter for data migration + tests
- `apps/accounts/migrations/0002_user_avatar_url.py` - avatar_url field on User model
- `apps/accounts/migrations/0003_set_superuser_emails.py` - Data migration for superuser email
- `apps/accounts/tests/test_oauth.py` - 14 tests for adapter, data migration, password login
- `requirements.txt` - Added django-allauth[socialaccount]>=65.15,<66
- `config/settings/base.py` - allauth INSTALLED_APPS, MIDDLEWARE, AUTHENTICATION_BACKENDS, SOCIALACCOUNT config
- `config/urls.py` - allauth URL patterns mounted
- `apps/accounts/models.py` - User.avatar_url field
- `apps/accounts/admin.py` - avatar_url in list_display and fieldset
- `apps/accounts/apps.py` - ready() imports signals module
- `templates/registration/login.html` - Dual-mode: Google button or password form
- `templates/base.html` - Avatar-aware sidebar, welcome toast with CSS animations
- `templates/registration/dev_login.html` - Dev-only role picker login (DEBUG mode bypass)
- `apps/accounts/views.py` - DevLoginView for local development without OAuth

## Decisions Made
- Used settings-based allauth APP config (not DB SocialApp) to avoid needing DB setup for tests and simpler deployment
- Put migration helper function in `migration_helpers.py` (not inside `migrations/`) to prevent Django migration loader conflict
- Wrapped welcome toast signal handler in try/except since test client's login() doesn't have messages middleware
- Used `allauth.core.exceptions.ImmediateHttpResponse` (not deprecated `allauth.exceptions`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migration helper module location**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `set_superuser_emails.py` inside `migrations/` was picked up by Django migration loader as invalid migration
- **Fix:** Moved to `apps/accounts/migration_helpers.py`, updated test imports
- **Files modified:** apps/accounts/migration_helpers.py, apps/accounts/tests/test_oauth.py
- **Committed in:** 234bd8e

**2. [Rule 1 - Bug] Signal handler crash in test environment**
- **Found during:** Task 2
- **Issue:** `user_logged_in` signal fired during `client.login()` but test request lacks messages middleware, causing MessageFailure
- **Fix:** Wrapped signal handler in try/except to gracefully handle missing middleware
- **Files modified:** apps/accounts/signals.py
- **Committed in:** 0cd2497

**3. [Rule 3 - Blocking] allauth SocialApp.DoesNotExist in tests**
- **Found during:** Task 2
- **Issue:** `{% provider_login_url 'google' %}` template tag requires SocialApp record in DB, failing in tests
- **Fix:** Added `APP` key to `SOCIALACCOUNT_PROVIDERS.google` in settings for settings-based config
- **Files modified:** config/settings/base.py
- **Committed in:** 0cd2497

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All auto-fixes necessary for correctness and test compatibility. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required

**GCP OAuth credentials must be created before end-to-end testing.** The plan's user_setup section details:
- Create OAuth consent screen (Internal type) in GCP Console utilities-vipl project
- Create OAuth 2.0 Web Application credentials
- Add redirect URIs: `https://triage.vidarbhainfotech.com/accounts/google/login/callback/` and `http://triage.local/accounts/google/login/callback/`
- Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in `.env`

## Next Phase Readiness
- OAuth infrastructure complete, GCP credentials configured, checkpoint approved
- Dev-login bypass available for local development without OAuth
- Phase 2 (Settings + Spam Whitelist) has no dependency on OAuth and can proceed independently

## Self-Check: PASSED

All key files verified present (7/7). All commits verified (4/4).

---
*Phase: 01-google-oauth-sso*
*Completed: 2026-03-14*
