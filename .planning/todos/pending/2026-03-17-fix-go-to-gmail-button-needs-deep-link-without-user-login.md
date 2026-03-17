---
created: 2026-03-17T16:02:30.000Z
title: Fix Go to Gmail button — needs deep link without user login
area: ui
files:
  - templates/emails/thread_detail.html
  - apps/emails/models.py
---

## Problem

The "Go to Gmail" button on thread detail panel doesn't work properly. Users viewing emails in the triage dashboard are not necessarily logged into the Gmail account that received the email (emails come from info@ and sales@ shared inboxes via domain-wide delegation). Clicking the button either does nothing or opens Gmail in a context where the user can't see the email.

## Solution

- The Gmail message ID is stored on the Email model — construct a proper Gmail deep link: `https://mail.google.com/mail/u/?authuser=<inbox>/#inbox/<message_id>`
- Include the `authuser` param so it targets the correct inbox account
- If the user isn't logged into that Google account, Gmail will prompt them — this is expected behavior
- Consider showing the source inbox (info@ or sales@) next to the button so users know which account context is needed
- Alternative: remove the button entirely if it's not useful (users may not have access to shared inbox directly)
