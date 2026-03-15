# Phase 4: Read/Unread Tracking - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Per-user read/unread state for threads. Users see which threads they haven't read, threads auto-mark as read on open, users can manually mark unread, and sidebar shows unread counts. ThreadReadState model is created in Phase 1.

</domain>

<decisions>
## Implementation Decisions

### Visual design
- Blue dot + bold text = "unread by you" (per-user), replacing the current `status == 'new'` logic on thread cards
- Blue-500 dot color (same as current, familiar)
- Read threads: normal weight text, no dot — regardless of thread status
- New emails arriving in an already-read thread flip it back to unread (compare `read_at` vs `last_message_at`)
- Initial deploy state: no ThreadReadState row = treated as read (avoids wall of bold on first login)

### Read trigger behavior
- Opening thread detail panel marks it as read immediately (no delay timer)
- View upserts ThreadReadState on the detail panel GET request
- Card updates to read styling via OOB swap in the detail response (optimistic feel)
- Assignment to a user resets their read state for that thread (thread becomes unread for assignee)

### Unread badge scope
- Sidebar count badges show unread count (not total) when there are unreads; show muted total when all read
- Unread badges on: My Inbox (required by READ-05), All Open, Closed views, plus Claude's discretion on Triage Queue
- Browser tab title shows unread count: "(3) VIPL Triage | Inbox" — standard pattern
- Counts update on HTMX navigation (OOB swaps), no background polling

### Mark unread UX
- "Mark as unread" icon button in thread detail header actions bar (alongside assign, status, close)
- Marking unread closes the detail panel and returns focus to thread list
- Card immediately shows as unread (bold + dot) via OOB swap or list refresh
- No confirmation needed — instant, low-risk action
- No bulk "Mark all read" initially (Phase 5 context menu may add it)

### Claude's Discretion
- Keyboard shortcut for mark unread (e.g., 'U' key) — decide based on effort and existing keyboard nav
- Bulk "Mark all as read" — decide based on implementation effort vs UX value
- Whether Triage Queue gets unread badges or just My Inbox + Views
- Exact icon choice for mark unread button
- Loading/transition states during OOB swaps

</decisions>

<specifics>
## Specific Ideas

- "Replace New dot" approach: the blue dot currently means `thread.status == 'new'` — redefine it to mean "unread by current user". Thread status badge (New/Acknowledged/Closed chip) still shows separately.
- Gmail-like behavior: tab title count, instant mark-as-read on open, auto-unread on new replies, close panel on mark-unread
- Assignment = unread: when someone assigns a thread to you, it shows as unread in your inbox so you notice it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ThreadViewer` model (`apps/emails/models.py:257`): tracks ephemeral presence (who's viewing), separate from read state
- Thread card template (`templates/emails/_thread_card.html`): already has blue dot + bold logic for `status == 'new'` — swap condition to per-user unread
- `sidebar_counts` aggregate in `thread_list` view (`apps/emails/views.py:155`): already computes counts per view — extend with unread counts
- OOB swap pattern: thread card already supports `hx-swap-oob="outerHTML"` via `{% if oob %}` flag

### Established Patterns
- HTMX OOB swaps for updating cards after actions (card template has `oob` parameter)
- `sidebar_counts` dict passed to template context — add `unread_mine`, `unread_open`, etc.
- `ThreadReadState` model planned in Phase 1 with user, thread, read_at fields
- `SoftDeleteModel` base class — ThreadReadState should NOT use soft delete (it's ephemeral state)

### Integration Points
- `thread_detail` view: upsert ThreadReadState + include OOB card swap in response
- `assign_thread` view: reset ThreadReadState for new assignee
- `pipeline.py`: new emails already update `thread.last_message_at` — unread logic compares this against `read_at`
- `base.html` title block: add unread count prefix
- Sidebar template in `thread_list.html`: swap total counts for unread counts

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-read-unread-tracking*
*Context gathered: 2026-03-15*
