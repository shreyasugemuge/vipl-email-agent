---
phase: 2
slug: assignment-enforcement
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest apps/emails/tests/ -x -q --tb=short` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/ -x -q --tb=short`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | ROLE-03 | unit | `pytest apps/emails/tests/test_assignment_enforcement.py -k test_admin_can_assign` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ROLE-03 | unit | `pytest apps/emails/tests/test_assignment_enforcement.py -k test_gatekeeper_can_assign` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | ROLE-03 | unit | `pytest apps/emails/tests/test_assignment_enforcement.py -k test_member_cannot_assign_others` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | ROLE-04 | unit | `pytest apps/emails/tests/test_assignment_enforcement.py -k test_member_can_claim_unassigned` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | ROLE-05 | unit | `pytest apps/emails/tests/test_assignment_enforcement.py -k test_member_reassign_requires_reason` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | ROLE-03 | integration | `pytest apps/emails/tests/test_assignment_enforcement.py -k test_assign_button_hidden_for_member` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | ROLE-05 | integration | `pytest apps/emails/tests/test_assignment_enforcement.py -k test_reassign_reason_in_activity_log` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_assignment_enforcement.py` — stubs for ROLE-03, ROLE-04, ROLE-05
- [ ] Test fixtures for admin, gatekeeper, and member users with CategoryVisibility setup

*Existing test infrastructure (pytest, conftest.py, factories) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Disabled claim button tooltip renders correctly | ROLE-04 | CSS tooltip rendering not testable via Django test client | Load thread detail as member for out-of-category thread, verify tooltip text visible on hover |
| Context menu shows correct options per role | ROLE-03 | HTMX partial rendering + right-click interaction | Right-click thread card as member/gatekeeper/admin, verify menu items match spec |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
