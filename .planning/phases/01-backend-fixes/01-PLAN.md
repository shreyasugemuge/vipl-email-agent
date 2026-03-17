---
phase: 1
plan: 1
title: Treat irrelevant as closed everywhere
wave: 1
depends_on: []
requirements: [BUG-01]
files_modified:
  - apps/emails/views.py
autonomous: true
---

# Plan 01: Treat irrelevant as closed everywhere

## Objective

Make `irrelevant` status behave identically to `closed` in all queryset filters — excluded from open views, included in Closed tab, excluded from unread/stat counts.

## Tasks

<task id="1">
<title>Update all open-status filters to exclude irrelevant</title>
<read_first>
- apps/emails/views.py (lines 160-320 for view filters, sidebar counts, stat cards)
</read_first>
<action>
In `thread_list` view (apps/emails/views.py):

1. Every `status__in=["new", "acknowledged", "reopened"]` filter already excludes closed and irrelevant — no change needed there.

2. `view=closed` filter (line ~175): Change `status="closed"` to `status__in=["closed", "irrelevant"]`

3. `open_q` definition (line ~231): Currently `Q(status__in=["new", "acknowledged", "reopened"])` — this already excludes irrelevant, OK.

4. Sidebar `closed` count (line ~236): Change `Q(status="closed")` to `Q(status__in=["closed", "irrelevant"])`

5. `unread_closed` count (line ~256): Change `status="closed"` to `status__in=["closed", "irrelevant"]`

6. Stat card closed filter (line ~309): Change `status="closed"` to `status__in=["closed", "irrelevant"]`

7. Bulk mark-irrelevant (line ~2033): Check the `status__in` filter includes irrelevant-eligible statuses.
</action>
<acceptance_criteria>
- `grep -n 'status="closed"' apps/emails/views.py` returns 0 matches (all converted to status__in)
- `grep -c 'status__in=\["closed", "irrelevant"\]' apps/emails/views.py` returns at least 3
- All existing tests pass
</acceptance_criteria>
</task>

## Verification

- Irrelevant threads don't appear in Triage Queue, My Inbox, or All Open views
- Irrelevant threads appear in Closed tab
- Sidebar closed count includes irrelevant threads
- Stat cards exclude irrelevant from Total/Unassigned/Urgent/New

## must_haves

- irrelevant excluded from every open queryset
- irrelevant included in closed tab and closed count
