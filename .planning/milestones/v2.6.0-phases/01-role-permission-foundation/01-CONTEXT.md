# Phase 1: Role + Permission Foundation - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Triage Lead role to the User model and centralize all 28+ scattered `is_admin` permission checks into reusable helpers. After this phase, every permission check in the codebase uses `can_assign()`, `is_admin_only()`, or similar helpers — zero inline `is_admin` checks remain. Gatekeeper sees threads filtered to their assigned categories.

</domain>

<decisions>
## Implementation Decisions

### Permission Classification
- **Settings page**: Triage Lead gets read-only access (can view, cannot edit)
- **Dev Inspector**: Triage Lead gets view-only access (poll history, MIS stats — no force poll)
- **Team page**: Triage Lead can view members and approve pending new users, but cannot change roles
- **Reports page**: Full access (core to understanding volume, SLA, workload)
- **Assignment**: Triage Lead can assign/reassign (same as admin) — this is Phase 2 but the helpers must support it
- **Thread visibility**: Category-scoped via AssignmentRules (not `can_see_all_emails`)

### Permission Helper Design
- Replace all 28+ `is_admin = user.is_staff or user.role == User.Role.ADMIN` patterns
- New helpers on User model:
  - `can_assign` — True for admin and triage_lead (used in assignment views)
  - `is_admin_only` — True only for admin (settings write, role management, force poll)
  - `can_triage` — True for admin and triage_lead (mark irrelevant, bulk actions)
  - `can_approve_users` — True for admin and triage_lead (team page approve)
- Each of the 28+ checks must be classified into one of these helpers based on what it gates

### Role Visibility in UI
- Display label: **"Triage Lead"** (not "Gatekeeper" or "Assigner")
- Badge color: **Blue** (distinct from admin's plum)
- Welcome banner: Assignment-focused copy — "Your job: keep the queue empty. Assign threads, dismiss irrelevant ones, help the AI learn."
- Dev login dropdown: Add "triage_lead" test user alongside admin/member
- Team page role dropdown: Add "Triage Lead" option for admin to promote/demote

### Category Scoping
- Triage Lead visibility scoped via existing **AssignmentRule** model — no new model needed
- No AssignmentRules configured = **see nothing** (strict — forces admin to configure before role is useful)
- Sidebar shows **category pills** under Triage Lead's name (makes scope visible)
- Thread list filters to categories matching the Triage Lead's AssignmentRules

### Role Field Migration
- Widen `role` CharField from `max_length=10` to `max_length=20` (future-proof)
- DB value: `"triage_lead"` (matches display label, readable in raw queries)
- `Role.TRIAGE_LEAD = "triage_lead", "Triage Lead"`
- `can_see_all_emails` stays **False** for Triage Lead — visibility comes from AssignmentRules
- No auto-config on promotion — admin must set up AssignmentRules separately

### Claude's Discretion
- Exact helper method signatures and where to put them (model properties vs utility functions)
- How to handle the `is_staff` sync (currently `is_staff = (role == admin)`)
- Template refactoring approach (conditional blocks vs template tags)
- Test data setup for the new role

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Role model
- `apps/accounts/models.py` — User model with Role TextChoices, `is_admin_role` property, `can_see_all_emails` field
- `apps/accounts/views.py` — Team page views: `team_page`, `update_user_role`, `_is_admin` helper at line 65

### Permission checks (28+ locations to refactor)
- `apps/emails/views.py` — All 28 `is_admin` check locations (lines 101, 291, 495, 514, 574, 608, 649, 689, 748, 808, 1026, 1087, 1116, 1192, 1216, 1250, 1289, 1304, 1351, 1406, 1554, 1619, 1660, 1693, 2145, 2288, 2377, 2441)
- `apps/accounts/views.py` — Role checks in team management views
- `apps/core/views.py` — Health endpoint admin checks

### Templates (12 files with role checks)
- `templates/emails/thread_list.html`, `templates/emails/_thread_detail.html`, `templates/emails/_email_card.html`, `templates/emails/_assign_dropdown.html`, `templates/emails/_context_menu.html`
- `templates/accounts/team.html`, `templates/accounts/_user_row.html`
- `templates/base.html`, `templates/registration/dev_login.html`
- `templates/emails/_editable_status.html`, `templates/emails/_email_detail.html`, `templates/emails/email_list.html`

### Assignment rules
- `apps/emails/services/assignment.py` — AssignmentRule logic, category-based assignment

### Research
- `.planning/research/PITFALLS.md` — 13 pitfalls, permission scatter is #1 risk
- `.planning/research/ARCHITECTURE.md` — Integration points and build order
- `.planning/research/STACK.md` — Zero new deps, helper design approach

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `User.is_admin_role` property: Already exists, can be extended with `is_triage_lead` and compound helpers
- `_is_admin()` function in `accounts/views.py:65`: Single existing helper — model for the new centralized helpers
- `ActivityLog` model: Ready to log role changes
- `AssignmentRule` model: Already maps categories to users — reuse for Triage Lead scoping
- Welcome banner logic in `base.html`: Already role-aware (admin vs member), extend for triage_lead
- Dev login in `registration/dev_login.html`: Already has admin/member users, add triage_lead

### Established Patterns
- Role checks use `user.is_staff or user.role == User.Role.ADMIN` — must be replaced uniformly
- Template role checks use `{% if is_admin %}` context variable passed from views
- `update_user_role` view syncs `is_staff` with role — extend for triage_lead (`is_staff=False`)
- Sidebar navigation conditionally shows/hides items based on `is_admin` context var

### Integration Points
- Every view that sets `is_admin` in context must be updated to also pass role-specific booleans or a richer permission object
- `_user_row.html` hardcodes two `<option>` tags for admin/member — must add triage_lead
- Team page `update_user_role` must handle triage_lead promotion/demotion
- Sidebar thread count queries must be filtered by AssignmentRule categories for triage_lead

</code_context>

<specifics>
## Specific Ideas

- Internal DB value `triage_lead` matching the display label "Triage Lead" — consistency for raw SQL queries
- Category pills in sidebar showing which categories the Triage Lead is scoped to
- Strict "see nothing" behavior when no AssignmentRules exist — prevents accidental full access

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-role-permission-foundation*
*Context gathered: 2026-03-15*
