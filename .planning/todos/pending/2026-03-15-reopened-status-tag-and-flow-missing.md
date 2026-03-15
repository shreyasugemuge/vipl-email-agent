---
created: 2026-03-15T16:25:00.000Z
title: Reopened status tag and flow missing from UI
area: ui
files:
  - templates/emails/_thread_detail.html
  - templates/emails/_thread_card.html
  - apps/emails/models.py
  - apps/emails/views.py
---

## Problem

The "Reopened" status was built and confirmed working in earlier phases, but the tag/badge and the flow to reopen a closed thread are not visible in the current UI. A closed thread should be reopenable (e.g., when a new email arrives in a closed thread, or via manual action), and the "Reopened" status badge should display on cards and detail panels.

## Solution

- Check if `REOPENED` is in the Thread status choices (`models.py`)
- Verify the status badge renders "Reopened" with appropriate color in templates
- Ensure there's a UI path to reopen: button in detail panel, context menu option, or automatic on new email in closed thread
- Check if pipeline auto-reopens closed threads when new emails arrive
