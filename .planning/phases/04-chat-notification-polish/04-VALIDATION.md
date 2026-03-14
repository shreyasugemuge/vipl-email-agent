---
phase: 4
slug: chat-notification-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-django |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest apps/emails/tests/test_chat_notifier.py apps/emails/tests/test_sla.py -x -q` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~13 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/test_chat_notifier.py apps/emails/tests/test_sla.py -x -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 13 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | R4.1 | unit | `pytest apps/emails/tests/test_sla.py::TestBreachSummary -x` | Exists (extend) | ⬜ pending |
| 04-01-02 | 01 | 1 | R4.2 | unit | `pytest apps/emails/tests/test_chat_notifier.py::TestChatPersonalBreach -x` | Exists (extend) | ⬜ pending |
| 04-01-03 | 01 | 1 | R4.3 | unit | `pytest apps/emails/tests/test_chat_notifier.py -k urgency -x` | Wave 0 | ⬜ pending |
| 04-01-04 | 01 | 1 | R4.4 | unit | `pytest apps/emails/tests/test_chat_notifier.py -k card_format -x` | Partially exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] New test: `test_sla.py::TestBreachSummary::test_entry_contains_pk` — assert `pk` key in per_assignee entry dicts
- [ ] New test: `test_sla.py::TestBreachSummary::test_top_offenders_contain_pk` — assert `pk` key in top_offenders dicts
- [ ] New test: `test_chat_notifier.py::TestChatPersonalBreach::test_personal_breach_has_open_button` — assert decoratedText has button.onClick.openLink
- [ ] New test: `test_chat_notifier.py::test_sla_urgency_label_helper` — test the extracted helper function
- [ ] New test: `test_chat_notifier.py::test_urgency_label_consistency_across_cards` — verify all cards use same urgency format

*Existing test infrastructure covers most needs. Only new test methods needed, no new files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Card renders correctly in Google Chat | R4.4 | Webhook rendering not testable in unit tests | 1. Copy card payload from test output 2. Paste into [Card Builder](https://gw-card-builder.web.app/chat) 3. Verify visual rendering |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 13s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
