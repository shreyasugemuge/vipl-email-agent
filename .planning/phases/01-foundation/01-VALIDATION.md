---
phase: 1
slug: foundation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-09
audited: 2026-03-12
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-django |
| **Config file** | `pytest.ini` (`DJANGO_SETTINGS_MODULE=config.settings.dev`) |
| **Quick run command** | `pytest apps/ --tb=short -q` |
| **Full suite command** | `pytest apps/ -v` |
| **Phase 1 command** | `pytest apps/accounts/tests/ apps/core/tests/test_health.py apps/core/tests/test_models.py apps/core/tests/test_system_config.py -v` |
| **Phase 1 test count** | 43 |
| **Estimated runtime** | ~1.2 seconds |

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
| 01-01-01 | 01 | 1 | AUTH-01 | unit | `pytest apps/accounts/tests/test_auth.py -v` | Yes (7 tests) | green |
| 01-01-02 | 01 | 1 | AUTH-02 | unit | `pytest apps/accounts/tests/test_models.py -v` | Yes (5 tests) | green |
| 01-01-03 | 01 | 1 | AUTH-03 | unit | `pytest apps/accounts/tests/test_models.py apps/accounts/tests/test_auth.py -v` | Yes (12 tests) | green |
| 01-01-04 | 01 | 1 | INFR-01 | unit | `pytest apps/core/tests/test_models.py apps/core/tests/test_system_config.py -v` | Yes (20 tests) | green |
| 01-02-01 | 02 | 2 | INFR-02 | smoke | `docker compose up -d && docker compose exec web python manage.py check` | Manual | manual-only |
| 01-02-02 | 02 | 2 | INFR-03 | smoke | `gh workflow run deploy.yml` | Manual | manual-only |
| 01-02-03 | 02 | 2 | INFR-06 | integration | `pytest apps/core/tests/test_health.py -v` | Yes (8 tests) | green |
| 01-02-04 | 02 | 2 | INFR-12 | unit | `pytest apps/accounts/tests/test_admin.py -v` | Yes (3 tests) | green |

*Status: pending -- green -- red -- flaky -- manual-only*

---

## Wave 0 Requirements

- [x] `pytest.ini` — `DJANGO_SETTINGS_MODULE=config.settings.dev` configured
- [x] `conftest.py` — shared fixtures (Django test client, admin_user factory, member_user factory, make_email_message, make_triage_result)
- [x] `apps/accounts/tests/` — test directory and `__init__.py`
- [x] `apps/core/tests/` — test directory and `__init__.py`
- [x] `apps/emails/tests/` — test directory and `__init__.py`
- [x] `requirements-dev.txt` — pytest, pytest-django installed

---

## Requirement-to-Test Coverage

### AUTH-01: Login/Logout (7 tests)
**File:** `apps/accounts/tests/test_auth.py`
| Test | Behavior |
|------|----------|
| `test_login_page_renders` | Login page returns 200 |
| `test_login_with_valid_credentials` | Valid creds redirect to /emails/ |
| `test_login_with_invalid_credentials` | Invalid creds stay on login page |
| `test_logout_redirects_to_login` | Logout redirects to login |
| `test_unauthenticated_redirects_to_login` | Protected views redirect unauthenticated users |
| `test_authenticated_user_can_access_dashboard` | Authenticated users access /emails/ |
| `test_old_dashboard_redirects_to_emails` | Legacy /accounts/dashboard/ redirects to /emails/ |

### AUTH-02: User Model with Roles (5 tests)
**File:** `apps/accounts/tests/test_models.py`
| Test | Behavior |
|------|----------|
| `test_role_defaults_to_member` | New users default to MEMBER role |
| `test_can_see_all_emails_defaults_to_false` | can_see_all_emails defaults false |
| `test_is_admin_role_true_for_admin` | Admin role detected correctly |
| `test_is_admin_role_false_for_member` | Member role detected correctly |
| `test_role_choices` | Role enum has admin/member values |

### AUTH-03: Role-Based Access (covered by AUTH-01 + AUTH-02 tests)
Protected view tests in `test_auth.py` verify access control. Role mechanics in `test_models.py` verify role assignment.

### INFR-01: Database Models (20 tests)
**File:** `apps/core/tests/test_models.py` (7 tests)
| Test | Behavior |
|------|----------|
| `test_delete_sets_deleted_at` | Soft delete sets deleted_at timestamp |
| `test_default_manager_excludes_soft_deleted` | Default queryset hides soft-deleted |
| `test_all_objects_includes_soft_deleted` | all_objects manager includes soft-deleted |
| `test_hard_delete_removes_row` | hard_delete() permanently removes row |
| `test_created_at_auto_set` | TimestampedModel auto-sets created_at |
| `test_updated_at_auto_set` | TimestampedModel auto-sets updated_at |
| `test_updated_at_changes_on_save` | updated_at changes on save |

**File:** `apps/core/tests/test_system_config.py` (13 tests)
| Test | Behavior |
|------|----------|
| `test_get_string_value` | SystemConfig returns str |
| `test_get_int_value` | SystemConfig casts to int |
| `test_get_bool_value_true` | SystemConfig casts "true" to True |
| `test_get_bool_value_false` | SystemConfig casts "false" to False |
| `test_get_float_value` | SystemConfig casts to float |
| `test_get_json_value` | SystemConfig parses JSON |
| `test_get_missing_key_returns_default` | Missing key returns provided default |
| `test_get_missing_key_returns_none` | Missing key returns None |
| `test_typed_value_invalid_returns_raw` | Invalid cast returns raw string |
| `test_get_all_by_category` | Category filter returns typed dict |
| `test_seed_data_exists` | Data migration seeds expected config |
| `test_email_processing_status_choices` | Email model has processing status enum |
| `test_email_has_new_fields` | Email model has all required fields |

### INFR-02: Docker Compose (manual-only)
Requires running VM. See Manual-Only Verifications below.

### INFR-03: CI/CD Pipeline (manual-only)
Requires GitHub Actions + VM. See Manual-Only Verifications below.

### INFR-06: Health Endpoint (8 tests)
**File:** `apps/core/tests/test_health.py`
| Test | Behavior |
|------|----------|
| `test_health_returns_200` | /health/ returns 200 |
| `test_health_returns_json` | Response is application/json |
| `test_health_contains_required_fields` | JSON has status, version, uptime, database, scheduler |
| `test_health_status_healthy_when_db_connected` | Healthy status when DB connected |
| `test_health_uptime_is_non_negative` | Uptime >= 0 |
| `test_scheduler_not_started_when_no_heartbeat` | No heartbeat = not_started (healthy) |
| `test_scheduler_running_with_fresh_heartbeat` | Fresh heartbeat = running |
| `test_scheduler_stale_with_old_heartbeat` | Stale heartbeat = degraded |

### INFR-12: Django Admin (3 tests)
**File:** `apps/accounts/tests/test_admin.py`
| Test | Behavior |
|------|----------|
| `test_admin_accessible_by_staff_user` | Staff user can access /admin/ |
| `test_admin_user_list_shows_role` | User list page loads for superuser |
| `test_admin_can_create_user_with_role` | User creation form includes role field |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose starts | INFR-02 | Requires running VM | SSH into VM, run `docker compose up -d`, verify containers are healthy |
| CI/CD deploys on tag | INFR-03 | Requires GitHub Actions + VM | Push a version tag, verify workflow completes and app updates |

---

## Validation Sign-Off

- [x] All tasks have automated verify or are documented manual-only
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all test infrastructure dependencies
- [x] No watch-mode flags
- [x] Feedback latency < 15s (1.2s actual)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Audit Trail

| Date | Auditor | Action | Result |
|------|---------|--------|--------|
| 2026-03-12 | GSD Nyquist Auditor | Initial audit: read all 6 test files, ran 43 tests, mapped requirements to tests | 43/43 passed in 1.16s. All 6 automated requirements covered. 2 manual-only requirements documented. Status upgraded from draft to complete. |
