# Phase M6-P2: Thread Card & Detail UX - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Polish thread cards and detail panel: better spacing/organization, inline pill dropdowns for category/priority, readable context menu, and AI draft reply display. Requirements: CARD-01, CARD-02, CARD-03, CARD-04.

</domain>

<decisions>
## Implementation Decisions

### Card spacing & organization (CARD-01)
- Reorganize card info for better UX, not just more padding
- Bump ALL text sizes +1-2px: sender 11→13px, subject 12→13px, summary 11→12px, badges 8→9px
- Increase card padding (py-2.5 → py-3 or similar)
- AI summary: allow 2-line wrap instead of single-line 80-char truncation — makes summary actually useful
- Move badges (priority dot, confidence dot, status badge, SLA countdown, inbox badge) from subject row to row 3 alongside summary area — subject gets its own clean row
- Increase card gap from my-0.5 to my-1 or my-1.5 — cards feel like distinct items
- Unread indicator: bigger dot (w-1.5 → w-2 or w-2.5) + bold subject line
- Sender row: Claude's discretion on reorganizing (name, email, time, message count, assignee avatar) for clarity

### Pill dropdowns (CARD-02)
- Replace current badge→select toggle with styled select pills: colored background, rounded, subtle caret indicator
- Applies to priority and category dropdowns only — NOT status (status keeps action buttons: Acknowledge/Close)
- Caret hidden by default, revealed on hover (clean at rest, clear affordance on interaction)
- Native `<select>` dropdown on click (not custom popover) — simpler, works with HTMX
- HTMX submit on change (same as current behavior)

### Context menu font (CARD-03)
- Bigger text: bump from text-[12px] to text-[13px] or text-sm (14px)
- Better contrast: brighten text from slate-200 to white or slate-100 on the slate-800 background
- Both size and contrast need improvement — menu items should be effortless to read
- Keyboard shortcut hints (U, K, X, S, W): keep subtle — small and muted, for power users

### AI draft display (CARD-04)
- Add a copy-to-clipboard button — main use case is pasting draft into Gmail for reply
- Visibility and collapse behavior: Claude's discretion (expanded vs collapsed default)
- Font choice: Claude's discretion (proportional vs monospace)
- Keep the draft section only visible when `thread.ai_draft_reply` is non-empty

### Claude's Discretion
- Sender row reorganization (what to show, what to move/drop)
- Exact padding and gap values within the new ranges
- AI draft: expanded vs collapsed default, proportional vs monospace font
- Badge arrangement in row 3 (order, grouping)
- Any micro-interactions (transitions, hover states)

</decisions>

<specifics>
## Specific Ideas

- User wants cards to feel less like a wall of text — distinct items with breathing room
- Subject line should have its own clean row without badge clutter
- AI summary should be readable at the card level (2 lines), not a throwaway truncated line
- Pill dropdowns should look like the existing colored badges but with an interactive caret on hover
- Context menu needs to be effortless to read — both size and contrast improvements
- Copy button on AI draft is key — the whole workflow is: read draft → copy → paste into Gmail

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_thread_card.html`: 3-row card template with priority border, badges, AI summary (lines 1-93)
- `_thread_detail.html`: Full detail panel with AI sections, action bar, timeline (577 lines)
- `_editable_priority.html`: Badge → select toggle with HTMX submit
- `_editable_category.html`: Badge → select toggle with custom category fallback
- `_editable_status.html`: Badge → select toggle (will NOT become pill — keeps action buttons)
- `_context_menu.html`: Dark-themed right-click menu with role-aware actions (127 lines)

### Established Patterns
- HTMX form submission: `hx-post`, `hx-target="#thread-detail-panel"`, `hx-swap="innerHTML"`
- Tailwind arbitrary values: `text-[Npx]` used throughout for precise sizing
- Priority colors: defined per priority level (bg-red for URGENT, bg-amber for HIGH, etc.)
- Category badge: neutral `bg-slate-100 text-slate-500` styling
- Unread state: `font-semibold` + blue dot indicator already in place

### Integration Points
- Card template included in thread list via `{% include "_thread_card.html" %}`
- Detail panel loaded via HTMX GET to `/emails/threads/<pk>/detail/`
- Editable partials are standalone templates swapped via HTMX responses
- Context menu fetched server-side: `GET /emails/threads/<pk>/context-menu/`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: M6-P2-thread-card-detail-ux*
*Context gathered: 2026-03-15*
