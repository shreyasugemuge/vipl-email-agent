# Feature Landscape

**Domain:** Email triage dashboard UI/UX polish & bug fixes
**Researched:** 2026-03-15
**Scope:** v2.2.1 milestone -- fixes and polish on existing Django + HTMX + Tailwind v4 dashboard. All v2.2 features (OAuth, branding, whitelist, settings) already shipped.

**Existing baseline (already shipped in v2.2):**
- Google OAuth SSO with domain lock (@vidarbhainfotech.com)
- VIPL brand identity (plum palette #a83362, logo, favicon)
- SpamWhitelist model with pipeline integration + management tab
- Type-aware settings inputs with pre-filled values
- Inline save feedback on all settings tabs
- Chat card branding with deep links
- 7 settings tabs, team management, activity log

---

## Table Stakes

Features users expect. Missing = product feels broken or unfinished.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| AI summary XML markup stripping | Raw XML-like tags (e.g. `<suggestion>`, `<greeting>`) render visibly in email cards and detail panel. Users see markup noise instead of clean text. Most visible bug. | Low | `_email_card.html`, `_email_detail.html`, `pipeline.py` | AI uses tool-use structured output via `triage_email` tool, but `ai_summary` or draft reply fields may contain XML remnants. Fix server-side in pipeline before DB save with a `re.sub(r'<[^>]+>', '', text)` strip. Template `striptags` filter is a fallback but masks root cause. Pipeline fix is correct -- clean data at rest. |
| Mobile detail panel visibility | Detail panel is `fixed inset-0 z-50 translate-x-full` on mobile. Slide-in JS handler exists in `htmx:afterSwap` but the panel is effectively invisible/inaccessible on first load. Dashboard is unusable on phones. | Low | `email_list.html` JS, CSS for panel and overlay | Current implementation is close. Verify: (1) overlay z-index layering, (2) `closeDetail()` back button works, (3) body scroll locked when panel open. May need visual hint on cards ("tap to view") for discoverability. |
| Mobile-friendly filter bar | Filters use `hidden md:flex` with a mobile toggle. But `toggleFilters()` adds `flex-wrap` inside a `flex items-center gap-5` parent -- 5 selects + search input overflow and look broken. | Medium | `email_list.html` filter section | Restructure for mobile: stack filters vertically with full-width selects. Use a proper collapsible section below tabs (not inline). Each select needs 44px+ touch target height. |
| Activity page filter chip overflow | Filter chips on activity page have `overflow-x-auto` but no visual scroll indicator. Users on mobile don't know more chips exist off-screen. | Low | `activity_log.html` line 63 | Add gradient fade masks on edges, or convert to a `<select>` dropdown on mobile (below md breakpoint). Simplest: add `scrollbar-hide` + left/right gradient pseudo-elements. |
| Email count accuracy across views | `{{ total_count }}` in header should reflect the filtered queryset for the active view/tab, not a different count. Users switching between All/Unassigned/Mine tabs need accurate numbers. | Low | `views.py` email_list view | Verify `total_count` is derived from the fully-filtered queryset (after view + status + priority + category + search filters). Consider adding counts to tab labels: "Unassigned (3)". |
| Page title consistency | Every page needs descriptive `<title>`. Pattern: "VIPL Triage \| {Page Name}". Already correct on email_list and activity_log. Need to audit settings, team, login, and error pages. | Low | Each template's `{% block title %}` | 5-minute audit. Check: settings.html, team.html, login.html, signup.html, socialaccount templates. |
| Toast positioning on mobile | Toasts at `top-4 right-4` can overlap the hamburger menu button and header bar on mobile. Close button (16x16 SVG) is too small for touch. Multiple toasts stack and push off-screen. | Low | `base.html` toast container | Move to `top-14 right-4` (below 48px header). Increase close button touch target to 44x44px. Cap visible toasts at 3, queue extras. |

---

## Differentiators

Features that elevate the daily experience. Not expected, but valued by a 4-5 person team.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| First-login welcome experience | New team members (auto-provisioned via OAuth) land on dashboard with zero context. A one-time dismissible banner explaining their role reduces "how do I use this?" questions to Shreyas. | Low | Session flag or User model field | Use `request.session['welcomed'] = True` to avoid schema change. Role-specific content: admin sees "Assign from Unassigned tab", member sees "Your emails appear in My Emails". Dismissible banner, not blocking modal. |
| Active filter indicators with clear-all | When filters are applied, no visual badge shows "2 filters active" and no easy way to clear all. Users forget filters are on and wonder why emails are missing. | Medium | `email_list.html` filter bar | Show filter count on mobile toggle: "Filters (2)". Add "Clear" link when any filter differs from default. Pairs naturally with mobile filter bar fix. |
| Mobile stat cards scroll snap | 4 stat cards have `overflow-x-auto` but scroll loosely on mobile. Adding CSS scroll-snap makes them swipeable and feel native. | Low | `email_list.html` stats bar | Add `snap-x snap-mandatory scrollbar-hide` to container, `snap-start shrink-0` to each card. One-line CSS additions on existing markup. |
| Keyboard navigation for email list | Cards already have `tabindex="0"` and Enter/Space handlers. Missing: ArrowDown/ArrowUp between cards, Escape to close detail panel. | Low | `email_list.html` extra_js block | Add `keydown` listener on list container for arrow key focus cycling. Escape closes detail. Minimal JS, significant accessibility improvement. Already partially implemented with existing tabindex. |
| HTMX loading skeleton for detail panel | Clicking a card shows previous email at reduced opacity (`htmx-swapping` class) until new content loads. A skeleton placeholder feels more polished. | Low | `_email_detail.html`, `base.html` CSS | `htmx:beforeRequest` handler replaces detail-panel innerHTML with CSS-only skeleton (animated gray bars). Purely cosmetic improvement. |

---

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full PWA / mobile app | 4-5 users, Google Chat notifications already push alerts to phones. Service worker adds complexity for near-zero value. | Keep responsive web. Chat handles urgency push. |
| Client-side search / filtering JS | Server-side HTMX search with 300ms debounce already works well. Client-side filtering duplicates logic and creates state sync issues with URL-based filter state. | Keep current `hx-trigger="keyup changed delay:300ms"` pattern. |
| Drag-and-drop email assignment | Overkill for 3-person team. Select dropdown + Assign is faster for actual workflow. | Keep current dropdown assignment UI. |
| Dark mode | Doubles CSS surface area. Team uses dashboard during business hours (8AM-8PM IST) only. | Skip entirely. |
| Real-time websocket updates | 4-5 concurrent users, 5-min poll interval. Django Channels dependency + deployment complexity for near-zero benefit at this scale. | Keep HTMX manual refresh or add simple auto-refresh interval. |
| Inline email reply composer | Explicitly out of scope per PROJECT.md. Team replies from Gmail directly. | Keep "Open in Gmail" button in detail panel. |
| Complex onboarding wizard | Multi-step onboarding for a 4-5 person tool is over-engineering. | Single dismissible welcome banner. |
| Pull-to-refresh gesture | Adds JS complexity for marginal value given 5-min poll interval and desktop-primary usage. | Add a "Refresh" button in header if needed. |

---

## Feature Dependencies

```
XML markup fix           --> (none, standalone pipeline fix)
Mobile detail panel      --> (none, CSS/JS fix on existing code)
Mobile filter bar        --> (none, CSS restructure of existing markup)
Activity filter overflow --> (none, CSS fix)
Email count accuracy     --> (none, view logic verification)
Page title consistency   --> (none, template audit)
Toast improvements       --> (none, CSS/JS positioning fix)
Welcome experience       --> Toast system (reuses notification pattern)
Active filter indicators --> Mobile filter bar (design together, same area)
Stat cards scroll snap   --> (none, CSS-only addition)
Keyboard navigation      --> (none, standalone JS addition)
Loading skeleton         --> (none, standalone CSS/JS)
```

**No new models or migrations required** for any feature in this milestone. All work is template/CSS/JS/view-logic level.

---

## MVP Recommendation

**Priority order for v2.2.1:**

### Must fix (bugs visible to users):
1. **AI summary XML markup stripping** -- Most visible bug. Raw tags in every email card. Pipeline-side regex strip, 30 minutes.
2. **Mobile detail panel** -- Dashboard is non-functional on phones. CSS/JS fix, 1-2 hours.
3. **Mobile filter bar layout** -- Filters overflow on mobile. CSS restructure, 1-2 hours.
4. **Email count accuracy** -- Misleading numbers erode trust. View logic check, 30 minutes.

### Should fix (polish users will notice):
5. **Activity page filter overflow** -- Quick CSS fix, 30 minutes.
6. **Toast positioning and sizing** -- Prevents mobile overlap, 30 minutes.
7. **Page title consistency** -- 15-minute template audit.

### Nice to have (differentiators):
8. **Welcome experience** -- Session-based banner for new team members, 1 hour.
9. **Active filter indicators** -- Clear-all link + count badge, 1-2 hours.
10. **Stat cards scroll snap** -- One-line CSS, 10 minutes.

**Defer to future:** Keyboard navigation, loading skeletons. Polish that can wait until core mobile experience is solid.

**Total estimated effort:** 6-10 hours for must-fix + should-fix items. 2-3 hours for differentiators.

---

## Implementation Notes

### XML Markup Stripping (Pipeline Fix)
The AI uses tool-use structured output (`triage_email` tool), so fields should be clean. The bug likely manifests in `ai_summary` or draft reply when Claude occasionally wraps content in XML-like tags. Fix in `pipeline.py` before saving:
```python
import re
def _strip_xml_tags(text: str) -> str:
    """Remove XML-like tags from AI response text."""
    return re.sub(r'<[^>]+>', '', text).strip()

# Apply before save:
email_obj.ai_summary = _strip_xml_tags(triage.summary)
```
Also apply `striptags` filter in templates as defense-in-depth.

### Mobile Detail Panel
Current code is nearly correct. The panel uses `fixed inset-0 z-50 translate-x-full` with `htmx:afterSwap` removing `translate-x-full`. Verify:
1. Overlay z-index (40) is below panel z-index (50) -- correct in current code
2. `closeDetail()` removes both overlay and panel -- correct
3. Add `overflow-hidden` to `<body>` when panel is open to prevent background scroll
4. Back button at top of `_email_detail.html` is already implemented

### Mobile Filter Bar
Replace inline layout on mobile with stacked vertical:
- Below md: Full-width search, then 2x2 grid of select dropdowns
- Each select: `w-full` on mobile, current width on desktop
- Filter toggle button shows active count: "Filters (2)"
- Keep `toggleFilters()` but render as a proper section, not inline

### Welcome Banner
```python
# In email_list view:
show_welcome = not request.session.get('welcomed', False)
if show_welcome:
    request.session['welcomed'] = True
# Pass show_welcome to template context
```
Banner content varies by role. Dismissible with a close button. Shows once per session (or use a more persistent flag if desired).

---

## Sources

- Direct codebase analysis: `email_list.html`, `_email_card.html`, `_email_detail.html`, `base.html`, `activity_log.html`, `views.py`, `ai_processor.py`, `pipeline.py` -- HIGH confidence
- WCAG 2.1 touch target guidelines: 44x44px minimum for interactive elements -- HIGH confidence
- Tailwind CSS v4 scroll-snap utilities -- HIGH confidence
- HTMX 2.0 lifecycle events (`htmx:beforeRequest`, `htmx:afterSwap`) -- HIGH confidence
- Django template `striptags` filter documentation -- HIGH confidence
