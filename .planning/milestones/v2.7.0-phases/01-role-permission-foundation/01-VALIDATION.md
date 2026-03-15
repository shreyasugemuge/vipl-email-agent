---
phase: 1
slug: role-permission-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest apps/accounts -v --tb=short` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/accounts -v --tb=short`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | ROLE-01 | unit | `pytest apps/accounts/tests/test_models.py -v` | ✅ | ⬜ pending |
| 01-01-02 | 01 | 1 | ROLE-06 | unit | `pytest apps/accounts/tests/test_models.py -v` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | ROLE-01 | integration | `pytest apps/accounts/tests/test_team.py -v` | ✅ | ⬜ pending |
| 01-02-02 | 02 | 1 | ROLE-02 | integration | `pytest apps/emails/tests/ -v -k "triage_lead or gatekeeper or role"` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | ROLE-06 | integration | `pytest apps/emails/tests/ -v -k "permission or can_assign"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Tests for new permission helpers (`can_assign`, `is_admin_only`, `can_triage`, `can_approve_users`)
- [ ] Tests for triage_lead role in team page (promote/demote)
- [ ] Tests for category-scoped thread visibility

*Existing test infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Category pills render in sidebar | ROLE-02 | Visual template rendering | Log in as triage_lead, verify category pills appear under name in sidebar |
| Welcome banner shows assignment-focused copy | ROLE-01 | Visual template content | Log in as new triage_lead, verify welcome banner text |
| Blue badge renders for Triage Lead | ROLE-01 | Visual CSS styling | View team page, verify blue badge next to triage_lead users |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
