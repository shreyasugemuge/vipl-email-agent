---
phase: 3
slug: vipl-branding
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-django |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest apps/emails/tests/test_branding.py apps/emails/tests/test_chat_notifier.py -x -v` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/test_branding.py apps/emails/tests/test_chat_notifier.py -x -v`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | R3.1 | unit | `pytest apps/emails/tests/test_branding.py::test_static_assets_exist -x` | Wave 0 | ⬜ pending |
| 03-01-02 | 01 | 1 | R3.2 | smoke | `pytest apps/emails/tests/test_branding.py::test_sidebar_contains_logo -x` | Wave 0 | ⬜ pending |
| 03-01-03 | 01 | 1 | R3.3 | manual-only | Visual inspection of rendered pages | N/A | ⬜ pending |
| 03-01-04 | 01 | 1 | R3.4 | unit | `pytest apps/emails/tests/test_branding.py::test_no_indigo_in_templates -x` | Wave 0 | ⬜ pending |
| 03-01-05 | 01 | 1 | R3.chat | unit | `pytest apps/emails/tests/test_chat_notifier.py -x -v` | Existing (update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_branding.py` — stubs for R3.1, R3.2, R3.4 (new file)
- [ ] Update `apps/emails/tests/test_chat_notifier.py` — verify imageUrl in card headers and footer textParagraph

*Existing infrastructure covers most phase requirements. Only new file needed is test_branding.py.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Brand palette renders correctly in browser | R3.3 | CSS theming not testable without browser rendering | 1. Run `python manage.py runserver` 2. Visit `triage.local` 3. Verify purple/plum palette across dashboard, login, sidebar |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
