---
created: 2026-03-17T16:05:00.000Z
title: Activity page UX revamp — filtering by user, status, and navigation
area: ui
files:
  - apps/emails/views/activity_views.py
  - templates/emails/activity.html
---

## Problem

The Activity page is a flat chronological list of all events with too many filter pills (20+) but no structured navigation. Hard to answer practical questions like "what did Shreyas do today?" or "show me all status changes this week". The stat cards are clickable but the filtering UX is clunky — no user-based filtering, no date range picker, no grouped/tabbed view.

## Solution

- **Filter by user**: Dropdown or pill selector to filter activity by team member (who performed the action)
- **Filter by date**: Date range picker or quick presets (Today, This Week, Last 7 Days)
- **Group by thread**: Option to group related events under their thread instead of flat list
- **Reduce filter pill clutter**: Collapse into dropdown categories or use a secondary filter row
- **Pagination or infinite scroll**: Current page loads everything — add pagination for performance
- **Better stat card interaction**: Clicking a stat card should smoothly filter the list below, not trigger a separate request that 500s
- **Search**: Quick search across activity descriptions
- Consider the Reports page design as inspiration — it has a cleaner tab/chart layout
