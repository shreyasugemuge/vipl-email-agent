# Phase 2: Settings Page + Spam Whitelist - Research

**Researched:** 2026-03-14
**Domain:** Django models, HTMX forms, spam filtering
**Confidence:** HIGH

## Summary

This phase is entirely within the existing stack (Django 4.2, HTMX 2.0, Tailwind v4 CDN). No new libraries are needed. The work involves: (1) a new `SpamWhitelist` model with migrations, (2) modifying `spam_filter.is_spam()` to check the whitelist before regex, (3) adding a 7th "Whitelist" tab to the settings page, (4) adding a "Whitelist Sender" button to the email detail panel, (5) fixing boolean checkbox handling in config editor, (6) a data migration to normalize existing bool values, and (7) consistent inline save feedback across all settings tabs.

All patterns needed already exist in the codebase. The config editor template already has type-aware inputs and save feedback. The settings page already has 6 tabs with a `switchTab()` JS function. Admin-only POST endpoints with HTMX partial re-rendering are established throughout.

**Primary recommendation:** Follow existing patterns exactly. No new dependencies. The main architectural decision is how `spam_filter.py` accesses the whitelist (it currently has no Django imports -- the whitelist check should be injected via the pipeline, same as the function is already injected via `spam_filter_fn` parameter).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Whitelist tab: simple table layout with rows (email/domain, type badge, added-by, date, delete button). Inline add form always visible at top. Delete requires inline confirmation. Empty state message specified.
- Whitelist button in email detail: whitelists exact sender email (not domain). Button in action bar next to Assign/Acknowledge/Close. Visible on all emails (not just spam). Admin-only. Green success banner with 3s fade via HTMX swap.
- Settings save feedback: all tabs get consistent inline green banner "Configuration saved successfully." Same style across all 7 tabs.
- Bool normalization: data migration to lowercase existing values. `typed_value` getter made case-insensitive. Hidden input fallback before each checkbox (value="false") so unchecked checkboxes submit correctly.

### Claude's Discretion
- Exact table column widths and responsive behavior
- Confirmation UI pattern for whitelist delete (inline "Sure?" text vs small popover)
- Whether save feedback auto-fades or stays until next action
- SpamWhitelist model field details beyond email/domain/type/added_by

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| R2.1 | Type-aware input widgets in _config_editor.html (checkbox/number/text/textarea by value_type) | Config editor already has type-aware inputs (bool->checkbox, int->number, float->number, str->text). Only gap: no textarea for long strings or JSON. Add textarea for `json` type. |
| R2.2 | Pre-fill all settings inputs with current DB values | Already implemented -- `value="{{ cfg.value }}"` and `{% if cfg.typed_value %}checked{% endif %}` in config editor. Verify other tabs also pre-fill. |
| R2.3 | SpamWhitelist model with email/domain entry types, migration | New model extending SoftDeleteModel + TimestampedModel. Schema migration + seed data. |
| R2.4 | spam_filter.is_spam() checks whitelist first, AI triage always runs regardless | Modify pipeline to pass whitelist data to spam_filter_fn, or make spam_filter import-aware. Key: whitelisted emails skip spam filter but ALWAYS go through AI triage. |
| R2.5 | "Whitelist Sender" button in email detail panel (admin-only POST endpoint) | New URL pattern, new view function, HTMX button in _email_detail.html action bar. |
| R2.6 | Spam whitelist management tab in settings (add/remove entries, HTMX) | New tab partial _whitelist_tab.html, new view for add/remove, settings_view context update. |
| R2.7 | Data migration to normalize existing bool values to lowercase | RunPython migration on SystemConfig, pattern exists in 0004 migration. |
| R2.8 | Inline save feedback on SLA Config tab (currently silent) | Extend existing _config_editor.html pattern to SLA tab partial. |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Web framework | Already in use, all patterns established |
| HTMX | 2.0 (CDN) | Partial page updates | Already used for all settings saves |
| Tailwind CSS | v4 (CDN play) | Styling | Already used for all UI |
| pytest-django | (in requirements-dev) | Testing | Already used for 257 tests |

### No New Dependencies Needed
This phase requires zero new packages. Everything is built with existing Django models, views, templates, and HTMX patterns already in the codebase.

## Architecture Patterns

### Recommended Project Structure Changes
```
apps/emails/
  models.py                    # + SpamWhitelist model
  views.py                     # + whitelist CRUD views, whitelist_sender view
  urls.py                      # + whitelist URL patterns
  services/spam_filter.py      # + whitelist check before regex
  migrations/
    0007_spamwhitelist.py       # Schema migration
    0008_normalize_bools.py     # Data migration

templates/emails/
  _whitelist_tab.html           # New settings tab partial
  _email_detail.html            # + Whitelist Sender button
  _config_editor.html           # + hidden input for checkboxes
  settings.html                 # + 7th tab button
```

### Pattern 1: SpamWhitelist Model
**What:** New model for email/domain whitelist entries
**When to use:** Storing trusted sender addresses/domains

```python
class SpamWhitelist(SoftDeleteModel, TimestampedModel):
    """Trusted sender/domain that bypasses spam regex filter."""

    class EntryType(models.TextChoices):
        EMAIL = "email", "Email"
        DOMAIN = "domain", "Domain"

    entry = models.CharField(max_length=255, db_index=True)
    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
        default=EntryType.EMAIL,
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="whitelist_entries",
    )
    reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("entry", "entry_type")]

    def __str__(self):
        return f"{self.entry} ({self.entry_type})"
```

Key design decisions:
- Uses `SoftDeleteModel` (project convention: nothing truly deleted)
- Uses `TimestampedModel` for `created_at`/`updated_at`
- `entry` field holds either email address or domain
- `entry_type` discriminator for email vs domain matching
- `unique_together` prevents duplicate entries
- `added_by` FK tracks who added it (admin accountability)
- Optional `reason` field (Claude's discretion area)

### Pattern 2: Whitelist-Aware Spam Filter
**What:** Check whitelist before regex patterns
**Critical requirement:** Whitelisted senders MUST still go through AI triage (phishing via spoofed addresses)

The current `spam_filter.py` is a pure module with no Django imports. Two approaches:

**Approach A (Recommended): Pass whitelist data into pipeline**
```python
# In pipeline.py, before calling spam_filter_fn:
from apps.emails.models import SpamWhitelist

def _is_whitelisted(sender_email: str) -> bool:
    """Check if sender email or domain is whitelisted."""
    domain = sender_email.split("@")[-1] if "@" in sender_email else ""
    return SpamWhitelist.objects.filter(
        models.Q(entry_type="email", entry__iexact=sender_email) |
        models.Q(entry_type="domain", entry__iexact=domain)
    ).exists()

# In process_email():
if _is_whitelisted(email_msg.sender_email):
    # Skip spam filter, proceed directly to AI triage
    spam_result = None
else:
    spam_result = spam_filter_fn(email_msg)
```

This keeps `spam_filter.py` pure (no Django imports) and puts the whitelist check in `pipeline.py` which already has ORM access.

**Approach B: Modify spam_filter.py to accept whitelist**
```python
def is_spam(email_msg: EmailMessage, whitelisted_emails=None, whitelisted_domains=None):
    if whitelisted_emails and email_msg.sender_email.lower() in whitelisted_emails:
        return None
    # ... existing regex check
```

**Recommendation:** Approach A. It maintains the separation of concerns, keeps spam_filter.py testable without DB, and the pipeline already orchestrates all the steps.

### Pattern 3: Hidden Input for Checkbox Bool Fix
**What:** HTML pattern to ensure unchecked checkboxes submit "false"
```html
<!-- Hidden input sends "false" when checkbox unchecked -->
<input type="hidden" name="config_{{ cfg.key }}" value="false">
<input type="checkbox" name="config_{{ cfg.key }}" value="true"
       {% if cfg.typed_value %}checked{% endif %}>
```

When checkbox is checked, HTML submits both values but the last one wins (the checkbox "true"). When unchecked, only the hidden "false" submits. The existing `settings_config_save` view already handles `elif cfg.value_type == "bool"` for missing fields, but the hidden input approach is more robust and standard.

**Note:** The existing view already handles this at line 746-749 of views.py. The hidden input is a belt-and-suspenders approach that makes the form self-documenting.

### Pattern 4: HTMX Whitelist Sender Button
**What:** Button in email detail action bar that whitelists the sender
```html
<form hx-post="{% url 'emails:whitelist_sender' email.pk %}"
      hx-target="#whitelist-feedback" hx-swap="innerHTML">
    {% csrf_token %}
    <button type="submit" class="px-3 py-1.5 text-[10px] font-bold ...">
        Whitelist Sender
    </button>
</form>
<div id="whitelist-feedback"></div>
```

The view returns an inline success banner HTML fragment that auto-fades.

### Anti-Patterns to Avoid
- **Importing Django ORM in spam_filter.py:** Keep it pure for testability. Put whitelist check in pipeline.py.
- **Hard-deleting whitelist entries:** Use SoftDeleteModel.delete() (project convention).
- **Skipping AI triage for whitelisted senders:** The whole point is that whitelisted senders skip SPAM FILTER only. AI triage ALWAYS runs (phishing protection).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Soft delete | Custom delete logic | SoftDeleteModel base class | Project convention, already tested |
| Admin check | Custom middleware | `_require_admin()` helper (views.py:481) | Already used everywhere |
| HTMX partials | Custom AJAX | HTMX `hx-post` + `hx-target` + `hx-swap` | Already used in all settings tabs |
| Tab switching | Custom JS router | Existing `switchTab()` function | Already works for 6 tabs |

## Common Pitfalls

### Pitfall 1: Checkbox Bool Submission
**What goes wrong:** Unchecked checkboxes send no form field at all
**Why it happens:** HTML spec -- unchecked checkboxes are excluded from form submission
**How to avoid:** Hidden input with value="false" before each checkbox. The server-side view already handles missing bool fields (views.py:746-749), but the hidden input is cleaner.
**Warning signs:** Toggling a bool off doesn't save.

### Pitfall 2: Whitelist Bypasses AI Triage
**What goes wrong:** Whitelisted senders skip both spam filter AND AI, getting no triage at all
**Why it happens:** Confusing "skip spam" with "skip all processing"
**How to avoid:** Whitelist check ONLY bypasses `spam_filter_fn()`. The `ai_processor` step must ALWAYS run regardless of whitelist status.
**Warning signs:** Whitelisted emails saved with empty category/priority/summary.

### Pitfall 3: Case Sensitivity in Whitelist Matching
**What goes wrong:** `John@Acme.com` not matched against whitelist entry `john@acme.com`
**Why it happens:** String comparison without normalization
**How to avoid:** Store entries lowercase, compare with `__iexact` or normalize both sides
**Warning signs:** Inconsistent whitelist behavior.

### Pitfall 4: Bool Value Normalization Incomplete
**What goes wrong:** Data migration normalizes existing values, but new values could still be saved uppercase
**Why it happens:** Only fixing existing data, not the write path
**How to avoid:** The `typed_value` getter is already case-insensitive (line 87: `self.value.lower() in ("true", "1", "yes")`). The write path in `settings_config_save` already writes "true"/"false" lowercase from the form. The hidden input also sends lowercase "false". This is safe.
**Warning signs:** None expected -- both read and write paths are covered.

### Pitfall 5: HTMX Swap Target Missing on Tab Switch
**What goes wrong:** Save feedback shows in wrong panel or not at all after tab switch
**Why it happens:** HTMX target div may not exist if user switches tabs before response
**How to avoid:** Each tab partial has its own feedback container with unique ID. Use `hx-target` pointing to the container inside the partial itself.

## Code Examples

### Existing Config Save Pattern (to replicate for SLA/other tabs)
```python
# views.py:732-761 -- settings_config_save
# Returns partial template with save_success=True context
return render(request, "emails/_config_editor.html", {
    "config_groups": config_groups,
    "save_success": True,
})
```

```html
<!-- _config_editor.html:4-7 -- success banner -->
{% if save_success %}
<div class="mb-4 px-4 py-2 bg-emerald-50 border border-emerald-200/60 rounded-lg text-xs font-medium text-emerald-700">
    Configuration saved successfully.
</div>
{% endif %}
```

### Existing Admin Check Pattern
```python
# views.py:481-483
def _require_admin(user):
    """Return True if user is admin/staff."""
    return user.is_staff or user.role == User.Role.ADMIN
```

### Existing HTMX Form Pattern
```html
<form hx-post="{% url 'emails:settings_config_save' %}"
      hx-target="#config-editor" hx-swap="innerHTML">
    {% csrf_token %}
    <!-- fields -->
    <button type="submit">Save</button>
</form>
```

### Data Migration Pattern (from 0004)
```python
from django.db import migrations

def normalize_bools(apps, schema_editor):
    SystemConfig = apps.get_model("core", "SystemConfig")
    for cfg in SystemConfig.objects.filter(value_type="bool"):
        if cfg.value in ("True", "TRUE", "False", "FALSE", "Yes", "No"):
            cfg.value = cfg.value.lower()
            if cfg.value in ("yes",):
                cfg.value = "true"
            elif cfg.value in ("no",):
                cfg.value = "false"
            cfg.save(update_fields=["value"])

def reverse_noop(apps, schema_editor):
    pass  # No meaningful reverse

class Migration(migrations.Migration):
    dependencies = [("core", "XXXX_previous"),]
    operations = [migrations.RunPython(normalize_bools, reverse_noop),]
```

**Note:** The bool normalization migration goes in `apps/core/migrations/` since `SystemConfig` is in `apps.core.models`.

### Whitelist Tab Template Pattern
```html
<!-- _whitelist_tab.html -->
<div id="whitelist-content">
    {% if save_success %}
    <div class="mb-4 px-4 py-2 bg-emerald-50 border border-emerald-200/60 rounded-lg text-xs font-medium text-emerald-700">
        {{ save_message|default:"Changes saved." }}
    </div>
    {% endif %}

    <!-- Add form (always visible) -->
    <form hx-post="{% url 'emails:whitelist_add' %}"
          hx-target="#whitelist-content" hx-swap="innerHTML"
          class="flex items-center gap-2 mb-4">
        {% csrf_token %}
        <input type="text" name="entry" placeholder="email@example.com or example.com"
               class="text-sm border border-slate-200/80 rounded-lg px-3 py-1.5 ...">
        <select name="entry_type" class="text-sm border border-slate-200/80 rounded-lg px-3 py-1.5 ...">
            <option value="email">Email</option>
            <option value="domain">Domain</option>
        </select>
        <button type="submit" class="px-4 py-2 text-xs font-bold text-white bg-indigo-600 rounded-lg ...">Add</button>
    </form>

    <!-- Table of entries -->
    <table class="w-full text-xs">...</table>
</div>
```

## State of the Art

No technology changes relevant to this phase. All tools and patterns are stable Django 4.2 + HTMX 2.0 patterns that have been in use since v2.0.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails/tests/test_spam_filter.py apps/emails/tests/test_settings_views.py -x` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| R2.1 | Type-aware inputs render correctly | unit (view) | `pytest apps/emails/tests/test_settings_views.py -x -k config` | Partial (test_settings_views.py exists but no specific config render tests) |
| R2.2 | Settings pre-filled with DB values | unit (view) | `pytest apps/emails/tests/test_settings_views.py -x -k prefill` | Wave 0 |
| R2.3 | SpamWhitelist model CRUD | unit (model) | `pytest apps/emails/tests/test_whitelist.py -x` | Wave 0 |
| R2.4 | Whitelist check before spam filter, AI always runs | unit (service) | `pytest apps/emails/tests/test_spam_filter.py apps/emails/tests/test_pipeline.py -x -k whitelist` | Wave 0 |
| R2.5 | Whitelist sender button POST endpoint | unit (view) | `pytest apps/emails/tests/test_settings_views.py -x -k whitelist_sender` | Wave 0 |
| R2.6 | Whitelist management tab add/remove | unit (view) | `pytest apps/emails/tests/test_settings_views.py -x -k whitelist_tab` | Wave 0 |
| R2.7 | Bool normalization migration | unit (migration) | `pytest apps/core/tests/test_bool_migration.py -x` | Wave 0 |
| R2.8 | Inline save feedback on SLA tab | unit (view) | `pytest apps/emails/tests/test_settings_views.py -x -k sla_feedback` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_spam_filter.py apps/emails/tests/test_settings_views.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_whitelist.py` -- covers R2.3, R2.4, R2.5, R2.6
- [ ] `apps/core/tests/test_bool_migration.py` -- covers R2.7 (or inline in test_models.py)
- [ ] Tests for save feedback (R2.8) in test_settings_views.py

## Open Questions

1. **SLA tab save feedback mechanism**
   - What we know: The SLA tab uses `_sla_config.html` partial with its own save endpoint `settings_sla_save`. Need to verify if it already has a success banner or not.
   - What's unclear: Whether the SLA save view already returns `save_success` context.
   - Recommendation: Check `settings_sla_save` view and `_sla_config.html` template during implementation. If missing, add same pattern as config editor.

2. **Whitelist entry validation**
   - What we know: Need to validate email format and domain format before saving.
   - What's unclear: How strict validation should be (full RFC 5322 or simple regex).
   - Recommendation: Use Django's `EmailField` validator for email type, simple domain regex for domain type. Reject empty/whitespace entries.

## Sources

### Primary (HIGH confidence)
- Project codebase: `apps/emails/views.py`, `apps/emails/models.py`, `apps/core/models.py` -- all patterns verified by reading source
- Project codebase: `templates/emails/_config_editor.html`, `templates/emails/settings.html` -- existing UI patterns
- Project codebase: `apps/emails/services/spam_filter.py`, `apps/emails/services/pipeline.py` -- current spam filter architecture

### Secondary (MEDIUM confidence)
- Django 4.2 documentation -- model patterns, migrations, form handling (well-known, stable API)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns exist in codebase
- Architecture: HIGH -- direct extension of existing models/views/templates
- Pitfalls: HIGH -- checkbox bool handling and whitelist-vs-AI-triage are well-understood edge cases

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable Django 4.2 patterns, no fast-moving dependencies)
