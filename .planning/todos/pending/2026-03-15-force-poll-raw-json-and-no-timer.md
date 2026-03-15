---
created: 2026-03-15T16:20:00.000Z
title: Dev inspector poll UX — timer, force poll, and history fixes
area: ui
files:
  - apps/emails/views.py
  - templates/emails/inspect.html
  - apps/emails/models.py
---

## Problem

1. Force poll navigates to raw JSON (`/emails/inspect/force-poll/`) instead of staying on inspector page
2. Poll countdown timer doesn't tick live — shows static "Due now" / "Last poll: 8m ago"
3. Force poll doesn't update `last_poll_epoch` so timer doesn't reset after force poll
4. Poll history doesn't show "0 new emails" for empty cycles — admin can't tell if system is working or broken
5. "Last poll" display doesn't reflect force polls, only scheduler polls

## Solution

1. Force poll: HTMX POST with inline result display, not page navigation
2. JS countdown timer ticking every second based on `last_poll_epoch + poll_interval`
3. Force poll endpoint must update `last_poll_epoch` in SystemConfig
4. PollLog entries should record `emails_found: 0` for empty cycles
5. After force poll, refresh timer widget via HTMX OOB swap
