# Phase 2: Polish & UX - Research

**Researched:** 2026-03-15
**Domain:** Django templates + HTMX 2.0 + Tailwind CSS v4 (CDN) -- frontend polish patterns
**Confidence:** HIGH

## Summary

Phase 2 adds five UX polish features to the existing Django/HTMX/Tailwind dashboard: a session-based welcome banner, active filter indicators with clear-all, CSS scroll-snap for mobile stat cards, keyboard navigation for email cards, and a loading skeleton for the detail panel. All five features are well-understood web patterns that require no new libraries -- they use sessionStorage (JS), Django template logic, CSS scroll-snap, vanilla JS keydown listeners, and HTMX event hooks respectively.

The existing codebase already has the right structure: `_email_card.html` partial with `tabindex="0"` and `role="article"`, HTMX swap targeting `#detail-panel`, filter state tracked via query params in the view, and stat cards in a flex container. Each feature slots into the existing architecture with minimal changes.

**Primary recommendation:** Implement all five features using only Tailwind utility classes, Django template conditionals, and vanilla JS in `{% block extra_js %}`. No new Python packages, no npm, no build steps.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | First-login welcome banner with role-specific guidance, dismissible, session-only | sessionStorage pattern, Django template `{{ user.role }}` conditional, Tailwind banner styling |
| UX-02 | Active filter indicators with count badge and clear-all link | Django view already tracks `current_status`, `current_priority`, `current_category`, `current_inbox` -- count non-empty filters in template, render badge + reset link |
| UX-03 | Mobile stat cards scroll-snap | CSS `scroll-snap-type: x mandatory` on container, `scroll-snap-align: start` on cards, Tailwind v4 utilities |
| UX-04 | Arrow key navigation between email cards, Escape closes detail | JS `keydown` listener on email list container, `document.querySelectorAll` for cards, `focus()` API |
| UX-05 | Loading skeleton in detail panel during HTMX fetch | `htmx:beforeRequest` event to inject skeleton HTML, or `hx-indicator` with skeleton markup |
</phase_requirements>

## Standard Stack

### Core (already installed -- no changes)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Server-rendered templates, views | Already in use |
| HTMX | 2.0.8 | Declarative AJAX, partial swaps | CDN, already loaded in base.html |
| Tailwind CSS | v4 | Utility-first CSS | CDN play script, already in base.html |
| django-htmx | (installed) | `request.htmx` detection | Already in middleware |

### Supporting (no new additions needed)
No new libraries required. All five features use browser-native APIs:
- `sessionStorage` (welcome banner dismiss state)
- CSS `scroll-snap-*` properties (stat card swiping)
- `KeyboardEvent` handling (arrow/escape navigation)
- HTMX events `htmx:beforeRequest` / `htmx:afterSwap` (loading skeleton)

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sessionStorage for banner | Django session (`request.session`) | Server round-trip to dismiss; sessionStorage is simpler for "once per browser session" |
| Vanilla JS keyboard nav | alpine.js | Adds another framework; 5 users don't need it |
| CSS scroll-snap | JS carousel library | Over-engineering for 4 stat cards |

## Architecture Patterns

### Where Each Feature Lives

```
templates/
  emails/
    email_list.html          # UX-01 (welcome banner), UX-02 (filter indicators), UX-04 (keyboard JS)
    _email_list_body.html    # (no changes needed)
    _email_card.html         # (already has tabindex="0", no changes)
    _email_detail.html       # (no changes needed)
  base.html                  # UX-05 (loading skeleton CSS in <style>)

apps/emails/views.py         # UX-01 (pass user.role to context -- already there)
                             # UX-02 (pass active_filter_count to context)
```

### Pattern 1: Session-Based Welcome Banner (UX-01)
**What:** A dismissible banner shown on first page load per browser session. Uses `sessionStorage` to track dismissal -- no server round-trip needed.
**When to use:** One-time-per-session UI elements.
**Example:**
```html
<!-- In email_list.html, before the stats bar -->
<div id="welcome-banner" class="hidden bg-gradient-to-r from-primary-50 to-primary-100 border-b border-primary-200/60 px-4 md:px-5 py-3 shrink-0">
    <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2.5 min-w-0">
            <span class="text-sm font-semibold text-primary-800">
                <!-- Role-specific text rendered server-side -->
                {% if is_admin %}
                    Welcome! As an admin, you can assign emails, manage team visibility, and configure SLA rules.
                {% else %}
                    Welcome! Check "My Emails" for your assignments. Claim unassigned emails from categories visible to you.
                {% endif %}
            </span>
        </div>
        <button onclick="dismissWelcome()" class="shrink-0 text-primary-400 hover:text-primary-600">
            <svg class="w-4 h-4" ...><!-- X icon --></svg>
        </button>
    </div>
</div>
<script>
(function() {
    if (!sessionStorage.getItem('welcome_dismissed')) {
        document.getElementById('welcome-banner').classList.remove('hidden');
    }
})();
function dismissWelcome() {
    sessionStorage.setItem('welcome_dismissed', '1');
    document.getElementById('welcome-banner').classList.add('hidden');
}
</script>
```

### Pattern 2: Active Filter Indicators (UX-02)
**What:** Count active filters and show a badge + "Clear all" link.
**When to use:** Any filtered list view.
**Implementation approach:** Compute `active_filter_count` in the Django view by counting non-empty filter params. Pass to template. Render conditionally.
```python
# In email_list view, add to context:
active_filters = sum(1 for f in [status, priority, category, inbox, search_query] if f)
context["active_filter_count"] = active_filters
```
```html
<!-- In email_list.html filter bar area -->
{% if active_filter_count %}
<div class="flex items-center gap-2 px-4 md:px-5 py-1.5 bg-amber-50/60 border-b border-amber-200/40 shrink-0">
    <span class="text-[10px] font-bold text-amber-700">
        {{ active_filter_count }} filter{{ active_filter_count|pluralize }} active
    </span>
    <a href="{% url 'emails:email_list' %}?view={{ current_view }}"
       class="text-[10px] font-bold text-amber-600 hover:text-amber-800 underline">
        Clear all
    </a>
</div>
{% endif %}
```

### Pattern 3: CSS Scroll-Snap for Mobile Stat Cards (UX-03)
**What:** Horizontal scroll with snap points on mobile so each card aligns cleanly.
**When to use:** Horizontal card rows on mobile.
```html
<!-- Modify the stat cards container in email_list.html -->
<div class="flex items-center gap-2.5 overflow-x-auto snap-x snap-mandatory scrollbar-hide">
    <div class="stat-card snap-start ... min-w-[120px] shrink-0">
        <!-- existing card content -->
    </div>
    <!-- repeat for each stat card -->
</div>
```
Note: `snap-x`, `snap-mandatory`, and `snap-start` are built-in Tailwind v4 utilities. The existing `scrollbar-hide` class is already defined in base.html `<style>`.

### Pattern 4: Arrow Key Navigation (UX-04)
**What:** Up/Down arrow keys move focus between email cards. Escape closes the detail panel.
**When to use:** List views with focusable items.
```javascript
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeDetail();
        return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        var cards = Array.from(document.querySelectorAll('#email-list [role="article"]'));
        if (!cards.length) return;
        var currentIdx = cards.indexOf(document.activeElement);
        var nextIdx;
        if (e.key === 'ArrowDown') {
            nextIdx = currentIdx < cards.length - 1 ? currentIdx + 1 : 0;
        } else {
            nextIdx = currentIdx > 0 ? currentIdx - 1 : cards.length - 1;
        }
        cards[nextIdx].focus();
        cards[nextIdx].scrollIntoView({ block: 'nearest' });
        e.preventDefault();
    }
});
```

### Pattern 5: Loading Skeleton in Detail Panel (UX-05)
**What:** Show pulsing placeholder while HTMX fetches email detail.
**Implementation:** Use `htmx:beforeRequest` to inject skeleton HTML into `#detail-panel` before the HTMX request fires, but only when the target is `#detail-panel`.
```javascript
document.addEventListener('htmx:beforeRequest', function(e) {
    if (e.detail.target && e.detail.target.id === 'detail-panel') {
        e.detail.target.innerHTML = '<div class="p-5 space-y-4 animate-pulse">...</div>';
    }
});
```
The skeleton should mimic the detail panel layout: header bar with badge placeholders, subject line, sender row, body area.

### Anti-Patterns to Avoid
- **Server-side session for banner dismiss:** Adds unnecessary DB/cache writes for a purely cosmetic feature. Use `sessionStorage`.
- **JS-based scroll snapping:** CSS `scroll-snap` has full browser support (since 2019). Never polyfill this.
- **Alpine.js or similar for keyboard nav:** Adding a framework for 20 lines of vanilla JS is over-engineering.
- **`hx-indicator` for skeleton:** The built-in `hx-indicator` class toggles visibility of an existing element. For a skeleton that replaces content, use the `htmx:beforeRequest` event approach instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scroll snapping | JS touch/scroll handlers | CSS `scroll-snap-type` + `scroll-snap-align` | Native, performant, zero JS |
| Session state for banner | Cookie parsing, server sessions | `sessionStorage.getItem/setItem` | Built-in, no server cost, auto-clears on tab close |
| Filter count | Template-only counting with `{% with %}` hacks | Python view adds `active_filter_count` to context | Cleaner, testable |
| Loading animation | Custom CSS keyframes | Tailwind `animate-pulse` utility | Already available via CDN |

## Common Pitfalls

### Pitfall 1: Scroll-Snap Not Working on iOS Safari
**What goes wrong:** Container needs `-webkit-overflow-scrolling: touch` on older iOS, and children need explicit widths.
**Why it happens:** iOS Safari had partial scroll-snap support before iOS 15.
**How to avoid:** Ensure stat cards have `min-w-[120px] shrink-0` (already present) and the container has `overflow-x-auto`. Tailwind v4's `snap-x` maps to `scroll-snap-type: x mandatory` which works on all modern browsers including Safari 15+.
**Warning signs:** Cards don't snap on iPhone but work on desktop.

### Pitfall 2: Keyboard Navigation Conflicts with Input Fields
**What goes wrong:** Arrow key handler fires when user is typing in the search input.
**Why it happens:** Event listener on `document` catches all keydown events.
**How to avoid:** Check `document.activeElement.tagName` -- skip if it's `INPUT`, `SELECT`, or `TEXTAREA`.
```javascript
if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
```

### Pitfall 3: Loading Skeleton Flash on Fast Responses
**What goes wrong:** Skeleton appears for 50ms then disappears, causing a visual flash.
**Why it happens:** HTMX request completes before the user perceives the skeleton.
**How to avoid:** Only show skeleton after a short delay (e.g., 100ms). Or accept the flash since it's brief and non-jarring for the detail panel use case. Given this is a side panel loading, the flash is acceptable.

### Pitfall 4: Welcome Banner Shows After HTMX Navigation
**What goes wrong:** Banner reappears when HTMX replaces page content.
**Why it happens:** HTMX partial swap re-renders the banner HTML but the JS init runs only on page load.
**How to avoid:** The banner is in `email_list.html` (full page template), not in `_email_list_body.html` (HTMX partial). HTMX swaps only target `#email-list`, so the banner div is never re-rendered by HTMX. No issue here -- just don't put the banner inside the HTMX-swapped container.

### Pitfall 5: Filter Clear-All Link Loses View Tab
**What goes wrong:** "Clear all" resets to default view instead of keeping the current tab (All/Unassigned/Mine).
**Why it happens:** The clear link href doesn't include `?view=` param.
**How to avoid:** Always include `?view={{ current_view }}` in the clear-all link href.

## Code Examples

### Tailwind v4 Scroll-Snap Classes
```html
<!-- Container -->
<div class="flex overflow-x-auto snap-x snap-mandatory scrollbar-hide">
    <!-- Each card -->
    <div class="snap-start shrink-0 min-w-[120px]">...</div>
</div>
```
Tailwind v4 CDN play script supports `snap-x`, `snap-mandatory`, `snap-start` out of the box. These map directly to:
- `scroll-snap-type: x mandatory`
- `scroll-snap-align: start`

### sessionStorage API
```javascript
// Check
sessionStorage.getItem('key')  // returns null if not set
// Set
sessionStorage.setItem('key', 'value')
// Cleared automatically when browser tab/window closes
```

### HTMX Event Hooks
```javascript
// Fires before any HTMX request
document.addEventListener('htmx:beforeRequest', function(evt) {
    // evt.detail.target is the DOM element being swapped
    // evt.detail.elt is the element that triggered the request
});

// Fires after content is swapped in
document.addEventListener('htmx:afterSwap', function(evt) {
    // Good place to re-initialize JS on new content
});
```

### Skeleton HTML Pattern
```html
<div class="p-5 space-y-4 animate-pulse">
    <!-- Badge placeholders -->
    <div class="flex gap-2">
        <div class="h-5 w-16 bg-slate-200 rounded-md"></div>
        <div class="h-5 w-14 bg-slate-200 rounded-md"></div>
    </div>
    <!-- Subject line -->
    <div class="h-5 w-3/4 bg-slate-200 rounded"></div>
    <!-- Summary -->
    <div class="h-4 w-full bg-slate-100 rounded"></div>
    <!-- Sender row -->
    <div class="flex items-center gap-3 pt-2">
        <div class="w-7 h-7 bg-slate-200 rounded-full"></div>
        <div class="space-y-1.5">
            <div class="h-3.5 w-28 bg-slate-200 rounded"></div>
            <div class="h-3 w-40 bg-slate-100 rounded"></div>
        </div>
    </div>
    <!-- Body area -->
    <div class="space-y-2 pt-4 border-t border-slate-100">
        <div class="h-3 w-full bg-slate-100 rounded"></div>
        <div class="h-3 w-5/6 bg-slate-100 rounded"></div>
        <div class="h-3 w-4/6 bg-slate-100 rounded"></div>
    </div>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JS scroll libraries (Swiper, etc.) | CSS `scroll-snap` | Widespread since 2019-2020 | Zero JS, native performance |
| Cookie-based session tracking | `sessionStorage` API | Available since IE8 | Auto-clears, no server cost |
| Custom loading spinners | Skeleton screens (`animate-pulse`) | Industry shift ~2020 | Better perceived performance |
| `tabindex` + manual focus management | `tabindex="0"` + `focus()` + `scrollIntoView` | Stable pattern | Already partially implemented in codebase |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + Django test client |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails/tests/test_views.py -x` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-01 | Welcome banner renders for authenticated users, role-specific content | unit (template rendering) | `pytest apps/emails/tests/test_views.py::TestWelcomeBanner -x` | Wave 0 |
| UX-02 | Active filter count badge appears when filters applied | unit (view context + response content) | `pytest apps/emails/tests/test_views.py::TestFilterIndicators -x` | Wave 0 |
| UX-03 | Stat cards container has scroll-snap CSS classes | unit (response content check) | `pytest apps/emails/tests/test_views.py::TestScrollSnap -x` | Wave 0 |
| UX-04 | Keyboard navigation JS present in page | unit (response content check) | `pytest apps/emails/tests/test_views.py::TestKeyboardNav -x` | Wave 0 |
| UX-05 | Loading skeleton script present in page | unit (response content check) | `pytest apps/emails/tests/test_views.py::TestLoadingSkeleton -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_views.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Test classes for UX-01 through UX-05 in `apps/emails/tests/test_views.py` -- covers all phase requirements
- No new framework install needed -- pytest already configured

## Open Questions

1. **Welcome banner text content**
   - What we know: Admin vs member roles exist, guidance text should differ
   - What's unclear: Exact wording for each role
   - Recommendation: Use generic guidance (admin: assign/manage, member: claim/view) -- can be refined later

## Sources

### Primary (HIGH confidence)
- Existing codebase: `templates/base.html`, `templates/emails/email_list.html`, `apps/emails/views.py` -- direct inspection of current architecture
- CSS Scroll Snap: W3C spec, universally supported since 2019
- sessionStorage: Web Storage API, supported in all browsers
- HTMX events: HTMX 2.0 documentation (htmx.org)

### Secondary (MEDIUM confidence)
- Tailwind v4 utility names (`snap-x`, `snap-mandatory`, `snap-start`): verified against Tailwind CSS v4 docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, all browser-native APIs
- Architecture: HIGH - all features slot into existing template/view structure
- Pitfalls: HIGH - well-understood web patterns with known edge cases

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable patterns, no version dependencies)
