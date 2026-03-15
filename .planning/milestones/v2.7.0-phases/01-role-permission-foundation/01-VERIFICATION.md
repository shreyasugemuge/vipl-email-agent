---
phase: 01-role-permission-foundation
verified: 2026-03-16T06:00:00Z
status: gaps_found
score: 11/12 must-haves verified
re_verification: false
gaps:
  - truth: "Triage Lead welcome banner shows assignment-focused copy"
    status: partial
    reason: "Welcome banner with 'keep the queue empty' copy exists in templates/emails/email_list.html (legacy /emails/legacy/ route) but NOT in templates/emails/thread_list.html, which is the primary /emails/ route rendered by the thread_list view."
    artifacts:
      - path: "templates/emails/thread_list.html"
        issue: "No welcome banner block for Triage Lead role — the template only has the no-categories empty state (line 219), not a welcome banner with assignment-focused guidance"
    missing:
      - "Add Triage Lead welcome banner to templates/emails/thread_list.html with copy matching email_list.html: 'keep the queue empty. Assign threads to the right people, dismiss irrelevant ones, and help the AI learn from corrections.'"
---

# Phase 1: Role + Permission Foundation Verification Report

**Phase Goal:** Gatekeeper role exists in the system and all permission checks use centralized helpers instead of scattered inline checks
**Verified:** 2026-03-16T06:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Admin can promote a user to Triage Lead from the team page | VERIFIED | `test_admin_can_promote_to_triage_lead` passes; `_user_row.html` has triage_lead dropdown option |
| 2 | Admin can demote a Triage Lead back to Member | VERIFIED | `TestTriageLeadRole.test_admin_can_promote_to_triage_lead` tests demotion path; change_role view handles all Role.choices |
| 3 | Triage Lead cannot change roles (admin-only operation) | VERIFIED | `test_triage_lead_cannot_change_roles` passes; views.py `change_role` uses `_require_admin` (is_admin_only) |
| 4 | Permission helpers can_assign, is_admin_only, can_triage, can_approve_users, is_triage_lead exist on User model | VERIFIED | All 5 properties present in `apps/accounts/models.py` lines 35-58 |
| 5 | Dev login offers Triage Lead option for local testing | VERIFIED | `templates/registration/dev_login.html` has `value="triage_lead"` and "Assigns threads, manages queue" text |
| 6 | Triage Lead sees only threads in their assigned categories | VERIFIED | `thread_list` view lines 126-134 filter `qs.filter(category__in=lead_categories)` or `threads.none()`; test passes |
| 7 | Triage Lead with no AssignmentRules sees empty state with guidance text | VERIFIED | `thread_list.html` lines 219-232: "No categories assigned" with guidance; test passes |
| 8 | Sidebar counts match filtered thread list for Triage Lead | VERIFIED | views.py lines 195-197 apply same lead_categories filter to `base_threads` for sidebar counts |
| 9 | Sidebar shows category pills for Triage Lead | VERIFIED | `templates/base.html` lines 180-186: "Your Categories" section gated on `user.is_triage_lead` with `lead_categories` loop |
| 10 | Zero inline is_admin patterns remain in views | VERIFIED | `grep -c 'is_admin\s*=' apps/emails/views.py` returns 0; `TestZeroInlineIsAdmin` tests pass |
| 11 | Triage Lead can view settings (read-only) and inspector (view-only) | VERIFIED | settings_view uses `can_triage` gate with readonly flag; test_triage_lead_can_view_settings and test_triage_lead_can_view_inspect pass |
| 12 | Triage Lead welcome banner shows assignment-focused copy | FAILED | Copy exists in `email_list.html` (legacy route) but NOT in `thread_list.html` (primary `/emails/` route) |

**Score:** 11/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|---------|--------|---------|
| `apps/accounts/models.py` | Role.TRIAGE_LEAD + 5 permission properties | VERIFIED | TRIAGE_LEAD at line 12, max_length=20, all 5 properties lines 35-58 |
| `apps/accounts/migrations/0004_add_triage_lead_role.py` | AlterField for role max_length=20 + triage_lead choice | VERIFIED | Migration present, generated 2026-03-15 |
| `conftest.py` | triage_lead_user fixture | VERIFIED | Fixture at lines 44-58 with Role.TRIAGE_LEAD, is_staff=False |
| `apps/accounts/tests/test_models.py` | TestPermissionProperties class with 15 tests | VERIFIED | Class at line 37, includes test_admin_can_assign, test_triage_lead_not_admin_only |
| `apps/accounts/tests/test_team.py` | TestTriageLeadRole class with promote/demote tests | VERIFIED | Class at line 205, includes test_admin_can_promote_to_triage_lead, test_triage_lead_cannot_change_roles |
| `apps/emails/views.py` | All is_admin checks replaced with permission properties | VERIFIED | Zero `is_admin =` patterns; uses can_assign, is_admin_only, can_triage throughout |
| `apps/emails/tests/test_triage_lead.py` | Category scoping + permission enforcement tests | VERIFIED | 3 test classes: TestTriageLeadCategoryScoping, TestTriageLeadPermissions, TestZeroInlineIsAdmin |
| `templates/base.html` | Per-link sidebar + category pills | VERIFIED | user.can_triage (lines 131, 135, 169), user.can_assign (147), user.can_approve_users (158), category pills (180-186) |
| `templates/emails/thread_list.html` | Triage Lead welcome banner copy | FAILED | Only has no-categories empty state (line 219), no welcome banner |
| `apps/accounts/context_processors.py` | user_permissions function providing lead_categories | VERIFIED | Function present, provides lead_categories for triage_lead role |
| `config/settings/base.py` | user_permissions context processor registered | VERIFIED | Line 70: "apps.accounts.context_processors.user_permissions" |
| `templates/emails/settings.html` | Read-only banner for Triage Lead | VERIFIED | Lines 10-15: `{% if readonly %}` with "You have view-only access to settings" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `apps/accounts/views.py` | `apps/accounts/models.py` | change_role handles triage_lead value | WIRED | `_require_admin` uses `user.is_admin_only`; change_role validates against `User.Role.choices` which includes triage_lead |
| `templates/accounts/_user_row.html` | `User.Role.choices` | dropdown includes triage_lead option | WIRED | Line 27: `<option value="triage_lead"` with selected state; line 31: blue badge |
| `apps/emails/views.py thread_list` | `apps/emails/models.py AssignmentRule` | Category-scoped queryset filtering for triage_lead | WIRED | `AssignmentRule.objects.filter(assignee=request.user, is_active=True)` at lines 128-132 |
| `templates/base.html` | `apps/accounts/models.py User properties` | Template checks use user.can_assign, user.is_admin_only | WIRED | `user.can_triage`, `user.can_assign`, `user.can_approve_users` used for per-link visibility gates |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| ROLE-01 | Plan 01 | Admin can promote/demote user to gatekeeper role from team page | SATISFIED | Team page has triage_lead dropdown; `test_admin_can_promote_to_triage_lead` passes; blue "TRIAGE LEAD" badge in `_user_row.html` |
| ROLE-02 | Plan 02 | Gatekeeper sees all threads in their assigned categories (category-scoped visibility) | SATISFIED | `thread_list` view filters by AssignmentRule categories; `test_triage_lead_sees_assigned_category_threads` passes |
| ROLE-06 | Plan 01 + 02 | Permission checks centralized into can_assign/is_admin_only helpers replacing 25+ scattered is_admin checks | SATISFIED | Zero `is_admin =` patterns in emails/views.py; zero `{% if is_admin %}` in templates; `TestZeroInlineIsAdmin` tests pass |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|---------|--------|
| `templates/emails/thread_list.html` | N/A | Missing Triage Lead welcome banner | Warning | Triage Lead users see no contextual guidance on the primary /emails/ route; the welcome banner exists only in the legacy email_list.html |

### Human Verification Required

#### 1. Triage Lead Role End-to-End Flow

**Test:** Log in via /dev-login/ as Triage Lead, navigate to /emails/, then to /emails/settings/
**Expected:** Sidebar shows "Your Categories" section (empty if no rules); settings page shows blue read-only banner with disabled inputs; Reports, Team, Settings, Inspector links visible; force poll returns 403
**Why human:** Visual appearance, disabled input states, banner styling cannot be verified via grep

#### 2. Welcome Banner on Primary Route

**Test:** Log in as Triage Lead, visit /emails/ (primary thread list)
**Expected:** Welcome banner with assignment-focused copy ("keep the queue empty") visible above thread list
**Why human:** Banner is absent from thread_list.html — this is the gap requiring a fix. Human should confirm whether the banner from email_list.html needs to be ported to thread_list.html.

### Gaps Summary

One gap blocks the `score: passed` status:

**Missing Triage Lead welcome banner in thread_list.html** — The welcome banner with "keep the queue empty" assignment-focused copy was implemented in `templates/emails/email_list.html` (the legacy `/emails/legacy/` route) but was not added to `templates/emails/thread_list.html`, which is the primary `/emails/` route users see. The no-categories empty state IS correctly implemented in `thread_list.html`. The gap is specifically the contextual welcome banner for Triage Lead users who DO have categories assigned — they see no onboarding guidance on the primary route.

All other phase goals are fully achieved: the Triage Lead role exists with all 5 permission properties, all 25+ scattered `is_admin` checks are replaced with centralized helpers, category-scoped filtering works correctly, sidebar pills are implemented, settings read-only mode works, and 65 tests all pass.

---

_Verified: 2026-03-16T06:00:00Z_
_Verifier: Claude (gsd-verifier)_
