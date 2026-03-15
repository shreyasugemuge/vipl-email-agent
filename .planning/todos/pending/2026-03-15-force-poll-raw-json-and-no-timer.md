---
created: 2026-03-15T16:20:00.000Z
title: Force poll shows raw JSON and poll timer not counting down
area: ui
files:
  - apps/emails/views.py
  - templates/emails/inspect.html
---

## Problem

1. Force poll button navigates to `/emails/inspect/force-poll/` and shows raw JSON response (`{"status": "ok", "output": "Running single poll cycle...\nSingle poll cycle complete.\n", "errors": ""}`) instead of staying on the inspector page with a nice result display.
2. Poll countdown timer says "Due now" / "Last poll: 8m ago" but doesn't count down live — should show a ticking countdown to next poll.

## Solution

1. Force poll should be an HTMX POST that updates a result area on the inspector page, not a page navigation to raw JSON
2. Add JS countdown timer that ticks every second based on `last_poll_epoch + poll_interval`
