# Phase 3: Conversation UI - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current card-based email list with a three-panel conversation UI. Users browse and manage threads (not individual emails) in a layout with left sidebar (views/filters), center panel (thread list), and right panel (thread detail with full message history). All existing actions (assign, acknowledge, close, whitelist) move to thread-level.

Requirements: UI-01, UI-02, UI-03, UI-04, UI-05, INBOX-04

</domain>

<decisions>
## Implementation Decisions

### Three-panel layout
- Desktop: Sidebar 220px (fixed) + Thread List ~35% + Thread Detail ~65%
- Keep current sidebar width, maintain existing proportions from v2.0 layout
- Mobile: Thread list full-width, detail panel slides over list (same pattern as current). Sidebar via hamburger menu
- Stats bar removed — counts move inline into sidebar view labels (e.g., "Unassigned (12)")
- Sidebar content replaces current nav: quick-access views + inbox filter + nav links (Activity, Settings, Team)

### Thread list card design
- Compact 2-line cards for density (~15-20 threads visible)
  - Line 1: Sender name + time_ago + message count badge [N] + small assignee avatar (20px)
  - Line 2: Subject (truncated) + priority dot + status badge + inbox pill badge(s)
- SLA countdown on card only when breached or within 1 hour of breach — hidden otherwise
- Unread/new messages indicated by bold text + small colored dot (resets after viewing thread)
- Assignee shown as tiny avatar only — hover for name. Gray placeholder if unassigned

### Thread detail panel
- Stacked message cards in chronological order (oldest at top, newest at bottom)
- Each message card shows: sender email, time_ago, inbox badge, and email body (HTML-sanitized)
- Auto-scroll to newest message when opening a thread
- Sticky header bar at top: thread subject + status/priority/category badges + action buttons (assign, acknowledge, close, whitelist)
- Collapsible AI triage card below sticky header: shows summary, reasoning, draft reply, suggested assignee. Collapsed by default after first view. Uses latest triage from the thread
- Activity log events (assignment changes, status changes, reopens) appear inline between messages in chronological order — small, muted entries showing what happened and when

### View switching + inbox filter (UI-05, INBOX-04)
- Sidebar views: Unassigned, Mine, All Open, Closed — each with count badge
  - "All Open" = threads with status New or Acknowledged
  - Active view highlighted with sidebar accent
- Inbox filter: row of pill toggles below views — "All" | "info@" | "sales@" (single-select)
  - Persists across view changes
  - Filters thread list to threads received on selected inbox
- Search bar positioned above thread list (prominent, not in sidebar)
- Priority/category/status dropdowns in a collapsible "Filters" section in sidebar below inbox toggles
- Default landing view: All Open

### Claude's Discretion
- Exact color scheme for unread dot indicator
- Message card internal spacing and typography
- Collapsible AI card expand/collapse animation
- Empty state design for each view
- How thread sorting works (by last_message_at descending is assumed)
- Pagination style for thread list (infinite scroll vs traditional pagination)
- Transition animations between views

</decisions>

<specifics>
## Specific Ideas

- Layout should feel like Gmelius/Front — professional shared inbox, not a basic email list
- Activity events inline between messages create a full timeline of the thread's lifecycle
- Compact cards are key — the list should let you scan 15-20 threads without scrolling
- Inbox pill badges from Phase 2 appear on both thread cards and individual messages in detail

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `base.html` — sidebar structure (220px, dark #0f1117), top header, toast system, HTMX progress bar all reusable
- `_email_card.html` — card structure pattern, can be adapted to `_thread_card.html`
- `_email_detail.html` — detail panel structure, SLA bar, action bar patterns all reusable at thread level
- `email_tags.py` — `priority_base`, `status_base`, `priority_border`, `sla_color`, `sla_countdown`, `time_ago` all reusable
- `inbox_tags.py` — inbox pill badge template tags (from Phase 2) ready to use
- Custom Tailwind theme — Plus Jakarta Sans, plum palette (#c94476), `.card-hover`, `.card-selected`, `.nav-active`

### Established Patterns
- HTMX: `hx-get` → `hx-target="#detail-panel"` → `hx-swap="innerHTML"` for list-detail interaction
- OOB swaps: `hx-swap-oob="innerHTML"` for updating card + detail simultaneously on actions
- URL-based filter state with `hx-push-url="true"` — bookmarkable views
- nh3 HTML sanitization for email body content
- `_build_detail_context()` helper for assembling detail panel data
- Mobile: fixed panels with translate-x transforms, overlay for click-outside-to-close

### Integration Points
- `email_list` view → needs conversion to `thread_list` view querying Thread model
- `email_detail` view → needs conversion to `thread_detail` view loading all thread emails
- `assign_email_view` / `change_status_view` → operate on Thread instead of Email
- URL patterns → new thread-level endpoints or adapt existing `/emails/` routes
- Thread model (Phase 1) — has all needed fields: status, assigned_to, category, priority, last_message_at, message_count
- ActivityLog — already tracks events with ForeignKey to Email, needs thread-level grouping in display

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-conversation-ui*
*Context gathered: 2026-03-15*
