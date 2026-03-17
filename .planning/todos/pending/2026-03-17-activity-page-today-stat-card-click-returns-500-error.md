---
created: 2026-03-17T16:03:34.000Z
title: Activity page Today stat card click returns 500 error
area: ui
files:
  - apps/emails/views/activity_views.py
  - templates/emails/activity.html
---

## Problem

On the Activity page (`/emails/activity/`), clicking the "Today" stat card (showing 206 events) triggers a 500 server error. The HTMX request fails — visible as "Request failed (500)" modal in the screenshot. Other stat cards (Total Events, Assignments, Status Changes) likely work fine. The Today card probably passes a date filter parameter that causes a query or view error on the backend.

## Solution

- SSH into VM and check logs: `sudo docker logs vipl-email-agent-web-1 --tail 50`
- The view likely has a filtering bug when `?period=today` or similar param is passed
- Check the activity view's queryset filtering for date-based filters
- Could be a timezone issue (IST vs UTC) or a missing field in the filter logic
- Fix the view, add a test for the today filter, deploy
