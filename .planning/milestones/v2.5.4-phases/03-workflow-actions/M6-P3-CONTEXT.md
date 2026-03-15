# Phase M6-P3: Workflow Actions - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can self-serve on common actions — claim unassigned threads and undo spam mistakes. Both features have existing backend logic; this phase fixes broken UI and verifies existing behavior.

</domain>

<decisions>
## Implementation Decisions

### Claim button (FLOW-01)
- Claim button is currently **not showing** — this is a bug, likely in `can_claim` logic or template condition
- Fix the bug so Claim appears in **detail panel + context menu** for unassigned threads
- Do NOT add Claim to thread cards in the list — detail + context menu only
- Claim = assign only (no auto-acknowledge) — user manually acknowledges after claiming
- Show "Thread claimed" toast after successful claim

### Undo spam (FLOW-02)
- Current toggle (Mark Spam ↔ Not Spam) IS the undo mechanism — no timed undo toast needed
- Verify the toggle works correctly: after marking spam, "Not Spam" button appears; after marking not-spam, "Mark Spam" button appears
- Fix any bugs if the toggle isn't working properly

### Claude's Discretion
- Root cause investigation for why Claim button doesn't show
- Any toast styling/positioning decisions
- Whether to add ActivityLog entries for claim actions (if not already logged)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `claim_thread_view` (views.py:1393): Full claim logic with OOB card swap — just needs the template to actually show the button
- `mark_spam` / `mark_not_spam` (views.py:1516/1564): Complete spam toggle with SpamFeedback, SenderReputation, ActivityLog
- Toast pattern: `toast_msg` context variable in detail template
- HTMX pattern: `hx-post` → re-render detail panel + OOB card swap

### Established Patterns
- `can_claim` variable gates Claim button visibility in templates
- `_build_thread_detail_context()` builds the context dict for detail panel
- `hx-disabled-elt="this"` on all action buttons prevents double-submission
- `hx-confirm` on destructive actions (Mark Spam uses it)

### Integration Points
- `_thread_detail.html:160` — Claim button conditional (detail panel)
- `_context_menu.html:40` — Claim in right-click menu
- `_thread_detail.html:216-241` — Spam toggle buttons
- Views must return OOB card swap HTML for thread list updates

</code_context>

<specifics>
## Specific Ideas

No specific requirements — the user wants both features to simply work as designed. Claim button needs a bug fix, spam toggle needs verification.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: M6-P3-workflow-actions*
*Context gathered: 2026-03-15*
