# Phase 3: Mark Irrelevant - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Gatekeepers and admins can dismiss irrelevant threads from the queue with an auditable reason. The action closes the thread with a distinct IRRELEVANT status, excludes it from queue counts, and logs the reason in the activity timeline. Members cannot see or use this action.

</domain>

<decisions>
## Implementation Decisions

### Action UX flow
- Modal with textarea for mandatory reason (click button -> modal overlay with reason textarea + confirm/cancel)
- Button in a standalone section in the detail panel (below AI triage area, separate from mark-spam)
- Amber/warning button styling (not red like spam, not gray -- signals conscious decision)
- Keyboard shortcut: I key opens the modal
- Modal submitted via HTMX POST, swaps detail panel on success

### Queue behavior after marking
- Irrelevant threads hidden from Triage Queue, My Inbox, All Open views by default
- Accessible via status filter dropdown ("Irrelevant" option alongside New/Acknowledged/Closed)
- Excluded from Unassigned, Urgent, New stat cards
- New "Irrelevant" stat card visible to gatekeepers/admins only (shows count of irrelevant threads)
- Muted "Irrelevant" badge on thread cards when filtered in (similar to spam badge styling)
- Undo supported: "Revert to New" button on irrelevant thread detail -- resets status to NEW, clears assignment, logs reversal in ActivityLog

### Activity timeline display
- Prominent styled entry with amber background (visually distinct from normal status changes)
- Shows full reason text inline, who marked it, and when
- Badge only on cards; full reason visible only in activity timeline (keeps cards clean)
- On revert: both original "marked irrelevant" and new "reverted to New" entries stay in timeline (full audit trail)

### Context menu integration
- Mark Irrelevant sits in the Status group (after Acknowledge and Close)
- Keyboard shortcut I shown in menu
- Context menu click opens detail panel + auto-opens reason modal (consistent two-step flow)
- Completely hidden from members (not grayed out -- same pattern as Assign)
- Gated by gatekeeper/admin permission check (will use `can_assign` helper from Phase 1)

### Claude's Discretion
- Modal design details (exact dimensions, animation, z-index)
- Irrelevant badge color shade and sizing
- Stat card positioning among existing stat cards
- "Revert to New" button placement within detail panel

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` -- TRIAGE-01 through TRIAGE-06 define the mark-irrelevant requirements

### Roadmap
- `.planning/ROADMAP.md` -- Phase 3 success criteria (5 items) define acceptance gates

### Prior decisions
- `.planning/STATE.md` -- "Irrelevant" is a distinct Thread status (not overloading CLOSED), zero new dependencies

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Thread.Status` (TextChoices): Currently has NEW, ACKNOWLEDGED, CLOSED -- add IRRELEVANT here
- `ActivityLog` model: Already tracks status changes, assignments, AI edits -- use for irrelevant events
- `_context_menu.html`: Grouped sections with `is_admin` gating -- extend Status group
- `_thread_detail.html`: Mark spam button with `hx-confirm` and `hx-post` pattern -- similar HTMX pattern for modal
- Spam badge on thread cards: Reuse badge pattern for irrelevant badge (muted amber instead of red)

### Established Patterns
- `hx-post` + `hx-target="#thread-detail-panel"` for all thread actions
- `hx-disabled-elt="this"` for button loading states
- `is_admin` template checks gate admin-only actions (will become permission helper in Phase 1)
- `@require_POST` decorator on action views
- Status filter via URL query params (`?status=irrelevant`)

### Integration Points
- `apps/emails/models.py`: Thread.Status choices -- add IRRELEVANT
- `apps/emails/views.py`: Thread list queryset filtering -- exclude IRRELEVANT from default views
- `apps/emails/views.py`: Dashboard stat aggregation -- add irrelevant stat card, exclude from other stats
- `templates/emails/thread_list.html`: Status filter dropdown -- add Irrelevant option
- `templates/emails/_thread_detail.html`: Add standalone mark-irrelevant section + modal
- `templates/emails/_context_menu.html`: Add Mark Irrelevant to Status group
- `apps/emails/urls.py`: New URL patterns for mark_irrelevant and revert_irrelevant views

</code_context>

<specifics>
## Specific Ideas

- Amber styling differentiates from red spam and gray/neutral close -- three distinct "remove from active queue" tones
- The reason modal should feel like a lightweight form, not a heavy dialog -- similar weight to the AI summary edit modal
- Context menu -> detail panel -> modal is a two-step flow but ensures consistency (same modal everywhere)

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 03-mark-irrelevant*
*Context gathered: 2026-03-15*
