---
created: 2026-03-15T22:17:10.057Z
title: Activity page fully broken after UI revamp
area: ui
files:
  - templates/emails/activity_log.html
  - templates/emails/_activity_feed.html
---

## Problem

After the v2.6.0 UI revamp (pxl→vipl variable rename, dark/light theme conversion), clicking into the Activity page from the sidebar results in a fully broken page. The activity log and activity feed templates were converted by an agent during the UI revamp and may have broken template syntax, missing CSS variables, or incorrect class references.

## Solution

Debug the activity page — load it in browser, check for Django template errors or broken layout. Likely causes:
- Broken template tag or variable reference from the bulk conversion
- Missing or mismatched CSS variable references
- Incorrect nav-active class preventing sidebar highlighting
- Hardcoded colors that didn't get converted properly
