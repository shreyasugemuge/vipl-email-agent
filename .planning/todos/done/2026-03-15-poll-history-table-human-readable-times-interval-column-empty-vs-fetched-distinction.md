---
created: 2026-03-15T16:36:51.934Z
title: Poll history table — human readable times, interval column, empty vs fetched distinction
area: ui
files:
  - templates/emails/inspect.html
  - apps/emails/views.py
  - apps/emails/models.py
---

## Problem

The poll history table in the dev inspector (`/emails/inspect/`) has UX issues:

1. **Timestamps not human readable** — shows raw ISO/epoch format instead of friendly "3 min ago" or "16:34" style
2. **No interval column** — can't see the gap between consecutive polls at a glance (useful for diagnosing scheduler health)
3. **Empty polls and fetched polls look the same** — no visual distinction between polls that found 0 new emails vs polls that actually fetched emails. Admin can't tell if the system is working but inbox is quiet, or if something is broken.

## Solution

1. Format poll timestamps as human-readable relative time ("2m ago") or absolute time ("16:34") — whichever is more appropriate
2. Add an "Interval" column showing time since previous poll (e.g., "5m 12s")
3. Visually distinguish empty polls (0 emails found) from fetched polls — e.g., muted/gray row for empty, normal for fetched; or a status icon/badge
