---
phase: 02
slug: settings-spam-whitelist
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest apps/emails/tests/ apps/core/tests/ -x -q` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/ apps/core/tests/ -x -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | R2.7 | unit | `pytest apps/core/tests/ -x -q` | ✅ | ⬜ pending |
| 02-01-02 | 01 | 1 | R2.1, R2.2 | unit | `pytest apps/emails/tests/test_settings_views.py -x -q` | ✅ | ⬜ pending |
| 02-01-03 | 01 | 1 | R2.8 | unit | `pytest apps/emails/tests/test_settings_views.py -x -q` | ✅ | ⬜ pending |
| 02-01-04 | 01 | 1 | R2.3 | unit | `pytest apps/emails/tests/ -k whitelist -x -q` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | R2.4 | unit | `pytest apps/emails/tests/test_spam_filter.py -x -q` | ✅ | ⬜ pending |
| 02-01-06 | 01 | 1 | R2.5 | unit | `pytest apps/emails/tests/ -k whitelist -x -q` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 1 | R2.6 | unit | `pytest apps/emails/tests/ -k whitelist -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_whitelist.py` — stubs for R2.3, R2.5, R2.6
- [ ] Existing `test_spam_filter.py` covers R2.4 extension
- [ ] Existing `test_settings_views.py` covers R2.1, R2.2, R2.8

*Existing infrastructure covers most phase requirements. Only whitelist tests are new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Whitelist tab renders in settings | R2.6 | Visual layout verification | Visit /emails/settings/, click Whitelist tab, verify table + inline form |
| Save feedback banner appears | R2.8 | Visual animation/timing | Save any settings tab, verify green banner appears |
| Whitelist button in detail panel | R2.5 | Visual placement check | Open any email detail, verify "Whitelist Sender" in action bar |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
