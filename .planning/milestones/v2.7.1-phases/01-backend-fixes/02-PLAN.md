---
phase: 1
plan: 2
title: Deactivate teammate cascade
wave: 1
depends_on: []
requirements: [BUG-02]
files_modified:
  - apps/accounts/views.py
  - apps/accounts/tests/test_team.py
autonomous: true
---

# Plan 02: Deactivate teammate cascade

## Objective

When deactivating a user, unassign all their open threads, remove their AssignmentRules, clear ThreadViewers, and log activity entries.

## Tasks

<task id="1">
<title>Add cascade logic to toggle_active view</title>
<read_first>
- apps/accounts/views.py (toggle_active function, line ~99)
- apps/emails/models.py (Thread, AssignmentRule, ThreadViewer, ActivityLog)
</read_first>
<action>
In `toggle_active` (apps/accounts/views.py), after `target.is_active = not target.is_active` and `target.save()`:

If deactivating (target.is_active is now False):

1. Import Thread, AssignmentRule, ThreadViewer, ActivityLog from apps.emails.models
2. Find open threads: `open_threads = Thread.objects.filter(assigned_to=target, status__in=["new", "acknowledged", "reopened"])`
3. Count for response: `thread_count = open_threads.count()`
4. For each thread: create ActivityLog entry with action="unassigned", user=request.user, detail=f"User {target.get_full_name()} deactivated", old_value=target.get_full_name(), new_value=""
5. Bulk update: `open_threads.update(assigned_to=None, assigned_by=None, status="new")`
6. Remove assignment rules: `AssignmentRule.objects.filter(assignee=target).delete()`
7. Clear viewers: `ThreadViewer.objects.filter(user=target).delete()`
</action>
<acceptance_criteria>
- `grep -n 'AssignmentRule' apps/accounts/views.py` returns at least 1 match
- `grep -n 'ThreadViewer' apps/accounts/views.py` returns at least 1 match
- `grep -n 'open_threads' apps/accounts/views.py` returns at least 1 match
- Test: deactivating user with assigned threads → threads become unassigned with status "new"
- Test: deactivating user removes their AssignmentRule entries
</acceptance_criteria>
</task>

## Verification

- Deactivating user with 3 assigned threads → all 3 become unassigned, status=new
- AssignmentRules for that user deleted
- ThreadViewers for that user deleted
- ActivityLog entries created for each unassignment

## must_haves

- open threads unassigned on deactivation
- assignment rules removed
- activity log entries created
