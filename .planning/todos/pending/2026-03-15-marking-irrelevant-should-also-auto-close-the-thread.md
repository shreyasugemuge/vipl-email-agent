---
created: 2026-03-15T22:52:00.000Z
title: Marking irrelevant should also auto-close the thread
area: backend
files:
  - apps/emails/views.py
---

## Problem

When a gatekeeper/admin marks a thread as "irrelevant", the thread gets the `irrelevant` status but isn't treated as closed. It still appears in open views and counts toward active thread metrics. Irrelevant threads should behave exactly like closed threads — excluded from open counts, and visible under the Closed tab.

## Solution

Treat `irrelevant` as a closed state everywhere:

1. **Sidebar counts**: Add `irrelevant` alongside `closed` in the exclusion filter for open views (`open_q` should exclude both `closed` and `irrelevant`)
2. **Closed tab**: `view=closed` filter should match `status__in=["closed", "irrelevant"]` so irrelevant threads appear under the Closed tab
3. **Sidebar "Closed" count**: Include `irrelevant` in the closed count aggregate
4. **Stat cards**: Exclude `irrelevant` from Total/Unassigned/Urgent/New counts (same as closed)
5. **Unread counts**: Irrelevant threads excluded from unread badges in open views

In short: everywhere the code checks `status="closed"` or filters open statuses (`new`, `acknowledged`, `reopened`), `irrelevant` should be grouped with `closed`.
