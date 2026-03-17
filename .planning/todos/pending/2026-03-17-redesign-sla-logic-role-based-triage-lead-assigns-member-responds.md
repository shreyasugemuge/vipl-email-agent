---
created: 2026-03-17T16:06:00.000Z
title: Redesign SLA logic — role-based, triage lead assigns, member responds
area: emails
files:
  - apps/emails/models.py
  - apps/emails/services/assignment.py
  - apps/emails/services/reports.py
  - templates/emails/partials/_thread_card.html
---

## Problem

Current SLA tracking is one-size-fits-all — a single SLA timer from email received to resolution. This doesn't reflect the actual workflow where two different roles have two different responsibilities:

- **Triage Lead**: Responsible for assigning incoming emails quickly. Their SLA is time-to-assign (email received → assigned to someone).
- **Member**: Responsible for responding once assigned/claimed. Their SLA is time-to-respond (assigned → first action/response).

These are fundamentally different metrics and should be tracked separately. A triage lead shouldn't be penalized for slow member response, and vice versa.

## Solution

- Split SLA into two clocks:
  - `sla_assign`: Starts when thread is created, stops when assigned. Owned by triage lead.
  - `sla_respond`: Starts when thread is assigned/claimed, stops when member takes action (status change, note, reply). Owned by assigned member.
- Update Thread model with `assigned_at` timestamp (may already exist) and `first_response_at`
- SLA breach alerts should target the right person — triage lead for unassigned, member for unresponded
- Reports/SLA tab should show both metrics separately with per-user breakdown
- Dashboard SLA badges should reflect which SLA applies based on thread state (unassigned → assign SLA, assigned → respond SLA)
- Configurable thresholds per SLA type in SystemConfig
