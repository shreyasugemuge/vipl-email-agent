---
created: 2026-03-15T20:25:00.000Z
title: Next poll countdown stuck at due now
area: ui
files:
  - templates/emails/inspect.html
  - apps/emails/views.py
---

## Problem

The "Next poll in" countdown in the dev inspector frequently shows "Due now" and stays stuck there instead of counting down to the next poll cycle. This happens often, suggesting the countdown logic or the poll interval calculation is not updating correctly.

Possible causes:
- The countdown JS timer isn't resetting after a poll completes
- The server-side "next poll" timestamp isn't being recalculated properly
- The poll interval config value isn't being read correctly for the countdown

## Solution

TBD — investigate whether this is a frontend JS countdown bug or a backend issue with the next-poll timestamp calculation. Check the inspector's countdown timer logic and the poll epoch/interval values being passed to the template.
