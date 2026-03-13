---
phase: 6
slug: migration-cutover
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + Django test client |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest --tb=short -q` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest --tb=short -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | CUTV-04 | unit | `grep -r "cloud.run\|cloudrun\|gcloud run" .github/workflows/deploy.yml` | N/A | ⬜ pending |
| 06-01-02 | 01 | 1 | CUTV-04 | unit | `pytest --tb=short -q` (regression check) | ✅ | ⬜ pending |
| 06-01-03 | 01 | 1 | CUTV-02 | smoke | VM smoke test checklist | N/A | ⬜ pending |
| 06-01-04 | 01 | 1 | CUTV-01 | manual-only | Verify Sheet untouched | N/A | ⬜ pending |
| 06-01-05 | 01 | 1 | CUTV-03 | manual-only | `gcloud run services list` returns empty | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed.

This phase is primarily operational — verification is through manual smoke tests and infrastructure checks, not new automated test suites. The existing 257 tests validate the application itself; this phase validates deployment and operations.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sheet preserved as archive | CUTV-01 | Verify external resource (Google Sheet) unchanged | Open production Sheet, verify no rows deleted or modified |
| Both inboxes monitored | CUTV-02 | Requires live Gmail + production mode on VM | Set mode=production, wait 5min, verify new emails appear in dashboard |
| Cloud Run decommissioned | CUTV-03 | External GCP state check | `gcloud run services list --project=utilities-vipl` returns empty |
| Artifact Registry cleaned | CUTV-03 | External GCP state check | `gcloud artifacts repositories list --project=utilities-vipl --location=asia-south1` shows no vipl-repo |
| Go-live Chat announcement | N/A | One-time manual action | Post via docker exec, verify in Chat space |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
