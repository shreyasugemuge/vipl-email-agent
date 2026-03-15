# Phase 6: QA Bug Fixes - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 4 functional bugs found during QA front-end review (#39): thread count label, search view reset, mobile detail drawer, and Escape key closing detail panel.

</domain>

<decisions>
## Implementation Decisions

### QA-01: Thread count doesn't reflect view filter (#31)
- Root cause: `total_count` in context is `paginator.count` which counts the full queryset — BUT the queryset IS already filtered by view. The issue is likely that the count label says "11 threads" when on Unassigned view which has fewer.
- Actually on inspection, `paginator.count` IS the filtered count. Need to verify on live — may be an HTMX partial swap issue where the count label isn't inside the swapped target.
- Fix: ensure thread count label is inside `#thread-list-body` so it updates on HTMX swaps, OR add an OOB swap for it.

### QA-02: Search resets sidebar view filter (#32)
- Root cause: search input `hx-include` includes `[name='view-hidden']` which should preserve the view. But the search `hx-get` targets `thread_list` URL which does a fresh queryset. The hidden input value should carry through.
- Likely issue: the `view-hidden` input gets its value from initial page load but doesn't update when sidebar nav changes (HTMX pushes new URL but doesn't update the hidden input value).
- Fix: update `view-hidden` input value when sidebar navigation occurs (via `htmx:pushedIntoHistory` or similar).

### QA-03: Mobile detail drawer doesn't open (#35)
- Root cause: **confirmed** — parent container div at line 312 is `class="hidden lg:flex"`. On mobile (<1024px), the parent is `display:none` via Tailwind's `hidden` class. The HTMX afterSwap handler removes `translate-x-full` from the panel inside, but the parent is still hidden.
- Fix: change parent container to not use `hidden` — use a different approach that allows the panel to be visible on mobile when activated (e.g., remove `hidden` and use the translate-x approach for both mobile and desktop).

### QA-04: Escape key doesn't close detail panel (#36)
- Root cause: Escape keydown handler at line 411 only calls `closeContextMenu()`, not `closeThreadDetail()`.
- Fix: add `closeThreadDetail()` call when Escape is pressed and detail panel is open (check if panel has content or is visible).

### Claude's Discretion
- Exact CSS approach for mobile drawer fix (remove hidden, use translate-x, or use a different visibility mechanism)
- Whether to add tests for these JS-heavy fixes (template rendering tests for count label, view integration tests for search)

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above and GitHub issues #31, #32, #35, #36.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `closeThreadDetail()` function already exists in thread_list.html — just needs to be wired to Escape
- `htmx:afterSwap` handler for mobile panel — needs parent container fix
- `view-hidden` input pattern — used by all filter selects

### Established Patterns
- OOB swap pattern for updating elements outside HTMX target (used for card updates, sidebar badges)
- `updateActiveStates()` runs on `htmx:pushedIntoHistory` — can piggyback for view-hidden sync
- `hx-include` with hidden inputs preserves filter state across HTMX requests

### Integration Points
- `templates/emails/thread_list.html` — all 4 fixes are in this single file
- `templates/emails/_thread_list_body.html` — the partial swapped by HTMX (count label may need to move here)
- `apps/emails/views.py:thread_list_view` — context includes `total_count` from paginator

### Key Files
- `templates/emails/thread_list.html` — QA-01, QA-02, QA-03, QA-04
- `templates/emails/_thread_list_body.html` — QA-01 (count label location)
- `apps/emails/views.py` — QA-01 (total_count context)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — straightforward bug fixes from QA report.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-qa-bug-fixes*
*Context gathered: 2026-03-15*
