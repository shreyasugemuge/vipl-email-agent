---
phase: 4
slug: assignment-engine-sla
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-11
audited: 2026-03-12
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
| **Actual runtime** | ~9 seconds (232 tests) |

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
| 04-01-T1 | 01 | 1 | ASGN-03, SLA-02, INFR-09, INFR-10 | unit | `pytest apps/emails/tests/test_sla.py apps/emails/tests/test_auto_assignment.py -v` | Yes (35+15 tests) | green |
| 04-01-T2 | 01 | 1 | ASGN-03, INFR-09 | unit | `pytest apps/emails/tests/test_auto_assignment.py apps/emails/tests/test_claiming.py -v` | Yes (15+5 tests) | green |
| 04-01-T3 | 01 | 1 | ASGN-04 | unit | `pytest apps/emails/tests/test_ai_suggestion.py -v` | Yes (10 tests) | green |
| 04-02-T1 | 02 | 2 | ASGN-03, ASGN-04, SLA-02 | unit | `pytest apps/emails/tests/ -v -k "not test_settings"` | Yes | green |
| 04-02-T2 | 02 | 2 | INFR-09, INFR-10 | unit | `pytest apps/emails/tests/test_settings_views.py -v` | Yes (31 tests) | green |
| 04-03-T1 | 03 | 3 | SLA-03, SLA-04 | unit | `pytest apps/emails/tests/test_sla.py -v` | Yes (35 tests) | green |
| 04-03-T2 | 03 | 3 | SLA-03, SLA-04 | manual | Visual verification checkpoint | n/a | approved |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `apps/emails/tests/test_sla.py` — 35 tests: SLA calculator, business hours, deadlines, breach detection, escalation, Chat summary, personal alerts
- [x] `apps/emails/tests/test_auto_assignment.py` — 15 tests: AssignmentRule/SLAConfig/CategoryVisibility models, auto-assign batch, rule matching, priority order
- [x] `apps/emails/tests/test_claiming.py` — 5 tests: claim service, category visibility checks, admin bypass, activity log
- [x] `apps/emails/tests/test_ai_suggestion.py` — 10 tests: AI workload context injection, structured suggestion parsing, backward compat
- [x] `apps/emails/tests/test_settings_views.py` — 31 tests: settings CRUD, claim endpoint, AI accept/reject, SLA template filters
- [x] `apps/emails/tests/test_scheduler.py` — 3 tests: scheduler job count (5 jobs), signal handlers, heartbeat

*All test files exist with comprehensive coverage. Total: 96 Phase 4-specific tests + 3 scheduler tests.*

---

## Requirement Coverage Detail

| Requirement | Description | Test Files | Test Count | Status |
|-------------|-------------|------------|------------|--------|
| ASGN-03 | Auto-assign by category rules | test_auto_assignment.py, test_claiming.py, test_settings_views.py | 27 | COVERED |
| ASGN-04 | AI-suggested assignee with workload | test_ai_suggestion.py, test_settings_views.py | 15 | COVERED |
| SLA-02 | SLA deadlines (business hours) | test_sla.py | 21 | COVERED |
| SLA-03 | Breach detection + auto-escalation | test_sla.py | 4 | COVERED |
| SLA-04 | Breach summary Chat notifications | test_sla.py | 7 | COVERED |
| INFR-09 | Admin settings page | test_settings_views.py | 12 | COVERED |
| INFR-10 | Settings CRUD + endpoints | test_settings_views.py, test_scheduler.py | 13 | COVERED |

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s (actual: ~4s for Phase 4 tests, ~9s full suite)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete (audited 2026-03-12)

---

## Validation Audit 2026-03-12

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total Phase 4 tests | 99 |
| Full suite tests | 232 |
| All passing | Yes |
