# Phase 3: VIPL Branding - Research

**Researched:** 2026-03-14
**Domain:** Visual branding (Tailwind CSS v4 theming, Django static files, Google Chat Cards v2)
**Confidence:** HIGH

## Summary

Phase 3 is a pure visual branding pass: replace placeholder indigo/violet colors with VIPL's plum/purple brand identity, add logo assets, and update page titles. The logo source files (1.jpg Vi mark, 2.jpg full logo, 3.jpg white variant) are confirmed accessible on the local machine at the Google Drive sync path. The codebase uses Tailwind CSS v4 via CDN play script with `@theme` custom properties in `base.html`, but HTMX partials use hardcoded Tailwind color classes (63 occurrences of `indigo` or `violet` across 17 template files). The key technical challenge is ensuring partials that get HTMX-swapped contain the correct brand colors since they don't inherit `@theme` tokens -- they use hardcoded Tailwind utility classes directly.

Google Chat Cards v2 supports `imageUrl` in the card header for webhooks, allowing us to add the VIPL icon. However, `fixedFooter` is only available for dialogs (not webhook messages), so the "Sent by VIPL Email Triage" footer must be added as a `textParagraph` widget in the last section instead. The `imageUrl` must be a publicly accessible HTTPS URL, which means we must use the deployed static URL from `triage.vidarbhainfotech.com`.

**Primary recommendation:** Replace the `@theme` indigo palette in `base.html` with plum/purple values derived from the logo (~#7B2D5F), do a search-and-replace across all 17 template files for `indigo` -> brand and `violet` -> brand-accent, copy logo files to `static/img/`, generate favicon, and update chat_notifier.py card headers with `imageUrl` + footer `textParagraph`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Sidebar**: 1.jpg (Vi mark icon) in sidebar header
- **Login page**: 2.jpg (full logo with company name + tagline) centered on login card
- **Favicon**: Generate 32x32 favicon.ico from 1.jpg Vi mark icon
- Logo source files: `/Users/uge/Library/CloudStorage/GoogleDrive-shreyas@vidarbhainfotech.com/Other computers/Laptop/Downloads/vipl logo/` (1.jpg, 2.jpg, 3.jpg)
- Commit logos to `static/img/` -- do not hotlink from Drive
- Claude picks brand colors derived from the logo (dark purple/plum ~#7B2D5F + black #2D2D2D)
- Replace the indigo @theme palette in base.html with brand-derived purple/plum palette
- **Functional status colors stay as-is**: priority badges (red=CRITICAL, amber=HIGH, green=LOW), status dots, SLA countdown colors, spam badges -- all unchanged
- Only brand/accent colors change (buttons, active states, links, focus rings, gradients)
- Google OAuth button stays Google-standard (white + Google logo)
- Full branded login card: 2.jpg logo, tagline, Google sign-in button, clean white background with brand accent on card border, no split layout -- centered card
- Page title format: "VIPL Triage | {Page}" (e.g., "VIPL Triage | Emails", "VIPL Triage | Settings")
- Favicon from Vi mark icon
- Google Chat cards: add VIPL icon image in card header + "Sent by VIPL Email Triage" footer text on all card types, branding is additive
- Footer: Subtle bottom bar on dashboard: "2026 Vidarbha Infotech Pvt. Ltd." in small gray text

### Claude's Discretion
- Exact purple/plum palette values (50-900 scale)
- Sidebar light vs dark background
- Spacing and typography adjustments for logo placement
- Dev inspector (/emails/inspect/) -- leave as-is or update, Claude decides
- How to handle 3.jpg (white version) -- use on dark backgrounds if applicable

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| R3.1 | VIPL logo asset committed to static/img/ | Logo files confirmed accessible at Drive sync path; static/ dir exists with .gitkeep; STATICFILES_DIRS already configured in settings; WhiteNoise serves in production |
| R3.2 | Logo rendered in sidebar and login page | Sidebar logo area identified (base.html lines 76-88, currently SVG envelope icon); Login logo area identified (login.html lines 45-51, currently SVG icon); `{% load static %}` tag needed in both templates |
| R3.3 | Brand color palette applied in @theme block | Current @theme block identified (base.html lines 13-25, indigo values); Plus 6 hardcoded hex values in CSS rules (lines 39, 42-43) need updating |
| R3.4 | All _*.html HTMX partials audited and updated for brand colors | 63 occurrences of indigo/violet across 17 template files catalogued; Each occurrence categorized as brand-accent (change) vs functional (keep) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tailwind CSS v4 | CDN `@tailwindcss/browser@4` | Utility-first CSS | Already in use, @theme directive for custom properties |
| Django staticfiles | Built-in | Serve logo images | Already configured: STATICFILES_DIRS, STATIC_URL, WhiteNoise |
| sips (macOS) | System | Image conversion (favicon) | Native macOS tool, no dependencies needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| WhiteNoise | Already installed | Compressed static files in production | Automatically handles new static/img/ files |
| `{% load static %}` | Django built-in | Template tag for static file URLs | Required in templates that reference logo images |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sips for favicon | Pillow/ImageMagick | sips is zero-dependency on macOS; Pillow would need pip install |
| Hardcoded Tailwind classes | CSS custom properties everywhere | Partials can't reliably access @theme vars when HTMX-swapped; hardcoded classes are the established pattern |

## Architecture Patterns

### Asset File Structure
```
static/
  img/
    vipl-icon.jpg          # 1.jpg Vi mark (sidebar, favicon source)
    vipl-logo-full.jpg     # 2.jpg Full logo with text (login page)
    vipl-logo-white.jpg    # 3.jpg White version (dark backgrounds)
    favicon.ico            # 32x32 generated from vipl-icon.jpg
```

### Pattern 1: @theme Palette Definition
**What:** Define brand colors as CSS custom properties in the Tailwind @theme block, enabling `bg-primary-600`, `text-primary-700` etc.
**When to use:** In `base.html` `<style type="text/tailwindcss">` block.
**Example:**
```css
/* Source: Tailwind CSS v4 docs - @theme directive */
@theme {
    --font-sans: "Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif;
    --color-primary-50: #fdf2f8;
    --color-primary-100: #fce7f1;
    --color-primary-200: #fbc8e0;
    --color-primary-300: #f9a1c8;
    --color-primary-400: #f06da1;
    --color-primary-500: #e8457e;
    --color-primary-600: #7B2D5F;   /* Logo plum - primary brand */
    --color-primary-700: #6a2651;
    --color-primary-800: #582043;
    --color-primary-900: #4a1c39;
}
```
Note: The exact values above are DRAFT -- final palette should be derived from the actual logo plum color (~#7B2D5F) using a proper scale generator. The 600 value should be the logo's actual plum, with lighter/darker values around it.

### Pattern 2: Hardcoded Color Replacement in Partials
**What:** Replace `indigo-*` and `violet-*` classes with the brand color name in all `_*.html` HTMX partial templates.
**When to use:** Every HTMX partial that uses indigo/violet for brand/accent purposes.
**Why:** HTMX-swapped fragments are injected into the DOM and inherit CSS custom properties from the parent page. The `@theme` block in base.html defines `--color-primary-*` tokens. When partials use `bg-primary-600` or `text-primary-700`, Tailwind CSS v4's CDN browser plugin resolves these against the @theme tokens. This works because the CDN plugin is loaded in the parent page and processes the entire DOM, including HTMX-swapped content.

**Critical insight:** The current partials use `indigo-600` (a built-in Tailwind color), NOT `primary-600` (a custom @theme color). The fix has two options:
1. Replace `indigo-600` with `primary-600` in partials (uses @theme token, automatically brand-correct)
2. Replace `indigo-600` with a new brand color name (e.g., `plum-600`) defined in @theme

Option 1 is cleaner: partials say `bg-primary-600` and the @theme block defines what "primary" means. If the brand ever changes, only @theme needs updating.

**However**, there is a subtlety: Tailwind CSS v4 browser plugin processes `<style type="text/tailwindcss">` blocks to generate CSS. When HTMX swaps new HTML into the DOM, the browser plugin needs to detect and process new classes. The Tailwind CSS v4 CDN uses a MutationObserver to watch for DOM changes, so HTMX-swapped content IS processed. Using `bg-primary-600` in partials will work as long as `--color-primary-600` is defined in @theme.

### Pattern 3: Django Static Tag for Images
**What:** Use `{% load static %}` and `{% static 'img/vipl-icon.jpg' %}` in templates.
**When to use:** Every template that references a logo image.
**Example:**
```html
{% load static %}
<img src="{% static 'img/vipl-icon.jpg' %}" alt="VIPL" class="w-8 h-8 rounded-lg">
```

### Pattern 4: Google Chat Card Header with Image
**What:** Add `imageUrl` to card headers and a `textParagraph` footer widget.
**When to use:** All 5 notify methods in chat_notifier.py.
**Example:**
```python
# Source: Google Chat Cards v2 API reference
card = {
    "header": {
        "title": "Poll Summary -- 3 new email(s)",
        "subtitle": "HIGH: 1 | MEDIUM: 2",
        "imageUrl": "https://triage.vidarbhainfotech.com/static/img/vipl-icon.jpg",
        "imageType": "CIRCLE",
        "imageAltText": "VIPL Logo"
    },
    "sections": [
        # ... existing sections ...
        {
            "widgets": [
                {"textParagraph": {"text": "<i>Sent by VIPL Email Triage</i>"}}
            ]
        }
    ],
}
```
Note: `fixedFooter` only works in dialogs, NOT webhook messages. Use a `textParagraph` in the last section instead.

### Anti-Patterns to Avoid
- **Replacing functional status colors:** Priority badges (red, amber, green, blue), SLA countdown colors, and spam badges must NOT be rebranded. They use separate template tags (`priority_base`, `status_base`, `sla_color`) that resolve to semantic colors.
- **Using @theme custom properties directly in inline styles:** Tailwind utility classes like `bg-primary-600` are the correct approach, not `style="background: var(--color-primary-600)"`.
- **Hotlinking logo from Google Drive:** Logos must be committed to `static/img/` and served via WhiteNoise/Django staticfiles.
- **Using relative file paths for Chat imageUrl:** The Chat webhook needs an absolute HTTPS URL (the production domain).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Favicon generation | Custom Python script | `sips -s format ico -z 32 32 input.jpg --out favicon.ico` | macOS native, zero dependencies |
| Color palette generation | Manual hex calculation | Color scale tool or derive from logo plum ~#7B2D5F | Consistent perceptual lightness steps matter for UI |
| Static file serving | Custom middleware | Django staticfiles + WhiteNoise (already configured) | Production-proven, handles hashing/compression |

**Key insight:** This is a visual reskin, not a feature build. The technical complexity is in thoroughness (auditing all 17 files), not in novelty.

## Common Pitfalls

### Pitfall 1: Missing Color Occurrences in HTMX Partials
**What goes wrong:** Some `indigo-*` or `violet-*` classes get missed during replacement, causing inconsistent branding (some elements plum, others still indigo).
**Why it happens:** 63 occurrences across 17 files, some in deeply nested HTML. Easy to miss one.
**How to avoid:** Use grep to verify zero remaining `indigo` or `violet` occurrences after replacement (except in functional contexts like `bg-indigo-50` which should be replaced too since no functional colors use indigo).
**Warning signs:** Visual inspection shows inconsistent button/link colors.

### Pitfall 2: Breaking Functional Status Colors
**What goes wrong:** Accidentally replacing a color class that was used for priority/status indication (e.g., red for CRITICAL).
**Why it happens:** Overly aggressive find-and-replace.
**How to avoid:** The functional colors are: red (CRITICAL/danger), amber/yellow (HIGH/warning), green (LOW/success), blue (pending/info), emerald (claim/online). None of these use `indigo` or `violet`. All `indigo`/`violet` occurrences in the codebase are brand/accent colors and safe to replace.
**Warning signs:** Priority badges change color or disappear.

### Pitfall 3: Login Page Has Its Own @theme Block
**What goes wrong:** Updating base.html's @theme but forgetting that `login.html` and `dev_login.html` have their own standalone `<style type="text/tailwindcss">` blocks (they don't extend base.html).
**Why it happens:** Login pages are standalone templates (not `{% extends "base.html" %}`).
**How to avoid:** Update the @theme block in all 3 locations: base.html, login.html, dev_login.html.
**Warning signs:** Login page still shows indigo colors.

### Pitfall 4: Hardcoded Hex Values in CSS Rules
**What goes wrong:** The base.html `<style>` block (non-Tailwind CSS) has hardcoded indigo hex values in custom CSS rules.
**Why it happens:** `.card-selected`, `.nav-active`, `.nav-active::before` rules use hex values like `#6366f1` (indigo-500) and `#818cf8` (indigo-400).
**How to avoid:** Audit all `<style>` blocks (not just `<style type="text/tailwindcss">`) and replace hex values.
**Warning signs:** Selected card highlight or nav indicator still shows indigo.

### Pitfall 5: Chat Card imageUrl Must Be Publicly Accessible
**What goes wrong:** Using localhost or relative URL for the Chat card `imageUrl` field.
**Why it happens:** Development instinct to use local URLs.
**How to avoid:** Use the production URL: `https://triage.vidarbhainfotech.com/static/img/vipl-icon.jpg`. Consider making this configurable via SystemConfig `tracker_url`.
**Warning signs:** Chat card shows broken image icon.

### Pitfall 6: Login Page Gradient Background Uses Indigo Hex
**What goes wrong:** The `.gradient-bg` CSS in login.html uses hardcoded hex values (`#1a1635`, `#251d4d`) that are indigo-tinted.
**Why it happens:** These are in the `<style>` block, not Tailwind classes.
**How to avoid:** Update the gradient hex values to plum-tinted equivalents.
**Warning signs:** Login background still looks indigo/blue instead of plum/purple.

### Pitfall 7: 3.jpg Is White-on-White (Invisible on Light Backgrounds)
**What goes wrong:** Using 3.jpg on a light background makes the logo invisible.
**Why it happens:** 3.jpg confirmed as white/light variant (appears blank on white).
**How to avoid:** Only use 3.jpg on dark backgrounds (e.g., the dark sidebar). Use 1.jpg or 2.jpg on light backgrounds.
**Warning signs:** Logo appears as blank space.

## Code Examples

### Current Indigo @theme Block (to be replaced)
```css
/* Source: base.html lines 13-25 */
@theme {
    --font-sans: "Plus Jakarta Sans", ui-sans-serif, system-ui, -apple-system, sans-serif;
    --color-primary-50: #eef2ff;   /* indigo-50 */
    --color-primary-100: #e0e7ff;  /* indigo-100 */
    --color-primary-200: #c7d2fe;  /* indigo-200 */
    --color-primary-300: #a5b4fc;  /* indigo-300 */
    --color-primary-400: #818cf8;  /* indigo-400 */
    --color-primary-500: #6366f1;  /* indigo-500 */
    --color-primary-600: #4f46e5;  /* indigo-600 */
    --color-primary-700: #4338ca;  /* indigo-700 */
    --color-primary-800: #3730a3;  /* indigo-800 */
    --color-primary-900: #312e81;  /* indigo-900 */
}
```

### Recommended Brand Palette (derived from logo plum ~#7B2D5F)
```css
/* Brand plum palette -- derived from VIPL logo "i" stroke color */
@theme {
    --font-sans: "Plus Jakarta Sans", ui-sans-serif, system-ui, -apple-system, sans-serif;
    --color-primary-50: #fdf2f8;
    --color-primary-100: #fce7f1;
    --color-primary-200: #f9c4db;
    --color-primary-300: #f49bbe;
    --color-primary-400: #e06a97;
    --color-primary-500: #c94476;
    --color-primary-600: #a83362;  /* ~logo plum adjusted for accessibility */
    --color-primary-700: #8b2852;
    --color-primary-800: #742345;
    --color-primary-900: #5f1d3a;
}
```
Note: These are DRAFT values. The implementer should eye-drop the exact plum from the logo (~#7B2D5F) and build a perceptually uniform scale around it. The 600 shade should be the primary action color (buttons, active states) with sufficient contrast on white (WCAG AA requires 4.5:1 for normal text).

### Hardcoded Hex Values to Update (base.html CSS rules)
```css
/* BEFORE */
.card-selected { background: linear-gradient(135deg, #eef2ff, #f0f9ff) !important; border-left-color: #6366f1 !important; }
.nav-active { background: rgba(99,102,241,0.12); /* ... */ }
.nav-active::before { /* ... */ background: #818cf8; /* ... */ }

/* AFTER (use brand equivalents) */
.card-selected { background: linear-gradient(135deg, #fdf2f8, #fce7f1) !important; border-left-color: var(--color-primary-600) !important; }
.nav-active { background: rgba(123,45,95,0.12); /* brand plum at 12% opacity */ }
.nav-active::before { /* ... */ background: var(--color-primary-400); /* ... */ }
```

### Login Page Input Focus Shadow
```css
/* BEFORE */
.input-focus:focus { box-shadow: 0 0 0 3px rgba(99,102,241,0.12); }
/* AFTER */
.input-focus:focus { box-shadow: 0 0 0 3px rgba(123,45,95,0.12); }
```

### Complete Color Replacement Map
| Old Pattern | New Pattern | Occurrence Count |
|-------------|-------------|-----------------|
| `indigo-50` | `primary-50` | 8 |
| `indigo-100` | `primary-100` | 3 |
| `indigo-200` | `primary-200` | 5 |
| `indigo-300` | `primary-300` | 8 |
| `indigo-400` | `primary-400` | 4 |
| `indigo-500` | `primary-500` | 7 |
| `indigo-600` | `primary-600` | 10 |
| `indigo-700` | `primary-700` | 7 |
| `violet-50` | `primary-50` (lighter) | 1 |
| `violet-100` | `primary-100` | 1 |
| `violet-200` | `primary-200` | 1 |
| `violet-500` | `primary-500` | 3 |
| `violet-600` | `primary-600` | 4 |
| `violet-700` | `primary-700` | 1 |
| `from-indigo-* to-violet-*` gradients | `from-primary-500 to-primary-700` or similar | 5 |
| `indigo-200/30` (login footer text) | `primary-200/30` | 2 |
| `indigo-500/8` (decorative blurs) | `primary-500/8` | 1 |
| `violet-500/8` (decorative blurs) | `primary-500/8` | 1 |

### Template Title Block Updates
```html
<!-- base.html -->
<title>{% block title %}VIPL Triage{% endblock %}</title>

<!-- email_list.html -->
{% block title %}VIPL Triage | Inbox{% endblock %}

<!-- activity_log.html -->
{% block title %}VIPL Triage | Activity{% endblock %}

<!-- settings.html -->
{% block title %}VIPL Triage | Settings{% endblock %}
```

### Favicon Link Tag
```html
<!-- Add to base.html <head>, login.html <head>, dev_login.html <head> -->
{% load static %}
<link rel="icon" type="image/x-icon" href="{% static 'img/favicon.ico' %}">
```

### Chat Notifier Footer Pattern
```python
# Add to each card's sections list, as the last section
VIPL_FOOTER_SECTION = {
    "widgets": [
        {"textParagraph": {"text": "<i>Sent by VIPL Email Triage</i>"}}
    ]
}
```

## Complete File Audit

### Files That Need Modification (17 template files + 1 Python file)

| File | Changes Needed | indigo/violet Count |
|------|---------------|---------------------|
| `templates/base.html` | @theme palette, hex values in CSS rules, logo in sidebar, favicon link, `{% load static %}`, footer bar | 2 class + 5 hex |
| `templates/registration/login.html` | @theme, logo image, gradient-bg hex, input-focus hex, `{% load static %}`, favicon, decorative blur colors, title update | 8 |
| `templates/registration/dev_login.html` | indigo classes, `{% load static %}`, favicon, title update | 8 |
| `templates/emails/email_list.html` | focus:ring and focus:border indigo classes, title block | 5 |
| `templates/emails/activity_log.html` | indigo stat card colors, title block | 5 |
| `templates/emails/settings.html` | ghostClass indigo, title block | 1 |
| `templates/emails/_email_detail.html` | indigo classes (AI suggestion bar, form controls, assign button, avatar, acknowledge button, prose links) | 10 |
| `templates/emails/_config_editor.html` | form control indigo classes, save button | 6 |
| `templates/emails/_whitelist_tab.html` | form control, add button, badge colors | 3 |
| `templates/emails/_inboxes_tab.html` | form control, add button, icon color | 3 |
| `templates/emails/_sla_config.html` | form controls, save button | 3 |
| `templates/emails/_category_visibility.html` | checkbox, count badge, save button | 3 |
| `templates/emails/_webhooks_tab.html` | form control, test button | 2 |
| `templates/emails/_email_card.html` | assignee avatar gradient | 1 |
| `templates/emails/_assign_dropdown.html` | select focus ring | 1 |
| `templates/emails/_assignment_rules.html` | save button | 1 |
| `templates/emails/_activity_feed.html` | hover link color | 1 |
| `apps/emails/services/chat_notifier.py` | Add imageUrl to all card headers, add footer textParagraph to all cards | 5 methods |

### Files That Do NOT Need Changes
| File | Reason |
|------|--------|
| `templates/emails/_email_list_body.html` | No indigo/violet classes (just includes _email_card.html) |
| `templates/emails/inspect.html` | Standalone dark theme with no indigo classes (Claude's discretion: leave as-is) |
| `templates/emails/eod_email.html` | Email template uses `#1a4587` blue (not indigo -- separate from brand, keep as-is) |
| `templates/eod_email.html` | Legacy v1 email template (same blue, not indigo) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind config.js | Tailwind CSS v4 @theme in CSS | v4.0 (Jan 2025) | Configuration in CSS, not JS -- already adopted in this project |
| `tailwind.config.js` theme.extend | `@theme { --color-* }` | v4.0 | Custom colors defined directly in `<style type="text/tailwindcss">` blocks |

**Deprecated/outdated:**
- Tailwind CSS v3 `tailwind.config.js` approach -- not applicable, project already uses v4 CDN

## Open Questions

1. **Exact plum hex value from logo**
   - What we know: The "i" stroke in the Vi mark logo is a dark plum/purple. Visual inspection suggests approximately #7B2D5F.
   - What's unclear: The exact hex value may vary slightly depending on JPEG compression.
   - Recommendation: Use a color picker on the logo file during implementation. The implementer can eye-drop the exact color and build the palette scale.

2. **Dev inspector branding**
   - What we know: `/emails/inspect/` uses a completely standalone dark theme with custom CSS (no Tailwind, no indigo/violet classes). Zero indigo/violet occurrences.
   - Recommendation: Leave as-is. It's a dev-only tool with its own design language. Adding branding would require significant rework for minimal value.

3. **EOD email template colors**
   - What we know: Both eod_email.html templates use `#1a4587` (a dark blue), not indigo. These are HTML email templates with inline styles.
   - Recommendation: Leave as-is for now. HTML email styling is a separate concern (many email clients strip CSS). The blue is functional, not brand-conflicting.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails/tests/test_chat_notifier.py -x -v` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| R3.1 | Logo files exist in static/img/ | unit | `pytest apps/emails/tests/test_branding.py::test_static_assets_exist -x` | Wave 0 |
| R3.2 | Logo rendered in sidebar and login page | smoke | `pytest apps/emails/tests/test_branding.py::test_sidebar_contains_logo -x` | Wave 0 |
| R3.3 | Brand palette in @theme block | manual-only | Visual inspection of rendered pages | N/A -- CSS theming not testable without browser |
| R3.4 | No remaining indigo/violet in partials | unit | `pytest apps/emails/tests/test_branding.py::test_no_indigo_in_templates -x` | Wave 0 |
| R3.chat | Chat cards include imageUrl + footer | unit | `pytest apps/emails/tests/test_chat_notifier.py -x -v` | Existing (update needed) |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_chat_notifier.py apps/emails/tests/test_branding.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_branding.py` -- covers R3.1, R3.2, R3.4 (new file)
- [ ] Update `apps/emails/tests/test_chat_notifier.py` -- verify imageUrl in card headers and footer textParagraph

## Sources

### Primary (HIGH confidence)
- Codebase inspection: all 17 template files read and audited for indigo/violet occurrences
- Logo files visually inspected: 1.jpg (Vi mark, 1920x1080), 2.jpg (full logo, 1394x619), 3.jpg (white variant, 1920x1080, appears blank on white)
- [Google Chat Cards v2 API reference](https://developers.google.com/workspace/chat/api/reference/rest/v1/cards) -- CardHeader supports imageUrl, imageType, imageAltText
- [Tailwind CSS v4 @theme directive](https://tailwindcss.com/blog/tailwindcss-v4) -- CSS-first configuration

### Secondary (MEDIUM confidence)
- [Google Chat webhook guide](https://developers.google.com/workspace/chat/quickstart/webhooks) -- confirmed cardsV2 webhook format supports header imageUrl
- [Tailwind CSS v4 CDN Play plugin](https://tailwindcss.com/docs/installation/play-cdn) -- MutationObserver processes HTMX-swapped content

### Tertiary (LOW confidence)
- [fixedFooter limitation](https://developers.google.com/workspace/chat/design-components-card-dialog) -- only for dialogs, not webhook messages (verified via official docs, elevated to MEDIUM)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, just visual changes
- Architecture: HIGH -- patterns confirmed by reading actual codebase and templates
- Pitfalls: HIGH -- comprehensive audit of all 17 files with exact occurrence counts
- Chat integration: HIGH -- Google Chat Cards v2 header imageUrl confirmed via official API docs

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable -- visual branding, no rapidly changing APIs)
