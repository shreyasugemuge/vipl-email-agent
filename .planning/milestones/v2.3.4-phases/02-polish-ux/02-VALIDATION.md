---
phase: 2
slug: polish-ux
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
| **Framework** | pytest 7.x + Django test client |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest apps/emails/tests/test_views.py -x` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/test_views.py -x`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | UX-01 | unit (template rendering) | `pytest apps/emails/tests/test_views.py::TestWelcomeBanner -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | UX-02 | unit (view context + response) | `pytest apps/emails/tests/test_views.py::TestFilterIndicators -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | UX-03 | unit (response content) | `pytest apps/emails/tests/test_views.py::TestScrollSnap -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | UX-04 | unit (response content) | `pytest apps/emails/tests/test_views.py::TestKeyboardNav -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | UX-05 | unit (response content) | `pytest apps/emails/tests/test_views.py::TestLoadingSkeleton -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_views.py::TestWelcomeBanner` — stubs for UX-01
- [ ] `apps/emails/tests/test_views.py::TestFilterIndicators` — stubs for UX-02
- [ ] `apps/emails/tests/test_views.py::TestScrollSnap` — stubs for UX-03
- [ ] `apps/emails/tests/test_views.py::TestKeyboardNav` — stubs for UX-04
- [ ] `apps/emails/tests/test_views.py::TestLoadingSkeleton` — stubs for UX-05

*No new framework install needed — pytest already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Scroll-snap feel on mobile | UX-03 | CSS snap behavior is visual, can only assert classes exist | Open on mobile Safari/Chrome, swipe stat cards, verify snap |
| Keyboard navigation UX | UX-04 | Arrow key behavior is a JS runtime feature | Open dashboard, press arrow keys, verify focus moves |
| Loading skeleton visual | UX-05 | Pulse animation is visual, can only assert markup exists | Click email card, observe skeleton before content loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
