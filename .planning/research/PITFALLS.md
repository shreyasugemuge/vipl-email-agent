# Domain Pitfalls: v2.6.0 Gatekeeper Role + Irrelevant Emails

**Domain:** RBAC expansion + close-with-reason for existing Django email triage app
**Researched:** 2026-03-15

## Critical Pitfalls

### Pitfall 1: Permission Checks Scattered Across 30+ Locations

**What goes wrong:** Adding a gatekeeper role that can assign (like admin) but cannot access settings (like member) requires updating every permission check in the codebase. Miss one and you have a privilege escalation or a broken feature.

**Why it happens:** The codebase uses an inline pattern `is_admin = user.is_staff or user.role == User.Role.ADMIN` repeated verbatim in 25+ locations across `views.py`, plus `_require_admin()` helper in both `accounts/views.py` and `emails/views.py`. There is no centralized permission system. Each view decides independently what "admin" means.

**Consequences:** Gatekeeper either gets locked out of assignment (if you only update some checks) or gains access to settings/config (if you make `is_admin` include gatekeeper globally). Both are wrong.

**Prevention:**
- Before writing any code, audit every permission check. The current codebase has these distinct permission surfaces:
  - **Assignment actions** (assign, accept/reject AI suggestion): 7 views -- gatekeeper SHOULD have access
  - **Status changes** (change status, inline edit status): 3 views -- gatekeeper SHOULD have access
  - **Content editing** (edit summary, edit category/priority): 3 views -- gatekeeper SHOULD have access
  - **Settings/config** (inboxes, config editor, whitelist, blocked senders, SLA, assignment rules): 8 views -- gatekeeper should NOT have access
  - **Dev/admin tools** (inspector, force poll): 2 views -- gatekeeper should NOT have access
  - **Team management** (toggle active, change role, categories): 4 views in accounts -- gatekeeper should NOT have access
  - **Spam management** (mark spam/not-spam): 2 views -- gatekeeper SHOULD have access
  - **Thread visibility** (thread list queryset filtering): 1 view -- gatekeeper needs `can_see_all_emails`
- Replace the inline `is_admin` pattern with two distinct helpers:
  - `can_assign(user)` -- admin OR gatekeeper (for triage/assignment actions)
  - `is_admin_only(user)` -- admin only (for settings, team management, dev tools)
- Add `can_assign` as a property on the User model so templates can use `{% if user.can_assign %}`
- Create a single pass that replaces ALL 25+ inline checks with the correct helper

**Detection:** Grep for `is_admin` in views.py and templates after migration. Zero remaining inline checks = done.

### Pitfall 2: Role Field max_length=10 Fits "gatekeeper" Exactly

**What goes wrong:** The role field is `CharField(max_length=10)`. The string "gatekeeper" is exactly 10 characters. It fits, but any future role name longer than 10 chars will silently truncate or error.

**Why it happens:** Original design only anticipated "admin" (5) and "member" (6).

**Consequences:** Works today, but the tight fit signals the field should be widened. More importantly, if you typo the migration or choice value, you get a silent truncation on some databases.

**Prevention:**
- Widen `max_length` to 20 in the same migration that adds the GATEKEEPER choice. One migration, two changes.
- Use the TextChoices enum value, never a raw string, everywhere.

**Detection:** Migration reviewer catches it. Test that `User.objects.create(role="gatekeeper")` round-trips correctly.

### Pitfall 3: Existing Data Migration -- Who Becomes Gatekeeper?

**What goes wrong:** You add the role choice but nobody has it. The app works but there is no gatekeeper, so nothing actually changes. Or worse, you write a data migration that auto-assigns the gatekeeper role to the wrong user, breaking their admin access.

**Why it happens:** Schema migration adds the choice. Data migration (if any) assigns it. These are separate concerns that can get confused.

**Consequences:** Deploying without a plan for who gets the gatekeeper role means the feature ships but is unused until someone manually changes a role in admin.

**Prevention:**
- Do NOT auto-assign gatekeeper role in a data migration. The team is 4-5 people -- this is a manual admin action.
- DO update the team management UI (role dropdown) to include the gatekeeper option in the same PR.
- DO update the dev_login view to offer a gatekeeper login option for testing.
- Add a deployment note: "After deploy, admin sets gatekeeper role via Team page."

**Detection:** QA checklist item: "Can I set a user to gatekeeper in Team management?"

### Pitfall 4: Template Hardcoded Role Strings

**What goes wrong:** Templates contain hardcoded `'admin'` and `'member'` strings in option values and conditionals. The team management dropdown (`_user_row.html`) has exactly two `<option>` tags. The gatekeeper option will be missing unless templates are updated.

**Why it happens:** The role dropdown in `_user_row.html` is hand-coded HTML, not dynamically generated from `Role.choices`.

**Consequences:** Admin cannot set anyone to gatekeeper role from the Team page. Feature is unusable without direct DB access.

**Prevention:**
- Template audit: `_user_row.html` lines 26-27 hardcode `admin` and `member` options. Replace with a loop over `Role.choices` passed in context.
- `dev_login.html` lines 43 and 60 hardcode two role buttons. Add a third.
- `_assign_dropdown.html`, `_email_detail.html`, `_thread_detail.html` show "(Admin)" badge next to admin users in assignment dropdowns. Add "(Gatekeeper)" badge for the new role.
- `team.html` JS filter has `'admin'` case. Add `'gatekeeper'` case or make the filter data-driven.

**Detection:** Grep templates for hardcoded `'admin'` and `'member'` strings. Each one needs review.

## Moderate Pitfalls

### Pitfall 5: Member Self-Claim Bypass

**What goes wrong:** Members can currently self-claim unassigned threads via `claim_thread_view`. If the goal is "only gatekeeper/admin can assign," does claim count as assignment? If yes, members lose a feature they have today. If no, members can bypass the gatekeeper by claiming everything themselves.

**Why it happens:** The claim feature was built for a world where anyone could grab unassigned work. Gatekeeper role implies centralized assignment control.

**Consequences:** Either members feel restricted (claim removed) or gatekeeper role is undermined (members self-serve).

**Prevention:**
- Decide explicitly: members CAN still self-claim (gatekeeper role is about directing, not gatekeeping claims). This preserves existing behavior and avoids breaking working patterns.
- OR: members can claim only from categories they have visibility for (already enforced) but gatekeeper can assign any category (like admin).
- The PROJECT.md says "members reassign with mandatory reason" -- this implies members can still act on their own threads, just with accountability. Keep self-claim but log it prominently.

**Detection:** Test with member login: can they still claim? Is the claim logged in activity?

### Pitfall 6: Alert Storm from Unassigned Count Threshold

**What goes wrong:** Configuring unassigned threshold to 5, then a batch of 20 emails arrives. System fires alerts on every poll cycle (every 5 minutes) because count stays above threshold. Gatekeeper gets 50 Chat messages in an hour.

**Why it happens:** Naive implementation: `if unassigned_count > threshold: send_alert()`. No cooldown, no acknowledgment.

**Consequences:** Alert fatigue. Gatekeeper mutes the Chat space. Alerts become useless.

**Prevention:**
- **Cooldown period**: After firing an alert, suppress for N minutes (configurable, default 30 min). Store `last_unassigned_alert_at` in SystemConfig.
- **Rising threshold only**: Alert when count crosses the threshold going UP, not on every check while above.
- **Dashboard badge is primary**: The badge on the sidebar is always visible. Chat alert is secondary, for when gatekeeper is not in the app.
- **No alert if gatekeeper is active**: If a gatekeeper has loaded the thread list in the last 10 minutes (check ThreadViewer or session), skip Chat alert -- they already know.

**Detection:** Test by setting threshold to 1 and watching how many alerts fire in 15 minutes.

### Pitfall 7: Close-with-Reason Status vs Existing "Closed" Status

**What goes wrong:** The Thread model already has `Status.CLOSED = "closed"`. Adding "mark irrelevant" means either: (a) irrelevant threads get status "closed" with a reason field, or (b) you add a new status like "irrelevant". Option (b) breaks all existing queries that filter by status (reports, sidebar counts, SLA).

**Why it happens:** "Closed" and "irrelevant" are semantically different (closed = handled, irrelevant = not worth handling) but both mean "done, remove from triage queue."

**Consequences:** If you add a new status: every `status="closed"` filter, every stat card that counts "closed", every report query needs updating. If you reuse "closed": you need a separate field for the close reason, and queries filtering "closed" now include irrelevant threads in counts.

**Prevention:**
- Use the existing `CLOSED` status. Add a `close_reason` field on Thread (nullable CharField). Values: `null` (normal close), `"irrelevant"`, `"duplicate"`, `"spam"` (future-proof).
- Sidebar "Closed" view already exists -- irrelevant threads appear there naturally.
- Reports can optionally break down by close_reason.
- This is less invasive: zero changes to existing status filters, one new field, one new UI element.

**Detection:** After implementation, check that "Closed" counts in stat cards and reports still include irrelevant threads (or explicitly exclude them -- decide and be consistent).

### Pitfall 8: Reassignment Reason Not Actually Required

**What goes wrong:** PROJECT.md says "members reassign with mandatory reason." If this is just a frontend `required` attribute on a textarea, the POST endpoint still accepts empty strings. Members bypass by submitting an empty form or calling the endpoint directly.

**Why it happens:** Django views don't validate the "note" parameter -- it's optional in `assign_thread()`.

**Consequences:** Audit trail shows reassignments with no reason, defeating the purpose of requiring accountability.

**Prevention:**
- Server-side validation in the view: if `request.user.role == "member"` and the thread is already assigned to someone else, require non-empty `note` parameter. Return 400 if missing.
- Frontend: textarea with `required` attribute + helpful placeholder ("Why are you reassigning?").
- Admin and gatekeeper bypass the reason requirement (they are the authority).

**Detection:** Test: member POSTs reassignment with empty note. Expect 400, not 200.

### Pitfall 9: is_staff Coupling with Role

**What goes wrong:** The codebase couples `is_staff` with admin role: `target.is_staff = (new_role == User.Role.ADMIN)` in `change_role()`. The OAuth adapter does the same. If gatekeeper needs `is_staff=True` for Django admin access, this logic breaks. If gatekeeper should NOT have `is_staff`, then the `_require_admin` pattern `user.is_staff or user.role == ...` might incorrectly grant gatekeeper admin powers through the `is_staff` path.

**Why it happens:** `is_staff` was originally a proxy for "is admin" and used interchangeably.

**Consequences:** If gatekeeper gets `is_staff=True`, they access Django admin. If `is_staff=False`, the `or user.is_staff` check in views doesn't help them, but that's fine because you're replacing those checks anyway.

**Prevention:**
- Gatekeeper should have `is_staff=False`. They do not need Django admin access.
- When replacing permission checks, remove reliance on `is_staff` for application-level permissions. Use role-based helpers only.
- Update `change_role()` in accounts/views.py: `is_staff` should only be True for admin role.

**Detection:** Create gatekeeper user, verify `is_staff=False`, verify they cannot access `/admin/`.

## Minor Pitfalls

### Pitfall 10: OAuth Adapter Doesn't Know About Gatekeeper

**What goes wrong:** `VIPLSocialAccountAdapter.save_user()` sets new users to `Role.MEMBER`. This is correct -- new Google SSO users should not auto-become gatekeepers. But the superadmin auto-promotion sets `Role.ADMIN`. There's no path from OAuth to gatekeeper.

**Why it happens:** Gatekeeper is an admin-granted role, not an auto-provisioned one.

**Consequences:** None if this is intentional. But if someone expects OAuth to auto-provision gatekeepers, it won't.

**Prevention:** Document that gatekeeper is set manually via Team page. No adapter changes needed.

### Pitfall 11: ActivityLog Missing "Marked Irrelevant" Action

**What goes wrong:** Marking a thread as irrelevant creates a "closed" activity log entry, indistinguishable from a normal close. The audit trail loses context.

**Why it happens:** `change_thread_status()` maps status to action, and "closed" maps to `CLOSED`. There's no "marked_irrelevant" action.

**Consequences:** Activity log shows "closed" for both normal closes and irrelevant dismissals. No way to audit triage decisions.

**Prevention:**
- Add `MARKED_IRRELEVANT = "marked_irrelevant", "Marked Irrelevant"` to `ActivityLog.Action` choices.
- The close-with-reason view should create this specific action instead of using `change_thread_status()`.
- Store the reason text in `ActivityLog.detail`.

**Detection:** Check activity log after marking irrelevant. Should show "Marked Irrelevant" not "Closed."

### Pitfall 12: Bulk Assign UI Without Undo

**What goes wrong:** Gatekeeper selects 15 threads, assigns all to one person, realizes they meant a different person. No undo.

**Why it happens:** Bulk operations are fire-and-forget by nature.

**Prevention:**
- Show confirmation dialog: "Assign 15 threads to {name}?"
- After bulk assign, show toast with "Undo" button (stores previous assignments, reverts on click within 10 seconds).
- Each individual assignment is still logged in ActivityLog, so manual correction is always possible.

**Detection:** Test bulk assign flow end-to-end. Try assigning to wrong person and correcting.

### Pitfall 13: Welcome Banner Role Text Outdated

**What goes wrong:** The welcome banner shows role-specific guidance. It only knows about admin and member. Gatekeeper sees member guidance or nothing.

**Why it happens:** `sessionStorage`/`localStorage` based banner with hardcoded role text in template.

**Prevention:** Update the welcome banner template to include gatekeeper-specific guidance: "You are a triage gatekeeper. Review unassigned threads and assign them to team members."

**Detection:** Log in as gatekeeper, check welcome banner text.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Role model migration | Field too narrow (#2), no data migration needed (#3) | Widen max_length to 20, manual role assignment post-deploy |
| Permission refactor | Scattered checks (#1), is_staff coupling (#9) | Centralize into `can_assign` + `is_admin_only` helpers, audit all 25+ locations |
| Template updates | Hardcoded role strings (#4), welcome banner (#13) | Grep for 'admin'/'member' in templates, make dropdowns dynamic |
| Claim vs assign | Member self-claim conflict (#5) | Decide policy: keep claims, add accountability |
| Unassigned alerts | Alert storm (#6) | Cooldown timer, rising-edge only, dashboard badge primary |
| Mark irrelevant | Status field collision (#7), missing ActivityLog action (#11) | Add close_reason field, new ActivityLog action |
| Reassign with reason | Validation bypass (#8) | Server-side required check for member role |
| Bulk assign | No undo (#12) | Confirmation dialog + undo toast |

## Sources

- Direct codebase audit: `apps/accounts/models.py`, `apps/emails/views.py` (25+ `is_admin` checks), `apps/emails/services/assignment.py`, `apps/accounts/views.py`
- Template audit: 8 template files with `is_admin` references, `_user_row.html` with hardcoded role options
- `PROJECT.md` v2.6.0 requirements (gatekeeper role, mark irrelevant, unassigned alerts)
- Django RBAC patterns (HIGH confidence -- standard Django practice)
- Alert fatigue literature (MEDIUM confidence -- well-established operations pattern)
