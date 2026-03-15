# Phase 5: Editable Attributes + Context Menu - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can inline-edit thread category, priority, and status from the detail panel, and perform common actions via right-click context menu on thread/email cards. Every context menu action must also be accessible via the primary UI.

</domain>

<decisions>
## Implementation Decisions

### Inline edit interaction
- Pencil icon appears on hover next to category, priority, and status badges in detail panel
- Click pencil → dropdown opens inline (replaces badge momentarily)
- Auto-save on select: picking a value immediately POSTs via HTMX, no save button
- Category dropdown: shows existing categories + "Custom..." option for freeform input
- Priority dropdown: CRITICAL / HIGH / MEDIUM / LOW
- Status dropdown: New / Acknowledged / Closed (replaces current separate Acknowledge/Close buttons)
- All changes create ActivityLog entries (PRIORITY_CHANGED, CATEGORY_CHANGED, STATUS_CHANGED) with old_value → new_value
- Override flags (category_overridden, priority_overridden) set to True on user edit — pipeline won't overwrite

### Context menu layout
- Right-click on thread/email card shows floating context menu at cursor position
- Actions grouped with dividers:
  - Group 1: Mark Read / Mark Unread
  - Group 2: Assign to... / Claim
  - Group 3: Acknowledge / Close
  - Group 4: Mark Spam / Whitelist Sender
- "Assign to..." opens the detail panel (reuses existing assignment UI, no submenu)
- Keyboard shortcut hints shown on right side of each action (e.g., "Mark Read .... R")
- Role-aware: admin sees Assign + Whitelist, members see Claim if eligible
- Menu is navigable with arrow keys + Enter

### Mobile long-press
- Long-press (500ms) triggers the same context menu
- Menu appears floating near the finger position (not bottom sheet)
- Consistent with desktop — same actions, same layout

### Visual feedback
- After any action: toast notification ("Priority changed to HIGH") + card re-renders via HTMX OOB swap
- Menu closes on: click outside, Escape key, page scroll
- Menu close: 150ms fade-out transition

### Claude's Discretion
- Menu styling (dark vs light theme — pick what's most coherent with overall UI)
- Menu max-width and positioning logic (ensure stays in viewport)
- Keyboard shortcut key assignments
- Exact transition/animation timings
- How "Custom..." category input opens (inline text field or modal)

</decisions>

<specifics>
## Specific Ideas

- "Like Jira's inline field editing" — pencil on hover, dropdown opens in-place
- "Like VS Code right-click" — grouped actions with dividers and shortcut hints
- Every action in context menu MUST also be accessible via primary UI (detail panel buttons, etc.)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `edit_ai_summary` view + JS toggle pattern in `_thread_detail.html` — pencil icon → hidden form → save. Same pattern for category/priority edit.
- Existing status change endpoints: `change_thread_status_view`, `change_status_view` — reuse for status dropdown
- `updateActiveStates()` in `base.html` — extend for context menu active state
- Toast notification system in `base.html` — reuse for action feedback

### Established Patterns
- HTMX OOB swap for card updates after actions (already used in assign, status change)
- `@require_POST` on mutation endpoints
- `_build_thread_detail_context()` returns full context for re-rendering detail panel
- Template filters for tooltips (`status_tooltip`, `priority_tooltip`) in `email_tags.py`

### Integration Points
- `_thread_detail.html` badges row (~line 28-45): add pencil icons + inline dropdowns
- `_thread_card.html`: add `oncontextmenu` handler
- `base.html` `extra_js`: context menu JS component
- `views.py`: new endpoints for `edit_category`, `edit_priority`, `edit_status`
- `urls.py`: new URL patterns

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-editable-attrs-context-menu*
*Context gathered: 2026-03-15*
