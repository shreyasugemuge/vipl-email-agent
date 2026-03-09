---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django |
| **Config file** | `pytest.ini` (needs updating for Django settings) |
| **Quick run command** | `pytest apps/ --tb=short -q` |
| **Full suite command** | `pytest apps/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest apps/ --tb=short -q`
- **After every plan wave:** Run `pytest apps/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | AUTH-01 | unit | `pytest apps/accounts/tests/test_auth.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | AUTH-02 | unit | `pytest apps/accounts/tests/test_models.py -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | AUTH-03 | unit | `pytest apps/accounts/tests/test_models.py -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | INFR-01 | integration | `pytest apps/core/tests/test_db.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | INFR-02 | smoke | `docker compose up -d && docker compose exec web python manage.py check` | ❌ Manual | ⬜ pending |
| 01-02-02 | 02 | 2 | INFR-03 | smoke | `gh workflow run deploy.yml` | ❌ Manual | ⬜ pending |
| 01-02-03 | 02 | 2 | INFR-06 | unit | `pytest apps/core/tests/test_health.py -x` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 2 | INFR-12 | unit | `pytest apps/accounts/tests/test_admin.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pytest.ini` — update `DJANGO_SETTINGS_MODULE=config.settings.dev`
- [ ] `conftest.py` — shared fixtures (Django test client, admin user factory, member user factory)
- [ ] `apps/accounts/tests/` — test directory and `__init__.py`
- [ ] `apps/core/tests/` — test directory and `__init__.py`
- [ ] `apps/emails/tests/` — test directory and `__init__.py`
- [ ] `requirements-dev.txt` — add `pytest pytest-django factory-boy`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose starts | INFR-02 | Requires running VM | SSH into VM, run `docker compose up -d`, verify containers are healthy |
| CI/CD deploys on tag | INFR-03 | Requires GitHub Actions + VM | Push a version tag, verify workflow completes and app updates |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
