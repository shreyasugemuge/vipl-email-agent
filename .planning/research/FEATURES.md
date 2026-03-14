# Feature Landscape

**Domain:** Django shared-inbox triage app — v2.2 Polish & Hardening milestone
**Researched:** 2026-03-14
**Scope:** NEW features only. Existing features (assignment, SLA tracking, dashboard, Chat notifications, SystemConfig admin) are already shipped in v2.1.

**Existing baseline relevant to this milestone:**
- Simple password auth with custom `User` model (`AbstractUser`, admin/member roles)
- `SystemConfig` key-value store (str/int/bool/float/json types, category grouping, `get_all_by_category()`)
- 13 regex spam patterns in `spam_filter.py` — no whitelist or learning
- Chat notifier using Cards v2 via incoming webhook (assignment, breach summary, personal breach, EOD summary)
- Settings page with 6 tabs already built: Assignment Rules, Category Visibility, SLA Config, Webhooks, Inboxes, System Config (raw key/value editor)
- Login page: branded with "VIPL Email Triage" text, placeholder icon (generic indigo email SVG, not actual VIPL logo)

---

## Table Stakes

Features users expect at v2.2. Missing = product feels unfinished or harder to use than it should be.

| Feature | Why Expected | Complexity | Dependencies on Existing |
|---------|--------------|------------|--------------------------|
| Google OAuth SSO (domain-locked to @vidarbhainfotech.com) | All 4-5 users have @vidarbhainfotech.com Google accounts. Password auth for a Google Workspace org is unnecessary friction. Any internal tool at a Google Workspace company is expected to support "Sign in with Google". | Medium | `django-allauth[socialaccount]` package. SocialAccount/SocialApp/SocialToken migrations. Custom `SocialAccountAdapter` for server-side domain validation. GCP OAuth credentials. `django.contrib.sites` with `SITE_ID = 1` (common setup pitfall — allauth requires this). |
| Preserve password auth alongside OAuth during transition | If OAuth misconfiguration locks out the superuser, the system is completely inaccessible. The superuser must always have a fallback. One locked-out admin = catastrophic for a 4-person team. | Low | No conflict with allauth — it supports both simultaneously. Just don't disable `django.contrib.auth` login. |
| Settings page: pre-filled current values on inputs | The System tab currently shows raw key/value rows. Users editing `quiet_hours_start` must remember the current value and type it blind. This is a basic UX expectation for any settings form. | Low | `SystemConfig.get_all_by_category()` already exists. Context already passes `config_groups` to the template. Pure template change: add `value="{{ item.value }}"` to text inputs. |
| Settings page: type-aware input widgets | Boolean config currently shows as a text input — users type "true"/"false" manually. Integer fields have no numeric validation. `SystemConfig.ValueType` already declares str/int/bool/float/json — the UI should reflect this. | Low | Pure template change in `_config_editor.html`. No backend changes. `value_type` already in context. |
| Spam whitelist: "Not Spam" action per sender | When a legitimate email from a real client gets auto-filtered as spam, there is no recovery path except editing `spam_filter.py` and redeploying. This erodes trust in the spam filter. Users expect to be able to override false positives. | Medium | New `SpamWhitelist` model (email or domain entry). `spam_filter.py` updated to check whitelist before regex. Email detail panel needs "Whitelist Sender" action (admin-only). New migration. |
| VIPL logo/branding in navbar and login | The login page and sidebar currently show a generic placeholder icon. At `triage.vidarbhainfotech.com`, users expect VIPL brand identity. This is table stakes for any internal tool post-launch. | Low | Logo asset from Google Drive. `base.html` sidebar logo slot. `login.html` icon div. Template-only change. No backend work. |

---

## Differentiators

Features that make v2.2 meaningfully better than v2.1. Not strictly expected, but high daily value for the 4-person team.

| Feature | Value Proposition | Complexity | Dependencies on Existing |
|---------|-------------------|------------|--------------------------|
| OAuth domain lock: auto-provision new users | New team members sign in with Google and get an auto-created `User` account with `role=MEMBER`. Admin promotes via Django admin. Eliminates the manual "create account" step for onboarding. | Medium add-on to OAuth | Custom `SocialAccountAdapter.pre_social_login()` validates `@vidarbhainfotech.com` domain. `AUTH_PARAMS: {hd: 'vidarbhainfotech.com'}` is an advisory hint to Google's consent screen — server-side check is mandatory (hd can be bypassed by crafting a token). |
| Spam whitelist: domain-level blocking | Whitelist `@trustedclient.com` to prevent any future email from that domain being filtered. More efficient than per-sender entries when entire domains are trusted or untrusted. | Low add-on to whitelist | `SpamWhitelist` model with `entry_type` field (email vs domain). `is_spam()` checks domain prefix match. Same model, small extension. |
| Chat cards: per-email "Open Email" links in breach alerts | `notify_personal_breach` currently shows a list of overdue emails but only one global "Open Dashboard" button. Adding a direct link per email in the card lets assignees navigate to the specific overdue email in one tap, not two. | Low | Pure change to `notify_personal_breach()` in `chat_notifier.py`. URL pattern `/emails/?selected={pk}` already used in `notify_assignment`. No new endpoints. |
| Settings: inline HTMX save feedback on all tabs | System Config tab already has save confirmation. Webhooks and Inboxes tabs do. SLA Config tab currently lacks inline feedback — save is silent. Consistent feedback across all settings tabs. | Low | HTMX 2.0 already loaded. Pattern established in assignment rules and webhooks tabs. |
| Spam Whitelist management UI in Settings | View, add, and remove whitelist entries from a new "Spam" tab in the Settings page. Currently users would need Django admin to manage the whitelist, which is clunky. | Low-Medium | Extends existing settings tabs pattern. New HTMX partials. Relies on `SpamWhitelist` model (table stakes item above). |

---

## Anti-Features

Features to explicitly NOT build in v2.2.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Interactive Chat buttons (Acknowledge/Close from Chat) | Google Chat incoming webhooks are one-way. Responding to button clicks requires a full Chat bot with a public HTTPS endpoint, App credentials, and interaction event handling. This is a different architecture from a webhook notifier, not an upgrade. Confirmed: "Webhooks aren't conversational. They can't respond to or receive messages from users or Chat app interaction events." | Keep webhook-only design. All state-mutating actions go through the dashboard. |
| ML-based spam learning (Naive Bayes / retraining) | Overkill for under 50 real business emails/day. Requires scikit-learn, training data pipeline, model persistence, and ongoing maintenance. 13 regex patterns catch nearly all actual spam at this volume. | Whitelist/blacklist by sender or domain. Add patterns to `spam_filter.py` manually for new spam types. |
| Full open Google OAuth registration | Anyone with a Google account could create an account. VIPL needs controlled access. | Domain-lock to @vidarbhainfotech.com at the adapter level. Admin promotes auto-provisioned users to specific roles. |
| Dynamic theme colors from Settings UI | Tailwind CDN v4 (`@tailwindcss/browser`) compiles CSS from source HTML at runtime. Database-driven theme values cannot be injected into the Tailwind JIT compilation pipeline. CSS custom properties set via JS on `<html>` element are the workaround, but they do not affect Tailwind utility classes. | Set VIPL brand colors once in the `@theme {}` block in `base.html`. Not a settings-driven feature. |
| Password reset email flow | System has 4 users total. Admin resets passwords via Django admin. Configuring SMTP for password reset adds complexity for a feature that's used at most once a year, and becomes obsolete once OAuth is live. | Keep Django admin password reset. Post-OAuth, password auth is the superuser fallback only. |
| Settings "raw JSON editor" for SystemConfig | Error-prone for the team. A malformed JSON value can break the config system. Type-aware form inputs are safer. | Type-aware inputs (toggle for bool, number for int, textarea for json as fallback). |

---

## Feature Dependencies

```
Google OAuth SSO
  requires:
    django-allauth[socialaccount] installed
    SocialAccount/SocialApp/SocialToken migrations run on VM
    Custom SocialAccountAdapter (domain validation)
    GCP OAuth consent screen (Internal type, utilities-vipl project)
    Web app OAuth 2.0 credentials in GCP
    django.contrib.sites + SITE_ID = 1 in settings (common pitfall)
    Authorized redirect URI: https://triage.vidarbhainfotech.com/accounts/google/login/callback/
  enables:
    Auto-provision new users on first Google sign-in
    Superuser retains password auth as fallback (keep both active)

Spam Whitelist (table stakes)
  requires:
    New SpamWhitelist model + migration
    spam_filter.py updated: check whitelist before regex
    Email detail panel: "Whitelist Sender" button (admin-only, new POST endpoint)
  enables:
    Spam Whitelist domain-level blocking (low add-on — same model, entry_type field)
    Spam Whitelist management UI in Settings (new tab, HTMX partials)

Settings page type-aware inputs + pre-filled values
  requires:
    No new models or backend changes
    Template change in _config_editor.html only
  no blockers

VIPL branding
  requires:
    Logo asset (from Google Drive — external dependency)
    base.html and login.html template edits only
  no blockers

Chat per-email links in breach alerts
  requires:
    No new models or endpoints
    chat_notifier.py: notify_personal_breach() only
  no blockers
```

---

## MVP Recommendation for v2.2

Ship in this order:

1. **VIPL branding** — Unblocked, 1-2 hours, immediately visible improvement.
2. **Settings page type-aware inputs + pre-filled values** — Unblocked, 2-3 hours, immediate UX improvement for whoever manages config.
3. **Spam whitelist (model + filter logic + "Whitelist Sender" button)** — High daily value, medium effort. Builds foundation for the UI.
4. **Google OAuth SSO** — Biggest UX improvement. Slightly more setup (GCP credentials, allauth config, migrations). Do after other polish is in so a broken OAuth doesn't block access to anything else.
5. **Chat per-email links in breach alerts** — 30 minutes, pure logic change.
6. **Spam Whitelist management UI in Settings** — Can use Django admin as interim. Build UI once the model is stable.

---

## Implementation Notes by Feature

### Google OAuth SSO

**Package:** `django-allauth[socialaccount]` — HIGH confidence (official docs confirmed current, active in 2024-2025)

**Configuration pattern:**
```python
INSTALLED_APPS += [
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]
SITE_ID = 1  # Critical — allauth requires this
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email', 'openid'],
        'AUTH_PARAMS': {
            'access_type': 'online',
            'hd': 'vidarbhainfotech.com',  # Advisory hint to Google UI only
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}
SOCIALACCOUNT_ADAPTER = 'apps.accounts.adapters.VIPLSocialAccountAdapter'
```

**Domain enforcement (mandatory server-side — hd parameter is not a security control):**
```python
# apps/accounts/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect

class VIPLSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email', '')
        if not email.endswith('@vidarbhainfotech.com'):
            raise ImmediateHttpResponse(redirect('/accounts/login/?error=domain'))
```

**GCP setup:** OAuth consent screen type = Internal (automatically restricts to @vidarbhainfotech.com Workspace accounts as an additional guard, but server-side check is still required). Create credentials in `utilities-vipl` project. Add authorized redirect URI.

**SocialApp record:** Store client_id and secret in the `SocialApp` DB record via Django admin (post-migration), OR configure in `SOCIALACCOUNT_PROVIDERS` via settings/env vars to avoid DB dependency.

### Spam Whitelist

**Model design:**
```python
class SpamWhitelist(TimestampedModel):
    ENTRY_TYPE_EMAIL = 'email'
    ENTRY_TYPE_DOMAIN = 'domain'
    ENTRY_TYPE_CHOICES = [('email', 'Email Address'), ('domain', 'Domain')]

    entry = models.CharField(max_length=254, unique=True)  # e.g. "client@co.com" or "@co.com"
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True)
    class Meta:
        ordering = ['entry_type', 'entry']
```

**Logic in spam_filter.py:**
```python
def is_whitelisted(sender_email: str) -> bool:
    """Check if sender is in the whitelist. Returns True if whitelisted (not spam)."""
    domain = '@' + sender_email.split('@')[-1].lower() if '@' in sender_email else ''
    return SpamWhitelist.objects.filter(
        entry__in=[sender_email.lower(), domain]
    ).exists()
```

Cache this check (Django cache framework, 60s TTL) to avoid per-email DB queries during high-volume poll cycles.

**is_spam() updated order of operations:**
1. Check whitelist first — if whitelisted, return None immediately
2. Run regex patterns — if matched, return TriageResult(is_spam=True)
3. Return None (not spam)

Note: `spam_filter.py` currently has no Django imports (`# Django imports? No`). Adding whitelist DB check adds a Django ORM dependency. The module will need to import Django models, which is fine since it's called from `pipeline.py` which already runs in Django context.

### Settings Page Type-Aware Inputs

Pure template change in `templates/emails/_config_editor.html`. `SystemConfig.ValueType` choices already available in template context via `value_type` attribute on each config item. Map:
- `value_type == "bool"` → `<input type="checkbox">` checked if value is "true"/"1"/"yes"
- `value_type == "int"` → `<input type="number" step="1">`
- `value_type == "float"` → `<input type="number" step="any">`
- `value_type == "str"` → `<input type="text">` with current value pre-filled
- `value_type == "json"` → `<textarea>` (existing, keep)

The save endpoint must handle checkbox semantics: unchecked checkbox sends no form field, so the view must interpret missing bool field as "false".

### Chat Card Improvements

**Within webhook-only constraints** (no interactive callbacks possible):

`notify_personal_breach()` improvement — add per-email button:
```python
# For each breached email, add a buttonList alongside decoratedText
{
    "decoratedText": {
        "topLabel": f"{emoji} {pri} | {overdue_str} overdue",
        "text": item.get('subject', '')[:50],
        "button": {
            "text": "Open",
            "onClick": {"openLink": {"url": f"{tracker_url}/emails/?selected={item['pk']}"}}
        }
    }
}
```
Note: `decoratedText` supports an inline `button` field in Cards v2. The `item` dict in `notify_personal_breach` currently carries `subject`, `priority`, `overdue_minutes` — add `pk` to the breach data structure in the caller.

**Cannot improve without full Chat bot architecture:** Action buttons that POST back to mutate state (Acknowledge from Chat, Close from Chat, Assign from Chat).

---

## Sources

- django-allauth Google provider docs: https://docs.allauth.org/en/dev/socialaccount/providers/google.html — HIGH confidence
- django-allauth advanced adapter docs: https://docs.allauth.org/en/dev/socialaccount/advanced.html — HIGH confidence
- Google Chat Cards v2 reference: https://developers.google.com/workspace/chat/api/reference/rest/v1/cards — HIGH confidence
- Google Chat interactive elements: https://developers.google.com/workspace/chat/design-interactive-card-dialog — HIGH confidence
- Google Chat webhook one-way limitation confirmed: https://developers.google.com/workspace/chat/quickstart/webhooks — HIGH confidence
- Google Chat new widgets (Oct 2024): https://workspaceupdates.googleblog.com/2024/10/new-widgets-google-chat-app-cards.html — MEDIUM confidence
- Existing codebase (direct read): `spam_filter.py`, `chat_notifier.py`, `core/models.py`, `accounts/models.py`, `templates/emails/settings.html`, `templates/registration/login.html` — HIGH confidence
