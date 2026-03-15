---
created: 2026-03-15T11:12:00.000Z
title: MIS and reports module
area: ui
files:
  - apps/emails/views.py
  - apps/emails/urls.py
  - templates/emails/
---

## Problem

No MIS (Management Information System) or reports section exists. The current activity log has basic stats (total events, today, assignments, status changes) but no proper reporting:
- No daily/weekly/monthly email volume reports
- No response time analytics (time to first ack, time to close)
- No team performance metrics (emails per person, SLA compliance)
- No category/inbox breakdown charts
- No exportable reports (CSV/PDF)
- No trend visualizations

Worktree branch `feature/analytics-dashboard` already exists at `../vipl-email-agent-analytics`.

## Solution

### Full reports module — new nav section "Reports" in sidebar

1. **Dashboard overview**:
   - Email volume chart (daily/weekly, bar chart)
   - Response time trends (line chart)
   - SLA compliance rate (gauge/donut)
   - Current queue depth (real-time counter)

2. **Team performance**:
   - Emails handled per team member (bar chart)
   - Average response time per person
   - SLA breach rate per person
   - Workload distribution (pie chart)

3. **Category & inbox analytics**:
   - Volume by category (stacked bar)
   - Volume by inbox (info@ vs sales@)
   - Spam filter hit rate
   - AI triage accuracy (from user corrections)

4. **SLA reports**:
   - SLA compliance by priority
   - Breach count and details
   - Time to acknowledge / time to respond distributions

5. **Export**:
   - CSV export for any report
   - Date range picker
   - Scheduled email reports (ties into EOD reporter)

6. **Implementation**:
   - Work in existing worktree: `../vipl-email-agent-analytics` on `feature/analytics-dashboard`
   - Charts: Chart.js via CDN (no build step, matches HTMX/CDN pattern)
   - Django views with aggregate queries
   - New nav item in sidebar: "Reports" (chart icon)
