# Architecture Patterns

**Domain:** Gatekeeper role + irrelevant email features for Django email triage app
**Researched:** 2026-03-15

## Recommended Architecture

The gatekeeper role integrates into the existing system through three layers: (1) User model role expansion, (2) permission enforcement in views + assignment service, (3) new scheduler job for unassigned count alerts. No new Django apps needed. No new services needed. Every change touches existing components.

### Component Map: What Changes Where

| Component | Change Type | What Changes |
|-----------|-------------|--------------|
| `apps/accounts/models.py` | **Modify** | Add `GATEKEEPER` to `Role.choices`, update `is_admin_role` property |
| `apps/emails/views.py` | **Modify** | Replace `is_admin` checks with `can_assign` / `can_close_irrelevant` helpers |
| `apps/emails/services/assignment.py` | **Modify** | Add reassign-with-reason enforcement for members, add `mark_irrelevant()` |
| `apps/emails/models.py` | **Modify** | Add `IRRELEVANT` to `Thread.Status`, add `close_reason` field |
| `apps/emails/models.py` | **Modify** | Add `MARKED_IRRELEVANT` to `ActivityLog.Action` |
| `apps/emails/services/chat_notifier.py` | **Modify** | Add `notify_unassigned_alert()` method |
| `apps/emails/management/commands/run_scheduler.py` | **Modify** | Add unassigned count check job |
| `templates/emails/_context_menu.html` | **Modify** | Add "Mark Irrelevant" action, gate on `can_close_irrelevant` |
| `templates/emails/_thread_detail.html` | **Modify** | Add irrelevant button, show close reason, gate assignment on `can_assign` |
| `templates/accounts/_user_row.html` | **Modify** | Add `gatekeeper` option to role dropdown |
| `templates/base.html` | **Modify** | Update sidebar gating for gatekeeper access |
| `apps/accounts/views.py` | **Modify** | Add `gatekeeper` to valid roles in `change_role()` |
| `apps/core/models.py` (SystemConfig seed) | **Modify** | Add `unassigned_alert_threshold` config key |

**No new files needed** except one migration per app (accounts for role field, emails for Thread fields).

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| User model | Role storage (admin/gatekeeper/member) | All views, assignment service |
| Permission helpers | `can_assign(user)`, `can_close_irrelevant(user)`, `requires_reason(user)` | Views, templates |
| Assignment service | Enforce assignment rules, handle reassign-with-reason | Views, scheduler, chat notifier |
| Thread model | Store `close_reason`, `IRRELEVANT` status | Views, assignment service, templates |
| Chat notifier | Send unassigned count alerts | Scheduler job |
| Scheduler | Periodic unassigned count check | Chat notifier, SystemConfig |
| ActivityLog | Record `MARKED_IRRELEVANT` actions with reason | Assignment service |

## Data Flow

### Assignment Flow (Current vs. New)

**Current:**
```
User clicks Assign -> view checks `is_admin` -> assign_thread() -> ActivityLog + Chat
```

**New:**
```
User clicks Assign -> view checks `can_assign(user)` -> assign_thread() -> ActivityLog + Chat

where can_assign = admin OR gatekeeper

Member clicks Reassign -> view checks `requires_reason(user)` -> if member, reason required
  -> assign_thread(note=reason) -> ActivityLog with reason + Chat
```

### Mark Irrelevant Flow (New)

```
Gatekeeper/Admin clicks "Mark Irrelevant" -> modal/input for reason
  -> POST to mark_irrelevant view -> validates can_close_irrelevant(user)
  -> change_thread_status(thread, "irrelevant", reason=reason)
  -> Thread.status = "irrelevant", Thread.close_reason = reason
  -> ActivityLog(action=MARKED_IRRELEVANT, detail=reason)
  -> Thread removed from unassigned count
```

### Unassigned Count Alert Flow (New)

```
Scheduler (every 1 min via heartbeat, with 30-min cooldown):
  -> count = Thread.objects.filter(assigned_to=None, status__in=["new", "acknowledged"]).count()
  -> threshold = SystemConfig.get("unassigned_alert_threshold", 10)
  -> if count >= threshold AND not recently_alerted (cooldown 30min):
      -> ChatNotifier.notify_unassigned_alert(count)
      -> SystemConfig.set("last_unassigned_alert_at", now)
  -> Dashboard: badge always shows count, independent of alerts
```

## Patterns to Follow

### Pattern 1: Permission Helper Functions (not decorators)

**What:** Centralize role-based permission checks in helper functions, not Django permissions framework.

**Why:** The codebase already uses inline `is_admin = user.is_staff or user.role == User.Role.ADMIN` in 25+ locations. Extracting to helpers is the minimal-diff approach that matches existing patterns.

**Implementation:**
```python
# apps/emails/views.py (top-level, next to existing _require_admin)

def can_assign(user):
    """Can this user assign/reassign threads? Admin or Gatekeeper."""
    return user.is_staff or user.role in (User.Role.ADMIN, User.Role.GATEKEEPER)

def can_close_irrelevant(user):
    """Can this user mark threads as irrelevant? Admin or Gatekeeper."""
    return user.is_staff or user.role in (User.Role.ADMIN, User.Role.GATEKEEPER)

def requires_reassign_reason(user):
    """Does this user need to provide a reason when reassigning? Members only."""
    return user.role == User.Role.MEMBER
```

**Where used:** Every view that currently checks `is_admin` for assignment-related actions. The `is_admin` variable stays for non-assignment admin checks (settings, team management, inspector).

### Pattern 2: Extend Role.choices Without Breaking Data

**What:** Add `GATEKEEPER = "gatekeeper", "Gatekeeper"` to `User.Role.choices`. CharField max_length is already 10, "gatekeeper" is 10 chars -- fits exactly.

**Why:** TextChoices is the existing pattern. No new model, no M2M permissions table. The team is 4-5 people; a simple role string is appropriate.

**Implementation:**
```python
class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    GATEKEEPER = "gatekeeper", "Gatekeeper"
    MEMBER = "member", "Team Member"
```

**Migration:** `AlterField` on `role` to update choices. No data migration needed -- existing users stay admin/member.

### Pattern 3: Thread Status Extension for Irrelevant

**What:** Add `IRRELEVANT = "irrelevant", "Irrelevant"` to `Thread.Status.choices`, plus a `close_reason` TextField.

**Why:** "Irrelevant" is a terminal state like "closed" but semantically distinct. It should not count in unassigned metrics, SLA calculations, or reopen flows. Separate status makes queries clean.

**Implementation:**
```python
class Status(models.TextChoices):
    NEW = "new", "New"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    CLOSED = "closed", "Closed"
    IRRELEVANT = "irrelevant", "Irrelevant"

close_reason = models.TextField(blank=True, default="")
```

**Query impact:** All existing `status__in=["new", "acknowledged"]` queries for "open" threads already exclude "closed" and will naturally exclude "irrelevant". The sidebar count queries in `thread_list` use explicit open statuses, so no changes needed there.

### Pattern 4: Scheduler Job Piggyback

**What:** Add unassigned count check to the existing heartbeat job (runs every 1 minute), with a 30-minute cooldown stored in SystemConfig.

**Why:** No new APScheduler job needed. Heartbeat already runs frequently, already has `close_old_connections()`, and is fire-and-forget. The count query is trivial (indexed fields). Cooldown prevents alert fatigue.

**Implementation:**
```python
def _heartbeat_job():
    """Write timestamp + check unassigned count alert."""
    close_old_connections()
    # ... existing heartbeat code ...

    try:
        _check_unassigned_alert()
    except Exception:
        logger.warning("Unassigned alert check failed")

def _check_unassigned_alert():
    threshold = SystemConfig.get("unassigned_alert_threshold", 0)
    if not threshold:
        return  # disabled

    count = Thread.objects.filter(
        assigned_to__isnull=True,
        status__in=["new", "acknowledged"],
    ).count()

    if count < threshold:
        return

    # Cooldown: don't alert more than once per 30 min
    last_alert = SystemConfig.get("last_unassigned_alert_at", "")
    if last_alert:
        from datetime import datetime
        last = datetime.fromisoformat(last_alert)
        if (timezone.now() - last).total_seconds() < 1800:
            return

    # Send alert
    webhook_url = (SystemConfig.get("chat_webhook_url", "")
                   or os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", ""))
    if webhook_url:
        notifier = ChatNotifier(webhook_url=webhook_url)
        notifier.notify_unassigned_alert(count, threshold)
        SystemConfig.set("last_unassigned_alert_at", timezone.now().isoformat())
```

### Pattern 5: Reassign-With-Reason in View Layer

**What:** Enforce mandatory reason when a member reassigns a thread they own. The `assign_thread()` function already accepts a `note` parameter -- enforcement happens in the view layer.

**Why:** The assignment service is a thin action layer. Business rules about "who can do what" belong in views. The service just records whatever note is passed.

**View enforcement:**
```python
@login_required
@require_POST
def assign_thread_view(request, pk):
    user = request.user

    # Gatekeepers and admins can assign freely
    if can_assign(user):
        pass  # proceed
    # Members can only reassign threads assigned to them, with reason
    elif thread.assigned_to == user:
        note = request.POST.get("note", "").strip()
        if not note:
            return HttpResponse("Reason required for reassignment", status=400)
    else:
        return HttpResponseForbidden("You cannot assign threads.")
    ...
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Django Permissions Framework

**What:** Using `django.contrib.auth.permissions` or `django-guardian` for object-level permissions.

**Why bad:** The codebase has zero Django permissions usage. Adding `has_perm()` checks alongside existing role checks creates two permission systems. For 4-5 users with 3 roles, it's massive overkill.

**Instead:** Keep the role CharField pattern. Add helper functions that check `user.role in (...)`.

### Anti-Pattern 2: Separate Gatekeeper Model or Profile

**What:** Creating a `GatekeeperProfile` model or separate permissions table.

**Why bad:** Adds a join to every permission check. The existing User model already has a `role` field designed for this exact purpose. Adding a choice to TextChoices is a one-line change.

**Instead:** `GATEKEEPER = "gatekeeper", "Gatekeeper"` in `Role.choices`.

### Anti-Pattern 3: Frontend-Only Permission Gating

**What:** Hiding UI elements with `{% if is_gatekeeper %}` without server-side enforcement.

**Why bad:** HTMX POST requests bypass template conditionals. Any user can craft a POST to the assign endpoint.

**Instead:** Every view that gates on role must check server-side. Templates hide UI for UX, views enforce for security.

### Anti-Pattern 4: New Status "irrelevant" Without close_reason

**What:** Adding IRRELEVANT status but storing the reason only in ActivityLog.detail.

**Why bad:** When displaying a thread's current state, you'd need to query ActivityLog to find the reason. Denormalizing `close_reason` onto Thread is the pattern this codebase follows (denormalized preview fields on Thread from latest Email).

**Instead:** `close_reason` TextField on Thread, written when status changes to irrelevant or closed.

### Anti-Pattern 5: Polling Dashboard for Unassigned Alerts

**What:** Using JavaScript polling on the dashboard to check unassigned counts and show alerts.

**Why bad:** Dashboard already has sidebar counts updated on navigation. Alert needs to reach the gatekeeper even when they're not on the dashboard (hence Google Chat).

**Instead:** Server-side check in scheduler, Chat webhook for notification. Dashboard badge is a bonus from existing sidebar counts.

## Integration Point Inventory

Every location where `is_admin` is currently checked, categorized by required change:

### Replace with `can_assign()` (assignment-related)

| Location | Line | Current Check | New Check |
|----------|------|---------------|-----------|
| `views.py` `assign_thread_view` | ~1304 | `is_admin` | `can_assign(user)` |
| `views.py` `assign_email_view` | ~514 | `is_admin` | `can_assign(user)` |
| `views.py` `accept_thread_suggestion` | ~689 | `is_admin` | `can_assign(user)` |
| `views.py` `reject_thread_suggestion` | ~748 | `is_admin` | `can_assign(user)` |
| `views.py` `accept_ai_suggestion` | ~608 | `is_admin` | `can_assign(user)` |
| `views.py` `reject_ai_suggestion` | ~649 | `is_admin` | `can_assign(user)` |
| `views.py` `edit_ai_summary` | ~1087 | `is_admin` | `can_assign(user)` |
| `_thread_detail.html` assignment form | ~120 | `{% if is_admin %}` | `{% if can_assign %}` |
| `_context_menu.html` "Assign to..." | ~24 | `{% if is_admin %}` | `{% if can_assign %}` |

### Keep as `is_admin` (admin-only operations)

| Location | Reason |
|----------|--------|
| `views.py` `inspect` | Dev inspector = admin only |
| `views.py` `force_poll` | Dangerous operation = admin only |
| `accounts/views.py` `team_list`, `change_role`, etc. | Team management = admin only |
| `_context_menu.html` "Whitelist Sender" | Spam config = admin only |
| `base.html` Settings/Inspector sidebar links | Admin tools |

### New `can_close_irrelevant()` checks

| Location | What |
|----------|------|
| `views.py` new `mark_irrelevant` view | Server-side enforcement |
| `_thread_detail.html` | "Mark Irrelevant" button |
| `_context_menu.html` | "Mark Irrelevant" menu item |

### Template context changes

Views that pass `is_admin` to templates need to also pass `can_assign` as a separate context variable. The cleanest approach: compute both in each view function that renders thread detail/list, pass both to template context. Do NOT replace `is_admin` -- it is still needed for admin-only UI (settings links, whitelist button, inspector).

## Suggested Build Order

Based on dependency analysis:

### Phase 1: Role + Permissions Foundation
1. Add `GATEKEEPER` to `User.Role.choices` (migration)
2. Update `is_admin_role` property to include gatekeeper where appropriate
3. Add `can_assign()`, `can_close_irrelevant()`, `requires_reassign_reason()` helpers
4. Update `dev_login` view to support gatekeeper role
5. Update `change_role` view to accept gatekeeper
6. Update `_user_row.html` role dropdown
7. Tests for role model changes

### Phase 2: Assignment Permission Enforcement
1. Replace `is_admin` with `can_assign()` in all assignment views (9 locations)
2. Pass `can_assign` context variable to templates
3. Update `_thread_detail.html` and `_context_menu.html`
4. Add reassign-with-reason enforcement for members
5. Tests for permission enforcement

### Phase 3: Mark Irrelevant
1. Add `IRRELEVANT` to `Thread.Status.choices` + `close_reason` field (migration)
2. Add `MARKED_IRRELEVANT` to `ActivityLog.Action.choices`
3. Add `mark_irrelevant()` function to assignment service
4. Add `mark_irrelevant` view + URL
5. Add UI: button in detail panel + context menu item
6. Verify sidebar counts exclude irrelevant
7. Tests

### Phase 4: Unassigned Count Alerts
1. Add `unassigned_alert_threshold` to SystemConfig seed migration
2. Add `notify_unassigned_alert()` to ChatNotifier
3. Add `_check_unassigned_alert()` to scheduler heartbeat
4. Add threshold config to Settings page
5. Tests

**Why this order:** Phase 1 is foundation -- everything depends on the role existing. Phase 2 uses the role for assignment gating. Phase 3 uses the role for irrelevant gating. Phase 4 is independent but benefits from Phase 3 (irrelevant threads excluded from count).

## Scalability Considerations

Not applicable -- 4-5 users, 50-100 emails/day. The unassigned count query uses indexed fields (`assigned_to`, `status`) and runs once per minute. No performance concerns.

## Sources

- Direct codebase analysis (HIGH confidence -- read all relevant source files)
- `apps/accounts/models.py`: User.Role TextChoices, max_length=10
- `apps/emails/views.py`: 25+ `is_admin` check locations catalogued
- `apps/emails/services/assignment.py`: assign_thread(), claim_thread() patterns
- `apps/emails/models.py`: Thread.Status, ActivityLog.Action choices
- `apps/emails/management/commands/run_scheduler.py`: heartbeat job structure
- `templates/emails/_context_menu.html`: role-aware UI gating pattern
- `templates/accounts/_user_row.html`: role dropdown pattern
