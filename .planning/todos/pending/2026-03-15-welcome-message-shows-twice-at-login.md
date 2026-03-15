---
created: 2026-03-15T16:12:00.000Z
title: Welcome message shows twice at login
area: ui
files:
  - templates/emails/thread_list.html
  - templates/base.html
---

## Problem

The welcome banner/message appears twice when a user logs in. Likely the banner component renders in both the base template and the thread list template, or the localStorage/sessionStorage dismiss logic isn't working correctly on first load.

## Solution

Debug the welcome banner rendering — ensure it only renders once. Check the `localStorage`/`sessionStorage` dismiss flags and the template include hierarchy.
