---
phase: 3
slug: spam-learning-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-django |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest apps/emails/tests/test_spam_feedback.py -x -q` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/test_spam_feedback.py -x -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SPAM-01 | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_mark_spam -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | SPAM-02 | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_feedback_creates_record -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | SPAM-03 | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_reputation_updated -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | SPAM-04 | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_auto_block_threshold -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | SPAM-05 | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_unblock_auto_whitelist -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | SPAM-06 | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_has_spam_annotation -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 1 | FIX-01 | unit | `pytest apps/accounts/tests/test_oauth.py -x` | ✅ | ⬜ pending |
| 03-02-03 | 02 | 1 | FIX-02 | unit | `pytest apps/emails/tests/test_cross_inbox_dedup.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_spam_feedback.py` — stubs for SPAM-01 through SPAM-06
- [ ] No new fixtures needed — existing conftest.py has user, admin_user, email, thread factories

*Existing infrastructure covers FIX-01 and FIX-02.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Force Poll button works in production mode | FIX-03 | Requires running server with production mode | Set mode to production, click Force Poll, verify poll executes |
| Scheduler stoppage investigation | Operational | VM-level issue, not unit testable | SSH to VM, check scheduler container logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
