# Pitfalls Research

**Domain:** Adding SSO, settings UI, branding, spam learning, and notification improvements to existing Django 4.2 email triage system
**Researched:** 2026-03-14
**Confidence:** HIGH (codebase directly inspected + official docs verified)

---

> **Note:** This file covers v2.2 feature-addition pitfalls only. Migration-era pitfalls (v1 -> v2) are in the archived `PITFALLS.md` above commit f52cb60.

---

## Critical Pitfalls

### Pitfall 1: Google OAuth Auto-Connect Silently Grants Access to Non-VIPL Accounts

**What goes wrong:**
Django-allauth's `SOCIALACCOUNT_EMAIL_AUTHENTICATION` setting, if set to `True`, allows any Google account whose email matches an existing Django `User` email to silently log in as that user. If the existing user was created with a password (as all current VIPL users are), and if `pre_social_login` domain enforcement is missing or misconfigured, a Google account from `attacker@gmail.com` whose email happens to match can gain access. Separately, the `hd` OAuth parameter (Google's hosted domain hint) is only a UI hint — it does not block sign-in from non-VIPL accounts at the OAuth protocol level.

**Why it happens:**
Tutorials show `SOCIALACCOUNT_AUTO_SIGNUP = True` and `SOCIALACCOUNT_EMAIL_AUTHENTICATION = True` as the happy path for "link social to existing account." Developers test with their own VIPL account, confirm it works, and ship. Nobody tests with a personal Gmail.

**How to avoid:**
- Leave `SOCIALACCOUNT_EMAIL_AUTHENTICATION = False` (the default). Do NOT rely on email-matching for account linking.
- Enforce domain server-side via a custom `SocialAccountAdapter` that overrides `pre_social_login` and raises `ImmediateHttpResponse` for any email not ending in `@vidarbhainfotech.com`.
- Check both `email_verified == True` AND `hd == 'vidarbhainfotech.com'` in the extra data Google returns. The `hd` claim in the Google ID token is authoritative (it reflects the Workspace domain), unlike the UI hint.
- Verify that rejected social logins do NOT create orphaned `User` or `SocialAccount` DB rows.

**Warning signs:**
- Login succeeds with a `@gmail.com` account during testing.
- `SocialAccount` rows appear in Django admin for non-VIPL emails.
- `SOCIALACCOUNT_EMAIL_AUTHENTICATION = True` in settings with no custom adapter.

**Phase to address:** Phase 1 (Google OAuth SSO) — must be in the same PR as the OAuth setup, not added later.

---

### Pitfall 2: Existing Password Users Locked Out When OAuth Is Added

**What goes wrong:**
Current users (Shreyas + team) have accounts created with `createsuperuser` — they have a username, a hashed password, and likely no `email` field set (AbstractUser has `email` as optional blank). When allauth is installed with `ACCOUNT_LOGIN_METHODS = {'email'}` or `ACCOUNT_EMAIL_REQUIRED = True`, existing users without emails on their accounts either cannot log in at all or get stuck in an email verification loop. The login page may redirect to allauth's email confirmation flow even for the password path.

**Why it happens:**
allauth's installation affects ALL authentication views, including the existing password login. If allauth replaces Django's built-in `login` view (which it does by default when added to `INSTALLED_APPS`), and the existing users have blank `email` fields, allauth's email-required validation fires on the password form.

**How to avoid:**
- Before installing allauth, set a real email address on every existing user in the database (migration + one-off data script).
- Keep `ACCOUNT_LOGIN_METHODS = {'username'}` or keep the existing Django login view for password auth and add allauth only for the social path. The two approaches can coexist — allauth's `allauth.account.auth_backends.AuthenticationBackend` alongside `django.contrib.auth.backends.ModelBackend` in `AUTHENTICATION_BACKENDS`.
- Keep `ACCOUNT_EMAIL_VERIFICATION = 'none'` during the migration period to avoid existing users being asked to verify emails they already use.
- Test the password login flow with the existing user accounts in a staging database before deploying.

**Warning signs:**
- After installing allauth, the login page redirects to `/accounts/confirm-email/` for password-login attempts.
- Existing user can no longer authenticate via the `/accounts/login/` form.
- 500 error on login with "User has no email address" or similar.

**Phase to address:** Phase 1 (Google OAuth SSO) — test with the actual production user list, not just newly created test accounts.

---

### Pitfall 3: Spam Whitelist Bypasses Regex Patterns Entirely, Including Security-Relevant Ones

**What goes wrong:**
The spam whitelist (senders marked "not spam" by a user action) is intended to fast-track legitimate vendors. But if the whitelist check runs before `is_spam()` in `pipeline.py`, a spoofed email from a whitelisted sender address bypasses all 13 regex patterns — including phishing patterns like `kindly verify your account` and `your account will be suspended`. Email `From:` headers are trivially forged. An attacker who knows a whitelisted domain (e.g., a real vendor) can impersonate it.

**Why it happens:**
Whitelist-first logic feels right — "if I trust this sender, skip all checks." But spam regex patterns serve dual purposes: detecting spam AND detecting phishing. Phishing against the VIPL team is the higher risk, not spam volume.

**How to avoid:**
- The whitelist should ONLY skip the `is_spam()` pre-filter (which blocks obvious bulk spam). It must NOT skip AI triage.
- Keep AI triage mandatory for all emails, even whitelisted senders. The whitelist only affects whether the email goes through the spam bucket, not whether Claude analyzes it.
- In `pipeline.py`, the whitelist check should set a flag like `skip_spam_filter=True` but still run `ai_processor.triage()`.
- Whitelist by domain, not by full email address. Whitelisting `vendor@bigcompany.com` is acceptable. Whitelisting `bigcompany.com` is riskier — it covers all senders at that domain.
- Log whitelist hits at `INFO` level so the pattern is visible in production logs.

**Warning signs:**
- Pipeline code with `if is_whitelisted: return fast_pass_result` before `ai_processor.triage()`.
- Whitelist entry created by user action on an email that was later found to be phishing.
- No visibility into which emails hit the whitelist vs. which were AI-triaged.

**Phase to address:** Phase 3 (Spam Learning / Whitelist) — must define whitelist semantics in the design before writing code.

---

### Pitfall 4: Settings Page Overwrites SystemConfig With Wrong Types, Silently Breaking the Pipeline

**What goes wrong:**
`SystemConfig` stores values as `TextField` with a `value_type` column (`str/int/bool/float/json`). The settings page POSTs form data as strings. If the form saves `"false"` (string) to a key with `value_type='bool'`, `SystemConfig.typed_value` returns `False` correctly (it checks `.lower() in ('true','1','yes')`). But if the form saves `"False"` capitalized, or an empty string `""` for an integer field, `typed_value` falls back to the raw string with a warning log. The pipeline then gets `"False"` where it expected `False`, and the condition `if config_value:` evaluates as `True`.

**Why it happens:**
Forms deal in strings. The type-aware casting in `SystemConfig.typed_value` is lenient (returns raw string on error rather than raising). A settings form that doesn't validate input types before saving can silently corrupt config values that the pipeline trusts.

**How to avoid:**
- Build type-specific form widgets per `value_type`: checkboxes for bool, number inputs for int/float, textarea for json.
- Validate on submit: attempt `int(value)` / `float(value)` / `json.loads(value)` before saving, return form errors if they fail.
- For booleans, store `"true"` or `"false"` (lowercase), not `"True"` / `"False"` / `"1"` / `"0"`. Standardize on write.
- Add a migration to normalize existing values to the canonical format before the settings page goes live.
- Write tests that POST bad values to the settings endpoint and assert the DB retains the previous valid value.

**Warning signs:**
- `SystemConfig: failed to cast 'poll_interval_minutes' as int` in logs after settings save.
- Pipeline disables AI triage even though the settings page shows it as enabled.
- `chat_notifications_enabled` returns a string `"false"` (truthy) instead of `False`.

**Phase to address:** Phase 2 (Settings Page Overhaul) — type validation must be in the form layer, not just the model.

---

### Pitfall 5: Branding Changes in base.html Break HTMX Partial Renders That Bypass base.html

**What goes wrong:**
This codebase has 10+ partial templates (`_email_card.html`, `_email_detail.html`, `_activity_feed.html`, etc.) that are rendered standalone by HTMX requests — they do NOT extend `base.html`. Branding changes to `base.html` (new logo, Tailwind theme variables, new nav component) will NOT cascade into partials. Result: the full page load looks branded, but after any HTMX swap the card list, detail panel, or activity feed reverts to unbranded styles.

**Why it happens:**
Developers make changes to `base.html`, visually verify the page looks correct on full load, and mark branding as done. HTMX partial swaps are not part of the visual QA pass.

**How to avoid:**
- Identify every partial that has inline Tailwind classes (all files in `templates/emails/_*.html`). Branding colors applied as CSS classes (e.g., `bg-indigo-600`) must be updated in each partial, not just in `base.html`.
- Tailwind v4 CDN (play script) regenerates classes client-side from all elements, so a theme variable defined in `<style type="text/tailwindcss">` in `base.html` is NOT available in partial HTML fragments that arrive via HTMX after the page load — the script already ran.
- Use standard Tailwind utility classes for branding colors rather than custom CSS variables where possible. If using custom `@theme` variables, ensure the Tailwind play script CDN covers them. For production, this is a reason to move to a proper Tailwind CLI build step.
- After any branding change, test the full user flow: load page, trigger an HTMX action, inspect the swapped partial's styling.

**Warning signs:**
- Email cards look correct on initial load but lose styling after filtering or pagination.
- The detail panel uses old colors after being opened.
- Login page branding updated but dashboard cards still show old colors.

**Phase to address:** Phase 4 (VIPL Branding) — audit partials before making base.html changes, update all files in the same commit.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep password auth + add OAuth as separate path | Fastest route to SSO without disrupting existing logins | Two auth code paths to maintain, confusing for new users | Acceptable for this 4-user team during v2.2; revisit in v3 |
| Tailwind CDN play script instead of CLI build | Zero build step, works with Django templates | Theme variables in `base.html` don't apply to HTMX partial fragments; large JS download per user | Never in production if HTMX partials need shared theme tokens |
| Whitelist stored as simple `SystemConfig` JSON key | No new model needed | No audit trail, no per-entry metadata, hard to display/edit in UI | Only for MVP; move to a dedicated `SpamWhitelist` model if whitelist > 20 entries |
| Settings form with one input type for all `value_type`s | Faster to build | Silent type coercion bugs destroy pipeline config | Never acceptable for production settings UI |
| Hardcoded VIPL brand colors in CSS | Fast, no tokens needed | Colors drift across partials; design changes require find-and-replace | Acceptable if all colors defined in one CSS file; never if scattered across templates |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| django-allauth + existing `AbstractUser` | Installing allauth replaces Django's auth views immediately, breaking existing password login before OAuth is ready | Add allauth in `INSTALLED_APPS` but explicitly keep `LOGIN_URL = '/accounts/login/'` pointed at the Django built-in view until the OAuth flow is fully tested |
| Google OAuth `hd` parameter | Setting `AUTH_PARAMS = {'hd': 'vidarbhainfotech.com'}` and assuming this blocks non-VIPL logins | This is only a UI hint. Enforce server-side in `pre_social_login` via a custom adapter that checks the `hd` claim in `account.extra_data` |
| Google Chat Cards v2 webhook | Adding new fields (e.g., SLA badge) to existing card structure without checking `cardsV2` schema | Google Chat will silently ignore unknown card fields but will reject malformed widget arrays with a 400. Test card payloads in the Card Builder at https://gw-card-builder.web.app/chat before deploying |
| SystemConfig as settings form backend | POSTing form string `"true"`/`"false"` and assuming `typed_value` handles it | Standardize boolean values to `"true"`/`"false"` (lowercase) on write; the model's bool check covers this but mixed-case input from browsers is a real hazard |
| Spam whitelist + existing `is_spam()` | Treating whitelist as "skip all checks" | Whitelist only skips the regex pre-filter; AI triage must still run. Whitelist = "do not bin as spam," not "fully trusted" |
| Tailwind v4 CDN `@theme` tokens + HTMX | Defining custom color tokens in `<style type="text/tailwindcss">` in `base.html` | Those tokens are unavailable to HTMX-swapped HTML fragments loaded after page init; use only standard Tailwind utility classes in partials |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `SystemConfig.get()` called per-request inside template context processors | Settings page shows stale values; DB hit on every request | Cache `SystemConfig` values in `django.core.cache` with a 30s TTL; invalidate on save | Breaks at >20 requests/minute if DB is on same host — negligible for this team |
| Spam whitelist stored as JSON in a single `SystemConfig` key and loaded per email poll cycle | Slow poll cycle if whitelist grows; single-row DB lock on every poll | Use a dedicated indexed model if whitelist > 50 entries; for now, load once per poll cycle and cache in memory | Never a problem at 4 users + 2 inboxes |
| Branding assets (logo PNG from Drive) loaded via direct Drive link | CDN changes, auth required, slow fetch | Download logo once, commit to `static/images/`, serve via WhiteNoise | Breaks immediately if Drive link requires auth or becomes private |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `SOCIALACCOUNT_EMAIL_AUTHENTICATION = True` without custom adapter | Any Google user whose email matches an existing VIPL user account can log in without a password | Never enable this setting; enforce domain in `pre_social_login` hook instead |
| Spam whitelist stored by email address (not domain), whitelisting spoofable `From:` headers | Phishing email from spoofed `vendor@trusted.com` bypasses spam filter | Whitelist logic must use both domain AND DKIM verification signal from Gmail API where available; mark whitelist entries as "unverified" vs "DKIM-verified" |
| Settings page accessible to all logged-in users | Team member (non-admin) changes `poll_interval_minutes` or disables AI triage | Settings views must check `request.user.role == 'admin'` or `request.user.is_admin_role`; raise 403 for non-admins |
| OAuth callback URL registered in Google Cloud Console only for production domain | SSO broken in local dev (callback mismatch error) | Register both `https://triage.vidarbhainfotech.com/accounts/google/login/callback/` and `http://triage.local/accounts/google/login/callback/` in GCP OAuth app authorized redirect URIs |
| `state` parameter not verified in OAuth callback | CSRF on OAuth flow | django-allauth handles this automatically; do NOT implement a custom OAuth callback view that skips state verification |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| "Sign in with Google" button appears but password form disappears | Existing users with passwords can no longer log in via their credentials | Keep both forms: password form + Google SSO button on the same login page during transition |
| Settings page saves each field individually (one POST per field) | With HTMX inline editing, a failed save of one field leaves the page in a partial-save state | Save all settings in a category as one grouped POST; show success/error for the whole group, not individual fields |
| Spam whitelist shown as raw key-value JSON in SystemConfig admin | Manager cannot read or manage whitelist entries | Build a dedicated whitelist management UI in the settings page, not in Django admin |
| Chat notification cards redesigned mid-day | Team sees mixed old and new card formats in the same Chat space; confusing | Deploy notification format changes outside business hours; the space history shows old cards permanently |
| VIPL logo loaded from external Drive URL on login page | Login page blank/broken if Drive link changes or requires auth; CSP violation if Drive domain not allowlisted | Serve logo as static file; never hotlink from Drive or any external service |

---

## "Looks Done But Isn't" Checklist

- [ ] **Google OAuth:** Verify a `@gmail.com` (non-VIPL) account cannot log in — test this explicitly, not just with VIPL accounts.
- [ ] **Google OAuth:** Existing password users can still log in with their username/password after allauth is installed.
- [ ] **Google OAuth:** The OAuth callback redirect URI is registered for both production and local dev in GCP Console.
- [ ] **Settings page:** Bool fields save as `"true"`/`"false"` (lowercase), not `"True"` / `"1"`. Verify with `SystemConfig.objects.get(key='ai_triage_enabled').value` in shell.
- [ ] **Settings page:** Non-admin users get 403, not a blank form or 500.
- [ ] **Branding:** HTMX partial swaps (filter by status, paginate, open detail panel) render with updated brand colors, not the old indigo.
- [ ] **Branding:** Logo is served from `/static/`, not hotlinked from Drive or any external URL.
- [ ] **Spam whitelist:** Whitelisted sender's email still goes through AI triage — check the pipeline log shows `ai_processor` ran, not just `spam_filter bypassed`.
- [ ] **Spam whitelist:** Whitelisted domain does not whitelist ALL senders at that domain (e.g., whitelisting `vendor@trusted.com` should not whitelist `ceo@trusted.com`).
- [ ] **Chat notifications:** Existing notification methods (`notify_assignment`, `notify_new_emails`, `notify_breach_summary`) still post successfully after card redesign — run `test_pipeline --with-chat` against the new card structure.
- [ ] **Chat notifications:** New card fields don't cause 400 errors from the Google Chat API — test with Card Builder first.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| OAuth lets non-VIPL user in | MEDIUM | Disable Google OAuth immediately (`SOCIALACCOUNT_PROVIDERS` remove Google), audit `SocialAccount` and `User` tables for unauthorized entries, add server-side domain check, re-enable |
| Existing user locked out by allauth | LOW | Add user's email via `User.objects.filter(username=X).update(email='...')` in shell, or temporarily set `ACCOUNT_EMAIL_VERIFICATION = 'none'` |
| Settings page corrupts a SystemConfig bool | LOW | `python manage.py shell` → `SystemConfig.objects.filter(key='ai_triage_enabled').update(value='true')` |
| Spam whitelist allows phishing through | MEDIUM | Remove whitelist entry immediately, re-process affected emails manually, audit what the email did (if it prompted any action from the team) |
| Branding breaks HTMX partials | LOW | Revert `base.html` change, audit all `_*.html` partials, update in single commit with full-flow test |
| Chat card redesign causes 400 from Google | LOW | Revert `chat_notifier.py`, use Card Builder to validate new structure, redeploy |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| OAuth lets non-VIPL user in (Pitfall 1) | Phase 1: Google OAuth SSO | Test login with personal Gmail — must fail with domain error |
| Existing users locked out by allauth (Pitfall 2) | Phase 1: Google OAuth SSO | Test password login with existing user accounts after allauth install |
| Spam whitelist bypasses phishing checks (Pitfall 3) | Phase 3: Spam Learning | Inspect pipeline logs — AI triage must appear even for whitelisted senders |
| Settings page corrupts SystemConfig types (Pitfall 4) | Phase 2: Settings Page Overhaul | POST bad types (string for int field) — form must reject, DB must retain previous value |
| Branding breaks HTMX partials (Pitfall 5) | Phase 4: VIPL Branding | Click through all HTMX interactions after branding — no style regression |
| Chat card redesign breaks existing webhooks | Phase 5: Chat Notification UX | Run `test_pipeline --with-chat` against all 4 notification methods after changes |
| Settings accessible to non-admins | Phase 2: Settings Page Overhaul | Log in as a member-role user, attempt GET/POST to settings — must get 403 |

---

## Sources

- [django-allauth SOCIALACCOUNT_EMAIL_AUTHENTICATION docs](https://docs.allauth.org/en/dev/socialaccount/configuration.html) — HIGH confidence (official)
- [django-allauth Google provider docs](https://docs.allauth.org/en/dev/socialaccount/providers/google.html) — HIGH confidence (official)
- [django-allauth social account auto-connect security issue #418](https://github.com/pennersr/django-allauth/issues/418) — HIGH confidence (maintainer comment)
- [Trustwave: Spammers exploiting whitelists via spoofed From headers](https://www.trustwave.com/en-us/resources/blogs/spiderlabs-blog/spammers-are-taking-advantage-of-your-whitelists-by-spoofing-legitimate-brands/) — MEDIUM confidence
- [Hornetsecurity: Email whitelisting risks](https://www.hornetsecurity.com/en/blog/email-whitelisting-risks/) — MEDIUM confidence
- [Google Chat Card Builder](https://gw-card-builder.web.app/chat) — HIGH confidence (official tool)
- [Tailwind CSS v4 CDN usage limitations](https://tailkits.com/blog/tailwind-css-v4-cdn-setup/) — MEDIUM confidence
- Direct codebase inspection: `apps/emails/services/spam_filter.py`, `apps/emails/services/chat_notifier.py`, `apps/accounts/models.py`, `apps/core/models.py`, `config/settings/base.py` — HIGH confidence

---
*Pitfalls research for: v2.2 Polish & Hardening feature additions*
*Researched: 2026-03-14*
