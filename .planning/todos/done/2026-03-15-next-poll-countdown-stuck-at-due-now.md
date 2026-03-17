---
created: 2026-03-15T20:25:00.000Z
title: Poll timer keeps breaking — stuck at "Due now"
area: ui
files:
  - apps/emails/services/pipeline.py:543-551
  - apps/emails/services/pipeline.py:602-613
  - templates/emails/inspect.html:252-291
  - apps/emails/views/pages.py:559
---

## Problem

The "Next poll in" countdown in the dev inspector works initially but breaks later — gets stuck showing "Due now" with an increasingly stale "Last poll: Xm ago" even though polls are running every 5 minutes successfully (visible in the poll history table).

**Root cause found**: `last_poll_epoch` in SystemConfig is only updated when emails are found (pipeline.py:602-613). When `not new_emails`, the function returns early at line 551 without updating the epoch. So the epoch stays frozen at the time of the last poll that actually found an email.

The JS countdown (inspect.html:252-291) uses `window.__pollLastEpoch` set from the Django template at page load. It calculates `remaining = intervalSec - (now - epoch)`. Once the epoch is stale enough that `remaining <= 0`, it shows "Due now" permanently.

**Additional confusion**: the timer conflates "last poll epoch" (backend concept for deploy-safety skip) with "when did the scheduler last run" (what the user wants to see on the inspector). These are different — the epoch intentionally only updates when emails arrive (to avoid re-processing on restart), but the UI countdown should reflect the actual last poll time.

## Solution

Move `last_poll_epoch` update to happen on EVERY successful poll, not just when emails are found. The early-return path at line 543-551 needs to also persist the epoch. Alternatively, use `PollLog.started_at` from the most recent log entry for the UI countdown instead of `last_poll_epoch`, since PollLog is always created regardless of email count.
