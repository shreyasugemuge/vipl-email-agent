---
phase: 3
slug: dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django 4.9.x |
| **Config file** | `pytest.ini` (DJANGO_SETTINGS_MODULE = config.settings.dev) |
| **Quick run command** | `pytest apps/emails/tests/ -x -q` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/ -x -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | DASH-01 | unit | `pytest apps/emails/tests/test_views.py::test_email_list_shows_cards -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | DASH-02 | unit | `pytest apps/emails/tests/test_views.py::test_email_list_filters -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | DASH-03 | unit | `pytest apps/emails/tests/test_views.py::test_email_list_sorting -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | DASH-04 | unit | `pytest apps/emails/tests/test_views.py::test_default_view_admin -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | ASGN-01 | unit | `pytest apps/emails/tests/test_assignment.py::test_assign_email -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | ASGN-02 | unit | `pytest apps/emails/tests/test_assignment.py::test_reassign_email -x` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | ASGN-05 | unit | `pytest apps/emails/tests/test_assignment.py::test_assignment_notification -x` | ❌ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | SLA-01 | unit | `pytest apps/emails/tests/test_views.py::test_status_change -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | DASH-05 | unit | `pytest apps/emails/tests/test_activity.py::test_activity_log_creation -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 2 | DASH-06 | manual | Visual check in browser devtools | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_views.py` — dashboard view tests (DASH-01 through DASH-04, SLA-01)
- [ ] `apps/emails/tests/test_assignment.py` — assignment service + notification tests (ASGN-01, ASGN-02, ASGN-05)
- [ ] `apps/emails/tests/test_activity.py` — activity log model + creation tests (DASH-05)
- [ ] ActivityLog model + migration must exist before tests can run

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile-responsive card layout | DASH-06 | Visual check — CSS responsiveness can't be reliably unit-tested | Open dashboard in Chrome DevTools mobile emulation (iPhone 14 viewport), verify cards stack vertically |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
