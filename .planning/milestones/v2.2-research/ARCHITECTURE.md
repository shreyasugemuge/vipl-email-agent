# Architecture Patterns

**Domain:** UI/UX polish and bug fixes for Django + HTMX + Tailwind email triage dashboard
**Researched:** 2026-03-15
**Confidence:** HIGH (firsthand codebase analysis of all templates, views, and models)

---

## Current Architecture Summary

Server-rendered Django 4.2 app. HTMX 2.0 for partial page updates. Tailwind CSS v4 browser CDN for styling. Zero JavaScript build step -- all JS is inline `<script>` blocks in template `{% block extra_js %}`. HTMX handles all async interactions via `hx-get`/`hx-post` with `hx-target`/`hx-swap`. OOB (out-of-band) swaps keep card list and detail panel in sync after mutations.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `base.html` | Shell: sidebar, top bar, toast container, progress bar, sidebar toggle JS | All page templates extend this |
| `email_list.html` | Stats bar, tab bar, filters, search, list+detail split layout | `_email_list_body.html`, `_email_detail.html` |
| `_email_card.html` | Single email card with priority border, badges, claim/assign | Detail panel (via `hx-get` to `#detail-panel`) |
| `_email_detail.html` | Full email view: header, SLA, AI suggestion, actions, body, activity | Card list (via OOB swap on `#card-{pk}`) |
| `_email_list_body.html` | Card loop + pagination, swapped into `#email-list` | Individual `_email_card.html` instances |
| `activity_log.html` | MIS stats grid, filter chips, activity feed | `_activity_feed.html` |
| `views.py` | All view logic, HTMX detection via `request.htmx`, OOB response assembly | Templates, models, assignment service |

### Data Flow

```
User Action (click/filter/submit)
    |
    v
HTMX Request (hx-get or hx-post with CSRF header from body attribute)
    |
    v
Django View (detects request.htmx, returns partial or full page)
    |
    v
HTMX swaps target element (innerHTML or outerHTML)
    + OOB swaps for cross-component sync (card + detail panel)
    |
    v
JS event listeners (htmx:afterSwap) trigger side effects
    (e.g., mobile detail panel slide-in, progress bar)
```

---

## Integration Points for v2.2.1 Changes

### 1. AI Suggestion XML Markup Bug

**Problem:** `email.ai_suggested_assignee` is a JSONField (`dict`). The card template on line 59-61 of `_email_card.html` renders `{{ email.ai_suggested_assignee.name }}`. If Claude's response includes XML tags in the name (e.g., `<name>Shreyas</name>`), Django's auto-escaping shows the raw escaped markup to users.

**Root cause:** `ai_processor.py` does not strip XML/markup from parsed assignee name before storing.

**Fix approach -- data sanitization at source (recommended):**
- Strip XML tags in `ai_processor.py` when parsing Claude's response into the `ai_suggested_assignee` dict
- Add a `strip_xml` template filter in `email_tags.py` as defense-in-depth
- No template structure changes needed -- `{{ email.ai_suggested_assignee.name }}` continues to work

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `apps/emails/services/ai_processor.py` | Strip XML from assignee name before saving to JSONField | Modified |
| `apps/emails/templatetags/email_tags.py` | Add `strip_xml` filter (optional safety net) | Modified |
| Templates | None | Unchanged |

**Integration pattern:** Pure backend data fix. No HTMX or template architecture changes.

---

### 2. Mobile Detail Panel Visibility

**Current mechanism:** Detail panel (`#detail-panel`) is `fixed inset-0 z-50 translate-x-full` on mobile, `md:relative md:translate-x-0` on desktop. The `htmx:afterSwap` JS listener in `email_list.html` removes `translate-x-full` when content loads. `closeDetail()` adds it back.

**What works:** The slide-in mechanism is correct. The overlay (`#detail-overlay`) syncs with panel visibility.

**What to improve:**
- **Body scroll lock:** When detail is open on mobile, the card list behind it can still scroll. Add `document.body.classList.add('overflow-hidden')` in the afterSwap handler and remove it in `closeDetail()`.
- **Back button visibility:** The back button in `_email_detail.html` line 5-8 uses `md:hidden` correctly -- it is only visible on mobile. This is working as intended.
- **Safe area insets:** For notched phones, add `env(safe-area-inset-top)` padding to the detail panel header.

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `templates/emails/email_list.html` | Add body scroll lock in `htmx:afterSwap` and `closeDetail()` | Modified |
| `templates/emails/_email_detail.html` | Add safe-area padding (optional) | Modified |

**Integration pattern:** Extend existing JS in `{% block extra_js %}`. No new components.

---

### 3. Mobile Filter Toggle and Layout

**Current state:** The tab bar and filter toggle button share a single flex row (`email_list.html` lines 66-158). Filters are `hidden md:flex` in `#mobile-filters`. `toggleFilters()` toggles visibility and adds `flex-wrap`.

**Problem:** On small screens, tabs + filter button + email count all squeeze into one row, potentially causing overflow. When filters are expanded, they inline which overflows on narrow screens.

**Fix approach:**
- Split the tab bar into two rows on mobile: tabs in row 1, filters in row 2 (collapsible)
- Use `flex-wrap` as base, `md:flex-nowrap` for desktop inline layout
- Filter inputs need wider touch targets on mobile (min `py-2` instead of `py-1.5`)
- The "X emails" count badge should move below filters on mobile

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `templates/emails/email_list.html` | Restructure tab+filter section with mobile breakpoints | Modified |

**Integration pattern:** Pure Tailwind responsive classes + minor HTML restructure. Existing `toggleFilters()` JS stays. HTMX `hx-include` attributes on filter inputs remain unchanged.

---

### 4. Stats Bar Mobile Layout

**Current state:** `email_list.html` lines 12-62: four stat cards in a horizontal `flex overflow-x-auto` row. Each has `min-w-[120px]`.

**Problem:** On mobile, stat cards overflow horizontally with no visual scroll cue.

**Fix approach:**
- Use `grid grid-cols-2 md:flex md:overflow-x-auto` -- 2x2 grid on mobile, horizontal flex on desktop
- Remove `min-w-[120px]` on mobile (let grid handle sizing)
- Compact the stat card content slightly for mobile (smaller icons, tighter padding)

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `templates/emails/email_list.html` | Switch stats to grid on mobile | Modified |

---

### 5. Activity Page Filter Overflow

**Current state:** `activity_log.html` line 63: filter chips are in `flex overflow-x-auto`. This scrolls horizontally but has no visual affordance on mobile.

**Fix approach:**
- Use `flex flex-wrap gap-1.5 md:flex-nowrap md:overflow-x-auto` -- wrap chips on mobile, scroll on desktop
- Add `scrollbar-hide` class (already defined in `base.html` line 74-76) to the container on desktop

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `templates/emails/activity_log.html` | Wrap filter chips on mobile | Modified |

**Integration pattern:** Pure CSS. No JS changes. HTMX attributes on chips remain unchanged.

---

### 6. Welcome Toast / First-Login Experience

**Current toast system:** `base.html` lines 271-299 renders Django `messages` framework messages. Auto-dismiss after 4s with staggered timing. CSS animations `toast-in`/`toast-out` defined in `<style>`. Container has `role="status"` and `aria-live="polite"` for accessibility.

**Architecture for welcome toast:**

**Option A -- Django messages (recommended for simplicity):**
- In `VIPLSocialAccountAdapter.save_user()` or post-login signal: if `user.last_login` is None (first login), call `messages.info(request, "Welcome to VIPL Triage! ...")`
- Existing toast system renders it. Zero new components.
- Limitation: Django messages require a request object. The adapter has access to it.

**Option B -- localStorage-based dismissible card (richer UX):**
- Add a `{% if not request.COOKIES.vipl_welcome_dismissed %}` block in `email_list.html` content area
- Render a styled welcome card with quick tips
- Dismiss button sets `document.cookie = 'vipl_welcome_dismissed=1; ...'`
- No backend changes needed

**Recommended:** Option A for the welcome toast (works immediately). Option B only if a richer onboarding walkthrough is desired.

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `apps/accounts/adapters.py` | Add welcome message on first login | Modified |
| Templates | None (existing toast renders it) | Unchanged |

---

### 7. Email Count Accuracy

**Current state:** `email_list.html` line 156 shows `{{ total_count }}` which is `paginator.count` -- the **filtered** queryset count. Stat cards show `dash_stats.total` which counts ALL completed emails globally.

**This is correct behavior.** The stat cards are a global dashboard overview. The count label reflects what is currently filtered/shown. No bug here.

**Optional improvement:** Make the count label more descriptive to avoid confusion. E.g., "12 emails" becomes "12 matching" when filters are active.

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `templates/emails/email_list.html` | Clarify count label when filters active | Modified |
| `apps/emails/views.py` | Add `has_active_filters` bool to context | Modified |

---

### 8. Page Title Consistency

**Current state:**
| Page | `<title>` | Top bar `page_title` |
|------|-----------|---------------------|
| Inbox | `VIPL Triage \| Inbox` | `Inbox` |
| Activity | `VIPL Triage \| Activity` | `Activity` |
| Settings | Needs verification | Needs verification |
| Team | Needs verification | Needs verification |
| Login | Needs verification | N/A (no sidebar) |

**Fix:** Audit all templates extending `base.html`. Ensure all follow `VIPL Triage | <Page>` for `<title>`.

**Files modified:**
| File | Change | Type |
|------|--------|------|
| `templates/emails/settings.html` | Verify/fix title blocks | Possibly modified |
| `templates/accounts/team.html` | Verify/fix title blocks | Possibly modified |
| `templates/account/login.html` | Verify/fix title | Possibly modified |

---

## Component Map: New vs Modified

| Component | Status | What Changes |
|-----------|--------|--------------|
| `apps/emails/services/ai_processor.py` | **Modified** | Strip XML from AI response assignee name |
| `apps/emails/templatetags/email_tags.py` | **Modified** | Add `strip_xml` filter |
| `templates/emails/email_list.html` | **Modified** | Mobile filter layout, stats grid, count label, body scroll lock |
| `templates/emails/activity_log.html` | **Modified** | Filter chip wrapping on mobile |
| `templates/emails/_email_detail.html` | **Minor** | Safe-area padding (optional) |
| `apps/accounts/adapters.py` | **Modified** | Welcome message on first login |
| `apps/emails/views.py` | **Minor** | Add `has_active_filters` to context |
| `templates/emails/_email_card.html` | **Unchanged** | Already uses `.name` accessor correctly |
| `templates/base.html` | **Unchanged** | Toast system already complete |
| No new templates | -- | All changes fit existing component structure |
| No new JS files | -- | All JS stays inline in template blocks |
| No new models | -- | No migrations needed |
| No new URL routes | -- | No `urls.py` changes |

---

## Patterns to Follow

### Pattern 1: HTMX Partial Swap with OOB Sync
Every user action (assign, claim, status change) returns the primary target HTML + OOB swap HTML for related components. All v2.2.1 changes must preserve this. Do not add UI elements that display email state without participating in the OOB swap chain.

### Pattern 2: Mobile-First Responsive with Tailwind Breakpoints
Use base styles for mobile, `md:` prefix for desktop overrides. **Current gap:** The filter section is desktop-first (`hidden md:flex`) -- mobile is the afterthought. Restructure to be mobile-first.

### Pattern 3: Django Messages for Transient Feedback
Use `messages.success/info/error()` in views. `base.html` toast container renders them automatically with auto-dismiss and accessibility attributes. Use this for the welcome toast rather than building a new notification system.

### Pattern 4: Inline JS in Template Blocks
All JavaScript lives in `{% block extra_js %}` or inline `<script>` tags. No external JS files. Keep this pattern -- do not introduce Alpine.js, Vue, or any JS framework for simple toggle/scroll-lock behavior.

---

## Anti-Patterns to Avoid

### Adding a JS Framework for Simple Interactions
The app has zero JS dependencies beyond HTMX. Adding Alpine.js or similar for toast/drawer/toggle behavior adds load time and complexity for no gain. Inline vanilla JS is the established pattern.

### Duplicating OOB Response Assembly
Views like `assign_email_view`, `claim_email_view`, `accept_ai_suggestion`, etc. all have near-identical OOB response patterns. If adding new actions in this milestone, consider extracting a `_respond_with_card_and_detail()` helper rather than copy-pasting.

### Using localStorage for Critical State
`localStorage` is fine for cosmetic preferences (welcome dismissed, sidebar collapsed). Never use it for anything that must persist across devices or be visible to the backend.

### Fixing Data Bugs in Templates
The AI suggestion XML bug should be fixed at the data source (`ai_processor.py`), not masked with template filters. Template filters are defense-in-depth, not the primary fix.

---

## Recommended Build Order

Based on dependency analysis and risk profile:

```
Phase 1: Data Fixes (no UI risk, backend only)
  1. AI suggestion XML strip in ai_processor.py
  2. strip_xml template filter as safety net in email_tags.py

Phase 2: Mobile Layout (CSS/HTML, low risk, visually testable)
  3. Stats bar: grid on mobile
  4. Filter section: mobile restructure with collapsible filters
  5. Activity page: filter chip wrapping
  6. Detail panel: body scroll lock on mobile

Phase 3: Polish (additive, zero breakage risk)
  7. Page title consistency audit + fixes
  8. Email count label clarity
  9. Welcome toast on first login
```

**Rationale:**
- Data fix first: affects stored data quality, independent of all other changes
- Mobile layout second: CSS-only changes, testable by resizing browser, cannot break desktop
- Polish last: additive features that cannot break existing functionality

---

## Sources

- Direct codebase analysis of `base.html`, `email_list.html`, `_email_card.html`, `_email_detail.html`, `_email_list_body.html`, `activity_log.html`, `views.py`, `models.py` -- HIGH confidence
- HTMX 2.0 OOB swap behavior -- HIGH confidence (verified from existing working code)
- Tailwind CSS v4 browser CDN responsive utilities -- HIGH confidence (verified from existing `@theme` config)
