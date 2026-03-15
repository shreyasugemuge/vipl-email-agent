---
created: 2026-03-15T16:18:00.000Z
title: No read/unread marker visible on thread cards
area: ui
files:
  - templates/emails/_thread_card.html
  - apps/emails/views.py
---

## Problem

The read/unread visual indicators (bold text + blue dot) are not appearing on thread cards in production. The `is_unread` annotation may not be reaching the template, or the ThreadReadState rows haven't been created for existing threads after the v2.5.0 migration.

## Solution

- Check if `annotate_unread(qs, user)` is being called in `thread_list()` view
- Verify ThreadReadState rows exist for the logged-in user
- On fresh deploy with no ThreadReadState rows, convention is "no row = read" — so all threads appear read until user marks them unread or new emails arrive
- May need to seed ThreadReadState rows for existing threads, or flip convention to "no row = unread"
