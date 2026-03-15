# Technology Stack

**Domain:** v2.2.1 UI/UX Polish & Bug Fixes — additions to existing Django 4.2 LTS app
**Researched:** 2026-03-15
**Confidence:** HIGH

---

> This document covers ONLY new patterns and integration approaches needed for v2.2.1 UI/UX features.
> The existing validated stack (Django 4.2, HTMX 2.0.8, Tailwind CSS v4 CDN, django-allauth 65.x,
> django-htmx, nh3, APScheduler) is unchanged and not re-documented here.
> See the v2.2 STACK.md in git history for prior stack decisions.

---

## Verdict: Zero New Dependencies

Every v2.2.1 feature is achievable with the existing stack. No new pip packages, no new CDN scripts, no build tools. The work is CSS, HTML template changes, and minor vanilla JS.

---

## Feature-by-Feature Stack Analysis

### 1. Mobile Responsive Detail Panel

**Problem:** Detail panel uses `fixed inset-0 z-50 translate-x-full` on mobile, slides in via JS — but is currently invisible/broken on small screens.

**Solution: Tailwind v4 responsive utilities (already available)**

The existing `md:` breakpoint (768px) is already used throughout. The detail panel already has the mobile slide-in pattern wired up (`translate-x-full` toggled by `htmx:afterSwap` listener + `closeDetail()` JS). The issue is CSS/template bugs, not missing technology.

| What's Needed | Already Have It? | Notes |
|---------------|-----------------|-------|
| `md:` responsive breakpoints | YES | Tailwind v4 CDN includes sm/md/lg/xl/2xl |
| CSS transitions for slide-in | YES | `transition-transform duration-300 ease-out` already in template |
| Overlay backdrop | YES | `#detail-overlay` div already exists |
| Touch-friendly tap targets | YES | Tailwind spacing utilities (p-3, p-4) |
| `overflow-auto` for scroll | YES | Already on detail panel |

**Key pattern — fullscreen mobile detail with back button:**
```html
<!-- Already in _email_detail.html line 5-8 -->
<button onclick="closeDetail()" class="md:hidden flex items-center ...">
    Back
</button>
```

**What to fix (not add):**
- The `#detail-panel` needs `top-0` on mobile to clear the fixed header
- Filter bar needs `flex-wrap` on mobile (already partially done with `toggleFilters()`)
- Stat cards need horizontal scroll on small screens (already have `overflow-x-auto`)
- Action bar buttons in detail need stacking (`flex-wrap`) below ~400px

**No new library or extension needed.**

### 2. Toast Notifications (HTMX-Triggered)

**Problem:** Current toasts only show on full page loads (Django messages framework renders in `base.html`). HTMX partial swaps don't trigger toast display.

**Solution: HX-Trigger response header pattern (built into HTMX 2.0)**

HTMX natively supports `HX-Trigger` response headers that fire client-side events. Django views return the header, JS listens and creates toasts. This is the standard HTMX toast pattern — no extension or library needed.

| What's Needed | Already Have It? | Notes |
|---------------|-----------------|-------|
| `HX-Trigger` header support | YES | Built into HTMX 2.0 core |
| Toast container HTML | YES | `#toast-container` in base.html |
| Toast CSS animations | YES | `@keyframes toast-in/toast-out` in base.html |
| Django messages middleware | YES | `django.contrib.messages` already installed |

**Pattern — server-side (Django view):**
```python
from django.http import HttpResponse
import json

def assign_email(request, pk):
    # ... assignment logic ...
    response = render(request, 'emails/_email_card.html', ctx)
    response['HX-Trigger'] = json.dumps({
        'showToast': {'message': f'Assigned to {assignee.get_full_name()}', 'type': 'success'}
    })
    return response
```

**Pattern — client-side (vanilla JS in base.html):**
```javascript
document.addEventListener('showToast', function(e) {
    var data = e.detail;
    // Create toast element, append to #toast-container, auto-dismiss
});
```

**Why not django-htmx-messages-framework or django-toast-messages:**
These are thin wrappers around the same `HX-Trigger` pattern. Adding a pip dependency for 20 lines of JS is unnecessary. The project already has the toast HTML and CSS — just needs the event wiring.

**No new library needed.**

### 3. Welcome Toast / First-Login Experience

**Problem:** New users land on the dashboard with no orientation. Need a welcome message on first login.

**Solution: Django session flag + existing toast system**

| What's Needed | Already Have It? | Notes |
|---------------|-----------------|-------|
| Session storage | YES | Django sessions already configured |
| User model `date_joined` or `last_login` | YES | Django's built-in User fields |
| Toast rendering | YES | Toast container + animations in base.html |
| Conditional template logic | YES | Django template tags |

**Pattern:**
```python
# In login view or middleware — set session flag on first login
if user.last_login is None or (now - user.date_joined).seconds < 60:
    request.session['show_welcome'] = True
```

Then in the template, check `request.session.show_welcome` and render a welcome toast with slightly longer auto-dismiss (8s instead of 4s). Clear the flag after rendering.

**No new library needed.**

### 4. Onboarding Overlay / Tutorial

**Problem:** First-time users don't know what the dashboard sections do.

**Solution: CSS-only tooltip hints with `popover` API or pure CSS**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| CSS `:target` + overlay | Zero JS, accessible | URL hash changes | Viable but clunky |
| HTML `popover` attribute | Native browser API, zero JS, accessible | Safari 17+, Chrome 114+ | Best option |
| Intro.js (~10kB) | Polished step-by-step tours | New JS dependency, CDN or bundle | Overkill for 4 users |
| CSS tooltips on hover | Simplest | Doesn't work on touch/mobile | Not suitable |

**Recommendation: Skip a formal onboarding library.** For a 4-person internal tool, a welcome toast with 2-3 key tips is sufficient. If a walkthrough is needed later, the HTML `popover` attribute (supported in all modern browsers as of 2024) provides tooltip-like behavior without any JS library.

**Simpler alternative — contextual help text:**
Add `title` attributes or small `text-slate-400 text-[10px]` helper text beneath key UI elements. This is discoverable, accessible, and zero-complexity.

**No new library needed.**

### 5. CSS Animation Polish

**Problem:** Want smoother transitions for card selection, panel loading, filter changes.

**Solution: Existing CSS + Tailwind v4 transition utilities**

| Animation | Implementation | Notes |
|-----------|---------------|-------|
| Card selection highlight | `transition-colors duration-150` | Already have `.card-selected` class |
| Detail panel slide-in | `transition-transform duration-300` | Already wired |
| HTMX swap fade | `.htmx-settling` / `.htmx-swapping` | Already in base.html CSS |
| Progress bar | `#htmx-progress` with transitions | Already in base.html |
| Button loading state | `htmx-request` class + `hx-disabled-elt` | Already in use |
| Skeleton loading | Tailwind `animate-pulse` on placeholder divs | Built into Tailwind v4 |

**One useful addition — skeleton loading for detail panel:**
```html
<!-- Show while HTMX loads detail content -->
<div class="htmx-indicator p-5 space-y-3">
    <div class="h-4 bg-slate-200 rounded animate-pulse w-3/4"></div>
    <div class="h-3 bg-slate-100 rounded animate-pulse w-1/2"></div>
    <div class="h-3 bg-slate-100 rounded animate-pulse w-full"></div>
</div>
```

HTMX 2.0 supports `hx-indicator` to show/hide loading states natively. Combined with Tailwind's `animate-pulse`, this gives polished skeleton loading with zero new dependencies.

**Why not HTMX class-tools extension:**
The `class-tools` extension (htmx-ext-class-tools@2.0.1) adds timed class toggling. While useful for complex multi-step animations, every animation needed here is achievable with CSS transitions triggered by HTMX's built-in class lifecycle (`htmx-request`, `htmx-settling`, `htmx-swapping`, `htmx-added`). Adding the extension would be unnecessary complexity.

**No new library or extension needed.**

### 6. AI Suggestion XML Markup Bug

**Problem:** AI suggestions display raw XML tags in email cards.

**Solution: Fix in Python (strip XML before template rendering)**

This is a backend string processing fix, not a stack concern. Use Python's `re.sub()` or `xml.etree` to strip markup before saving `ai_summary` to the database, or sanitize in the template tag.

**No new library needed.**

---

## Recommended Stack — New Additions

**None.** Zero new pip packages. Zero new CDN scripts. Zero new extensions.

---

## Installation

```bash
# No new packages to install for v2.2.1
# All work is CSS, HTML templates, and minor vanilla JS changes
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Intro.js / Shepherd.js | Overkill JS onboarding library for 4-user internal tool | Welcome toast + contextual help text |
| htmx-ext-class-tools | Adds timed class toggling — not needed when CSS transitions suffice | HTMX built-in class lifecycle + CSS transitions |
| htmx-ext-sse | Real-time push for toast updates is overengineered for this volume | `HX-Trigger` response headers |
| Alpine.js | Tempting for small interactivity but adds a second JS paradigm alongside HTMX | Vanilla JS (existing pattern in base.html) |
| django-htmx-messages-framework | pip wrapper for 20 lines of JS | Manual `HX-Trigger` + event listener |
| Tailwind CSS CLI / PostCSS | Build step for production CSS — not needed while CDN play script works fine for 4 users | `@tailwindcss/browser@4` CDN (already in use) |
| Any CSS animation library (Animate.css, Motion One) | Tailwind's built-in transitions + `@keyframes` cover all needs | Tailwind utilities + custom `@keyframes` |

---

## Integration Points

### HTMX Toast Flow (the main new pattern)

```
User clicks "Assign" button
  -> HTMX POST to /emails/<pk>/assign/
  -> Django view processes assignment
  -> Django view returns:
       - HTML partial for card update (body)
       - HX-Trigger: {"showToast": {"message": "...", "type": "success"}} (header)
  -> HTMX swaps card HTML into #card-<pk>
  -> HTMX fires "showToast" JS event
  -> Vanilla JS listener creates toast DOM element in #toast-container
  -> CSS animation slides toast in, auto-dismisses after 4s
```

This is the ONLY new integration pattern. Everything else is CSS/template fixes.

### Mobile Detail Panel Flow (fix existing, don't rebuild)

```
User taps email card on mobile (<768px)
  -> HTMX GET loads detail into #detail-panel
  -> htmx:afterSwap event fires
  -> JS removes translate-x-full from #detail-panel (already coded)
  -> JS shows #detail-overlay backdrop (already coded)
  -> User taps "Back" button
  -> JS adds translate-x-full back (already coded via closeDetail())
```

The flow is already implemented. Fixes are CSS positioning bugs, not architectural changes.

---

## Version Compatibility (unchanged)

| Package | Version | Status |
|---------|---------|--------|
| HTMX | 2.0.8 (CDN) | Current, supports HX-Trigger headers |
| Tailwind CSS | v4 browser CDN | Current, supports all responsive utilities needed |
| django-htmx | 1.17+ | Current, provides `request.htmx` detection |
| Django | 4.2 LTS | Unchanged |

---

## Sources

- [HTMX Animations Examples](https://htmx.org/examples/animations/) — built-in class lifecycle for CSS transitions (htmx-settling, htmx-swapping, htmx-added) — HIGH confidence
- [HTMX class-tools Extension](https://github.com/bigskysoftware/htmx-extensions/blob/main/src/class-tools/README.md) — evaluated and rejected, not needed for this scope — HIGH confidence
- [Tailwind CSS v4 Play CDN](https://tailwindcss.com/docs/installation/play-cdn) — browser script at `@tailwindcss/browser@4`, dev/prototype use — HIGH confidence
- [Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design) — sm/md/lg/xl/2xl breakpoints, mobile-first — HIGH confidence
- [Django HTMX Toast Pattern](https://blog.benoitblanchon.fr/django-htmx-toasts/) — HX-Trigger header pattern for toast notifications — MEDIUM confidence
- [Django HTMX Messages Framework](https://joshkaramuth.com/blog/django-messages-toast-htmx/) — pattern reference (library itself not recommended) — MEDIUM confidence

---

*Stack research for: VIPL Email Agent v2.2.1 UI/UX Polish & Bug Fixes*
*Researched: 2026-03-15*
