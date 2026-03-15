# Phase 1: Data & Bug Fixes - Research

**Researched:** 2026-03-15
**Domain:** Django templates, HTMX, Tailwind CSS v4, JavaScript (mobile UX), Django data migrations
**Confidence:** HIGH

## Summary

Phase 1 fixes 7 bugs across the Django template/HTMX stack. All bugs are in existing code with well-understood patterns -- no new libraries or architectural changes needed. The fixes span three domains: (1) backend data cleanup in `ai_processor.py` + a data migration for BUG-01, (2) CSS/Tailwind responsive fixes for BUG-03/04/07, and (3) JavaScript behavioral fixes for BUG-02/05/06.

The codebase uses Django templates with HTMX 2.0 (CDN) and Tailwind CSS v4 (CDN browser build). All templates extend `base.html` which provides `{% block title %}`, `{% block page_title %}`, and `{% block extra_js %}` hooks. The HTMX partial rendering pattern (`request.htmx` detection) is established and works well -- BUG-05 needs to leverage `hx-swap-oob` or include the count element in partial responses.

**Primary recommendation:** Fix each bug independently in order of data-first (BUG-01), then template/CSS fixes (BUG-03, 04, 06, 07), then JS behavioral fixes (BUG-02, 05) since the JS fixes are the most complex.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- BUG-01: Clean at ingest time in `ai_processor.py` -- parse XML-wrapped names and extract inner text. Django data migration to fix existing records. No display-layer filter.
- BUG-02: Full-screen slide-in from right. Back button at top-left. Lock body scroll. Support browser back via `history.pushState`. Overlay stays.
- BUG-07: Mobile: position below header (top-16 / 64px), right-aligned. Desktop: no change. Swipe-right-to-dismiss gesture. Keep auto-dismiss 4s. Close button tap target 44x44px minimum on mobile.

### Claude's Discretion
- BUG-03: Mobile filter stacking implementation details
- BUG-04: Chip overflow fix approach (scroll vs wrap vs abbreviation)
- BUG-05: HTMX technique for updating email count
- BUG-06: Which templates need title block updates (audit all pages)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUG-01 | AI suggestion displays clean name text, not raw XML markup | XML parsing regex in `_parse_suggested_assignee()`, data migration pattern for JSONField cleanup |
| BUG-02 | Mobile detail panel slides in reliably with scroll lock and back button | Current panel JS in `email_list.html`, `history.pushState`/`popstate` pattern, body overflow toggle |
| BUG-03 | Mobile filter bar displays as stacked vertical layout | Tailwind responsive classes on `#mobile-filters` div |
| BUG-04 | Activity page filter chips don't truncate | Chip container CSS in `activity_log.html` |
| BUG-05 | Email count updates when switching views | HTMX `hx-swap-oob` or partial response includes count element |
| BUG-06 | All pages have consistent "VIPL Triage \| {Page Name}" title | Template audit -- `{% block title %}` in all templates |
| BUG-07 | Toast notifications position below header on mobile | Toast container CSS in `base.html`, touch event JS |
</phase_requirements>

## Standard Stack

### Core (Already in Use -- No Changes)
| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| Django | 4.2 LTS | Web framework | Templates, views, migrations |
| HTMX | 2.0.8 | Dynamic partials | CDN, `hx-swap-oob` for OOB updates |
| Tailwind CSS | v4 | Utility CSS | CDN browser build, responsive `md:` prefix |
| django-htmx | (installed) | `request.htmx` detection | Middleware already configured |

### No New Dependencies Required
This phase requires zero new packages. All fixes use existing Django template mechanics, Tailwind responsive utilities, and vanilla JavaScript.

## Architecture Patterns

### Existing Patterns (Follow These)

**1. Template Inheritance**
All pages extend `base.html` which defines:
- `{% block title %}VIPL Triage{% endblock %}` -- page `<title>` tag
- `{% block page_title %}Dashboard{% endblock %}` -- visible header text
- `{% block extra_js %}` -- page-specific JavaScript
- `{% block content %}` -- main content area

**2. HTMX Partial Rendering**
Views detect HTMX requests and return partial templates:
```python
if getattr(request, "htmx", False):
    return render(request, "emails/_email_list_body.html", context)
return render(request, "emails/email_list.html", context)
```

**3. OOB Swaps for Multi-Element Updates**
Already used for card + detail panel updates after assign/claim:
```python
oob_detail = f'<div id="detail-panel" hx-swap-oob="innerHTML">{detail_html}</div>'
return _HttpResponse(card_html + oob_detail)
```

**4. Toast Notifications**
Defined in `base.html` inside `{% if messages %}` block. Fixed position `top-4 right-4`, uses `toast-in`/`toast-out` CSS keyframe animations, auto-dismiss after 4 seconds.

### Anti-Patterns to Avoid
- **Inline styles for responsive behavior** -- use Tailwind `md:` prefix classes instead
- **jQuery or other JS libraries** -- project is vanilla JS only
- **Modifying `_email_list_body.html` to include non-list elements** -- keep partials focused; use OOB swaps for updating other elements

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XML tag stripping | Custom parser | `re.sub()` with a targeted regex | XML from Claude is simple `<parameter name="X">value</parameter>` pattern |
| Responsive breakpoints | Custom media queries | Tailwind `md:` prefix | Consistent with entire codebase |
| History API for panel | Full router | `history.pushState` + `popstate` listener | Minimal -- just need back button to close panel |

## Common Pitfalls

### Pitfall 1: HTMX Partial Not Updating Count (BUG-05)
**What goes wrong:** When tabs (All/Unassigned/My Emails) use `hx-target="#email-list"`, only the email list body is swapped. The `total_count` span is OUTSIDE `#email-list` in the parent `email_list.html`, so it never updates.
**Why it happens:** The count `<span>{{ total_count }} emails</span>` is at line 156 of `email_list.html`, outside the `#email-list` div that HTMX targets.
**How to avoid:** Two options:
1. **OOB swap (recommended):** Give the count span an ID (e.g., `id="email-count"`), and include an OOB element in the `_email_list_body.html` partial response.
2. **Move count into partial:** Move the count span into `_email_list_body.html` -- but this changes layout structure.

**Recommendation:** Use OOB swap. Add `id="email-count"` to the count span in `email_list.html`. In the view, when it's an HTMX request, render an additional OOB span with updated count and append it to the partial response.

### Pitfall 2: History API State Management (BUG-02)
**What goes wrong:** Using `pushState` without proper `popstate` handling causes the panel to stay open when the user presses back, or navigates away entirely.
**How to avoid:** Push state when panel opens, listen for `popstate` to close panel. Don't push state on desktop (panel is inline). Only push on mobile (`window.innerWidth < 768`).

### Pitfall 3: Body Scroll Lock Leaking (BUG-02)
**What goes wrong:** Setting `overflow: hidden` on body when panel opens, but not removing it when panel closes via all paths (back button, overlay click, browser back).
**How to avoid:** Create a single `closeDetail()` function that handles ALL cleanup (remove translate, add hidden to overlay, remove overflow hidden from body, go back in history if needed). Call it from all close paths.

### Pitfall 4: Data Migration on JSONField (BUG-01)
**What goes wrong:** JSONField contains dicts like `{"name": "<parameter name=\"name\">Shreyas</parameter>"}`. A simple string replace on the raw DB value could corrupt JSON structure.
**How to avoid:** Use Django's `RunPython` migration to iterate Email objects, parse the `ai_suggested_assignee` dict in Python, clean the `name` value with regex, and save back.

### Pitfall 5: Toast Swipe Gesture Conflicts (BUG-07)
**What goes wrong:** Touch event handlers for swipe-to-dismiss can interfere with page scrolling.
**How to avoid:** Only track horizontal swipes (check `deltaX > deltaY`). Use `touchstart`/`touchmove`/`touchend` with a threshold (e.g., 50px horizontal movement).

### Pitfall 6: Inspector Title Inconsistency (BUG-06)
**What goes wrong:** `inspect.html` does NOT extend `base.html` -- it's a standalone HTML page with its own `<title>` tag.
**How to avoid:** Since it's a dev-only page, just update the `<title>` string directly. Don't restructure it to extend `base.html`.

## Code Examples

### BUG-01: XML Cleanup Regex
```python
# In ai_processor.py _parse_suggested_assignee()
import re

def _clean_xml_tags(text: str) -> str:
    """Strip XML-style parameter tags from Claude responses.

    Handles: <parameter name="name">Shreyas</parameter> -> Shreyas
    """
    if not text:
        return text
    # Match <parameter name="...">content</parameter> and extract content
    cleaned = re.sub(r'<parameter\s+name="[^"]*">(.*?)</parameter>', r'\1', text)
    # Also strip any remaining XML-like tags as fallback
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    return cleaned.strip()
```

### BUG-01: Data Migration Pattern
```python
# In a new migration file
from django.db import migrations

def clean_xml_from_assignee(apps, schema_editor):
    import re
    Email = apps.get_model('emails', 'Email')
    pattern = re.compile(r'<parameter\s+name="[^"]*">(.*?)</parameter>')

    for email in Email.objects.exclude(ai_suggested_assignee={}).iterator():
        data = email.ai_suggested_assignee
        if isinstance(data, dict) and data.get('name'):
            name = data['name']
            if '<' in name:  # Quick check before regex
                cleaned = pattern.sub(r'\1', name)
                cleaned = re.sub(r'<[^>]+>', '', cleaned).strip()
                if cleaned != name:
                    data['name'] = cleaned
                    email.ai_suggested_assignee = data
                    email.save(update_fields=['ai_suggested_assignee'])

class Migration(migrations.Migration):
    dependencies = [('emails', '0007_spamwhitelist')]
    operations = [migrations.RunPython(clean_xml_from_assignee, migrations.RunPython.noop)]
```

### BUG-02: Mobile Panel with History API
```javascript
// In email_list.html extra_js block
document.addEventListener('htmx:afterSwap', function(e) {
    if (e.detail.target.id === 'detail-panel') {
        if (window.innerWidth < 768) {
            document.getElementById('detail-panel').classList.remove('translate-x-full');
            document.getElementById('detail-overlay').classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            history.pushState({ detailOpen: true }, '');
        }
    }
});

window.addEventListener('popstate', function(e) {
    if (document.getElementById('detail-panel') &&
        !document.getElementById('detail-panel').classList.contains('translate-x-full')) {
        closeDetailNoHistory();
    }
});

function closeDetailNoHistory() {
    document.getElementById('detail-panel').classList.add('translate-x-full');
    document.getElementById('detail-overlay').classList.add('hidden');
    document.body.style.overflow = '';
}

function closeDetail() {
    closeDetailNoHistory();
    if (history.state && history.state.detailOpen) {
        history.back();
    }
}
```

### BUG-03: Mobile Filter Stacking
```html
<!-- Change the mobile-filters div from flex row to stacked on mobile -->
<div class="hidden md:flex items-center gap-1.5 flex-1" id="mobile-filters">
    <!-- On mobile toggle: show as flex-col w-full -->
</div>
```
Recommended approach: When toggled on mobile, apply `flex-col w-full gap-2` classes, and add `w-full` to each select/input inside.

### BUG-05: OOB Count Update
```python
# In views.py email_list(), for HTMX requests:
if getattr(request, "htmx", False):
    list_html = render_to_string("emails/_email_list_body.html", context, request=request)
    count_html = f'<span id="email-count" hx-swap-oob="true" class="...">{paginator.count} email{"s" if paginator.count != 1 else ""}</span>'
    return _HttpResponse(list_html + count_html)
```

### BUG-06: Title Audit Results
| Template | Current Title | Status | Fix |
|----------|--------------|--------|-----|
| `base.html` | `VIPL Triage` (default) | OK | Base fallback |
| `email_list.html` | `VIPL Triage \| Inbox` | OK | Already correct |
| `activity_log.html` | `VIPL Triage \| Activity` | OK | Already correct |
| `settings.html` | `VIPL Triage \| Settings` | OK | Already correct |
| `registration/login.html` | `VIPL Triage \| Login` | OK | Already correct |
| `accounts/team.html` | (none -- no title block) | **BROKEN** | Add `{% block title %}VIPL Triage \| Team{% endblock %}` |
| `emails/inspect.html` | `VIPL Email Agent -- Dev Inspector` | **BROKEN** | Change to `VIPL Triage \| Dev Inspector` |

### BUG-07: Toast Swipe-to-Dismiss
```javascript
// Add to each toast-item on mobile
document.querySelectorAll('.toast-item').forEach(function(toast) {
    var startX = 0, currentX = 0;
    toast.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
    }, { passive: true });
    toast.addEventListener('touchmove', function(e) {
        currentX = e.touches[0].clientX;
        var deltaX = currentX - startX;
        if (deltaX > 0) {
            toast.style.transform = 'translateX(' + deltaX + 'px)';
            toast.style.opacity = Math.max(0, 1 - deltaX / 200);
        }
    }, { passive: true });
    toast.addEventListener('touchend', function() {
        if (currentX - startX > 50) {
            toast.style.animation = 'toast-out 0.2s ease-in forwards';
            setTimeout(function() { toast.remove(); }, 200);
        } else {
            toast.style.transform = '';
            toast.style.opacity = '';
        }
    });
});
```

## State of the Art

No technology changes needed. All tools are current:
- HTMX 2.0.8 -- current stable
- Tailwind CSS v4 browser build -- current stable
- Django 4.2 LTS -- supported until April 2026

## Open Questions

1. **How many existing records have XML markup in `ai_suggested_assignee`?**
   - What we know: The bug exists in production data on the VM (PostgreSQL)
   - What's unclear: How many records are affected
   - Recommendation: The data migration handles it regardless of count; just log the count during migration

2. **Should `inspect.html` match the pattern exactly?**
   - What we know: It's a standalone dev page (no `base.html` inheritance), currently uses "VIPL Email Agent -- Dev Inspector"
   - Recommendation: Change to "VIPL Triage | Dev Inspector" for consistency, but don't restructure the page

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `source .venv/bin/activate && pytest -x -q` |
| Full suite command | `source .venv/bin/activate && pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-01 | XML cleanup in `_parse_suggested_assignee` | unit | `pytest apps/emails/tests/test_ai_processor.py -x -k parse` | Needs new tests |
| BUG-01 | Data migration cleans existing records | unit | `pytest apps/emails/tests/test_ai_processor.py -x -k migration` | Needs new tests |
| BUG-02 | Mobile panel opens/closes correctly | manual-only | Manual -- browser JS behavior | N/A |
| BUG-03 | Mobile filter bar stacking | manual-only | Manual -- CSS responsive layout | N/A |
| BUG-04 | Activity chips not truncated | manual-only | Manual -- CSS visual check | N/A |
| BUG-05 | Email count updates on view switch | unit | `pytest apps/emails/tests/test_views.py -x -k count` | Needs new tests |
| BUG-06 | Page titles consistent | unit | `pytest apps/emails/tests/test_views.py -x -k title` | Partially exists in test_branding.py |
| BUG-07 | Toast positioning on mobile | manual-only | Manual -- CSS/JS visual check | N/A |

### Sampling Rate
- **Per task commit:** `source .venv/bin/activate && pytest -x -q`
- **Per wave merge:** `source .venv/bin/activate && pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_ai_processor.py` -- add tests for `_parse_suggested_assignee` with XML input (BUG-01)
- [ ] `apps/emails/tests/test_views.py` -- add test that HTMX email_list response includes OOB count element (BUG-05)
- [ ] `apps/emails/tests/test_branding.py` -- verify all pages have correct title pattern (BUG-06)

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `base.html`, `email_list.html`, `_email_card.html`, `_email_detail.html`, `activity_log.html`, `views.py`, `ai_processor.py`, `pipeline.py`, `models.py`
- All findings verified by reading actual source code

### Secondary (MEDIUM confidence)
- HTMX `hx-swap-oob` pattern -- well-documented, already used in codebase (assign/claim views)
- `history.pushState` / `popstate` -- standard Web API, widely documented

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no changes needed, all libraries already in use
- Architecture: HIGH -- all patterns already established in codebase
- Pitfalls: HIGH -- identified from actual code inspection, not speculation

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- no moving parts)
