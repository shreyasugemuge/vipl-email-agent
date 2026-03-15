# Phase 1: Role + Permission Foundation - Research

**Researched:** 2026-03-16
**Domain:** Django User model RBAC extension + permission check centralization
**Confidence:** HIGH

## Summary

Phase 1 adds a "Triage Lead" role (`triage_lead`) to the existing User model and centralizes all 28 scattered `is_admin` permission checks into reusable helper properties on the User model. The codebase currently uses `is_admin = user.is_staff or user.role == User.Role.ADMIN` repeated verbatim in 28 locations across `apps/emails/views.py`, plus `_require_admin()` helpers in both `accounts/views.py` and `emails/views.py`. Every check must be classified and replaced with the correct helper.

This is a zero-dependency change. No new packages, no new Django apps, no new models. The work is: one migration (widen role field + add choice), four User model properties, mechanical replacement of 28+ inline checks, template updates for role visibility, and category-scoped thread filtering via existing AssignmentRule model.

**Primary recommendation:** Implement helpers as `@property` methods on User model (not standalone functions), so templates can use `{% if user.can_assign %}` directly without views needing to pass extra context variables for every permission type.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Permission Classification:**
  - Settings page: Triage Lead gets read-only access (can view, cannot edit)
  - Dev Inspector: Triage Lead gets view-only access (poll history, MIS stats -- no force poll)
  - Team page: Triage Lead can view members and approve pending new users, but cannot change roles
  - Reports page: Full access
  - Assignment: Triage Lead can assign/reassign (same as admin)
  - Thread visibility: Category-scoped via AssignmentRules (not `can_see_all_emails`)
- **Permission Helpers:**
  - `can_assign` -- True for admin and triage_lead
  - `is_admin_only` -- True only for admin (settings write, role management, force poll)
  - `can_triage` -- True for admin and triage_lead (mark irrelevant, bulk actions)
  - `can_approve_users` -- True for admin and triage_lead (team page approve)
- **Role Visibility:**
  - Display label: "Triage Lead" (not "Gatekeeper")
  - Badge color: Blue (distinct from admin's plum)
  - Welcome banner: Assignment-focused copy
  - Dev login dropdown: Add "triage_lead" test user
  - Team page role dropdown: Add "Triage Lead" option
- **Category Scoping:**
  - Visibility scoped via existing AssignmentRule model
  - No AssignmentRules = see nothing (strict)
  - Sidebar shows category pills under Triage Lead's name
  - Thread list filters to categories matching AssignmentRules
- **Role Field Migration:**
  - Widen `max_length` from 10 to 20
  - DB value: `"triage_lead"`
  - `Role.TRIAGE_LEAD = "triage_lead", "Triage Lead"`
  - `can_see_all_emails` stays False for Triage Lead
  - No auto-config on promotion

### Claude's Discretion
- Exact helper method signatures and where to put them (model properties vs utility functions)
- How to handle the `is_staff` sync (currently `is_staff = (role == admin)`)
- Template refactoring approach (conditional blocks vs template tags)
- Test data setup for the new role

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ROLE-01 | Admin can promote/demote user to gatekeeper role from team page | User model Role.TRIAGE_LEAD choice + change_role view update + _user_row.html dropdown |
| ROLE-02 | Gatekeeper sees all threads in their assigned categories (category-scoped visibility) | AssignmentRule queryset filtering in thread_list view + sidebar category pills |
| ROLE-06 | Permission checks centralized into helpers replacing 28+ scattered `is_admin` checks | User model properties (can_assign, is_admin_only, can_triage, can_approve_users) replacing all inline checks |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Web framework | Already in use, no changes |
| Python | 3.13 (local) / 3.11 (Docker) | Runtime | Already in use |

### Supporting
No new dependencies. Zero changes to requirements.txt.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| User model properties | django-rules predicates | Adds dependency for 10 lines of property logic; 4-user team doesn't need it |
| User model properties | Django groups/permissions | 4 join tables, admin UI config, permission caching -- massive overkill |
| User model properties | Standalone helper functions in views.py | Works but templates need extra context variables passed from every view |

## Architecture Patterns

### Recommended Approach

No new files except one migration. All changes touch existing files.

### Pattern 1: Permission Helpers as User Model Properties

**What:** Add `@property` methods on User model for each permission level.
**When to use:** Every permission check in views and templates.

**Why properties instead of standalone functions:**
- Templates can use `{% if user.can_assign %}` directly (Django template engine resolves model properties)
- Views don't need to compute and pass separate context variables for each permission
- The existing `is_admin_role` is already a property on User -- consistent pattern
- Reduces the 28+ view locations that currently compute `is_admin` and pass it to context

**Implementation:**
```python
# apps/accounts/models.py - on User model

@property
def is_triage_lead(self):
    return self.role == self.Role.TRIAGE_LEAD

@property
def can_assign(self):
    """Admin and Triage Lead can assign/reassign threads."""
    return self.role in (self.Role.ADMIN, self.Role.TRIAGE_LEAD) or self.is_staff

@property
def is_admin_only(self):
    """Only admin: settings write, role changes, force poll."""
    return self.role == self.Role.ADMIN or self.is_staff

@property
def can_triage(self):
    """Admin and Triage Lead: mark irrelevant, bulk actions."""
    return self.can_assign  # Same boundary for now

@property
def can_approve_users(self):
    """Admin and Triage Lead: approve pending users on team page."""
    return self.role in (self.Role.ADMIN, self.Role.TRIAGE_LEAD) or self.is_staff
```

**Source:** Direct codebase analysis. The existing `is_admin_role` property at `accounts/models.py:31` confirms this pattern.

### Pattern 2: is_staff Sync Strategy

**What:** Keep `is_staff = (role == admin)` for Triage Lead. Triage Lead gets `is_staff=False`.
**Why:** `is_staff` controls Django admin access. Triage Lead should not access Django admin. The existing sync in `change_role()` at `accounts/views.py:132` and `dev_login()` at `accounts/views.py:41` sets `is_staff` based on role.

**Implementation in change_role:**
```python
target.is_staff = (new_role == User.Role.ADMIN)
# triage_lead -> is_staff=False (correct)
# admin -> is_staff=True (correct)
# member -> is_staff=False (correct)
```

No change needed to the is_staff sync logic -- it already works correctly for any non-admin role.

### Pattern 3: Permission Check Classification

Each of the 28 `is_admin` checks in `emails/views.py` must be classified into the correct helper. Based on CONTEXT.md decisions:

**Replace with `user.can_assign` (assignment-related, 9 locations):**
- `assign_email_view` (line 514) -- assigning emails
- `assign_thread_view` (line 1304) -- assigning threads
- `accept_ai_suggestion` (line 608) -- accepting AI assignment suggestion
- `reject_ai_suggestion` (line 649) -- rejecting AI suggestion
- `accept_thread_suggestion` (line 689) -- thread-level AI suggestion
- `reject_thread_suggestion` (line 748) -- thread-level rejection
- `edit_ai_summary` (line 1087) -- editing AI summary (triage action)
- `mark_spam_view` (line ~1351) -- spam management
- `mark_not_spam_view` (line ~1406) -- spam management

**Replace with `user.can_triage` (triage context variables passed to templates, ~12 locations):**
- `thread_list` (line 101) -- computes `is_admin` for template context
- `email_list` (line 291) -- computes `is_admin` for template context
- `email_detail` (line 495) -- detail panel context
- `thread_detail` (line 574) -- detail panel context
- `thread_detail_inline` (line 808) -- inline detail context
- And similar views that pass `is_admin` to template context

**Keep as `user.is_admin_only` (admin-only operations):**
- `settings_view` (line 1699) -- settings page (read-only for triage lead)
- `inspect` (line 2377) -- dev inspector (view-only for triage lead)
- `force_poll` (line 2441) -- force poll (admin only, denied for triage lead)
- All settings save endpoints

**Replace with `user.can_approve_users` in accounts/views.py:**
- `team_list` (line 71) -- viewing team page
- `toggle_active` (line 101) -- approving/deactivating users

**Keep as admin-only in accounts/views.py:**
- `change_role` (line 119) -- changing roles (admin only)
- `toggle_visibility` (line 142) -- toggling email visibility (admin only)
- `save_categories` (line 156) -- saving category visibility (admin only)

### Pattern 4: Category-Scoped Thread Filtering

**What:** Triage Lead sees only threads matching their AssignmentRule categories. No rules = see nothing.

**Implementation in thread_list view:**
```python
# After base queryset setup, before view filtering
if user.role == User.Role.TRIAGE_LEAD:
    # Get categories from AssignmentRules where this user is the assignee
    lead_categories = list(
        AssignmentRule.objects.filter(
            assignee=user, is_active=True
        ).values_list("category", flat=True)
    )
    if lead_categories:
        qs = qs.filter(category__in=lead_categories)
    else:
        qs = qs.none()  # No rules = see nothing
```

**Sidebar counts must also be filtered** to show accurate numbers for the Triage Lead's scoped view.

**Source:** AssignmentRule model at `emails/models.py:401` -- already maps categories to users with `category` and `assignee` fields.

### Pattern 5: Template Refactoring Strategy

**What:** Replace `{% if is_admin %}` with `{% if user.can_assign %}` or `{% if user.is_admin_only %}` in templates.

**Key insight:** Because helpers are User model properties, templates access them via `{{ user.can_assign }}` / `{% if user.can_assign %}`. Views no longer need to compute and pass `is_admin` to context.

**However:** Views currently pass `is_admin` and templates check it. The refactor must:
1. Add properties to User model
2. Update templates to use `user.can_assign` instead of `is_admin`
3. Remove `is_admin` computation from views (or keep for backward compat initially)

**12 template files need updating:**
| Template | Current Check | New Check |
|----------|--------------|-----------|
| `thread_list.html` | `{% if is_admin and team_members %}` | `{% if user.can_assign and team_members %}` |
| `_thread_detail.html` | `{% if is_admin %}` (assign form) | `{% if user.can_assign %}` |
| `_thread_detail.html` | `{% if thread.assigned_to == request.user or is_admin %}` | `{% if thread.assigned_to == request.user or user.can_assign %}` |
| `_context_menu.html` | `{% if is_admin %}` (assign, whitelist) | `{% if user.can_assign %}` for assign, `{% if user.is_admin_only %}` for whitelist |
| `_email_card.html` | `{% if is_admin %}` | `{% if user.can_assign %}` |
| `_email_detail.html` | `{% if is_admin %}` | `{% if user.can_assign %}` |
| `_editable_status.html` | `{% if is_admin %}` | `{% if user.can_assign %}` |
| `email_list.html` | `{% if is_admin %}` | `{% if user.can_assign %}` |
| `base.html` | `{% if user.is_staff or user.is_admin_role %}` | `{% if user.is_admin_only %}` for settings/inspector, separate check for reports/team |
| `accounts/team.html` | N/A (guarded by view) | View uses `can_approve_users` |
| `accounts/_user_row.html` | Hardcoded admin/member options | Add triage_lead option |
| `registration/dev_login.html` | Hardcoded admin/member buttons | Add triage_lead button |

### Pattern 6: Settings and Inspector Access for Triage Lead

**What:** Triage Lead can VIEW settings and inspector but cannot WRITE settings or force poll.

**Implementation approach:**
- Settings view: Pass `readonly=True` in context for triage_lead. Templates conditionally disable form inputs/buttons.
- Inspector view: Allow GET access for triage_lead. Deny POST to force_poll endpoint.
- Sidebar: Show Settings, Reports, Team, Inspector links for triage_lead (currently only shown for admin).

```python
# settings_view
if user.is_admin_only:
    readonly = False
elif user.can_triage:  # triage_lead
    readonly = True
else:
    return HttpResponseForbidden("Access denied.")
```

### Anti-Patterns to Avoid

- **Replacing `is_admin` globally with a grep:** Each check must be classified individually. Some should become `can_assign`, others `is_admin_only`, others `can_approve_users`. A blind replacement breaks security.
- **Adding `is_staff=True` for Triage Lead:** This grants Django admin access. Triage Lead must have `is_staff=False`.
- **Frontend-only gating without server-side checks:** Every template `{% if user.can_assign %}` must have a corresponding server-side check in the view. HTMX POSTs bypass template conditionals.
- **Passing permission booleans from views to templates:** With model properties, templates access `user.can_assign` directly. Don't add `can_assign` to context dicts alongside `is_admin`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Permission framework | Django groups/permissions or django-guardian | User model `@property` methods | 3 roles, 5 users -- properties are simpler and consistent with existing `is_admin_role` |
| Role dropdown | Hardcoded `<option>` tags per role | `{% for value, label in role_choices %}` loop | Adding future roles won't require template changes |
| Category scoping | New CategoryScope model | Existing AssignmentRule model with `assignee` FK | AssignmentRule already maps users to categories |

## Common Pitfalls

### Pitfall 1: Missing a Permission Check Location
**What goes wrong:** One of the 28 `is_admin` checks is not replaced, leaving either a privilege escalation (Triage Lead blocked from assignment) or a security hole (Triage Lead accessing admin-only features).
**Why it happens:** 28 locations across 2500+ lines of views.py, plus 12 templates. Easy to miss one.
**How to avoid:** After refactoring, grep for `is_admin` and `is_staff` in all Python and template files. Zero inline `is_admin` patterns should remain. Each occurrence must have been deliberately classified.
**Warning signs:** Triage Lead gets 403 on an action they should have, or can access something they shouldn't.

### Pitfall 2: Sidebar Counts Not Filtered for Triage Lead
**What goes wrong:** Sidebar shows unassigned/all_open counts for ALL threads, but the thread list shows only category-scoped threads. The numbers don't match.
**Why it happens:** Sidebar count queries in `thread_list` view (line ~180) use `base_threads = Thread.objects.all()` without category filtering for triage_lead.
**How to avoid:** Apply the same AssignmentRule category filter to sidebar count queries when user is triage_lead.
**Warning signs:** Sidebar says "Unassigned (12)" but the list shows only 3 threads.

### Pitfall 3: Role Field max_length Too Narrow
**What goes wrong:** Current `max_length=10`. "triage_lead" is 12 characters -- it will be silently truncated or error.
**Why it happens:** Original field was sized for "admin" (5) and "member" (6).
**How to avoid:** CONTEXT.md mandates widening to `max_length=20`. Must be in the same migration as the new choice.
**Warning signs:** Migration error or truncated role value in database.

### Pitfall 4: Template Role Dropdown Has Only Two Options
**What goes wrong:** `_user_row.html` lines 26-27 hardcode `admin` and `member` `<option>` tags. Triage Lead option is missing.
**Why it happens:** Template was never made dynamic.
**How to avoid:** Replace with a loop over `Role.choices` passed via context, or add the third option explicitly.
**Warning signs:** Admin cannot set anyone to Triage Lead from Team page.

### Pitfall 5: Dev Login Missing Triage Lead Option
**What goes wrong:** `dev_login.html` has two forms (admin/member). No way to test as Triage Lead locally.
**Why it happens:** Template has hardcoded role buttons.
**How to avoid:** Add a third form posting `role=triage_lead`. Update `dev_login` view to handle `triage_lead` role correctly (is_staff=False, can_see_all_emails=False).
**Warning signs:** Cannot test Triage Lead locally during development.

### Pitfall 6: Welcome Banner Shows Wrong Role Guidance
**What goes wrong:** Welcome banner in `email_list.html` (the legacy view) has role-specific text. Triage Lead gets member guidance or nothing. The main `thread_list.html` does not appear to have a welcome banner.
**Why it happens:** Banner was built for two roles only.
**How to avoid:** Add triage_lead-specific welcome copy to whichever view(s) show the banner.
**Warning signs:** Triage Lead sees "Your emails will appear here" instead of assignment-focused guidance.

## Code Examples

### Role Model Extension
```python
# apps/accounts/models.py
class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    TRIAGE_LEAD = "triage_lead", "Triage Lead"  # NEW
    MEMBER = "member", "Team Member"

role = models.CharField(
    max_length=20,  # Widened from 10
    choices=Role.choices,
    default=Role.MEMBER,
)
```

### Permission Properties
```python
# apps/accounts/models.py - on User model
@property
def is_triage_lead(self):
    return self.role == self.Role.TRIAGE_LEAD

@property
def can_assign(self):
    """Admin and Triage Lead can assign/reassign threads."""
    return self.role in (self.Role.ADMIN, self.Role.TRIAGE_LEAD) or self.is_staff

@property
def is_admin_only(self):
    """Only admin: settings write, role management, force poll."""
    return self.role == self.Role.ADMIN or self.is_staff

@property
def can_triage(self):
    """Admin and Triage Lead: mark irrelevant, bulk actions."""
    return self.can_assign

@property
def can_approve_users(self):
    """Admin and Triage Lead: approve pending users."""
    return self.role in (self.Role.ADMIN, self.Role.TRIAGE_LEAD) or self.is_staff
```

### Category-Scoped Thread Queryset
```python
# In thread_list view, after base queryset
if user.role == User.Role.TRIAGE_LEAD:
    lead_categories = list(
        AssignmentRule.objects.filter(
            assignee=user, is_active=True
        ).values_list("category", flat=True)
    )
    if lead_categories:
        qs = qs.filter(category__in=lead_categories)
    else:
        qs = qs.none()
```

### Dev Login Triage Lead
```python
# In dev_login view, the existing logic handles role correctly:
# is_staff = role == "admin" -> False for triage_lead
# can_see_all_emails = role == "admin" -> False for triage_lead
# Just need to add the triage_lead option in the template form
```

### Dynamic Role Dropdown in _user_row.html
```html
<select hx-post="/accounts/team/{{ u.pk }}/change-role/"
        hx-target="#user-{{ u.pk }}" hx-swap="outerHTML"
        name="role" class="...">
    <option value="admin" {% if u.role == 'admin' %}selected{% endif %}>Admin</option>
    <option value="triage_lead" {% if u.role == 'triage_lead' %}selected{% endif %}>Triage Lead</option>
    <option value="member" {% if u.role == 'member' %}selected{% endif %}>Member</option>
</select>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `is_admin = user.is_staff or user.role == User.Role.ADMIN` (28x) | `user.can_assign` / `user.is_admin_only` properties | This phase | Eliminates scattered checks, enables role extension |
| Two roles (admin/member) | Three roles (admin/triage_lead/member) | This phase | Centralized triage assignment role |
| `max_length=10` on role field | `max_length=20` | This phase | Future-proofs for longer role names |

## Open Questions

1. **Settings read-only UX for Triage Lead**
   - What we know: Triage Lead can view settings but not edit
   - What's unclear: Should we pass `readonly=True` to templates and disable all form elements, or render a separate read-only template?
   - Recommendation: Pass `readonly` flag to context, use `{% if not readonly %}` around form submit buttons and editable inputs. Simpler than maintaining two templates.

2. **Sidebar navigation for Triage Lead**
   - What we know: Currently Settings/Reports/Team/Inspector links are gated behind `{% if user.is_staff or user.is_admin_role %}`
   - What's unclear: Triage Lead needs to see Reports (full), Team (view + approve), Settings (view-only), Inspector (view-only). This means the sidebar gate must change.
   - Recommendation: Replace the single gate with per-link checks: Reports visible to `can_assign`, Team visible to `can_approve_users`, Settings visible to `can_triage`, Inspector visible to `can_triage`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/accounts -x -q` |
| Full suite command | `pytest -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROLE-01 | Admin promotes user to triage_lead via team page | unit | `pytest apps/accounts/tests/test_team.py::TestChangeRole -x` | Yes (extend) |
| ROLE-01 | Admin demotes triage_lead back to member | unit | `pytest apps/accounts/tests/test_team.py::TestChangeRole -x` | Yes (extend) |
| ROLE-01 | Triage Lead role appears in dropdown | unit | `pytest apps/accounts/tests/test_team.py -x` | Yes (extend) |
| ROLE-02 | Triage Lead sees only threads in assigned categories | unit | `pytest apps/emails/tests/test_views.py -x -k triage_lead` | No -- Wave 0 |
| ROLE-02 | Triage Lead with no AssignmentRules sees nothing | unit | `pytest apps/emails/tests/test_views.py -x -k triage_lead` | No -- Wave 0 |
| ROLE-02 | Sidebar counts match filtered thread list | unit | `pytest apps/emails/tests/test_views.py -x -k triage_lead` | No -- Wave 0 |
| ROLE-06 | can_assign returns True for admin and triage_lead | unit | `pytest apps/accounts/tests/test_models.py -x` | Yes (extend) |
| ROLE-06 | is_admin_only returns True only for admin | unit | `pytest apps/accounts/tests/test_models.py -x` | Yes (extend) |
| ROLE-06 | Zero inline is_admin patterns remain in views | unit | grep-based verification | No -- Wave 0 |
| ROLE-06 | Triage Lead can assign threads (not 403) | unit | `pytest apps/emails/tests/test_thread_assignment.py -x` | Yes (extend) |
| ROLE-06 | Triage Lead cannot force poll (403) | unit | `pytest apps/emails/tests/test_views.py -x -k force_poll` | No -- Wave 0 |
| ROLE-06 | Triage Lead can view settings (200, readonly) | unit | `pytest apps/emails/tests/test_settings_views.py -x` | Yes (extend) |

### Sampling Rate
- **Per task commit:** `pytest apps/accounts apps/emails -x -q`
- **Per wave merge:** `pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_triage_lead.py` -- covers ROLE-02 (category scoping, sidebar counts, welcome banner)
- [ ] `apps/accounts/tests/test_models.py` -- extend with can_assign, is_admin_only, can_triage, can_approve_users property tests
- [ ] `apps/accounts/tests/test_team.py` -- extend with triage_lead promotion/demotion tests
- [ ] `apps/emails/tests/test_views.py` or `test_triage_lead.py` -- triage_lead permission enforcement (assign allowed, force_poll denied, settings read-only)
- [ ] `conftest.py` -- add `triage_lead_user` fixture

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `apps/accounts/models.py` (User.Role, is_admin_role property)
- Direct codebase analysis: `apps/emails/views.py` (28 is_admin check locations verified by grep)
- Direct codebase analysis: `apps/accounts/views.py` (_require_admin, change_role, dev_login)
- Direct codebase analysis: `apps/emails/models.py` (AssignmentRule model at line 401)
- Direct codebase analysis: `templates/` (12 files with is_admin template checks)
- Prior research: `.planning/research/PITFALLS.md`, `ARCHITECTURE.md`, `STACK.md`

### Secondary (MEDIUM confidence)
- Django TextChoices documentation (standard Django 4.2 feature, well-documented)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - zero new dependencies, all changes to existing code
- Architecture: HIGH - direct codebase analysis, every file read and verified
- Pitfalls: HIGH - 28 check locations verified by grep, template audit complete
- Permission classification: HIGH - each of 28 locations manually categorized per CONTEXT.md decisions

**Research date:** 2026-03-16
**Valid until:** Indefinite (codebase-specific, no external dependency concerns)
