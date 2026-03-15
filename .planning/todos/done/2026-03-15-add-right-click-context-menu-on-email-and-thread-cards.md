---
created: 2026-03-15T11:09:00.000Z
title: Add right-click context menu on email and thread cards
area: ui
files:
  - templates/emails/_thread_card.html
  - templates/emails/_email_card.html
  - templates/base.html
---

## Problem

No right-click context menu on thread/email cards. Users must open the detail panel to perform any action. Quick actions like mark read/unread, assign, change status, or flag require extra clicks.

## Solution

1. **Custom context menu component**: Add a reusable `<div id="card-context-menu">` in `base.html` (hidden by default, positioned absolutely).

2. **Trigger**: `oncontextmenu` handler on thread/email cards:
   - Prevent default browser menu
   - Position menu at cursor
   - Populate with card-specific actions via data attributes

3. **Menu options** (role-aware):
   - Mark as Read / Mark as Unread (depends on read/unread todo)
   - Assign to... (admin only — submenu with team members)
   - Claim (if unassigned and user has visibility)
   - Acknowledge / Close (status transitions)
   - Mark as Spam / Not Spam
   - Whitelist Sender (admin only)
   - Open in Gmail (external link)
   - Copy Subject

4. **Implementation**:
   - Each card gets `data-thread-id` or `data-email-id` + `data-status` + `data-assigned` attributes
   - JS builds menu dynamically based on attributes + user role (passed via `data-is-admin` on body)
   - Actions fire HTMX POST requests to existing endpoints
   - Menu closes on click outside, Escape, or scroll

5. **Mobile**: Long-press triggers same menu (touchstart with 500ms delay)

6. **Styling**: Dark dropdown (matches sidebar theme), subtle shadow, 200ms fade-in, max-width 220px
