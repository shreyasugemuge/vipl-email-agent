# Phase 2: Polish & UX - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the dashboard feel polished with guided onboarding, visible filter state, responsive scroll-snap stat cards, keyboard navigation, and a loading skeleton in the detail panel. No new pages or features — purely UX improvements to existing views.

</domain>

<decisions>
## Implementation Decisions

### Welcome banner (UX-01)
- Toast notification style (top-right), reusing existing toast system in base.html
- Personalized: "Welcome, {first_name}!" with role-specific guidance
- Admin message: guidance about assigning emails, managing team, configuring settings
- Member message: guidance about claiming emails and checking My Emails
- Dismiss via X button; also offer "Don't show again" checkbox/link
  - Default: sessionStorage key — reappears on new browser session
  - "Don't show again": sets localStorage key — permanently hidden
- Auto-fade after 8s if not interacted with

### Filter indicators (UX-02)
- Count badge + "Clear all" link appears between tab bar and email list when any filter is active
- Text format: "N filters active · Clear all"
- Search query counts as a filter in the badge count
- "Clear all" resets dropdowns (status, priority, category, inbox) AND search box
- "Clear all" does NOT reset the view tab (All/Unassigned/My Emails) — stays on current view
- Bar hidden when no filters are active (zero visual clutter by default)

### Mobile stat cards scroll-snap (UX-03)
- CSS scroll-snap on the stat cards container for mobile
- Each card snaps cleanly when swiping horizontally

### Keyboard navigation (UX-04)
- Arrow keys (up/down) navigate between email cards in the list
- Escape closes the detail panel (mobile overlay + desktop)

### Loading skeleton (UX-05)
- Layout-matching skeleton in detail panel: badge row, subject, summary, sender row, body lines
- Tailwind animate-pulse on slate-colored placeholder blocks
- Shows immediately on card click (htmx:beforeRequest), no delay threshold
- Replaces default "Select an email" empty state during load

### Claude's Discretion
- Scroll-snap CSS specifics (snap-type, snap-align values, padding)
- Keyboard nav: whether to skip events when focus is in INPUT/SELECT/TEXTAREA
- Welcome toast exact wording and icon choice
- Skeleton block widths, heights, and spacing to match actual detail panel layout
- Whether arrow keys also auto-open the detail panel for the focused card

</decisions>

<specifics>
## Specific Ideas

- Welcome toast should feel like existing toast system — same rounded card, shadow, animation
- Filter indicator should be subtle (small text, slate color) — not a loud banner
- Skeleton should use same slate-100/200 grays as the rest of the UI

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `base.html` toast system: toast-in/toast-out keyframe animations, auto-dismiss JS, toast-container div
- `base.html` HTMX progress bar: htmx:beforeRequest/afterRequest event listeners already wired
- `_email_card.html`: cards have `tabindex="0"`, `role="article"`, Enter/Space click handlers
- Stat cards container: flex with `overflow-x-auto` and `scrollbar-hide` — scroll-snap is additive

### Established Patterns
- HTMX event system for request lifecycle (beforeRequest, afterSwap, afterRequest)
- django-htmx middleware provides `request.htmx` for partial vs full page detection
- Filter state tracked via template variables: `current_status`, `current_priority`, `current_category`, `current_inbox`, `current_search`, `current_view`
- `closeDetail()` JS function already exists for mobile detail panel

### Integration Points
- Welcome toast: inject in `base.html` or `email_list.html` block, check sessionStorage/localStorage
- Filter bar: add conditional row in `email_list.html` between tab bar div and email list div
- Scroll-snap: add CSS classes to stat cards container div in `email_list.html`
- Keyboard nav: add keydown listener in `email_list.html` extra_js block
- Loading skeleton: show via htmx:beforeRequest targeting detail-panel, replace on htmx:afterSwap

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-polish-ux*
*Context gathered: 2026-03-15*
