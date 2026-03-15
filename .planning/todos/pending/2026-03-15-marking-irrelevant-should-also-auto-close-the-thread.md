---
created: 2026-03-15T22:52:00.000Z
title: Marking irrelevant should also auto-close the thread
area: backend
files:
  - apps/emails/views.py
---

## Problem

When a gatekeeper/admin marks a thread as "irrelevant", the thread gets the `irrelevant` status but isn't treated as closed. It still appears in open views and counts toward active thread metrics. Semantically, an irrelevant thread is done — it should be auto-closed so it leaves the active queue.

## Solution

In the `mark_irrelevant` view, after setting `status='irrelevant'`, also treat it as functionally closed — either by making `irrelevant` behave like `closed` in all queryset filters, or by setting both `status='irrelevant'` as a sub-state of closed. The simplest approach: update the view filters to exclude `irrelevant` from open views (same as `closed`), so irrelevant threads don't show in Triage Queue, My Inbox, or All Open.
