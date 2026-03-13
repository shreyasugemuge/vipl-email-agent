---
phase: 3
slug: dashboard
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-11
audited: 2026-03-12
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django 4.9.x |
| **Config file** | `pytest.ini` (DJANGO_SETTINGS_MODULE = config.settings.dev) |
| **Quick run command** | `pytest apps/emails/tests/test_views.py apps/emails/tests/test_assignment.py apps/emails/tests/test_activity.py -x -q` |
| **Full suite command** | `pytest -v` |
| **Phase 3 test count** | 40 (views:13, assignment:20, activity:7) |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/ -x -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Tests | Status |
|---------|------|------|-------------|-----------|-------------------|-------|--------|
| 03-01-01 | 01 | 1 | DASH-01 | unit | `pytest apps/emails/tests/test_views.py::TestEmailListAuth apps/emails/tests/test_views.py::TestEmailListTabs apps/emails/tests/test_views.py::TestEmailListHTMX apps/emails/tests/test_views.py::TestEmailListPagination -v` | 5 | ✅ green |
| 03-01-02 | 01 | 1 | DASH-02 | unit | `pytest apps/emails/tests/test_views.py::TestEmailListFilters -v` | 3 | ✅ green |
| 03-01-03 | 01 | 1 | DASH-03 | unit | `pytest apps/emails/tests/test_views.py::TestEmailListSort -v` | 2 | ✅ green |
| 03-01-04 | 01 | 1 | DASH-04 | unit | `pytest apps/emails/tests/test_views.py::TestEmailListDefaultView -v` | 2 | ✅ green |
| 03-02-01 | 02 | 2 | ASGN-01 | unit | `pytest apps/emails/tests/test_assignment.py::TestAssignEmail::test_assign_sets_fields apps/emails/tests/test_assignment.py::TestAssignEmail::test_assign_creates_activity_log apps/emails/tests/test_assignment.py::TestAssignEmailView -v` | 4 | ✅ green |
| 03-02-02 | 02 | 2 | ASGN-02 | unit | `pytest apps/emails/tests/test_assignment.py::TestAssignEmail::test_reassign_creates_reassigned_log -v` | 1 | ✅ green |
| 03-02-03 | 02 | 2 | ASGN-05 | unit | `pytest apps/emails/tests/test_assignment.py::TestChatNotifierAssignment apps/emails/tests/test_assignment.py::TestNotifyAssignmentEmail apps/emails/tests/test_assignment.py::TestAssignEmail::test_assign_calls_chat_notifier apps/emails/tests/test_assignment.py::TestAssignEmail::test_assign_calls_email_notification -v` | 5 | ✅ green |
| 03-02-04 | 02 | 2 | SLA-01 | unit | `pytest apps/emails/tests/test_assignment.py::TestChangeStatus apps/emails/tests/test_assignment.py::TestChangeStatusView -v` | 7 | ✅ green |
| 03-03-01 | 03 | 2 | DASH-05 | unit | `pytest apps/emails/tests/test_activity.py -v` | 7 | ✅ green |
| 03-03-02 | 03 | 2 | DASH-06 | manual | Visual check in browser devtools | N/A | ✅ verified |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `apps/emails/tests/test_views.py` — 13 tests: dashboard views (DASH-01 through DASH-04)
- [x] `apps/emails/tests/test_assignment.py` — 20 tests: assignment service, status changes, notifications (ASGN-01, ASGN-02, ASGN-05, SLA-01)
- [x] `apps/emails/tests/test_activity.py` — 7 tests: activity log view, pagination, ordering (DASH-05)
- [x] ActivityLog model + migration exists and functional

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Status |
|----------|-------------|------------|-------------------|--------|
| Mobile-responsive card layout | DASH-06 | Visual check — CSS responsiveness can't be reliably unit-tested | Open dashboard in Chrome DevTools mobile emulation (iPhone 14 viewport), verify cards stack vertically | ✅ verified (Phase 3 UAT) |

---

## Test Coverage Summary

| File | Tests | Requirements Covered |
|------|-------|---------------------|
| `apps/emails/tests/test_views.py` | 13 | DASH-01 (card list, auth, pagination, HTMX), DASH-02 (filters), DASH-03 (sorting), DASH-04 (default views) |
| `apps/emails/tests/test_assignment.py` | 20 | ASGN-01 (assign), ASGN-02 (reassign), ASGN-05 (chat + email notifications), SLA-01 (status changes + view permissions) |
| `apps/emails/tests/test_activity.py` | 7 | DASH-05 (activity log view, entries, pagination, ordering, HTMX partial, auth) |
| **Total** | **40** | **9 automated + 1 manual = 10/10 requirements** |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s (8.16s measured)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** APPROVED

---

## Audit Trail

| Date | Action | Result |
|------|--------|--------|
| 2026-03-12 | Nyquist audit: ran 40 tests across 3 files | 40/40 passed in 8.16s |
| 2026-03-12 | Mapped 10 requirements to test coverage | 9 automated, 1 manual-only (DASH-06) |
| 2026-03-12 | Updated frontmatter: status=complete, nyquist_compliant=true, wave_0_complete=true | Signed off |
