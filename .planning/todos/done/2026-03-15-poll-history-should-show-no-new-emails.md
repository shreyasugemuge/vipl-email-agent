---
created: 2026-03-15T16:20:00.000Z
title: Poll history should show "no new emails" result
area: ui
files:
  - templates/emails/inspect.html
  - apps/emails/models.py
---

## Problem

When a poll cycle completes but finds no new emails, the poll history table doesn't indicate this. "Last poll: 8m ago" with "Due now" implies something's wrong, but it's normal — there were just no new emails. The poll history below should show each poll result including "0 new emails" so the admin knows the system is working.

## Solution

- PollLog entries should record `emails_found: 0` when a cycle completes with no new messages
- Poll history table should display "0 new emails" for empty cycles
- The countdown widget should show "No new emails" under the last poll time when the last cycle was empty
