---
phase: 2
slug: ai-confidence-auto-assign
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
| **Framework** | pytest 7.x + pytest-django |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest apps/emails/tests/test_ai_confidence.py apps/emails/tests/test_auto_assign_inline.py apps/emails/tests/test_feedback.py apps/emails/tests/test_distillation.py -x -q` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/test_ai_confidence.py apps/emails/tests/test_auto_assign_inline.py apps/emails/tests/test_feedback.py apps/emails/tests/test_distillation.py -x -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | INTEL-01 | unit | `pytest apps/emails/tests/test_ai_confidence.py::test_confidence_in_triage_result -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | INTEL-02 | unit | `pytest apps/emails/tests/test_ai_confidence.py::test_confidence_template_filter -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | INTEL-03 | unit | `pytest apps/emails/tests/test_auto_assign_inline.py::test_inline_auto_assign_high_confidence -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | INTEL-04 | unit | `pytest apps/emails/tests/test_auto_assign_inline.py::test_auto_assign_threshold_disabled -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | INTEL-05 | unit | `pytest apps/emails/tests/test_feedback.py::test_reject_auto_assignment -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | INTEL-06 | unit | `pytest apps/emails/tests/test_feedback.py::test_accept_suggestion -x` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 2 | INTEL-07 | unit | `pytest apps/emails/tests/test_feedback.py::test_feedback_recorded -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | INTEL-08 | unit | `pytest apps/emails/tests/test_distillation.py::test_distill_corrections -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_ai_confidence.py` — stubs for INTEL-01, INTEL-02
- [ ] `apps/emails/tests/test_auto_assign_inline.py` — stubs for INTEL-03, INTEL-04
- [ ] `apps/emails/tests/test_feedback.py` — stubs for INTEL-05, INTEL-06, INTEL-07
- [ ] `apps/emails/tests/test_distillation.py` — stubs for INTEL-08

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Confidence dot color on cards | INTEL-02 | Visual CSS rendering | Open dashboard, verify green/amber/red dots on thread cards |
| Auto badge "(auto)" appearance | INTEL-05 | Visual CSS rendering | Auto-assign a thread, verify "(auto)" pill next to assignee |
| Accept/reject bar updates in place | INTEL-06 | HTMX swap behavior | Click accept/reject, verify bar updates without page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
