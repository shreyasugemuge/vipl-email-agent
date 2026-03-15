# Phase 2: Assignment Enforcement - Research

**Researched:** 2026-03-16
**Domain:** Django view-level permission enforcement + HTMX UI gating for thread assignment
**Confidence:** HIGH

## Summary

Phase 2 enforces assignment permissions now that Phase 1 has established the Triage Lead role and `can_assign`/`is_admin_only` helpers. The work is mechanical: modify `assign_thread_view` to accept gatekeeper/admin (using `can_assign`), add a new `reassign_thread_view` for member self-reassignment with mandatory reason, update the detail panel template to show role-conditional UI (assign dropdown vs claim/reassign buttons), and update the context menu. A new `REASSIGNED_BY_MEMBER` ActivityLog action type stores the mandatory reason in the `detail` field.

The codebase already has all the building blocks. `assign_thread()` and `claim_thread()` service functions handle the ORM logic. The `_build_thread_detail_context()` function passes `is_admin` and `can_claim` to templates. The `_thread_detail.html` template already has an `{% if is_admin %}` / `{% else %}` branch for the assignment section. The `_context_menu.html` has the same pattern. Phase 1 will have replaced `is_admin` with `can_assign` throughout, so Phase 2 extends the template logic with new member-specific branches.

**Primary recommendation:** Add `REASSIGNED_BY_MEMBER` action to ActivityLog, create `reassign_thread()` service function with mandatory reason enforcement, add `reassign_thread_view` endpoint, and update two templates (`_thread_detail.html`, `_context_menu.html`) with role-conditional assignment UI.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Inline textarea for mandatory reason appears in the detail panel when member clicks "Reassign" on a thread assigned to them
- Reason is required (non-empty, no minimum length) -- server-side enforced
- Member can only reassign to users who share CategoryVisibility for that thread's category (not anyone active)
- Dedicated `REASSIGNED_BY_MEMBER` ActivityLog action type -- distinct from regular `REASSIGNED` for easy filtering/reporting
- Admin/gatekeeper reassign does NOT require a reason (optional note field, same as today)
- Members: "Assign to" dropdown completely hidden in detail panel
- Members see "Claim" button on unassigned threads (in their categories) and "Reassign" button on threads assigned to them
- Gatekeepers/admins: full "Assign to" dropdown with all active users, optional note field
- Right-click context menu is role-conditional (admin/gatekeeper: full assign submenu; member on unassigned: claim; member on own thread: reassign; member on others' threads: no assignment options)
- Member viewing thread assigned to someone else: read-only view (can see detail, activity log, add notes -- but no assignment/status/priority actions)
- Server-side guard returns 403 with role-aware message: "Only gatekeepers and admins can assign threads to other users."
- Members can only claim threads matching their CategoryVisibility entries
- If thread's category is outside member's visibility: claim button shown disabled with tooltip "This thread is outside your assigned categories"
- Members cannot claim threads already assigned to someone else
- Gatekeepers bypass CategoryVisibility like admins

### Claude's Discretion
- Exact placement and styling of the inline reassign reason textarea
- How the disabled claim button tooltip is implemented (title attr vs custom tooltip)
- Server-side validation error message wording details
- Whether to add a client-side character counter on the reason field

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ROLE-03 | Only gatekeeper and admin can assign threads to other users | `assign_thread_view` guard using `can_assign` helper from Phase 1; server returns 403 for members |
| ROLE-04 | Members can self-claim unassigned threads in their category | Existing `claim_thread()` service + `claim_thread_view` already handle this; extend gatekeeper bypass |
| ROLE-05 | Members can reassign threads only with mandatory reason (logged in ActivityLog) | New `reassign_thread()` service function + `REASSIGNED_BY_MEMBER` action type + new view endpoint |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Web framework | Already in use, no changes |
| HTMX | 2.0 (CDN) | Partial page updates | Already in use for all assignment flows |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| nh3 | existing | HTML sanitization | Already in use in detail panel |

**No new dependencies.** All changes use existing Django views, models, templates, and HTMX patterns.

## Architecture Patterns

### What Phase 1 Delivers (Prerequisites)

Phase 2 assumes these exist from Phase 1:
- `User.Role.TRIAGE_LEAD` choice on the User model
- `user.can_assign` property: True for admin and triage_lead
- `user.is_admin_only` property: True only for admin
- `user.can_triage` property: True for admin and triage_lead
- All 28+ `is_admin` checks in views.py replaced with appropriate helpers
- Templates use `can_assign` instead of `is_admin` for assignment gating
- Gatekeeper/triage_lead bypasses CategoryVisibility in `claim_thread()`

### Modified Files

```
apps/emails/models.py                    # Add REASSIGNED_BY_MEMBER to ActivityLog.Action
apps/emails/services/assignment.py       # Add reassign_thread() function
apps/emails/views.py                     # Add reassign_thread_view; update assign_thread_view guard
apps/emails/urls.py                      # Add reassign URL pattern
templates/emails/_thread_detail.html     # Role-conditional assignment UI (3 branches)
templates/emails/_context_menu.html      # Role-conditional menu items
```

### Pattern 1: Three-Branch Assignment UI in Detail Panel

**What:** The template assignment section branches into three states based on user role and thread ownership.
**When to use:** `_thread_detail.html` action bar

```html
<!-- Branch 1: Admin/Gatekeeper (can_assign) -->
{% if can_assign %}
    <!-- Full "Assign to" dropdown with all active users + optional note -->
    <form hx-post="{% url 'emails:assign_thread' thread.pk %}" ...>
        <select name="assignee_id">...</select>
        <input name="note" placeholder="Note (optional)">
        <button type="submit">Assign</button>
    </form>

<!-- Branch 2: Member viewing their own assigned thread -->
{% elif thread.assigned_to == request.user %}
    <!-- "Reassign" button that reveals inline textarea for mandatory reason -->
    <button onclick="toggleReassignForm(this)">Reassign</button>
    <form hx-post="{% url 'emails:reassign_thread' thread.pk %}" style="display:none">
        <select name="assignee_id"><!-- Category-visible users only --></select>
        <textarea name="reason" required placeholder="Why are you reassigning?"></textarea>
        <button type="submit">Reassign</button>
        <button type="button" onclick="cancelReassign(this)">Cancel</button>
    </form>

<!-- Branch 3: Member on unassigned thread (can_claim) -->
{% elif can_claim %}
    <form hx-post="{% url 'emails:claim_thread' thread.pk %}">
        <button type="submit">Claim Thread</button>
    </form>

<!-- Branch 4: Member on someone else's thread (read-only) -->
{% else %}
    <span>Assigned to {{ thread.assigned_to.get_full_name }}</span>
{% endif %}
```

### Pattern 2: Service Function with Mandatory Reason

**What:** `reassign_thread()` enforces that members provide a non-empty reason.
**When to use:** When a member (non-admin, non-gatekeeper) reassigns a thread they own.

```python
def reassign_thread(thread, new_assignee, reassigned_by, reason):
    """Member-initiated reassignment with mandatory reason.

    Validates:
    1. reassigned_by is the current assigned_to (owns the thread)
    2. reason is non-empty after stripping whitespace
    3. new_assignee has CategoryVisibility for thread's category

    Creates REASSIGNED_BY_MEMBER ActivityLog with reason in detail field.
    """
    if not reason or not reason.strip():
        raise ValueError("A reason is required when reassigning a thread.")

    if thread.assigned_to != reassigned_by:
        raise PermissionError("You can only reassign threads assigned to you.")

    # Check new_assignee has CategoryVisibility for this thread's category
    has_visibility = CategoryVisibility.objects.filter(
        user=new_assignee, category=thread.category,
    ).exists()
    if not has_visibility:
        raise PermissionError(
            f"{new_assignee.get_full_name()} does not handle {thread.category} threads."
        )

    old_assignee_name = _user_display(thread.assigned_to)

    thread.assigned_to = new_assignee
    thread.assigned_by = reassigned_by
    thread.assigned_at = timezone.now()
    thread.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "updated_at"])

    ActivityLog.objects.create(
        thread=thread,
        user=reassigned_by,
        action=ActivityLog.Action.REASSIGNED_BY_MEMBER,
        detail=reason.strip(),
        old_value=old_assignee_name,
        new_value=_user_display(new_assignee),
    )

    # Fire-and-forget notifications (same pattern as assign_thread)
```

### Pattern 3: Context Menu Role Gating

**What:** Context menu shows different assignment actions based on role and thread state.
**When to use:** `_context_menu.html`

```html
{# Admin/Gatekeeper: full assign submenu #}
{% if can_assign %}
    <button>Assign to...</button>
{% endif %}

{# Member on unassigned thread in their category: claim #}
{% if can_claim and not can_assign %}
    <button hx-post="{% url 'emails:claim_thread' thread.pk %}">Claim</button>
{% endif %}

{# Member on own thread: reassign option #}
{% if not can_assign and thread.assigned_to == request.user %}
    <button>Reassign...</button>
{% endif %}

{# Member on others' threads: no assignment options shown at all #}
```

### Pattern 4: Read-Only View for Members on Others' Threads

**What:** When a member views a thread assigned to someone else, status/priority/category edit actions are hidden.
**When to use:** `_thread_detail.html` status actions section

The existing pattern is:
```html
{% if thread.assigned_to == request.user or is_admin %}
    <!-- Status action buttons -->
{% endif %}
```

Phase 1 will have changed `is_admin` to `can_assign` or similar. Phase 2 must verify this pattern extends to inline edit dropdowns for category, priority, and status.

### Pattern 5: Disabled Claim Button with Tooltip

**What:** When a member sees an unassigned thread outside their categories, the claim button is disabled with a tooltip explaining why.
**When to use:** `_thread_detail.html` and `_context_menu.html`

The `_build_thread_detail_context` already computes `can_claim` using CategoryVisibility. Extend it to also compute `claim_disabled_reason` for threads where the member lacks visibility:

```python
can_claim = False
claim_disabled = False
if thread.assigned_to is None:
    if user.can_assign:  # admin/gatekeeper
        can_claim = True
    else:
        has_vis = CategoryVisibility.objects.filter(
            user=user, category=thread.category
        ).exists()
        if has_vis:
            can_claim = True
        else:
            claim_disabled = True  # show disabled button with tooltip
```

Template:
```html
{% if claim_disabled %}
<button disabled title="This thread is outside your assigned categories"
        class="... opacity-50 cursor-not-allowed">
    Claim Thread
</button>
{% endif %}
```

### Anti-Patterns to Avoid
- **Checking `is_admin` directly:** All permission checks must use the Phase 1 helpers (`can_assign`, `is_admin_only`, `can_triage`). Zero new inline `is_admin` checks.
- **Allowing member to reassign to any user:** Member reassignment targets must be filtered by CategoryVisibility for the thread's category. Do not pass `User.objects.filter(is_active=True)` to the member reassign dropdown.
- **Skipping server-side reason validation:** Even though the textarea has `required`, always validate `reason.strip()` on the server. HTMX requests can be crafted manually.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Permission checking | Custom decorator per view | `user.can_assign` property from Phase 1 | Consistent, tested, single source of truth |
| Activity logging | Manual SQL or custom fields | `ActivityLog.objects.create()` with `REASSIGNED_BY_MEMBER` action | Established pattern, already rendered in timeline |
| Category-filtered user list | Custom query in template | `CategoryVisibility.objects.filter(category=thread.category)` queryset | Already used in claim_thread; same pattern |
| HTMX response pattern | Custom JSON response | `render_to_string` for detail_html + OOB card_html pattern | Every assignment view uses this exact pattern |

## Common Pitfalls

### Pitfall 1: Forgetting Server-Side Guard on assign_thread_view
**What goes wrong:** Template hides the "Assign to" dropdown for members, but the POST endpoint still accepts requests from any authenticated user.
**Why it happens:** UI-only gating without corresponding server check.
**How to avoid:** `assign_thread_view` must check `request.user.can_assign` and return 403 if False. The existing `if not is_admin:` check (line 1306) must have been replaced by Phase 1 to `if not user.can_assign:`.
**Warning signs:** Member can assign by crafting a POST request to `/emails/threads/<pk>/assign/`.

### Pitfall 2: Member Reassign Dropdown Showing All Active Users
**What goes wrong:** Member sees users who don't handle the thread's category, leading to invalid reassignment.
**Why it happens:** Passing `User.objects.filter(is_active=True)` to the reassign form instead of filtering by CategoryVisibility.
**How to avoid:** Query `CategoryVisibility.objects.filter(category=thread.category).values_list('user', flat=True)` then filter users by those IDs. Exclude the current user (they already have it).
**Warning signs:** Member can reassign to someone with no CategoryVisibility for that category.

### Pitfall 3: Missing REASSIGNED_BY_MEMBER in ActivityLog.Action Choices
**What goes wrong:** Django migration error or ActivityLog creation fails with invalid choice.
**Why it happens:** Forgetting to add the new choice to TextChoices and create a migration.
**How to avoid:** Add `REASSIGNED_BY_MEMBER = "reassigned_by_member", "Reassigned by Member"` to `ActivityLog.Action` and run `makemigrations`.
**Warning signs:** `ValidationError` on ActivityLog creation in tests.

### Pitfall 4: Gatekeeper Not Bypassing CategoryVisibility in claim_thread
**What goes wrong:** Gatekeeper cannot claim threads outside their AssignmentRule categories.
**Why it happens:** `claim_thread()` only bypasses for `is_staff or role == admin`. Phase 1 should have extended this to include triage_lead/gatekeeper.
**How to avoid:** Verify Phase 1 updated `claim_thread()` to use `user.can_assign` or `user.can_triage` for the bypass check.
**Warning signs:** Gatekeeper gets PermissionError when claiming a thread.

### Pitfall 5: OOB Card Not Updating After Reassignment
**What goes wrong:** After member reassigns, the thread card in the list still shows old assignee.
**Why it happens:** Forgetting to include OOB card_html in the HTMX response.
**How to avoid:** Follow the exact same response pattern as `assign_thread_view`: return `detail_html + card_html` where card_html is rendered with `oob: True`.
**Warning signs:** Thread card shows stale assignee until page refresh.

### Pitfall 6: Read-Only Enforcement Incomplete
**What goes wrong:** Member viewing someone else's thread can still change status/priority/category via the inline edit dropdowns.
**Why it happens:** Only blocking the "Assign" action but not the status/priority/category edit actions.
**How to avoid:** The detail panel must also hide inline edit dropdowns and status buttons when `not can_assign and thread.assigned_to != request.user`. Check all three edit views (`edit_category`, `edit_priority`, `edit_status`) have server-side guards.
**Warning signs:** Member can change priority on a thread assigned to someone else.

## Code Examples

### New URL Pattern
```python
# apps/emails/urls.py
path("threads/<int:pk>/reassign/", views.reassign_thread_view, name="reassign_thread"),
```

### New View
```python
@login_required
@require_POST
def reassign_thread_view(request, pk):
    """Member self-reassignment with mandatory reason."""
    user = request.user
    thread = get_object_or_404(Thread, pk=pk)

    # Only the currently assigned member (non-admin/non-gatekeeper) uses this
    if user.can_assign:
        return HttpResponseForbidden("Use the standard assign endpoint instead.")

    if thread.assigned_to != user:
        return HttpResponseForbidden("You can only reassign threads assigned to you.")

    reason = request.POST.get("reason", "").strip()
    if not reason:
        return HttpResponseForbidden("A reason is required when reassigning.")

    assignee_id = request.POST.get("assignee_id")
    if not assignee_id:
        return HttpResponseForbidden("Missing assignee_id.")

    assignee = get_object_or_404(User, pk=assignee_id, is_active=True)

    try:
        reassign_thread(thread, assignee, user, reason)
    except (ValueError, PermissionError) as exc:
        return HttpResponseForbidden(str(exc))

    # Reset read state for new assignee
    ThreadReadState.objects.update_or_create(
        thread=thread, user=assignee,
        defaults={"is_read": False, "read_at": None},
    )

    # Reload and return detail + OOB card (standard pattern)
    thread = Thread.objects.select_related("assigned_to", "assigned_by").get(pk=pk)
    team_members = []  # Member doesn't get team_members list
    detail_context = _build_thread_detail_context(thread, request, False, team_members)
    detail_html = render_to_string("emails/_thread_detail.html", detail_context, request=request)
    card_html = render_to_string("emails/_thread_card.html", {"thread": thread, "oob": True}, request=request)
    return _HttpResponse(detail_html + card_html)
```

### Category-Filtered User List for Member Reassign
```python
# In _build_thread_detail_context or the reassign view
from apps.emails.models import CategoryVisibility

# Users who share CategoryVisibility for this thread's category (excluding current user)
reassign_candidates = User.objects.filter(
    is_active=True,
    pk__in=CategoryVisibility.objects.filter(
        category=thread.category
    ).values_list("user_id", flat=True)
).exclude(pk=request.user.pk).order_by("first_name", "username")
```

### Inline Reassign Form (HTMX)
```html
<!-- Revealed when member clicks "Reassign" button -->
<div id="reassign-form-{{ thread.pk }}" style="display: none" class="mt-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
    <form hx-post="{% url 'emails:reassign_thread' thread.pk %}"
          hx-target="#thread-detail-panel" hx-swap="innerHTML">
        {% csrf_token %}
        <label class="block text-[11px] font-medium text-slate-600 mb-1">Reassign to</label>
        <select name="assignee_id" required class="w-full text-[11px] border border-slate-200 rounded-md px-2 py-1.5 mb-2">
            <option value="">Select team member...</option>
            {% for candidate in reassign_candidates %}
            <option value="{{ candidate.pk }}">{{ candidate.get_full_name|default:candidate.username }}</option>
            {% endfor %}
        </select>
        <label class="block text-[11px] font-medium text-slate-600 mb-1">Reason (required)</label>
        <textarea name="reason" required rows="2" placeholder="Why are you reassigning this thread?"
                  class="w-full text-[11px] border border-slate-200 rounded-md px-2 py-1.5 mb-2 resize-none"></textarea>
        <div class="flex gap-1.5">
            <button type="submit" hx-disabled-elt="this"
                    class="px-3 py-1.5 text-[10px] font-bold text-white bg-amber-500 rounded-md hover:bg-amber-600 transition-colors">
                Reassign
            </button>
            <button type="button" onclick="this.closest('[id^=reassign-form]').style.display='none'"
                    class="px-3 py-1.5 text-[10px] font-bold text-slate-500 bg-white border border-slate-200 rounded-md hover:bg-slate-50 transition-colors">
                Cancel
            </button>
        </div>
    </form>
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `is_admin` inline checks | `user.can_assign` / `user.is_admin_only` helpers | Phase 1 (this milestone) | All Phase 2 code uses helpers, not raw checks |
| Single REASSIGNED action | Separate REASSIGNED_BY_MEMBER action | Phase 2 | Enables filtering/reporting on member-initiated reassignments |
| Admin-only assignment | Admin + Gatekeeper assignment | Phase 2 | Gatekeepers can dispatch threads without admin involvement |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails/tests/test_thread_assignment.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROLE-03 | Admin/gatekeeper can assign; member gets 403 | unit + integration | `pytest apps/emails/tests/test_assignment_enforcement.py -x` | No -- Wave 0 |
| ROLE-04 | Member can claim unassigned thread in their category; gatekeeper bypasses CategoryVisibility | unit | `pytest apps/emails/tests/test_thread_assignment.py::TestClaimThread -x` | Partial -- extend existing |
| ROLE-05 | Member reassign requires reason; reason stored in ActivityLog; REASSIGNED_BY_MEMBER action | unit + integration | `pytest apps/emails/tests/test_assignment_enforcement.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_assignment_enforcement.py apps/emails/tests/test_thread_assignment.py apps/emails/tests/test_context_menu.py -x`
- **Per wave merge:** `pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_assignment_enforcement.py` -- covers ROLE-03, ROLE-05 (new file)
  - `test_admin_can_assign_thread` -- admin assigns, 200 response
  - `test_gatekeeper_can_assign_thread` -- triage_lead assigns, 200 response
  - `test_member_cannot_assign_thread` -- member POST to assign, 403 response
  - `test_member_reassign_own_thread_with_reason` -- member reassigns, reason in ActivityLog
  - `test_member_reassign_without_reason_fails` -- empty reason, 403 response
  - `test_member_reassign_others_thread_fails` -- member on others' thread, 403
  - `test_member_reassign_targets_filtered_by_category` -- only CategoryVisibility users
  - `test_reassign_creates_reassigned_by_member_log` -- REASSIGNED_BY_MEMBER in ActivityLog
  - `test_member_read_only_on_others_thread` -- cannot change status/priority on others' thread
  - `test_context_menu_gatekeeper_sees_assign` -- gatekeeper sees "Assign to" in context menu
  - `test_context_menu_member_own_thread_sees_reassign` -- member sees "Reassign" on own thread
  - `test_context_menu_member_others_thread_no_assignment` -- no assignment options on others' thread
  - `test_disabled_claim_outside_category` -- disabled button with tooltip text
- [ ] Extend `conftest.py` -- add `triage_lead_user` fixture (depends on Phase 1 completing first)
- [ ] Extend `test_thread_assignment.py::TestClaimThread` -- add `test_gatekeeper_bypasses_visibility`

## Open Questions

1. **Phase 1 helper naming**
   - What we know: Phase 1 CONTEXT says `can_assign`, `is_admin_only`, `can_triage`, `can_approve_users`
   - What's unclear: Exact implementation (model properties vs standalone functions)
   - Recommendation: Phase 2 plan should reference these by name; implementation adapts to whatever Phase 1 delivers

2. **Template variable for `can_assign` in context**
   - What we know: Phase 1 will replace `is_admin` context variable in `_build_thread_detail_context`
   - What's unclear: Whether Phase 1 passes `can_assign` as a separate variable or replaces `is_admin`
   - Recommendation: Phase 2 implementation reads the Phase 1 code before starting template work

3. **Member reassign endpoint naming**
   - What we know: Need a new URL for member reassignment
   - What's unclear: Whether to use a separate endpoint (`/reassign/`) or overload the existing `/assign/` with different validation based on role
   - Recommendation: Separate endpoint (`/reassign/`) -- cleaner separation of concerns, easier to test, clearer intent

## Sources

### Primary (HIGH confidence -- direct codebase analysis)
- `apps/emails/services/assignment.py` -- `assign_thread()`, `claim_thread()` function signatures and patterns (lines 378-508)
- `apps/emails/views.py` -- `assign_thread_view` (line 1301), `claim_thread_view` (line 1393), `_build_thread_detail_context` (line 853)
- `apps/emails/models.py` -- `ActivityLog.Action` TextChoices (line 191), `CategoryVisibility` model (line 476)
- `templates/emails/_thread_detail.html` -- Assignment section with `is_admin` / `can_claim` branching (lines 120-171)
- `templates/emails/_context_menu.html` -- Role-conditional menu items (lines 24-54)
- `apps/emails/tests/test_thread_assignment.py` -- Existing test patterns for assign/claim
- `apps/emails/tests/test_context_menu.py` -- Existing context menu test patterns
- `conftest.py` -- `admin_user`, `member_user` fixtures, `create_thread()` factory

### Secondary (MEDIUM confidence -- Phase 1 design documents)
- `.planning/phases/01-role-permission-foundation/01-CONTEXT.md` -- Phase 1 decisions on helper naming, role naming
- `.planning/research/SUMMARY.md` -- Architecture approach, pitfall catalog

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all existing patterns
- Architecture: HIGH -- every file and function location verified by reading source
- Pitfalls: HIGH -- identified from direct code reading of current permission patterns
- Test strategy: HIGH -- existing test patterns well-established, clear gaps identified

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable Django codebase, no external dependencies in flux)
