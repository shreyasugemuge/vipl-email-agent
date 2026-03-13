---
phase: 5
slug: reporting-admin-sheets-mirror
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-django |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest apps/emails -v -x` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails -v -x`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | INFR-05 | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_generate_stats -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | INFR-05 | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_render_email -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | INFR-05 | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_chat_notification -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | INFR-05 | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_feature_flags -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | INFR-05 | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_dedup -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | INFR-07 | unit | `pytest apps/emails/tests/test_settings_views.py::test_inboxes_add -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | INFR-07 | unit | `pytest apps/emails/tests/test_settings_views.py::test_config_editor -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 1 | INFR-04 | unit | `pytest apps/emails/tests/test_sheets_sync.py -x` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 1 | INFR-04 | unit | `pytest apps/emails/tests/test_sheets_sync.py::test_sync_failure_does_not_crash -x` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 1 | INFR-04 | unit | `pytest apps/emails/tests/test_sheets_sync.py::test_ensure_tab_exists -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_eod_reporter.py` — stubs for INFR-05 (EOD stats, email render, Chat card, feature flags, dedup)
- [ ] `apps/emails/tests/test_sheets_sync.py` — stubs for INFR-04 (tab creation, append, update, fire-and-forget, row index cache)
- [ ] Extend `apps/emails/tests/test_settings_views.py` — stubs for INFR-07 (add inbox, remove inbox, config editor save)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| EOD email renders correctly in Gmail | INFR-05 | Visual email rendering | Send test EOD via `test_pipeline --with-chat`, check inbox |
| Sheets mirror shows correct data | INFR-04 | Requires Google Sheets API access | Run sync, verify Sheet tab |
| Inboxes tab UX | INFR-07 | Visual layout | Open `/emails/settings/`, check Inboxes tab |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
