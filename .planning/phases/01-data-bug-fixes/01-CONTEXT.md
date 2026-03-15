# Phase 1: Data & Bug Fixes - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 7 bugs (BUG-01 through BUG-07) so users see clean, accurate, consistent information across all pages and devices. No new features — only fixing what's broken or misleading.

</domain>

<decisions>
## Implementation Decisions

### AI Suggestion Cleanup (BUG-01)
- Clean at ingest time in `ai_processor.py` — parse XML-wrapped names and extract inner text
- If Claude returns `<parameter name="name">Shreyas</parameter>`, extract "Shreyas" (not strip to empty)
- Django data migration to fix existing records with XML markup in `ai_suggested_assignee` JSONField
- No display-layer filter — fix the data at source

### Mobile Detail Panel (BUG-02)
- Full-screen slide-in from right (fix current broken implementation, not new pattern)
- Back button at top-left of panel (← Back)
- Lock body scroll (`overflow: hidden`) when panel is open on mobile
- Support browser hardware/software back button via `history.pushState` — pressing back closes panel instead of navigating away
- Overlay behind panel stays (current `detail-overlay` div)

### Mobile Filter Bar (BUG-03)
- Claude's Discretion — stacked full-width selects on mobile, match acceptance criteria

### Activity Page Chips (BUG-04)
- Claude's Discretion — ensure "Priority Bump" is fully visible, no truncation

### Email Count Accuracy (BUG-05)
- Claude's Discretion — count must update when switching views via HTMX (likely needs hx-swap-oob or wrapping count in its own target)

### Page Title Consistency (BUG-06)
- Claude's Discretion — all pages follow "VIPL Triage | {Page Name}" pattern

### Toast Positioning (BUG-07)
- Mobile: position below header (top-16 / 64px), right-aligned
- Desktop: keep current top-right positioning (top-4 right-4) — no change
- Add swipe-right-to-dismiss gesture on mobile (touch event handling in JS)
- Keep auto-dismiss after 4 seconds
- Increase close button tap target to 44x44px minimum on mobile

### Claude's Discretion
- BUG-03: Mobile filter stacking implementation details
- BUG-04: Chip overflow fix approach (scroll vs wrap vs abbreviation)
- BUG-05: HTMX technique for updating email count (hx-swap-oob vs separate request vs wrapping)
- BUG-06: Which templates need title block updates (audit all pages)

</decisions>

<specifics>
## Specific Ideas

- Toast swipe-to-dismiss should feel like iOS notifications — natural right swipe gesture
- Mobile detail panel should feel like a native app view push (slide from right, back at top-left)
- Browser back button closing the panel is important for mobile UX — users expect it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_email_card.html`: Card template with HTMX `hx-get` to load detail — needs no change, just the panel receiving end
- `_email_detail.html`: Detail partial already rendered correctly, just not displaying on mobile
- `base.html` toast container: Already has animation CSS (`toast-in`, `toast-out`) — extend with swipe

### Established Patterns
- HTMX `hx-target` + `hx-swap="innerHTML"` for partial updates — used throughout
- Django template `{% block title %}` inheritance from `base.html`
- `htmx:afterSwap` event listener for post-swap JS (used for mobile panel toggle)
- Tailwind responsive classes (`md:` prefix) for mobile/desktop splits

### Integration Points
- `ai_processor.py` `_parse_suggested_assignee()` — where XML cleanup logic goes
- `email_list.html` JS block — where mobile panel, filter toggle, and history API code lives
- `base.html` toast container — where toast positioning and swipe JS goes
- `views.py` `email_list()` — where count context is set for HTMX partials

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-data-bug-fixes*
*Context gathered: 2026-03-15*
