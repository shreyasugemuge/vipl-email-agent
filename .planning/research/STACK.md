# Technology Stack

**Domain:** v2.2 Polish & Hardening additions to existing Django 4.2 LTS app
**Researched:** 2026-03-14
**Confidence:** HIGH

---

> This document covers ONLY new libraries and integration patterns needed for v2.2 features.
> The existing validated stack (Django 4.2, HTMX 2.0, Tailwind CDN, APScheduler, django-htmx,
> nh3, tenacity, pypdf) is unchanged and not re-documented here.

---

## Recommended Stack — New Additions Only

### Google OAuth SSO

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| django-allauth | 65.15.0 | Google OAuth SSO with domain restriction | De facto standard for Django social auth. First-class Google provider with `hd` domain hint param (presents only @vidarbhainfotech.com accounts in the Google picker). Supports `SOCIALACCOUNT_ONLY = True` to disable password login entirely. Custom adapter hook (`pre_social_login`) provides server-side enforcement of domain restriction — the `hd` param alone is client-side only and can be bypassed. Compatible with Django 4.2+. |

**No additional OAuth libraries needed.** django-allauth pulls in `requests` and `requests-oauthlib` as transitive dependencies — already satisfiable without pinning.

**Version note:** 65.15.0 was released 2026-03-09 (latest stable as of 2026-03-14). Drops Python 3.8/3.9 but supports 3.10–3.14 and Django 4.2+.

**Integration pattern — domain restriction (two-layer):**

Layer 1: `hd` hint in `AUTH_PARAMS` tells Google to pre-filter the account picker:
```python
# config/settings/base.py
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {
            'access_type': 'online',
            'hd': 'vidarbhainfotech.com',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}
SOCIALACCOUNT_ONLY = True  # Disable username/password login
```

Layer 2: Custom adapter enforces domain server-side (mandatory — `hd` is UI-only):
```python
# apps/accounts/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import PermissionDenied

class VIPLSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email', '')
        if not email.endswith('@vidarbhainfotech.com'):
            raise PermissionDenied("Only @vidarbhainfotech.com accounts are permitted.")

# config/settings/base.py
SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.VIPLSocialAccountAdapter'
```

**GCP OAuth app setup required:** Create OAuth 2.0 credentials in GCP Console (project `utilities-vipl` or `cm-sec-455407`), set redirect URI to `https://triage.vidarbhainfotech.com/accounts/google/login/callback/`. Store `client_id` and `secret` in Django admin → Social Applications, or via env vars.

**Migration needed:** `django-allauth` requires three new tables (`socialaccount_socialapp`, `socialaccount_socialaccount`, `socialaccount_socialtoken`) via `python manage.py migrate`.

**Existing users:** Current password-auth users need to be migrated or re-created as Google OAuth users. With `SOCIALACCOUNT_ONLY = True`, existing password users can no longer log in. Plan: create a transition window where both work, then flip the flag.

### Settings Page Form UI

**No new libraries needed.** The existing stack (Django forms + HTMX + Tailwind CDN) is sufficient.

The v2.2 settings page uses Django's built-in `ModelForm` / custom `Form` classes rendered manually in templates with Tailwind utility classes. HTMX `hx-post` on individual form sections provides per-section save without full page reloads.

**Why not django-crispy-forms / crispy-tailwind:**
- `crispy-tailwind 0.5.x` targets Tailwind v3 class names. The project uses Tailwind v4 CDN (class names changed). Using crispy-tailwind would produce broken styles.
- Manual template rendering is 30 lines of HTML and gives full control over layout, grouping, and type-aware inputs (checkbox vs text vs number vs JSON textarea). No abstraction needed for a settings page with ~15 fields.

**Pattern for grouped, type-aware settings form:**
- `SystemConfig` already stores typed values as strings. The settings form reads current values via `SystemConfig.get()` and renders input type based on a field metadata dict (bool → checkbox, int → number, str → text, json → textarea).
- Each settings group (Scheduler, Notifications, SLA, Inboxes) is a separate `<form>` tag with `hx-post` and its own save endpoint, so saving one group doesn't affect others.

### Spam Learning / Whitelisting

**No new libraries needed.** This is a pure-Django database pattern.

**Data model — SpamRule table:**
```
SpamRule:
  rule_type: CharField  # 'whitelist_sender', 'whitelist_domain', 'blacklist_sender', 'blacklist_keyword'
  value: CharField      # e.g. "partner@client.com", "@trusted.com", "unsubscribe"
  created_by: FK(User)
  created_at: DateTimeField
  note: CharField       # optional human note
  is_active: BooleanField
```

**Integration point:** `spam_filter.py` `SpamFilter` class currently uses 13 hardcoded regex patterns. v2.2 adds a DB lookup step: before regex matching, check `SpamRule.objects.filter(is_active=True)` for whitelists (skip spam check entirely for trusted senders) and blacklists (mark as spam immediately).

**"Not spam" action:** Dashboard card context menu gains a "Not spam — whitelist sender" action. This creates a `SpamRule(rule_type='whitelist_sender', value=email.from_address)` record and re-triages the email.

**Why not ML-based spam learning:** The existing regex filter already achieves very high precision for this use case. ML retraining infrastructure (scikit-learn, training loop, model storage) is 10x the complexity for marginal improvement on a 2-3 inbox volume. The team's whitelist/blacklist actions are the signal — not a classifier.

### Chat Notification UX Improvements

**No new libraries needed.** Google Chat Cards v2 JSON structure improvements only (no library change — `httpx` already handles webhook POSTs).

**Verified available widgets in Cards v2 (current, not deprecated):**

| Widget | Use in v2.2 |
|--------|-------------|
| `decoratedText` | Primary email info rows (from, subject, priority badge) |
| `chipList` | Category and status chips — visually distinct from text rows |
| `columns` | Two-column layout for SLA deadline + assignee side by side |
| `buttonList` | Quick-action buttons (View in Dashboard) |
| `divider` | Visual separation between card sections |
| `textParagraph` | Email preview snippet |

**SLA alert card pattern:** When SLA breaches or approaches breach, send a dedicated alert card (separate from the triage notification) using `decoratedText` with `startIcon` (warning icon) and a red-tinted header. Cards v1 is deprecated as of 2025 — the existing `chat_notifier.py` already uses Cards v2 format, so this is a JSON structure enhancement, not an architectural change.

**Per-category webhook routing** is already in v2.1. v2.2 improvements are layout and information density changes to the card JSON — no new services or models.

---

## Installation — New Dependencies Only

```bash
# Activate venv
source .venv/bin/activate

# Only ONE new package for v2.2
pip install "django-allauth[socialaccount]>=65.15,<66"
```

Add to `requirements.txt`:
```
# v2.2: Google OAuth SSO
django-allauth[socialaccount]>=65.15,<66
```

Add to `INSTALLED_APPS`:
```python
'allauth',
'allauth.account',
'allauth.socialaccount',
'allauth.socialaccount.providers.google',
```

Add to `MIDDLEWARE` (after `SessionMiddleware`):
```python
'allauth.account.middleware.AccountMiddleware',
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| django-allauth 65.x | python-social-auth | Less actively maintained, separate from Django's auth system. django-allauth is the standard. |
| django-allauth 65.x | authlib + custom views | authlib is excellent for OAuth clients but requires writing all the login/callback/session views manually. django-allauth provides these out of the box. |
| django-allauth 65.x | Google Identity Services (JS) | JavaScript-only flow. Would require a JS SDK on the login page and a separate Django API endpoint to verify the ID token. More complexity, harder to test. |
| Manual form templates | crispy-tailwind | crispy-tailwind targets Tailwind v3. Project uses v4 CDN. Class names differ — would produce broken styles. Manual rendering is simpler for 15 fields. |
| DB SpamRule model | ML classifier (scikit-learn) | Massive complexity overhead (training pipeline, model persistence, retraining triggers) for marginal accuracy gain at low email volume. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `crispy-tailwind` | Tailwind v3 class names, incompatible with v4 CDN | Manual template rendering |
| `django-oauth-toolkit` | For building an OAuth *server*, not client. Wrong direction. | django-allauth (OAuth client) |
| `python-jose` / `PyJWT` | Only needed for JWT-based auth. Django sessions + allauth handle everything. | Django sessions (already in place) |
| `django-allauth[mfa]` | 2FA is out of scope for a 4-person internal tool | Omit the `[mfa]` extra |
| `scikit-learn` for spam | Overengineered for this volume. DB whitelist/blacklist achieves the goal. | SpamRule model |
| `google-auth-oauthlib` standalone | Already pulled in by django-allauth as a dependency. Don't pin it separately. | Let allauth manage it |

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| django-allauth | 65.15.0 | Django 4.2, Python 3.11 (Docker), 3.13 (local) | Verified: supports Django 4.2+, Python 3.10-3.14 |
| existing django-htmx | 1.17+ | django-allauth 65.x | No conflict — different layers |
| existing nh3 | 0.2+ | django-allauth 65.x | No conflict |
| PostgreSQL | 12.3 | django-allauth migrations | allauth's 3 new tables are simple — no PG13+ features needed |

---

## Sources

- [django-allauth Google provider docs](https://docs.allauth.org/en/dev/socialaccount/providers/google.html) — `hd` param in `AUTH_PARAMS`, `OAUTH_PKCE_ENABLED`, `SCOPE` configuration — HIGH confidence
- [django-allauth requirements](https://docs.allauth.org/en/dev/installation/requirements.html) — Django 4.2+ and Python 3.10+ required, latest stable 65.15.0 — HIGH confidence
- [django-allauth social account adapter docs](https://docs.allauth.org/en/dev/socialaccount/adapter.html) — `pre_social_login()` hook for server-side domain enforcement — HIGH confidence
- [django-allauth SOCIALACCOUNT_ONLY](https://docs.allauth.org/en/dev/socialaccount/configuration.html) — disables password login when set to True — HIGH confidence
- [Google Chat Cards v2 reference](https://developers.google.com/workspace/chat/api/reference/rest/v1/cards) — widget inventory including `chipList`, `columns`, `decoratedText`, `carousel` — HIGH confidence
- [crispy-tailwind PyPI](https://pypi.org/project/crispy-tailwind/) — version 0.5 targets Tailwind v3, confirmed mismatch with v4 — HIGH confidence

---

*Stack research for: VIPL Email Agent v2.2 Polish & Hardening*
*Researched: 2026-03-14*
