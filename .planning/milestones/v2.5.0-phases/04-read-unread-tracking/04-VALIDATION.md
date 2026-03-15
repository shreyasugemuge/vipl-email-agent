---
phase: 4
slug: read-unread-tracking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 4 — Validation Strategy

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
| 04-01-01 | 01 | 1 | READ-01 | unit | `pytest apps/emails/tests/test_read_state.py -k "test_thread_read_state"` | ✅ (Phase 1) | ⬜ pending |
| 04-01-02 | 01 | 1 | READ-02 | unit+integration | `pytest apps/emails/tests/test_read_state.py -k "test_mark_read_on_detail"` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | READ-03 | unit | `pytest apps/emails/tests/test_read_state.py -k "test_unread_visual"` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | READ-04 | unit+integration | `pytest apps/emails/tests/test_read_state.py -k "test_mark_unread"` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | READ-05 | unit | `pytest apps/emails/tests/test_read_state.py -k "test_sidebar_unread_count"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_read_state.py` — test stubs for READ-01 through READ-05 (model tests from Phase 1 exist; view/template tests needed)
- [ ] Fixtures: test user, test thread with ThreadReadState in conftest.py (may already exist from Phase 1)

*Existing infrastructure covers model-level requirements (Phase 1 created ThreadReadState tests). View and template tests need stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Blue dot + bold text visual | READ-03 | CSS styling can't be verified in unit tests | 1. Open thread list 2. Verify unread threads show blue dot + bold 3. Open thread 4. Verify card updates to read styling |
| Browser tab title count | READ-05 (extended) | JS title update requires browser | 1. Load page with unread threads 2. Check tab shows "(N) VIPL Triage" 3. Read all threads 4. Check tab shows "VIPL Triage" |
| OOB card swap after detail open | READ-02 | HTMX swap timing is visual | 1. Click unread thread 2. Verify card immediately loses bold+dot 3. Sidebar count decrements |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
