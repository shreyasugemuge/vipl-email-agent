---
phase: 4
slug: alerts-bulk-actions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
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
| 04-01-01 | 01 | 1 | ALERT-01 | unit | `pytest apps/emails/tests/test_views.py -k unassigned_badge -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | ALERT-02 | unit | `pytest apps/emails/tests/test_scheduler.py -k unassigned_alert -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | ALERT-03 | unit | `pytest apps/emails/tests/test_scheduler.py -k alert_cooldown -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | TRIAGE-04 | unit | `pytest apps/emails/tests/test_views.py -k bulk_assign -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | TRIAGE-05 | unit | `pytest apps/emails/tests/test_views.py -k bulk_irrelevant -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | ALERT-04 | unit | `pytest apps/emails/tests/test_views.py -k corrections_digest -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_unassigned_alerts.py` — stubs for ALERT-01, ALERT-02, ALERT-03
- [ ] `apps/emails/tests/test_bulk_actions.py` — stubs for TRIAGE-04, TRIAGE-05
- [ ] `apps/emails/tests/test_corrections_digest.py` — stubs for ALERT-04

*Existing test infrastructure (pytest, conftest.py, factories) covers all framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Floating bottom bar slides in on checkbox selection | TRIAGE-04 | CSS animation + JS interaction | 1. Load triage queue as gatekeeper 2. Hover thread card 3. Check checkbox 4. Verify floating bar appears at bottom |
| Badge color changes at threshold boundaries | ALERT-01 | Visual styling verification | 1. Create 0, 3, 5 unassigned threads 2. Verify sidebar badge is green, yellow, red |
| Google Chat card renders with category breakdown | ALERT-02 | External service integration | 1. Set threshold to 1 2. Create 2 unassigned threads 3. Trigger heartbeat 4. Verify Chat card in webhook channel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
