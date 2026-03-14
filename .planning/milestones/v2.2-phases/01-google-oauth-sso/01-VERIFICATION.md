---
phase: 01-google-oauth-sso
verified: 2026-03-14T12:00:00Z
status: human_needed
score: 6/7 must-haves verified
re_verification: false
human_verification:
  - test: "Click 'Sign in with Google' with a @vidarbhainfotech.com account"
    expected: "Redirected to /emails/ after OAuth callback; welcome toast with first name and avatar appears in top-right; sidebar shows Google avatar photo instead of initials."
    why_human: "End-to-end OAuth callback requires live GCP credentials and a real browser session. Cannot verify redirect + toast render via grep."
  - test: "Click 'Sign in with Google' with a @gmail.com or other non-VIPL account"
    expected: "Redirected to /accounts/login/?error=domain with 'Only @vidarbhainfotech.com accounts can sign in.' error message displayed in red card."
    why_human: "Requires real Google OAuth interaction; domain rejection ImmediateHttpResponse path needs browser verification."
  - test: "First-time Google sign-in with a new @vidarbhainfotech.com account"
    expected: "Account created as inactive; redirected to /accounts/login/?pending=1 showing 'Account created. Waiting for admin approval.' in blue card."
    why_human: "Requires live OAuth token from Google; new-user save_user path needs real first-time login."
---

# Phase 1: Google OAuth SSO Verification Report

**Phase Goal:** Replace password login with Google Workspace SSO. Domain-locked to @vidarbhainfotech.com, auto-creates inactive users for admin approval, preserves superuser password fallback.
**Verified:** 2026-03-14T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User sees a 'Sign in with Google' button on the login page | VERIFIED | `templates/registration/login.html` line 123: `<a href="{% provider_login_url 'google' %}">...Sign in with Google</a>` in the `{% else %}` (Google mode) branch |
| 2 | Google sign-in with @vidarbhainfotech.com account logs in and redirects to /emails/ | HUMAN NEEDED | `LOGIN_REDIRECT_URL = "/emails/"` in base.py; adapter allows VIPL domain; end-to-end flow requires live OAuth session |
| 3 | Google sign-in with non-VIPL domain is rejected with clear error message | HUMAN NEEDED | `adapters.py` raises `ImmediateHttpResponse(redirect('/accounts/login/?error=domain'))` for non-VIPL; login.html renders error card for `?error=domain`; unit tests pass; needs real OAuth browser test |
| 4 | First-time Google sign-in creates inactive account and shows 'Waiting for admin approval' | HUMAN NEEDED | `save_user` sets `is_active=False`, redirects to `?pending=1`; login.html renders pending card; unit tests for save_user pass; needs real first-login browser test |
| 5 | Existing superuser can log in with username/password at /accounts/login/?password=1 | VERIFIED | `test_password_login_works_at_password_param` passes (302 → /emails/); login.html shows password form at `?password=1` |
| 6 | Sidebar shows Google avatar and user name for OAuth users | VERIFIED | `base.html` lines 150-155: `{% if user.avatar_url %}<img src="{{ user.avatar_url }}" ...>{% else %}` initials fallback |
| 7 | Post-login shows a welcome toast with first name and avatar | VERIFIED | `base.html` lines 216-234: toast rendered from Django messages; `signals.py` fires `messages.info(request, f"Welcome, {first_name}!")` on `user_logged_in`; adapter adds welcome message for returning OAuth users |

**Score:** 4/7 automated verifications (3 require human — all involve live OAuth browser flow)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/accounts/adapters.py` | VIPLSocialAccountAdapter with domain enforcement + auto-inactive + avatar | VERIFIED | 100 lines; checks email suffix AND hd claim; raises ImmediateHttpResponse for domain violations; sets is_active=False on new users; stores avatar_url |
| `config/settings/base.py` | allauth INSTALLED_APPS, MIDDLEWARE, AUTHENTICATION_BACKENDS, SOCIALACCOUNT_PROVIDERS | VERIFIED | allauth.socialaccount.providers.google in INSTALLED_APPS; AccountMiddleware in MIDDLEWARE; SOCIALACCOUNT_ADAPTER points to VIPLSocialAccountAdapter; APP key configured for settings-based config |
| `templates/registration/login.html` | Google Sign-In button, hidden password form, domain error display, approval pending message | VERIFIED | Dual-mode: Google button by default, password form at ?password=1; domain error at ?error=domain; pending message at ?pending=1; `{% load socialaccount %}` at top |
| `templates/base.html` | Google avatar in sidebar user section, welcome toast | VERIFIED | avatar_url conditional img tag with referrerpolicy="no-referrer"; toast with CSS keyframe animations and 4s auto-remove JS |
| `apps/accounts/migrations/0002_user_avatar_url.py` | avatar_url field on User model | VERIFIED | Adds URLField(max_length=500, blank=True, default='') with help_text |
| `apps/accounts/migrations/0003_set_superuser_emails.py` | Data migration setting email on existing superusers | VERIFIED | RunPython forwards sets username@vidarbhainfotech.com on superusers with blank email; backwards is no-op |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `templates/registration/login.html` | allauth Google provider | `{% provider_login_url 'google' %}` template tag | VERIFIED | Line 123 contains `{% provider_login_url 'google' %}` |
| `apps/accounts/adapters.py` | `config/settings/base.py` | `SOCIALACCOUNT_ADAPTER` setting | VERIFIED | `SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.VIPLSocialAccountAdapter"` at line 122 |
| `config/urls.py` | allauth.urls | `include('allauth.urls')` | VERIFIED | `path("accounts/", include("allauth.urls"))` at line 15 |
| `apps/accounts/apps.py` | `apps/accounts/signals.py` | `ready()` imports signals | VERIFIED | `import apps.accounts.signals` in `ready()` method |
| `apps/accounts/signals.py` | `user_logged_in` Django signal | `user_logged_in.connect(on_user_logged_in)` | VERIFIED | Connected at module level in signals.py line 19 |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| R1.1 | Install django-allauth[socialaccount], configure INSTALLED_APPS, MIDDLEWARE, AUTHENTICATION_BACKENDS | SATISFIED | `requirements.txt` line 24; base.py has all allauth apps, AccountMiddleware, two AUTHENTICATION_BACKENDS |
| R1.2 | Custom SocialAccountAdapter with server-side @vidarbhainfotech.com domain enforcement | SATISFIED | `adapters.py`: checks both email suffix AND hd claim; unit tests pass for gmail rejection, spoofed email, missing hd |
| R1.3 | Google Sign-In button on login page, password form preserved | SATISFIED | login.html: Google button in default mode; password form at `?password=1` |
| R1.4 | Auto-provision new Google users as MEMBER role | SATISFIED | `save_user` sets `is_active=False, role="member", can_see_all_emails=False`; unit test `test_new_user_created_inactive` passes |
| R1.5 | Data migration to set email on existing superuser accounts | SATISFIED | `0003_set_superuser_emails.py` with RunPython; unit tests in `TestDataMigration` all pass |
| R1.6 | GCP OAuth consent screen (Internal) + credentials in utilities-vipl project | HUMAN NEEDED | PLAN notes this is a user_setup step requiring manual GCP Console action; checkpoint was "approved" per SUMMARY; cannot verify GCP Console state programmatically |

### Anti-Patterns Found

No blockers or warnings found. No TODO/FIXME/placeholder comments in any phase-modified files. No empty implementations. Signal handler uses try/except intentionally (documented decision for test resilience).

### Human Verification Required

#### 1. Google Sign-In Happy Path

**Test:** With `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` set in `.env`, start `python manage.py runserver 8000`, visit `http://triage.local/accounts/login/`, click "Sign in with Google", sign in with a `@vidarbhainfotech.com` account.
**Expected:** Redirected to `/emails/`; welcome toast appears top-right with first name (and avatar if photo permission granted); sidebar shows Google profile photo.
**Why human:** Requires live GCP OAuth credentials and a real Google Workspace session.

#### 2. Domain Rejection Flow

**Test:** Visit login page, click "Sign in with Google", sign in with a personal `@gmail.com` account.
**Expected:** Redirected to `/accounts/login/?error=domain` with red card: "Only @vidarbhainfotech.com accounts can sign in."
**Why human:** Requires real Google OAuth callback with a non-VIPL account token.

#### 3. New User Pending Approval Flow

**Test:** Sign in with a `@vidarbhainfotech.com` Google account that has never signed in before.
**Expected:** Blue card at `/accounts/login/?pending=1`: "Account created. Waiting for admin approval."; new user visible in Django admin with `is_active=False`.
**Why human:** Requires a first-time Google login with a real account.

#### 4. R1.6 — GCP OAuth Credentials

**Test:** Check GCP Console → utilities-vipl project → APIs & Services → Credentials for an OAuth 2.0 Web Application credential with redirect URIs for both `https://triage.vidarbhainfotech.com/accounts/google/login/callback/` and `http://triage.local/accounts/google/login/callback/`.
**Expected:** Credentials exist; consent screen is type "Internal"; both redirect URIs present.
**Why human:** Cannot query GCP Console programmatically in this context.

### Gaps Summary

No structural or code gaps found. All 6 artifacts exist and are substantive. All 5 key links are wired. All 6 requirements have code evidence (R1.6 is infrastructure/manual). The 3 human verification items are all end-to-end browser flows that require live OAuth credentials — they cannot be verified by code inspection alone.

271 tests pass with zero regressions (14 new OAuth tests + all 257 pre-existing tests).

---

_Verified: 2026-03-14T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
