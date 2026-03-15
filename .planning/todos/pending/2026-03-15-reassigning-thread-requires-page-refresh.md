---
created: 2026-03-15T20:21:33.753Z
title: Reassigning thread requires page refresh
area: ui
files:
  - templates/emails/_thread_card.html
  - templates/emails/_thread_detail.html
  - apps/emails/views.py
---

## Problem

When a thread is reassigned (via the assign dropdown or AI suggestion accept), the change doesn't reflect everywhere on the page without a full refresh. The thread card in the list, sidebar counts, stat cards, and detail panel assignee avatar may show stale data after reassignment.

This is because the HTMX OOB swap for the thread card updates the card, but sidebar counts, stat cards, and other panels that reference the assignee aren't refreshed in the same response.

## Solution

Ensure the assign/reassign endpoints return OOB swaps for:
- The thread card itself (already done)
- Sidebar counts (unassigned count changes)
- Stat cards (unassigned count changes)
- Detail panel assignee section (if open)

Alternatively, trigger a lightweight HTMX re-fetch of the sidebar counts and stat bar after assignment actions.
