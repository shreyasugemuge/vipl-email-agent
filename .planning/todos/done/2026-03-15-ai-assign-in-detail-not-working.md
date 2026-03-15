---
created: 2026-03-15T16:35:00.000Z
title: AI Assign button in detail card not working
area: ui
files:
  - templates/emails/_thread_detail.html
  - apps/emails/views.py
---

## Problem

The AI suggested assignee / auto-assign button in the thread detail panel is not working when clicked. Either the HTMX POST isn't firing, the endpoint is returning an error, or the suggestion bar isn't rendering correctly.

## Solution

- Check if `show_suggestion_bar` context variable is being set correctly in `_build_thread_detail_context`
- Verify `accept_thread_suggestion` and `reject_thread_suggestion` views handle the POST
- Check browser console for JS/HTMX errors on click
- Verify URL patterns are correct for thread-level accept/reject
