# Project Research Summary

**Project:** VIPL Email Agent v2.2 — Polish & Hardening
**Domain:** Django internal tooling — SSO, settings UX, spam learning, notification polish
**Researched:** 2026-03-14
**Confidence:** HIGH

## Executive Summary

v2.2 is a polish milestone on a live, stable system. The research confirms this is incremental feature work, not architectural change — only one new library (`django-allauth[socialaccount]`) is needed, two new DB tables (`SpamWhitelist` and allauth social tables), and the rest of the scope is service-layer and template modifications. All 4 researchers had direct access to the production codebase, so findings are grounded in actual code rather than speculation. The recommended stack and architecture are already proven in production; the question is only where to attach new features.

The highest-value features in order are: (1) Google OAuth SSO eliminates password friction for the 4-person team; (2) spam whitelisting fixes the only broken trust loop in the pipeline — false positives with no recovery path; (3) settings page type-aware inputs prevent silent pipeline misconfiguration; (4) VIPL branding and Chat card improvements are low-effort high-visibility polish. The research recommends shipping in this order because OAuth introduces the one real dependency (allauth migrations must run on VM before Google accounts can work), and branding changes to `base.html` are safest done last to avoid merge conflicts with the login page changes from OAuth.

The key risks are concentrated in Phase 1 (OAuth): two critical security pitfalls (non-VIPL accounts gaining access; existing password users locked out) that must be explicitly tested, not assumed correct. The spam whitelist has a non-obvious security implication — whitelisted senders must still go through AI triage or phishing emails can slip through. Settings form type coercion is a silent failure mode that can corrupt pipeline config. These are all preventable with the specific mitigations documented in PITFALLS.md.

## Key Findings

### Recommended Stack

The existing stack is unchanged. Only one new package is required for v2.2: `django-allauth[socialaccount]>=65.15,<66`. The STACK researcher and ARCHITECTURE researcher diverged on library choice (allauth vs. `social-auth-app-django`) — allauth is the stronger recommendation because it is more actively maintained, has first-class Django 4.2 support, and provides the `pre_social_login` adapter hook for server-side domain enforcement. Note the `hd` param in `AUTH_PARAMS` is a UI hint only and is not a security control.

**Core technologies (new additions only):**
- `django-allauth[socialaccount]` 65.15.0: Google OAuth SSO — de facto Django standard, verified compatible with Django 4.2 + Python 3.11 (Docker)
- `SpamWhitelist` model (pure Django ORM): per-sender/domain whitelist — no new library, indexed FK query is safe at this scale
- Settings form widgets: no new library — manual Tailwind templates outperform `crispy-tailwind` which targets Tailwind v3 (incompatible with v4 CDN)

### Expected Features

**Must have (table stakes):**
- Google OAuth SSO domain-locked to `@vidarbhainfotech.com` — all users have Google Workspace accounts; password auth is unnecessary friction
- Preserve password login alongside OAuth during transition — superuser fallback if OAuth misconfigures
- Settings page pre-filled values + type-aware inputs — bool fields currently require typing "true"/"false" blind; silent type coercion can break pipeline
- Spam whitelist "Not Spam" action — no current recovery path for false positives; erodes trust in the filter
- VIPL branding in navbar and login — generic placeholder icon on a live production tool

**Should have (differentiators):**
- OAuth auto-provision new users with `role=MEMBER` on first Google sign-in — eliminates manual onboarding step
- Domain-level whitelist entries (not just per-sender) — more efficient for trusted client domains
- Chat breach alerts with per-email direct links — one tap to the specific email vs. two
- Spam whitelist management UI in Settings — avoids requiring Django admin for day-to-day whitelist management
- Inline HTMX save feedback on all settings tabs — SLA Config tab currently silent on save

**Defer (post-v2.2):**
- Interactive Chat buttons (Acknowledge/Close from Chat) — requires full Chat bot architecture, not a webhook upgrade; Google Chat webhooks are explicitly one-way
- ML-based spam learning — overkill for under 50 emails/day; DB whitelist achieves the goal
- Full open Google registration — explicitly anti-feature; domain lock is required
- Password reset email flow — obsolete once OAuth is live; 4-user team uses Django admin

### Architecture Approach

All v2.2 features hook into existing anchors: the `User` model (unchanged), `SystemConfig` KV store (unchanged), the settings view pattern (modified in-place at `/emails/settings/`), and `spam_filter.py` (gains one DB dependency). The most substantial change is adding `SpamWhitelist` to `apps/emails/models.py` and having `spam_filter.is_spam()` check it before running regex patterns. The `spam_filter.py` module will gain its first Django import, which is acceptable since it is only ever called from `pipeline.py` inside a Django context.

**Major components and what changes:**
1. `apps/accounts/adapters.py` (NEW) — `VIPLSocialAccountAdapter.pre_social_login()` enforces `@vidarbhainfotech.com` server-side; the `hd` OAuth param alone is not a security control
2. `apps/emails/models.py:SpamWhitelist` (NEW) — per-sender/domain whitelist with `added_by` FK, indexed `sender_email`, `entry_type` field (email vs domain)
3. `apps/emails/services/spam_filter.py:is_spam()` (MODIFIED) — whitelist check before regex; non-fatal on DB failure (try/except, fall through to regex)
4. `apps/emails/services/chat_notifier.py` (MODIFIED) — richer Cards v2 structure using `chipList`, `columns`, `decoratedText` with inline button; per-email links in `notify_personal_breach()`
5. `templates/` (MODIFIED) — `login.html` Google button, `base.html` logo + brand colors, `_config_editor.html` type-aware inputs, email detail "Whitelist Sender" button
6. `config/settings/base.py` + `config/urls.py` (MODIFIED) — allauth `INSTALLED_APPS`, `MIDDLEWARE`, `SOCIALACCOUNT_PROVIDERS`, `AUTHENTICATION_BACKENDS`

### Critical Pitfalls

1. **OAuth lets non-VIPL Google accounts in** — `hd` param is a UI hint only; a personal Gmail can bypass it at the protocol level. Enforce domain in `pre_social_login` adapter AND check `hd` claim in Google's ID token `extra_data`. Test explicitly with a `@gmail.com` account — must fail with a domain error, not a generic 500.

2. **Existing password users locked out by allauth** — allauth replaces Django's auth views on install and can enforce email requirements that existing `createsuperuser` accounts (with blank `email` fields) don't satisfy. Keep both `ModelBackend` and `AuthenticationBackend` in `AUTHENTICATION_BACKENDS`; set `ACCOUNT_EMAIL_VERIFICATION = 'none'` during migration period; test password login with the actual production user list.

3. **Spam whitelist bypasses phishing checks** — whitelisted senders skip regex spam patterns, but phishing originates from spoofed-but-trusted addresses. Whitelist must only skip the spam pre-filter; AI triage must still run for every email. In `pipeline.py`, set `skip_spam_filter=True` flag but always call `ai_processor.triage()`.

4. **Settings form corrupts SystemConfig types silently** — POSTing `"False"` (capitalized) or `""` for an integer causes `typed_value` to return the raw string, which is truthy. Standardize bool writes to `"true"`/`"false"` lowercase; validate `int(value)` / `json.loads(value)` before saving; write tests that POST bad values and assert the DB retains the previous valid value.

5. **Branding changes don't cascade to HTMX partials** — Tailwind v4 CDN play script runs on page load; `@theme` tokens defined in `base.html` are unavailable to HTMX-swapped HTML fragments loaded after initial render. Audit all `_*.html` partials and update inline classes in the same commit as `base.html` changes. Test the full click-through flow (filter, paginate, open detail panel) after branding — not just the initial page load.

## Implications for Roadmap

Based on research, dependency analysis, and the pitfall-to-phase mapping in PITFALLS.md, the suggested structure is 4 phases:

### Phase 1: Google OAuth SSO
**Rationale:** Highest team impact; introduces the one hard dependency (allauth migrations must run on VM before Google accounts can authenticate). Must come first so the team uses SSO from the start of v2.2, and OAuth is not bolted onto half-finished features.
**Delivers:** Google Sign-In button on login page, domain lock to `@vidarbhainfotech.com`, auto-provision new users as `role=MEMBER`, password login preserved as fallback for superuser emergency access
**Addresses:** "Google OAuth SSO" and "Preserve password auth" table stakes from FEATURES.md
**Avoids:** Pitfalls 1 and 2 (non-VIPL access; lockout) — both must be explicitly tested in the same PR before merging

### Phase 2: Settings Page + Spam Whitelist
**Rationale:** These two features share a dependency: the settings page template is touched by both (whitelist management UI lives in a new settings tab), and knowing what new model/config keys v2.2 adds is required before doing a final settings page template pass. Building them together avoids double-touching the same files. Neither blocks nor is blocked by OAuth.
**Delivers:** Type-aware settings inputs (toggle/number/text by value_type), pre-filled values from DB, `SpamWhitelist` model + migration, "Not Spam / Whitelist Sender" button in email detail panel, whitelist management tab in settings
**Uses:** `SystemConfig.get_all_by_category()` (existing), `SpamWhitelist` model (new), HTMX per-section saves (existing pattern)
**Implements:** Modified `spam_filter.is_spam()` — whitelist check before regex, non-fatal on DB error, AI triage always runs regardless
**Avoids:** Pitfalls 3 (whitelist bypasses phishing) and 4 (type coercion corrupts config)

### Phase 3: VIPL Branding
**Rationale:** Zero dependencies on other v2.2 features. Done after Phase 1 (not before) to avoid merge conflicts on `login.html` which Phase 1 also modifies. Branding changes are lowest risk but require a full HTMX partial audit — safest to do as a focused standalone phase.
**Delivers:** VIPL logo in sidebar and login page, brand color swap from indigo to VIPL brand palette, logo served from `/static/img/` (not a Drive link)
**Avoids:** Pitfall 5 (HTMX partial styling regression) — all `_*.html` partials updated in the same commit as `base.html`, full click-through flow tested

### Phase 4: Chat Notification Polish
**Rationale:** Purely service-layer work in `chat_notifier.py`: no model changes, no migrations, no URL changes, zero dependencies on other v2.2 features. Placed last because it is incremental improvement to a working feature, not a broken workflow.
**Delivers:** Per-email "Open Email" direct links in `notify_personal_breach()` breach alerts, richer card structure using `chipList`/`columns`/`decoratedText` with inline button, consistent SLA urgency display across card types
**Implements:** Modifications to `chat_notifier.py` only; validates via `test_pipeline --with-chat` against all 4 notify methods
**Avoids:** Chat card 400 errors — validate card payloads in Card Builder (`https://gw-card-builder.web.app/chat`) before deploying; deploy outside business hours to avoid mixed old/new card formats in the Chat space

### Phase Ordering Rationale

- OAuth first because it introduces migrations that must run on VM, and the team should not be on password auth for the entire v2.2 development window
- Settings + Whitelist grouped because the Settings page template is touched by both features, and whitelist management UI lives in settings — building them together avoids two separate template passes on the same file
- Branding after OAuth because both touch `login.html`; sequential order avoids merge conflicts
- Chat last because it is a pure internal service refactor with no dependency on anything else in v2.2

### Research Flags

All 4 phases have standard, well-documented patterns. No `/gsd:research-phase` runs are needed before planning.

Areas that need validation during implementation (not additional research):
- **Phase 1:** Existing production users may have blank `email` fields (created via `createsuperuser`). Set real email addresses on all users via Django shell before installing allauth, or allauth's email validation will break password login. Test with actual production user list, not just newly created test accounts.
- **Phase 1:** Register OAuth callback URI for local dev (`http://triage.local/accounts/google/login/callback/`) in GCP Console in addition to the production URI — otherwise local OAuth testing is impossible.
- **Phase 2:** Normalize existing `SystemConfig` bool values to lowercase `"true"`/`"false"` via a data migration before the settings page goes live, to prevent `typed_value` mismatch on the first load.
- **Phase 3:** Audit all `templates/emails/_*.html` partials for hardcoded `indigo-*` / `violet-*` Tailwind classes before changing `base.html` `@theme` block.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | One new library; allauth docs verified against Django 4.2 + Python 3.11; version 65.15.0 confirmed latest stable as of 2026-03-14 |
| Features | HIGH | Codebase directly inspected; feature gaps identified from running system, not from spec assumptions |
| Architecture | HIGH | Integration points are exact file paths and line references from real code; two researchers converged on the same integration map (minor library disagreement resolved in favor of allauth) |
| Pitfalls | HIGH | Security pitfalls sourced from allauth official docs and maintainer GitHub issues; codebase inspection confirmed which pitfalls apply to this specific setup |

**Overall confidence:** HIGH

### Gaps to Address

- **Library disagreement (minor, resolved):** STACK.md recommends `django-allauth`; ARCHITECTURE.md recommends `social-auth-app-django`. Use `django-allauth` — it is the community standard, has better docs, and FEATURES.md also references it. The ARCHITECTURE.md integration map is equivalent with allauth (adapters instead of a pipeline file; same domain enforcement logic).
- **GCP OAuth credentials:** Requires manual work in GCP Console — create OAuth 2.0 credentials, set consent screen to Internal type, add redirect URIs. Not automatable via code. Must be completed before Phase 1 can be tested end-to-end.
- **Logo asset:** VIPL logo from Google Drive is an external dependency for Phase 3. Must be obtained and committed to `static/img/` before Phase 3 starts. If unavailable, a text-based SVG logo is the fallback.
- **Existing user email fields:** Production users created via `createsuperuser` may have blank `email` fields. Requires a one-off data fix before installing allauth — can be done in the same Phase 1 migration.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `apps/emails/services/spam_filter.py`, `apps/emails/services/chat_notifier.py`, `apps/accounts/models.py`, `apps/core/models.py`, `config/settings/base.py`, `templates/base.html`, `templates/registration/login.html`
- [django-allauth Google provider docs](https://docs.allauth.org/en/dev/socialaccount/providers/google.html) — `hd` param, `OAUTH_PKCE_ENABLED`, `SCOPE`, adapter pattern
- [django-allauth SOCIALACCOUNT_EMAIL_AUTHENTICATION docs](https://docs.allauth.org/en/dev/socialaccount/configuration.html) — security configuration
- [django-allauth social account adapter](https://docs.allauth.org/en/dev/socialaccount/adapter.html) — `pre_social_login()` hook for server-side enforcement
- [django-allauth requirements](https://docs.allauth.org/en/dev/installation/requirements.html) — Django 4.2+, Python 3.10+ compatibility
- [Google Chat Cards v2 reference](https://developers.google.com/workspace/chat/api/reference/rest/v1/cards) — widget inventory including `chipList`, `columns`, `decoratedText`
- [Google Chat webhook limitations](https://developers.google.com/workspace/chat/quickstart/webhooks) — one-way webhook confirmed; no interactive callbacks

### Secondary (MEDIUM confidence)
- [social-auth-app-django Django config docs](https://python-social-auth.readthedocs.io/en/latest/configuration/django.html) — reviewed and rejected in favor of allauth
- [Google Chat new widgets Oct 2024](https://workspaceupdates.googleblog.com/2024/10/new-widgets-google-chat-app-cards.html) — `chipList`, `columns` widget availability confirmed
- [Tailwind CSS v4 CDN usage limitations](https://tailkits.com/blog/tailwind-css-v4-cdn-setup/) — `@theme` tokens unavailable to dynamically loaded HTMX fragments
- [django-allauth security issue #418](https://github.com/pennersr/django-allauth/issues/418) — auto-connect pitfall documented by maintainer
- [crispy-tailwind PyPI](https://pypi.org/project/crispy-tailwind/) — version 0.5 targets Tailwind v3; confirmed incompatible with v4 CDN

### Tertiary (LOW confidence)
- [Trustwave: Spammers exploiting whitelists via spoofed From headers](https://www.trustwave.com/en-us/resources/blogs/spiderlabs-blog/) — confirms whitelist bypass risk; motivates keeping AI triage mandatory even for whitelisted senders
- [Hornetsecurity: Email whitelisting risks](https://www.hornetsecurity.com/en/blog/email-whitelisting-risks/) — secondary source for same finding

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
