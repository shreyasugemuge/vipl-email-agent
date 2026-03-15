---
created: 2026-03-15T16:30:00.000Z
title: Sidebar should show version name instead of "Online"
area: ui
files:
  - templates/base.html
---

## Problem

The sidebar user section shows "Online" with a green dot under the user's name. Should show the app version (e.g., "v2.5.3") instead — more useful info, and "Online" is obvious since the user is logged in.

## Solution

Replace "Online" text with the app version from settings or a template context variable. Keep the green dot if desired.
