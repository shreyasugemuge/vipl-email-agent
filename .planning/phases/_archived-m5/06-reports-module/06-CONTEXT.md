# Phase 6: Reports Module - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Dedicated analytics dashboard for the manager. Shows email volume, response times, SLA compliance, and team workload with interactive charts. Admin-only access. New "Reports" nav item in sidebar. Chart.js 4.x via CDN.

</domain>

<decisions>
## Implementation Decisions

### Dashboard layout
- 4 tabbed sections: Overview / Volume / Team / SLA
- Global date range picker at top of page (affects all tabs)
- Overview tab has 4 KPI summary cards at top, then charts below
- Admin-only: Reports nav item hidden for non-admin users

### KPI cards (Overview tab)
- Total emails received (in selected period)
- Avg response time (receipt → first acknowledgment)
- SLA compliance % (met vs breached)
- Open threads (real-time count, not period-based)

### Charts by tab
- **Overview**: KPI cards + summary chart (Claude decides type)
- **Volume**: Email volume chart (Claude decides: bar vs line vs stacked bar, daily granularity, color by inbox)
- **Team**: Handle count + avg response time per person (side-by-side bars or table)
- **SLA**: Donut chart for current compliance % AND trend line for compliance over time. Below: table of recent SLA breaches with thread subject, deadline, actual time.

### Date range + filtering
- Presets: Today, This Week, This Month, Last 7/30/90 days, Quarter, Year, Custom range
- Custom: start date + end date pickers
- Additional filters (apply globally across tabs):
  - By inbox (info@ / sales@)
  - By category
  - By team member
- Default: Last 30 days, all inboxes, all categories, all members

### Empty state
- Show charts with zero data (render normally, flat zero lines/bars)
- Charts are always present — no placeholder messages

### Access control
- Admin-only: non-admin users don't see Reports in sidebar navigation
- No per-member scoped view (deferred)

### Claude's Discretion
- Exact chart configurations (colors, legends, tooltips, animation)
- Volume chart type (bar/line/stacked — pick most informative)
- Chart.js options and responsive settings
- Tab switching mechanism (HTMX vs JS-only)
- Pre-aggregation strategy for query performance on PG 12.3
- Whether to use a new Django app (`apps/reports/`) or keep views in `apps/emails/`

</decisions>

<specifics>
## Specific Ideas

- Research said to use pre-aggregated summary table for performance — PG 12.3 on 2-vCPU VM can't handle real-time GROUP BY on growing tables
- Chart.js 4.x via CDN with SRI hash (no npm, no build step)
- Destroy Chart.js instances on HTMX navigation to prevent memory leaks
- KPI cards should match the visual style of existing stat cards (activity log, team page)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- Stat card HTML/CSS pattern from `activity_log.html` and `team.html` — reuse for KPI cards
- Tab switching pattern from `settings.html` — JS-based tab toggle with description text
- `updateActiveStates()` in `base.html` — extend for Reports nav active state
- Existing aggregate queries in `views.py` — `sidebar_counts`, `dash_stats` use Django ORM aggregation

### Established Patterns
- HTMX for partial page updates (tab content could use `hx-get` for lazy loading)
- Template block structure: `{% block content %}`, `{% block extra_js %}`
- CDN scripts loaded in `<head>` of base.html (HTMX pattern)
- Dark sidebar nav with nav-active class for current page

### Integration Points
- `base.html` sidebar: add "Reports" nav link with chart icon (admin-only via `{% if is_admin %}`)
- `urls.py`: new report view paths
- `views.py`: new `reports_view` function with aggregate queries
- New template: `templates/emails/reports.html` (or `templates/reports/` if new app)

</code_context>

<deferred>
## Deferred Ideas

- CSV export for any report — future milestone
- Scheduled email reports (daily/weekly digest) — future milestone
- Per-member scoped reports view — future milestone
- Category breakdown analytics — future milestone

</deferred>

---

*Phase: 06-reports-module*
*Context gathered: 2026-03-15*
