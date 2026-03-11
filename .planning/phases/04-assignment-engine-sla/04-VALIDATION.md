---
phase: 4
slug: assignment-engine-sla
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with Django TestCase |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest apps/emails -v -x` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails -v -x`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-T1 | 01 | 1 | ASGN-03, SLA-02, INFR-09, INFR-10 | unit | `pytest apps/emails/tests/test_sla.py apps/emails/tests/test_auto_assignment.py -v` | W0 | pending |
| 04-01-T2 | 01 | 1 | ASGN-03, INFR-09 | unit | `pytest apps/emails/tests/test_auto_assignment.py apps/emails/tests/test_claiming.py -v` | W0 | pending |
| 04-01-T3 | 01 | 1 | ASGN-04 | unit | `pytest apps/emails/tests/test_ai_suggestion.py -v` | W0 | pending |
| 04-02-T1 | 02 | 2 | ASGN-03, ASGN-04, SLA-02 | unit | `pytest apps/emails/tests/ -v -k "not test_settings"` | W0 | pending |
| 04-02-T2 | 02 | 2 | INFR-09, INFR-10 | unit | `pytest apps/emails/tests/test_settings_views.py -v` | W0 | pending |
| 04-03-T1 | 03 | 3 | SLA-03, SLA-04 | unit | `pytest apps/emails/tests/test_sla.py -v` | W0 | pending |
| 04-03-T2 | 03 | 3 | SLA-03, SLA-04 | manual | Visual verification checkpoint | n/a | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_sla.py` — stubs for SLA calculator, breach detection, breach summary, escalation
- [ ] `apps/emails/tests/test_auto_assignment.py` — stubs for AssignmentRule model, auto-assign batch, rule matching
- [ ] `apps/emails/tests/test_claiming.py` — stubs for claim service, category visibility checks
- [ ] `apps/emails/tests/test_ai_suggestion.py` — stubs for AI workload context injection, structured suggestion parsing
- [ ] `apps/emails/tests/test_settings_views.py` — stubs for settings CRUD, claim endpoint, AI accept/reject

*Existing test infrastructure (conftest.py, pytest.ini) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SLA countdown color transitions | SLA-03 | Visual CSS rendering | Open email list, verify green/amber/red/flashing badges |
| Drag-to-reorder assignment rules | INFR-09 | Sortable.js interaction | Open settings page, drag rule items, verify order persists |
| Breach summary Chat card formatting | SLA-04 | External webhook rendering | Trigger breach summary, check Google Chat card layout |
| Per-assignee personal breach alert | SLA-04 | External webhook rendering | Verify separate message per assignee in Google Chat |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
