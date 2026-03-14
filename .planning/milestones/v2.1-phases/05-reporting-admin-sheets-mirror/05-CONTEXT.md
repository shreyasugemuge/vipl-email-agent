# Phase 5: Reporting + Admin + Sheets Mirror - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Daily EOD reporting from PostgreSQL (email + Chat), admin self-service for inbox management and full SystemConfig editing from the dashboard, and Google Sheets read-only sync mirror for legacy quick lookups. No new email processing logic, no new assignment features, no new SLA rules.

</domain>

<decisions>
## Implementation Decisions

### EOD Report Content + Delivery
- Stats include v1 parity PLUS SLA metrics: total emails today, by priority/category breakdown, open/unresolved count, response time averages, SLA breach count, worst overdue emails, avg time-to-acknowledge, avg time-to-respond
- Delivery: HTML email to configured recipients + Chat card to webhook (same as v1)
- Timing: 7 PM IST daily, with startup catch-up during business hours (deduplicated within 10 min, same as v1)
- Recipients: comma-separated email list in SystemConfig key `eod_recipients`, editable from Settings page
- Feature flags: respects `eod_email_enabled` (email) and `chat_notifications_enabled` (Chat) — both already seeded
- Reference: v1's `agent/eod_reporter.py` and `templates/eod_email.html` for format/structure

### Inbox Management UI
- Lives as a 4th tab ("Inboxes") on the existing Settings page at `/emails/settings/`
- Shows list of monitored email addresses with delete button each + input field to add new one
- Changes take effect on next poll cycle (no validation against Gmail API — if it fails to poll, pipeline logs warning and skips)
- Reads/writes the `monitored_inboxes` SystemConfig key (comma-separated string, already exists)
- Same HTMX pattern as the existing Rules/Visibility/SLA tabs

### Sheets Sync Mirror
- Columns: Date, From, Subject, Inbox, Category, Priority, Assignee, Status, SLA Deadline (core fields, no AI summary)
- Sync strategy: append new emails as rows + update existing rows on status/assignee change (match by message_id)
- Sync frequency: after each pipeline poll cycle (every 5 min), sync changed/new emails
- Target: same Google Sheet as v1 (GOOGLE_SHEET_ID env var), add a new "v2 Mirror" tab
- Service account already has Sheets access (domain-wide delegation scopes include `spreadsheets`)
- Reference: v1's `agent/sheet_logger.py` for Sheets API patterns
- Error handling: fire-and-forget (log warning on Sheets API failure, never block pipeline)

### Settings Page Expansion
- Full SystemConfig editor as a new tab (5th tab: "Config" or "System")
- Shows ALL SystemConfig keys grouped by category (notifications, polling, business_hours, etc.)
- Inline edit with save button per group — HTMX POST to save endpoint
- Edit existing keys only — no adding/deleting keys from the UI (use Django admin for that)
- Value type displayed but not changeable (prevents type mismatches)
- Inboxes tab is separate (has its own add/remove UI rather than just a text field)

### Claude's Discretion
- EOD email HTML template design (can reference v1's `templates/eod_email.html`)
- EOD Chat card layout (Cards v2 format, can reference existing breach summary card)
- Sheets sync implementation details (batch vs row-by-row, caching strategy)
- Config editor visual design within the existing settings page style
- Whether to add a "last synced" indicator for Sheets status
- Scheduler job organization (new jobs for EOD + Sheets sync)

</decisions>

<specifics>
## Specific Ideas

- v1's EOD reporter is proven and liked by the team — port the concept, enhance with SLA metrics from the new database
- The team uses the Google Sheet for quick "who has what" lookups — keep it as a convenience mirror, not a source of truth
- Settings page should eventually replace Django admin for all day-to-day config — Phase 5 is the step toward that

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/emails/services/chat_notifier.py`: Already has Cards v2 format, quiet hours check, `notify_breach_summary()` pattern reusable for EOD card
- `apps/core/models.py`: SystemConfig with `get()`, `get_all_by_category()`, typed casting — ready for config editor
- `templates/emails/settings.html`: Tab-based settings page with HTMX — extend with new tabs
- `apps/emails/views.py`: `settings_view` + `settings_*_save` pattern — reuse for new tabs
- `agent/eod_reporter.py`: v1 EOD reporter with Jinja2 HTML template + Chat card
- `agent/sheet_logger.py`: v1 Sheets logger with gspread patterns
- `apps/emails/services/state.py`: EOD dedup state manager (already ported from v1)
- `templates/eod_email.html`: v1 Jinja2 template for EOD email (reference for v2 Django template)

### Established Patterns
- Service layer: views call service functions, services handle ORM + external calls
- HTMX tabs: each tab has a partial template + save endpoint + HTMX POST
- Fire-and-forget notifications: try/except around all external calls (Chat, email, Sheets)
- Scheduler jobs: registered in `run_scheduler.py` with APScheduler intervals/crons
- SystemConfig: runtime config reads via `SystemConfig.get(key, default)`

### Integration Points
- `run_scheduler.py`: Add EOD job (CronTrigger 19:00 IST) + Sheets sync job (after poll cycle or separate interval)
- `pipeline.py`: Hook Sheets sync after `save_email_to_db()` or as a post-pipeline step
- `settings.html`: Add 2 new tab buttons + partial templates
- `urls.py`: Add routes for new settings tabs + save endpoints
- `views.py`: Add view functions for Inboxes tab, Config editor tab, and their save endpoints

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-reporting-admin-sheets-mirror*
*Context gathered: 2026-03-12*
