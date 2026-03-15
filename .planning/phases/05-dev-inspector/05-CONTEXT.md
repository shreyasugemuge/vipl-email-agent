# Phase M6-P5: Dev Inspector - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Dev inspector provides accurate real-time poll status and readable history. Polishes existing inspect page — poll timer, force poll, and history table. No new pages or features.

</domain>

<decisions>
## Implementation Decisions

### Force Poll
- Show inline result banner below button after poll completes: "Poll complete: 3 found, 1 spam, 245ms" — auto-dismiss after 5s
- History table also refreshes after force poll (without full page reload)
- Force Poll works in ALL modes (not just dev/off), admin only
- Timer does NOT reset after force poll — force poll is "extra", doesn't affect scheduled poll cycle
- Button shows "Polling..." while in progress, re-enables on completion

### Poll History Table
- Add "Interval" column showing time since previous poll (e.g., "5m 02s")
- Highlight gaps > 2x interval in amber (suggests missed polls or scheduler issues)
- Empty polls (found=0) shown as dimmed rows — still visible but muted text color
- Limit to last 25 polls by default (~2 hours at 5min interval)
- Timestamp format: 12-hour India time with AM/PM, both absolute and relative inline (e.g., "2:30:02 PM (5m ago)")
- Retain error/failure rows with full visibility (not dimmed) — key failures must be obvious

### Poll Timer
- No changes needed — existing countdown timer works correctly
- Timer shows live seconds, turns amber when < 60s, shows "Due now" when overdue

### Claude's Discretion
- Whether to use HTMX or vanilla JS for the inline result banner and table refresh
- Exact banner styling (color, animation)
- How to calculate interval server-side vs client-side
- Poll history pagination or "Show more" if user wants beyond 25

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `inspect.html` — Full standalone page with dark theme, stat cards, countdown JS, poll history table
- `PollLog` model (models.py:494) — already logs started_at, status, emails_found, emails_processed, spam_filtered, duration_ms, error_message
- `inspect` view (views.py:2369) — serves page with stats, poll_logs, pipeline_stats context
- `force_poll` view (views.py:2433) — triggers single poll, currently redirects back to inspect page
- Countdown JS (inspect.html:111-145) — uses `last_poll_epoch` and `poll_interval_minutes`

### Established Patterns
- Inspector is a standalone HTML page (not using base.html/HTMX) — inline styles, self-contained
- Force poll is a standard form POST with redirect
- Poll logs queried with `PollLog.objects.order_by('-started_at')`
- Stats computed from PollLog aggregation (last 7 days)

### Integration Points
- `force_poll` view needs to return JSON or partial HTML instead of redirect (for inline banner)
- Poll history table section could be extracted to a partial for HTMX refresh
- `last_poll_epoch` comes from SystemConfig

</code_context>

<specifics>
## Specific Ideas

- Timestamp format: "2:30:02 PM (5m ago)" — India 12-hour with AM/PM, relative time inline
- Amber highlight for poll gaps > 2x interval — makes scheduler issues immediately visible
- Key failures and errors must remain prominent (not dimmed) — only empty successful polls get dimmed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-dev-inspector*
*Context gathered: 2026-03-15*
