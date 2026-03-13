---
phase: 6
slug: migration-cutover
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-13
validated: 2026-03-14
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
| **Estimated runtime** | ~11 seconds |
| **Test count** | 257 passing |

---

## Sampling Rate

- **After every task commit:** Run `pytest --tb=short -q`
- **After every plan wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 06-01-01 | 01 | 1 | CUTV-04 | unit | `grep -c "sudo docker compose" .github/workflows/deploy.yml` returns 3 | ✅ green |
| 06-01-02 | 01 | 1 | CUTV-04 | unit | `pytest --tb=short -q` (257 passing) | ✅ green |
| 06-01-03 | 01 | 1 | CUTV-01 | manual | Verify REQUIREMENTS.md wording | ✅ green |
| 06-02-01 | 02 | 2 | CUTV-02 | smoke | `curl -s https://triage.vidarbhainfotech.com/health/` returns healthy+production | ✅ green |
| 06-02-02 | 02 | 2 | CUTV-02 | smoke | `set_mode` shows both inboxes monitored | ✅ green |
| 06-02-03 | 02 | 2 | CUTV-01 | manual | v2 running fresh, Sheet untouched | ✅ green |
| 06-02-04 | 02 | 2 | CUTV-03 | manual | Cloud Run has 0 services | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Automated Verifications Performed

```
# CUTV-04: No Cloud Run refs in deploy.yml
$ grep -ri "cloud run" .github/workflows/deploy.yml
(no output — PASS)

# CUTV-04: All docker commands use sudo
$ grep -c "sudo docker compose" .github/workflows/deploy.yml
3 — PASS

# CUTV-02: Health endpoint responds in production mode
$ curl -s https://triage.vidarbhainfotech.com/health/
{"status":"healthy","version":"v2.0.0-rc1","mode":"production",...} — PASS

# CUTV-02: Both inboxes monitored
$ docker compose exec web python manage.py set_mode
monitored_inboxes: info@vidarbhainfotech.com,sales@vidarbhainfotech.com — PASS

# Regression: All 257 tests pass
$ pytest --tb=short -q
257 passed — PASS
```

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Status |
|----------|-------------|------------|--------|
| Sheet preserved as archive | CUTV-01 | External resource (Google Sheet) | ✅ Not modified |
| Both inboxes monitored | CUTV-02 | Requires live Gmail + production mode | ✅ Verified via set_mode |
| Cloud Run decommissioned | CUTV-03 | External GCP state | ✅ 0 services (was already stopped) |
| Artifact Registry deleted | CUTV-03 | External GCP state | ⬜ Deferred (gcloud auth needed) |
| Go-live Chat announcement | N/A | One-time manual action | ⬜ Deferred |

---

## Validation Audit 2026-03-14

| Metric | Count |
|--------|-------|
| Requirements | 4 (CUTV-01 through CUTV-04) |
| Covered | 4 |
| Partial | 0 |
| Missing | 0 |
| Deferred non-blocking | 2 (Artifact Registry cleanup, Chat announcement) |

---

## Validation Sign-Off

- [x] All tasks have automated verify or manual verification
- [x] Sampling continuity maintained
- [x] All CUTV requirements verified
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-03-14
