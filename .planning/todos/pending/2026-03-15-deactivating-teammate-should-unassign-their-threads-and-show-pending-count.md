---
created: 2026-03-15T22:50:00.000Z
title: Deactivating teammate should unassign their threads and show pending count
area: backend
files:
  - apps/accounts/views.py
  - apps/emails/services/assignment.py
  - templates/accounts/team.html
  - templates/accounts/_user_row.html
---

## Problem

When an admin deactivates a team member (sets `is_active=False` from the Team page), the system doesn't handle their assigned work:

1. **Threads stay assigned** to the deactivated user — they become invisible/stuck since no one can act on them
2. **No warning** about pending work — admin doesn't know how many open threads the member has before deactivating
3. **No cascade cleanup** — the deactivated user should be removed from:
   - All open thread assignments (set `assigned_to=None`, status back to `new`)
   - AssignmentRule entries (so auto-assign doesn't route to them)
   - Any active ThreadViewer records
4. **No dynamic refresh** — after deactivation, the team list and any open thread cards showing that assignee don't update

## Solution

1. Before deactivation, show a confirmation with pending thread count: "This user has X open threads assigned. Deactivating will unassign them all."
2. On deactivation:
   - Bulk update all their non-closed threads: `assigned_to=None`, `status='new'`
   - Log ActivityLog entries for each unassignment
   - Remove from AssignmentRule entries
   - Clear ThreadViewer records
3. Return HTMX response that refreshes the team table row
4. Consider a Chat notification: "User X was deactivated. Y threads returned to triage queue."
