---
phase: 03
slug: mark-irrelevant
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest apps/emails/tests/ -x -q --tb=short` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/ -x -q --tb=short`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | TRIAGE-01 | unit | `pytest apps/emails/tests/test_mark_irrelevant.py -k test_mark_irrelevant_with_reason` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | TRIAGE-02 | unit | `pytest apps/emails/tests/test_mark_irrelevant.py -k test_irrelevant_excluded_from_queue` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | TRIAGE-06 | unit | `pytest apps/emails/tests/test_mark_irrelevant.py -k test_activity_log_entry` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | TRIAGE-03 | unit | `pytest apps/emails/tests/test_mark_irrelevant.py -k test_context_menu_and_detail` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_mark_irrelevant.py` — stubs for TRIAGE-01, TRIAGE-02, TRIAGE-03, TRIAGE-06
- [ ] Shared fixtures in `conftest.py` — thread with gatekeeper user

*Existing test infrastructure (pytest, conftest.py, factories) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Modal opens from context menu click | TRIAGE-03 | JS interaction (context menu → detail panel → modal auto-open) | Right-click thread → Mark Irrelevant → verify detail panel opens with modal |
| Keyboard shortcut I opens modal | TRIAGE-03 | JS keyboard event | Press I on thread card → verify modal appears |
| Irrelevant badge renders on card | TRIAGE-02 | Visual rendering | Filter by status=irrelevant → verify badge visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
