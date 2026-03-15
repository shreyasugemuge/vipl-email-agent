---
created: 2026-03-15T16:12:00.000Z
title: Settings needs better labeling and organizing across all tabs
area: ui
files:
  - templates/emails/settings.html
  - templates/emails/_settings_system_tab.html
  - templates/emails/_settings_pipeline_tab.html
  - templates/emails/_settings_notification_tab.html
---

## Problem

Settings page tabs (especially System) lack comprehensive labeling and organization. Config keys are shown with technical names, minimal descriptions, and inconsistent grouping. Most tabs are close but System tab needs the most work.

## Solution

- Add clear section headers grouping related settings (e.g., "Email Polling", "AI Triage", "Notifications", "SLA")
- Add help text / descriptions below each setting explaining what it does and valid values
- Organize System tab settings into logical groups instead of flat key-value list
- Ensure consistent labeling style across all tabs
