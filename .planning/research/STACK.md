# Technology Stack: v2.6.0 Gatekeeper Role + Irrelevant Emails

**Project:** VIPL Email Agent
**Researched:** 2026-03-15
**Scope:** Additions only -- existing stack (Django 4.2, HTMX 2.0, Tailwind v4, etc.) is validated and unchanged.

## Key Finding: Zero New Dependencies

Every v2.6.0 feature is implementable with the existing stack. The codebase already has all the primitives: `User.Role` TextChoices for roles, `ActivityLog` for audit, `ChatNotifier` for alerts, `SystemConfig` for thresholds, APScheduler for periodic checks. Adding libraries would be over-engineering for a 4-5 user app.

**requirements.txt: NO CHANGES.**

---

## Feature-by-Feature Stack Analysis

### 1. Gatekeeper Role (RBAC Addition)

**What's needed:** A third role alongside admin/member. Gatekeepers can assign threads, mark irrelevant, see all emails -- but cannot manage users or system config.

**Stack addition: NONE.**

| Concern | Solution | Why |
|---------|----------|-----|
| Role definition | Add `GATEKEEPER = "gatekeeper"` to `User.Role` TextChoices | Extends existing pattern, one-line change + migration |
| Permission helpers | Add properties on User: `can_assign`, `can_mark_irrelevant`, `can_manage_users` | Centralizes logic currently scattered as `is_admin` in 25+ view locations |
| Data migration | Seed script to optionally promote existing users | Django RunPython in migration, same pattern as SystemConfig seeds |

**Why NOT Django's built-in permissions framework (groups/permissions)?**
- 4-5 total users. Three roles with simple, well-defined boundaries.
- `User.Role` TextChoices is already used in 25+ permission checks across views.py.
- Django permissions adds 4 join tables (`auth_permission`, `auth_group`, `auth_group_permissions`, `auth_user_user_permissions`), admin UI configuration, and permission caching -- all unnecessary overhead.
- The existing pattern (`is_admin = user.is_staff or user.role == User.Role.ADMIN`) is readable, testable, and grep-able. Extending it to include gatekeeper is trivial.

**Why NOT django-guardian (object-level permissions)?**
- No object-level permission needs. A gatekeeper can assign ANY thread, not specific ones.
- Object-level perms add per-object permission rows -- massive overhead for zero benefit here.

**Why NOT django-rules (predicate-based permissions)?**
- Nice library, but it adds a dependency for logic that's 5 lines of Python.
- The predicate approach (`@rules.predicate def can_assign(user): ...`) is elegant but the codebase already has a simpler pattern that works.

**What changes in code:**

```python
# apps/accounts/models.py -- Role addition
class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    GATEKEEPER = "gatekeeper", "Gatekeeper"  # NEW
    MEMBER = "member", "Team Member"

# Permission helpers (replace scattered is_admin checks)
@property
def can_assign(self):
    """Admin and gatekeeper can assign threads."""
    return self.is_staff or self.role in (self.Role.ADMIN, self.Role.GATEKEEPER)

@property
def can_mark_irrelevant(self):
    """Admin and gatekeeper can mark threads irrelevant."""
    return self.can_assign  # Same permission boundary

@property
def can_manage_users(self):
    """Only admin can manage team members."""
    return self.is_staff or self.role == self.Role.ADMIN
```

**Confidence:** HIGH -- direct codebase analysis confirms TextChoices pattern is the right extension point.

---

### 2. Assignment Permission Enforcement

**What's needed:** Only gatekeeper/admin can assign. Members can reassign threads assigned to them, but must provide a mandatory reason.

**Stack addition: NONE.**

| Concern | Solution | Why |
|---------|----------|-----|
| Assign permission | Check `user.can_assign` in views before calling `assign_thread()` | Replaces scattered `is_admin` checks with single property |
| Reassign with reason | Add `reason` parameter to `assign_thread()`, validate non-empty for members | `ActivityLog.detail` field already stores notes -- reason goes there |
| View enforcement | Replace 25+ `is_admin` checks with `user.can_assign` or `user.can_manage_users` | Mechanical find-and-replace, no architectural change |
| Template enforcement | Pass `can_assign` to template context, hide/show assign buttons | Already passing `is_admin` to templates; rename/extend |
| Context menu | Server-rendered partial already checks permissions (`is_admin` guard) | Change guard to `can_assign`, menu items adapt per role |

**Current permission check pattern (25+ locations in views.py):**
```python
# CURRENT: scattered, admin-only
is_admin = user.is_staff or user.role == User.Role.ADMIN
if not is_admin:
    return HttpResponseForbidden("Admin only")
```

**New pattern:**
```python
# NEW: centralized, role-aware
if not user.can_assign:
    return HttpResponseForbidden("Gatekeeper or admin required")
```

**Reassign reason enforcement:**
```python
# In assign_thread view
if user.role == User.Role.MEMBER and thread.assigned_to == user:
    # Member reassigning their own thread -- reason required
    reason = request.POST.get("reason", "").strip()
    if not reason:
        return HttpResponse("Reason required for reassignment", status=400)
```

**Confidence:** HIGH -- pure Python logic change, no library involvement.

---

### 3. Count-Based Threshold Alerts (Unassigned Count)

**What's needed:** When unassigned thread count exceeds a configurable threshold, alert via dashboard badge + Google Chat notification.

**Stack addition: NONE.**

| Concern | Solution | Why |
|---------|----------|-----|
| Threshold config | `SystemConfig` keys: `unassigned_alert_threshold` (INT), `unassigned_alert_enabled` (BOOL) | Already have typed key-value config store |
| Periodic check | New APScheduler job (interval trigger, e.g. every 15min) | Already running 3 jobs (poll, retry, heartbeat); adding a 4th is trivial |
| Alert dedup | `SystemConfig` key `last_unassigned_alert_at` (timestamp) + minimum interval | Prevents alert spam; same pattern as `last_poll_epoch` persistence |
| Chat notification | `ChatNotifier` text message or Cards v2 card | Already have Google Chat integration; new card template or simple text |
| Dashboard badge | OOB swap of unassigned count badge on sidebar | Already using HTMX OOB swaps for unread count badge |

**New SystemConfig keys:**
| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `unassigned_alert_enabled` | BOOL | `false` | Feature toggle |
| `unassigned_alert_threshold` | INT | `10` | Alert when unassigned count >= this |
| `unassigned_alert_interval_minutes` | INT | `30` | Minimum minutes between alerts |
| `last_unassigned_alert_at` | INT | `0` | Epoch timestamp of last alert (dedup) |

**Scheduler integration (in `run_scheduler` management command):**
```python
# Add alongside existing jobs
scheduler.add_job(
    check_unassigned_alert,
    trigger="interval",
    minutes=15,
    id="unassigned_alert",
    name="Unassigned count alert check",
)
```

**Alert check function (in new or existing service):**
```python
def check_unassigned_alert():
    if not SystemConfig.get("unassigned_alert_enabled", False):
        return
    threshold = SystemConfig.get("unassigned_alert_threshold", 10)
    count = Thread.objects.filter(
        assigned_to__isnull=True, status=Thread.Status.NEW, is_deleted=False
    ).count()
    if count >= threshold:
        # Check dedup interval
        # Send Chat notification
        # Update last_unassigned_alert_at
```

**Confidence:** HIGH -- all components exist, just wiring them together.

---

### 4. Close-With-Reason (Mark Irrelevant)

**What's needed:** Gatekeeper/admin can mark a thread as irrelevant (a type of close). Requires a reason. Removes thread from unassigned count. Feeds AI learning.

**Stack addition: NONE.**

| Concern | Solution | Why |
|---------|----------|-----|
| Close reason storage | `close_reason` CharField on Thread model | Simple field, avoids over-normalization |
| Who closed | `closed_by` ForeignKey on Thread model | Audit trail for gatekeeper actions |
| Irrelevant vs normal close | `close_reason` being non-empty distinguishes irrelevant from normal close | No new status needed; `CLOSED` status + reason is sufficient |
| Activity log | New `MARKED_IRRELEVANT` action in `ActivityLog.Action` choices | Extends existing TextChoices, one line |
| AI learning | Gatekeeper corrections feed existing distillation pipeline | `distillation.py` already processes `ActivityLog` entries |
| UI | Close-with-reason modal (HTMX partial form) | Same pattern as assign dropdown |
| Unassigned count | `Thread.objects.filter(assigned_to__isnull=True, status=NEW)` naturally excludes CLOSED | No special handling needed |

**New Thread model fields:**
```python
# On Thread model
close_reason = models.TextField(blank=True, default="",
    help_text="Reason for closing, required when marking irrelevant")
closed_by = models.ForeignKey(
    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
    null=True, blank=True, related_name="closed_threads")
```

**New service function:**
```python
def mark_irrelevant(thread, reason, closed_by):
    """Mark thread as irrelevant (close with reason). Gatekeeper/admin only."""
    thread.status = Thread.Status.CLOSED
    thread.close_reason = reason
    thread.closed_by = closed_by
    thread.save(update_fields=["status", "close_reason", "closed_by", "updated_at"])
    ActivityLog.objects.create(
        thread=thread, user=closed_by,
        action=ActivityLog.Action.MARKED_IRRELEVANT,
        detail=reason, old_value="new", new_value="closed",
    )
```

**Why NOT a separate IrrelevantThread model or new Status choice?**
- A closed thread is a closed thread. The reason distinguishes WHY it was closed.
- Adding `IRRELEVANT` as a Status would require updating every status filter, every queryset, every template conditional. The `close_reason` field is simpler.
- Activity log with `MARKED_IRRELEVANT` action provides the audit trail without polluting Status choices.

**Confidence:** HIGH -- standard Django model field addition + service function.

---

## Alternatives Considered and Rejected

| Need | Rejected Option | Why Not |
|------|----------------|---------|
| RBAC | Django groups + permissions | 4 join tables, admin UI config, permission caching -- overkill for 3 roles, 5 users |
| RBAC | django-guardian | Object-level perms not needed; gatekeepers operate on ALL threads |
| RBAC | django-rules | Nice predicate API, but adds a dependency for 5 lines of property logic |
| Alerting | Celery + Redis | Massive infra addition; APScheduler already runs 3 jobs fine |
| Alerting | django-notifications | Full notification inbox system; we just need a Chat webhook POST |
| Close reason | Separate ClosureRecord model | Over-normalized; TextField on Thread + ActivityLog is sufficient |
| Close reason | New `IRRELEVANT` Status choice | Would require updating every status filter/queryset/template across the app |
| Bulk assign | django-bulk-update | Django's `queryset.update()` handles bulk natively |

---

## Complete Dependency Change

### requirements.txt: NO CHANGES

```bash
# Nothing to install. Existing dependencies cover all v2.6.0 features.
# Only Django migrations needed:
python manage.py makemigrations accounts emails
python manage.py migrate
```

### Frontend: NO CHANGES

No new CDN scripts. HTMX + Tailwind + existing vanilla JS patterns handle everything.

### New Vanilla JS: ~20 lines

| Feature | JS Needed | Lines (est.) |
|---------|-----------|-------------|
| Close-with-reason modal show/hide | Toggle visibility | ~10 |
| Reassign reason validation (client-side hint) | Required field check before submit | ~10 |

---

## Integration Points with Existing Stack

| Existing Component | How v2.6.0 Features Integrate |
|-------------------|-------------------------------|
| `User.Role` TextChoices | Add `GATEKEEPER` choice |
| `User` model properties | Add `can_assign`, `can_mark_irrelevant`, `can_manage_users` |
| `views.py` (25+ `is_admin` checks) | Replace with `user.can_assign` / `user.can_manage_users` |
| `assignment.py` service | Add `mark_irrelevant()` function, add reason param to reassign |
| `Thread` model | Add `close_reason`, `closed_by` fields |
| `ActivityLog.Action` | Add `MARKED_IRRELEVANT` choice |
| `SystemConfig` | Add threshold/alert config keys (seeded via migration) |
| `run_scheduler` command | Add `check_unassigned_alert` job |
| `ChatNotifier` | Add unassigned alert card/text method |
| `distillation.py` | Process `MARKED_IRRELEVANT` logs for AI learning |
| `_context_menu.html` | Add "Mark Irrelevant" option (gatekeeper/admin only) |
| Templates (assign buttons) | Gate on `can_assign` instead of `is_admin` |
| Settings page (team tab) | Add gatekeeper role option in user management |

---

## What NOT to Add

| Temptation | Why Resist |
|-----------|-----------|
| Django REST Framework | No SPA, no mobile app, no API consumers. HTMX partials are the API. |
| Celery + Redis | 4-5 users, APScheduler already handles background tasks. |
| django-guardian / django-rules | 3 roles, 5 users. Properties on User model are sufficient. |
| Any new Python package | Zero new dependencies. Django ORM + existing services cover everything. |
| Any new JS library | HTMX + vanilla JS. No Alpine, no React, no npm. |

---

## Sources

- Direct codebase analysis: `apps/accounts/models.py` (User.Role TextChoices), `apps/emails/models.py` (Thread, ActivityLog), `apps/emails/views.py` (25+ `is_admin` checks), `apps/emails/services/assignment.py` (assign/reassign functions)
- `requirements.txt` -- current dependency list (no changes needed)
- `.planning/PROJECT.md` -- v2.6.0 feature requirements
- `apps/core/models.py` -- SystemConfig key-value store pattern
