---
phase: 2
slug: email-pipeline
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-11
audited: 2026-03-12
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
| **Phase 2 test count** | 66 tests (all green) |
| **Estimated runtime** | ~0.5 seconds |

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
| 02-01-01 | 01 | 1 | PROC-01 | unit | `pytest apps/emails/tests/test_gmail_poller.py -x` | Yes (5 tests) | green |
| 02-01-02 | 01 | 1 | PROC-01 | unit | `pytest apps/emails/tests/test_pipeline.py::TestSaveEmailToDb -x` | Yes (3 tests) | green |
| 02-01-03 | 01 | 1 | PROC-02 | unit | `pytest apps/emails/tests/test_ai_processor.py -x` | Yes (5 tests) | green |
| 02-01-04 | 01 | 1 | PROC-03 | unit | `pytest apps/emails/tests/test_spam_filter.py -x` | Yes (8 tests) | green |
| 02-02-01 | 02 | 2 | PROC-06 | unit | `pytest apps/emails/tests/test_pipeline.py::TestRetryFailedEmails -x` | Yes (2 tests) | green |
| 02-02-02 | 02 | 2 | INFR-08,11 | unit | `pytest apps/core/tests/test_system_config.py -x` | Yes (13 tests) | green |
| 02-02-03 | 02 | 2 | INFR-11 | unit | `pytest apps/emails/tests/test_pipeline.py::TestProcessPollCycle::test_process_poll_cycle_ai_disabled_flag -x` | Yes (1 test) | green |
| 02-03-01 | 03 | 2 | PROC-04 | unit | `pytest apps/emails/tests/test_pdf_extractor.py -x` | Yes (5 tests) | green |
| 02-03-02 | 03 | 2 | PROC-05 | unit | `pytest apps/emails/tests/test_pipeline.py::TestProcessSingleEmail::test_language_stored_from_triage -x` | Yes (1 test) | green |

*Status: pending · green · red · flaky*

---

## Additional Coverage (not task-mapped but phase-relevant)

| Test File | Count | Covers |
|-----------|-------|--------|
| `apps/emails/tests/test_chat_notifier.py` | 8 | PROC-06: Cards v2 format, quiet hours, webhook failure handling |
| `apps/emails/tests/test_scheduler.py` | 3 | INFR-08: job creation (5 jobs), heartbeat, signal handlers |
| `apps/emails/tests/test_models.py` | 7 | PROC-01: Email/AttachmentMetadata model fields, soft delete, assignment |
| `apps/core/tests/test_system_config.py` (EmailModelNewFields) | 2 | PROC-01: processing_status choices, new Phase 2 fields |
| `apps/emails/tests/test_pipeline.py` (ProcessSingleEmail) | 4 | PROC-01/03/06: label-after-persist, spam skips AI, failed status, language |
| `apps/emails/tests/test_pipeline.py` (ProcessPollCycle) | 3 | PROC-06/INFR-11: dedup, circuit breaker, AI disabled flag |

---

## Wave 0 Requirements

- [x] `apps/emails/tests/test_gmail_poller.py` -- 5 tests for PROC-01 (mock Gmail API)
- [x] `apps/emails/tests/test_ai_processor.py` -- 5 tests for PROC-02 (mock Anthropic)
- [x] `apps/emails/tests/test_spam_filter.py` -- 8 tests for PROC-03
- [x] `apps/emails/tests/test_pdf_extractor.py` -- 5 tests for PROC-04
- [x] `apps/emails/tests/test_pipeline.py` -- 12 tests for PROC-01/02/03/05/06, INFR-11
- [x] `apps/core/tests/test_system_config.py` -- 13 tests for INFR-08, INFR-11
- [x] `apps/emails/tests/test_chat_notifier.py` -- 8 tests for Chat notification (PROC-06)
- [x] `apps/emails/tests/test_scheduler.py` -- 3 tests for scheduler command startup (INFR-08)
- [x] Test fixtures: `make_email_message` and `make_triage_result` factory helpers in `conftest.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gmail API polling real inbox | PROC-01 | Requires real Gmail service account | Run scheduler locally with `.env` configured, verify emails appear in DB |
| Chat webhook posts to Google Chat | PROC-06 | Requires real webhook URL | Set GOOGLE_CHAT_WEBHOOK_URL in `.env`, trigger a poll cycle, verify Chat message |
| Docker Compose scheduler container | INFR-08 | Infrastructure test | `docker compose up`, verify scheduler container starts and polls |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s (0.49s actual)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Audit Trail

| Date | Auditor | Action | Result |
|------|---------|--------|--------|
| 2026-03-12 | Nyquist auditor (claude-opus-4-6) | Full audit: read all 9 test files, ran 66 tests, cross-referenced 8 requirements | 66/66 green, 0 escalated |

### Audit Summary

- **Total Phase 2 tests:** 66 (across 9 test files)
- **All tests passing:** Yes (0.49s runtime)
- **Requirements covered:** PROC-01, PROC-02, PROC-03, PROC-04, PROC-05, PROC-06, INFR-08, INFR-11 (8/8)
- **Manual-only items:** 3 (real Gmail, real Chat, Docker scheduler)
- **New tests created:** 0 (all coverage already exists)
- **Implementation bugs found:** 0
