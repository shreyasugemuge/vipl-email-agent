---
created: 2026-03-15T10:33:57.505Z
title: Redesign activity page with intuitive sections
area: ui
files:
  - templates/emails/activity_log.html
  - apps/emails/views.py
---

## Problem

The activity page (`/emails/activity/`) currently shows a flat chronological list of all assignment and status change events. This makes it hard to scan and extract meaningful insights. Users need better visual organization — grouped sections (e.g., by date, by type, by email/thread), subsections for related events, and a clearer data hierarchy so the page feels like an actionable dashboard rather than a raw log dump.

## Solution

- Group activity entries by date (Today / Yesterday / This Week / Older)
- Within each date group, cluster related events (e.g., all actions on the same email/thread together)
- Add section headers with summary counts (e.g., "Today — 12 actions")
- Consider subsections by event type: Assignments, Status Changes, Notes
- Better visual hierarchy: icons per event type, user avatars, timestamps as relative ("2h ago")
- Optional filters: by user, by event type, by email/thread
