---
phase: 2
slug: email-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django 4.9.x |
| **Config file** | `pytest.ini` (exists, configured) |
| **Quick run command** | `pytest apps/emails/tests/ apps/core/tests/ -x -q` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/emails/tests/ apps/core/tests/ -x -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | PROC-01 | unit | `pytest apps/emails/tests/test_gmail_poller.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | PROC-01 | unit | `pytest apps/emails/tests/test_pipeline.py::test_save_email_to_db -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | PROC-02 | unit | `pytest apps/emails/tests/test_ai_processor.py -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | PROC-03 | unit | `pytest apps/emails/tests/test_spam_filter.py -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | PROC-06 | unit | `pytest apps/emails/tests/test_pipeline.py::test_dead_letter_retry -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | INFR-08,11 | unit | `pytest apps/core/tests/test_system_config.py -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | INFR-11 | unit | `pytest apps/emails/tests/test_pipeline.py::test_feature_flag_ai_disabled -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | PROC-04 | unit | `pytest apps/emails/tests/test_pdf_extractor.py -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | PROC-05 | unit | `pytest apps/emails/tests/test_pipeline.py::test_language_stored -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_gmail_poller.py` — stubs for PROC-01 (mock Gmail API)
- [ ] `apps/emails/tests/test_ai_processor.py` — stubs for PROC-02 (mock Anthropic)
- [ ] `apps/emails/tests/test_spam_filter.py` — stubs for PROC-03
- [ ] `apps/emails/tests/test_pdf_extractor.py` — stubs for PROC-04
- [ ] `apps/emails/tests/test_pipeline.py` — stubs for PROC-01/02/03/05/06, INFR-11
- [ ] `apps/core/tests/test_system_config.py` — stubs for INFR-08, INFR-11
- [ ] `apps/emails/tests/test_chat_notifier.py` — stubs for Chat notification
- [ ] `apps/emails/tests/test_scheduler.py` — stubs for scheduler command startup
- [ ] Test fixtures: EmailMessage and TriageResult factory helpers in conftest.py

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gmail API polling real inbox | PROC-01 | Requires real Gmail service account | Run scheduler locally with `.env` configured, verify emails appear in DB |
| Chat webhook posts to Google Chat | PROC-06 | Requires real webhook URL | Set GOOGLE_CHAT_WEBHOOK_URL in `.env`, trigger a poll cycle, verify Chat message |
| Docker Compose scheduler container | INFR-08 | Infrastructure test | `docker compose up`, verify scheduler container starts and polls |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
