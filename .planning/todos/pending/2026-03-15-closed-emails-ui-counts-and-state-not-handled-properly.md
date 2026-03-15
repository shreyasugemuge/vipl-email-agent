---
created: 2026-03-15T20:22:00.000Z
title: Closed emails UI counts and state not handled properly
area: ui
files:
  - templates/emails/thread_list.html
  - templates/emails/_thread_card.html
  - apps/emails/views.py
---

## Problem

The UI/UX doesn't handle closed emails properly across several dimensions:
- Sidebar counts may not update correctly when threads are closed/reopened
- Stat cards (Total, Unassigned, Urgent, New) don't reflect closed thread changes
- Thread cards in the list may not visually distinguish closed threads well enough
- The "Closed" view count in sidebar may be stale after status changes
- Closing a thread from the detail panel doesn't update the list or counts without refresh

## Solution

1. Ensure close/reopen status change endpoints return OOB swaps for sidebar counts and stat cards
2. Add visual distinction for closed thread cards (e.g., muted/greyed styling)
3. Verify the "Closed" sidebar view count updates on status transitions
4. Consider auto-removing closed threads from "All Open" view via HTMX swap
