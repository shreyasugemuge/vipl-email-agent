---
created: 2026-03-15T11:30:00.000Z
title: Force poll should work in production mode
area: api
files:
  - apps/emails/views.py
---

## Problem

The force poll button in the dev inspector currently returns 403 in production mode (`if mode == "production": return JsonResponse({"error": "Cannot force poll in production mode"}, status=403)`). User wants it to work in production too — admin should be able to trigger an immediate poll cycle without waiting for the scheduler interval.

## Solution

Remove the production mode check. Keep admin-only auth. Add a confirmation step or rate limit (1 force poll per 60 seconds) to prevent accidental spam.
