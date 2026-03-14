# Phase 4: Assignment Engine + SLA - Research

**Researched:** 2026-03-11
**Domain:** Auto-assignment rules, SLA deadline calculation with business hours, breach alerting, settings UI
**Confidence:** HIGH

## Summary

Phase 4 builds the automation layer: category-based auto-assignment rules, AI fallback suggestions for unmatched emails, two-tier SLA deadlines (acknowledge + respond) with business-hours-only counting, breach detection with 3x daily Chat summaries, and an admin settings page for rule/SLA configuration. All UI goes through the dashboard (no Django admin).

The existing codebase provides strong foundations: the `assign_email()` service function handles assignment + notifications + activity logging, the `ChatNotifier` already posts Cards v2 payloads, APScheduler 3.11 with `CronTrigger` supports the 3x daily summary schedule, and the `SystemConfig` model with JSON value type can store structured SLA/assignment config. The v1 `SLAMonitor` provides a proven pattern for summary-based alerting (not per-ticket spam).

Key technical challenges: (1) business-hours SLA calculation that correctly excludes nights/weekends, (2) the batch auto-assignment job that runs on a delay after pipeline to allow manual override, (3) the self-service claiming flow with category-based visibility, and (4) the settings page with drag-to-reorder priority lists. All are solvable with existing Django + HTMX patterns established in Phases 1-3.

**Primary recommendation:** Build as three layers -- models/migrations first (SLA fields on Email, AssignmentRule + SLAConfig models), then services (auto-assign batch job, SLA calculator, breach checker), then UI (settings page + SLA display on cards/detail + claim button).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Priority list per category: "Sales Inquiry -> Rahul, then Shreyas as backup"
- Always assigns to first person in the list (no workload balancing for rules)
- No availability/on-duty system -- implicit from the priority list order
- If all people in a category's list are gone, email stays unassigned (manager picks up manually)
- Batch assignment: runs as a separate scheduled job after pipeline (not inline with triage) -- gives a window for manual override before auto-assign kicks in
- Rules configured via a custom dashboard settings page (NOT Django admin -- premium UI/UX)
- Team members can claim unassigned emails in categories they're permitted to see
- Category visibility configured per person by admin
- "Claim" button on unassigned email cards within their visible categories
- Admin (manager) sees all categories and can assign anyone
- When no rule matches, AI suggests an assignee (ASGN-04) -- suggest only, manager confirms
- AI runs at triage time (enhances existing ai_suggested_assignee field with workload context)
- AI considers email content + category + each person's open email count
- Display: badge on email card ("AI: Rahul") + detailed suggestion bar in detail panel with Accept/Reject buttons
- Two-tier SLA: acknowledge deadline + respond deadline (pulling SLA-10 forward)
- Priority x Category matrix for deadline hours
- Business hours only clock: 8 AM - 8 PM IST
- Acknowledge deadline: configurable per priority (e.g., CRITICAL=15min, HIGH=30min, MEDIUM=1hr, LOW=2hr)
- Color-coded time remaining: Green (>50%), amber (25-50%), red (<25%), flashing red (breached)
- Shows both acknowledge and respond deadlines
- 3x daily summary at 9 AM, 1 PM, 5 PM IST
- Summary format: counts + top 3 worst offenders
- Recipients: manager gets full summary, each assignee gets personal alert
- Channel: Google Chat only (no email for breach alerts)
- Auto-escalation: breach auto-bumps priority one level
- Priority bump logged in ActivityLog for audit trail
- Dashboard route for assignment rules + SLA config (admin only)
- Category-to-person mapping with drag-to-reorder priority list
- Category visibility per team member
- SLA matrix: acknowledge + respond hours per priority x category
- Premium UI consistent with Phase 3 dashboard design language
- No Django admin UI anywhere -- everything through the dashboard

### Claude's Discretion
- Exact batch job interval for auto-assignment (suggestion: 2-5 minutes)
- Settings page layout and interaction patterns
- Rule test/preview feature (whether to include a dry-run preview after saving rules)
- ActivityLog action types for new events (auto_assigned, claimed, sla_breached, priority_bumped)
- SLA config model design (separate model vs JSON in SystemConfig)
- How to handle SLA for emails that arrive outside business hours

### Deferred Ideas (OUT OF SCOPE)
- AI feedback loop from manual corrections (ASGN-10) -- v2 requirement, not Phase 4
- Gmail thread monitoring for auto-detecting replies (ASGN-11, ASGN-12) -- v2 requirement
- Auto-reassignment on repeated breach (SLA-11) -- v2 requirement
- Workload analytics dashboard (ANLY-02) -- Phase 5 or later
- WhatsApp/SMS for CRITICAL escalations (NOTF-01) -- v2 requirement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ASGN-03 | System auto-assigns emails based on category-to-person mapping rules | AssignmentRule model + batch auto-assign job via APScheduler CronTrigger or interval; assign_email() service already handles assignment + notifications |
| ASGN-04 | System uses AI fallback for emails that don't match any assignment rule | Enhance AIProcessor triage prompt to include workload context; store structured suggestion in ai_suggested_assignee (upgrade from plain string to JSON); Accept/Reject UI in detail panel |
| SLA-02 | System calculates SLA deadline per email based on priority and category | SLA fields on Email model (sla_ack_deadline, sla_respond_deadline); SLAConfig model or SystemConfig JSON for the priority x category matrix; business-hours calculator utility |
| SLA-03 | System detects SLA breaches and posts summary alerts (3x daily) | APScheduler CronTrigger at 9,13,17 IST; breach detection query; ChatNotifier.notify_breach_summary(); follows v1 SLAMonitor pattern exactly |
| SLA-04 | SLA breach alerts manager via Chat + email | CONTEXT.md locked: Chat only (no email for breach alerts); manager gets full summary, assignees get personal alerts |
| INFR-09 | Admin can configure SLA deadlines per category/priority | Settings page with SLA matrix editor; SLAConfig model storing ack + respond hours per priority x category pair |
| INFR-10 | Admin can configure assignment rules (category-to-person mapping) | Settings page with AssignmentRule CRUD; drag-to-reorder priority list per category; category visibility per team member |
</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.29 LTS | Web framework, ORM, migrations | Already the project foundation |
| APScheduler | 3.11.2 | Background job scheduling | Already used for poll/retry/heartbeat jobs |
| django-htmx | 1.17+ | HTMX integration (request.htmx) | Already used for SPA-like partials |
| httpx | installed | HTTP client for Chat webhook | Already used by ChatNotifier |
| anthropic | installed | Claude API for AI fallback | Already used by AIProcessor |
| pytz | installed | IST timezone handling | Already used throughout |

### Supporting (No New Dependencies)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Tailwind CSS v4 | CDN | Styling for settings page + SLA display | All new UI components |
| HTMX 2.0 | CDN | Dynamic interactions (claim, accept/reject, drag-reorder) | All interactive elements |
| Sortable.js | CDN | Drag-to-reorder for assignment priority lists | Settings page rule ordering |

### New Dependency
| Library | Version | Purpose | Justification |
|---------|---------|---------|---------------|
| Sortable.js | 1.15.x | Drag-and-drop reordering | Only viable CDN option for accessible drag-reorder; 3KB gzipped; no build step needed |

**Installation:**
No pip installs needed. Sortable.js via CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.3/Sortable.min.js"></script>
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sortable.js | HTMX drag extension | HTMX Sortable extension exists but is less mature; Sortable.js is the de facto standard |
| Separate SLA models | JSON in SystemConfig | Separate models are better for querying and admin; SystemConfig JSON works but makes queries harder |
| Celery for batch jobs | APScheduler interval job | APScheduler is already running; adding Celery would mean a new dependency + Redis/RabbitMQ |

## Architecture Patterns

### Recommended Project Structure (New Files)
```
apps/emails/
  models.py                      # Add: AssignmentRule, SLAConfig, new Email fields
  services/
    assignment.py                # Extend: auto_assign_email(), claim_email()
    sla.py                       # NEW: SLACalculator, breach detection, business hours math
    chat_notifier.py             # Extend: notify_breach_summary()
    ai_processor.py              # Extend: workload context in prompt
  views.py                       # Extend: settings views, claim endpoint, SLA display
  urls.py                        # Extend: settings routes, claim route
  templatetags/
    email_tags.py                # Extend: sla_color, sla_countdown filters
  management/commands/
    run_scheduler.py             # Extend: add auto-assign job + SLA check jobs
  tests/
    test_auto_assignment.py      # NEW
    test_sla.py                  # NEW
    test_claiming.py             # NEW
    test_settings_views.py       # NEW

templates/emails/
  _email_card.html               # Extend: SLA countdown, AI badge, claim button
  _email_detail.html             # Extend: SLA bar, AI suggestion detail, accept/reject
  settings.html                  # NEW: full-page settings layout
  _assignment_rules.html         # NEW: partial for assignment rules section
  _sla_config.html               # NEW: partial for SLA matrix section
  _category_visibility.html      # NEW: partial for category visibility section
```

### Pattern 1: AssignmentRule Model (Dedicated Model, Not SystemConfig JSON)
**What:** Separate Django model for assignment rules with category, user FK, and priority ordering
**When to use:** When rules need per-row CRUD, ordering, and efficient querying
**Why not SystemConfig JSON:** Need to query "which rules match this category?" efficiently; need FK to User for cascade on delete; need ordering field for drag-reorder

```python
class AssignmentRule(TimestampedModel):
    """Category-to-person assignment rule with priority ordering."""
    category = models.CharField(max_length=100, db_index=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignment_rules",
    )
    priority_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "priority_order"]
        unique_together = [("category", "assignee")]
```

### Pattern 2: SLAConfig Model (Dedicated Model)
**What:** Per priority x category SLA configuration with ack + respond hours
**When to use:** When SLA lookup needs to be fast (per-email at save time) and admin-editable

```python
class SLAConfig(TimestampedModel):
    """SLA deadline configuration per priority x category."""
    priority = models.CharField(max_length=20)  # CRITICAL, HIGH, MEDIUM, LOW
    category = models.CharField(max_length=100)
    ack_hours = models.FloatField(default=1.0, help_text="Hours to acknowledge")
    respond_hours = models.FloatField(default=24.0, help_text="Hours to respond")

    class Meta:
        unique_together = [("priority", "category")]
```

### Pattern 3: CategoryVisibility Model
**What:** Per-user category visibility for self-service claiming
**When to use:** Controls which categories each team member can see and claim from

```python
class CategoryVisibility(TimestampedModel):
    """Which categories a team member can see for self-service claiming."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visible_categories",
    )
    category = models.CharField(max_length=100)

    class Meta:
        unique_together = [("user", "category")]
```

### Pattern 4: Business Hours SLA Calculator
**What:** Utility that calculates SLA deadlines counting only business hours (8 AM - 8 PM IST, Mon-Sat)
**When to use:** Called when email is saved to DB (pipeline) and when checking breach status

```python
def calculate_deadline(start_time, hours, biz_start=8, biz_end=20, biz_days=(0,1,2,3,4,5)):
    """Add `hours` of business time to `start_time`, skipping non-business hours.

    Returns timezone-aware datetime (IST).
    """
    # Convert to IST
    ist_time = start_time.astimezone(IST)
    remaining_minutes = hours * 60

    while remaining_minutes > 0:
        if ist_time.weekday() in biz_days and biz_start <= ist_time.hour < biz_end:
            # In business hours -- advance by 1 minute
            remaining_minutes -= 1
        ist_time += timedelta(minutes=1)

    return ist_time
```

**Optimization note:** The minute-by-minute loop is simple but O(n) where n = hours * 60. For a 24-hour SLA with 12 business hours/day, that's only ~1440 iterations max -- perfectly acceptable. A smarter approach (skip full non-business blocks) adds complexity for negligible gain at this team size.

### Pattern 5: Batch Auto-Assignment Job
**What:** Scheduled job that runs every N minutes, finds unassigned emails, and assigns based on rules
**When to use:** Decoupled from pipeline so manager has a window to manually assign before auto-kick-in

```python
def auto_assign_batch():
    """Find unassigned completed emails and apply assignment rules.

    Runs as APScheduler job every 3 minutes (configurable).
    Only assigns emails that are still status=NEW and unassigned.
    """
    unassigned = Email.objects.filter(
        assigned_to__isnull=True,
        status=Email.Status.NEW,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
    )
    for email in unassigned:
        rules = AssignmentRule.objects.filter(
            category=email.category,
            is_active=True,
            assignee__is_active=True,
        ).order_by("priority_order")

        if rules.exists():
            rule = rules.first()
            assign_email(email, rule.assignee, assigned_by=None, note="Auto-assigned by rule")
```

### Pattern 6: Claim Flow (HTMX POST)
**What:** Team member clicks "Claim" on unassigned email card, HTMX POSTs to claim endpoint
**When to use:** Self-service claiming within permitted categories

```python
def claim_email(email, claimed_by):
    """Team member claims an unassigned email.

    Validates: email is unassigned, user has category visibility.
    Uses assign_email() internally for consistency.
    """
    if email.assigned_to is not None:
        raise ValueError("Email is already assigned")
    # Category visibility check
    if not claimed_by.is_staff and not CategoryVisibility.objects.filter(
        user=claimed_by, category=email.category
    ).exists():
        raise PermissionError("No visibility for this category")
    return assign_email(email, claimed_by, assigned_by=claimed_by, note="Self-claimed")
```

### Anti-Patterns to Avoid
- **Inline auto-assignment in pipeline:** Do NOT call auto_assign inside process_single_email. The CONTEXT.md explicitly requires a delay window for manual override. Use a separate batch job.
- **Per-ticket SLA alerts:** Do NOT alert on each breach individually. The CONTEXT.md and v1 pattern both require 3x daily summaries only.
- **Overcomplicating business hours:** Do NOT use a third-party library for business hours calculation. The rules are simple (8-20 IST, Mon-Sat) and a utility function is sufficient.
- **SLA recalculation on every request:** Calculate SLA deadlines ONCE when email is saved/status changes, store as DateTimeFields. Display logic just computes remaining time from stored deadline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-and-drop reordering | Custom JS drag handlers | Sortable.js CDN | Cross-browser drag-drop is deceptively complex (accessibility, touch support, animation) |
| Cron scheduling for 3x daily | Custom time-checking logic | APScheduler CronTrigger | `CronTrigger(hour='9,13,17', timezone='Asia/Kolkata')` handles DST, missed fires, etc. |
| Assignment + notification | Separate DB write + Chat + email | Existing `assign_email()` service | Already handles all three with fire-and-forget notifications and activity logging |
| Priority/status color coding | New color system | Existing `email_tags.py` filters | `priority_base`, `status_base`, `priority_border` already cover the Tailwind color families |

**Key insight:** The existing service layer (assign_email, change_status, ChatNotifier, ActivityLog) already handles the hard parts of assignment workflow. Phase 4's job is to add the *automation trigger* (rules + batch job) and *SLA layer* on top, not to rebuild the assignment mechanics.

## Common Pitfalls

### Pitfall 1: SLA Deadline Stored as Duration Instead of Absolute Time
**What goes wrong:** Storing "4 hours" instead of "2026-03-11 16:00 IST" means every display recalculates from received_at, and business hours logic runs on every page load.
**Why it happens:** Feels simpler to store hours and compute on the fly.
**How to avoid:** Store `sla_ack_deadline` and `sla_respond_deadline` as DateTimeFields on Email. Calculate once at triage time (in pipeline.save_email_to_db or a post-save signal). Recalculate only if priority/category changes.
**Warning signs:** Template tags doing business-hours math.

### Pitfall 2: Race Condition in Batch Assignment
**What goes wrong:** Manager assigns email manually at the same moment the batch job runs, resulting in double assignment or overwriting the manual choice.
**Why it happens:** Batch job reads unassigned emails, processes them one by one, doesn't check again before saving.
**How to avoid:** Use `Email.objects.filter(pk=email.pk, assigned_to__isnull=True).update(...)` with optimistic locking. Or simpler: re-check `email.refresh_from_db()` and skip if already assigned.
**Warning signs:** ActivityLog showing "auto_assigned" immediately after a manual "assigned" for the same email.

### Pitfall 3: AI Suggestion Prompt Becomes Too Expensive
**What goes wrong:** Adding workload context (open email counts per person) to every triage call increases prompt size and cost.
**Why it happens:** Including full team roster + counts in system prompt on every call.
**How to avoid:** Keep AI suggestion lightweight -- add a short "Team workload" section to the user message (not system prompt, which is cached). Format: "Rahul: 5 open, Priya: 2 open, Shreyas: 8 open". This adds ~50 tokens, negligible cost.
**Warning signs:** Token counts jumping significantly after Phase 4 deployment.

### Pitfall 4: SLA Breach Summary Fires Multiple Times in Same Hour
**What goes wrong:** APScheduler CronTrigger fires, job takes 30 seconds, next minute's cron also fires.
**Why it happens:** CronTrigger with `hour='9,13,17'` fires every minute within those hours by default.
**How to avoid:** Use `CronTrigger(hour='9,13,17', minute=0)` to fire at exactly X:00. Set `max_instances=1` and `coalesce=True` on the job. Also track `_last_summary_hour` like v1 SLAMonitor does.
**Warning signs:** Duplicate Chat messages at summary times.

### Pitfall 5: Category Mismatch Between Rules and AI Triage Output
**What goes wrong:** AI returns "Sales Lead" but assignment rule uses "Sales". No rule matches, email stays unassigned.
**Why it happens:** VALID_CATEGORIES in dtos.py defines exact strings, but admin types slightly different text in settings.
**How to avoid:** Settings page should present a dropdown of VALID_CATEGORIES (from dtos.py), not a free-text field. This ensures assignment rules and SLA configs use the exact same category strings as AI output.
**Warning signs:** Emails with valid categories staying in "unassigned" despite matching rules being configured.

### Pitfall 6: Forgetting to Set SLA Deadlines for Existing Emails
**What goes wrong:** After Phase 4 deployment, all existing emails have NULL SLA deadlines. The breach checker queries for breached emails but finds none (NULL < now is False in SQL).
**Why it happens:** Migration adds fields but doesn't backfill.
**How to avoid:** Include a data migration that calculates and sets SLA deadlines for all existing emails with `processing_status=COMPLETED`. Or accept that existing emails won't have SLA tracking (document this in release notes).
**Warning signs:** SLA dashboard shows 0 breaches when there should be some.

## Discretion Recommendations

### Batch Job Interval: 3 minutes
**Reasoning:** 2 minutes is too aggressive (manager barely has time to see the email before auto-assign fires). 5 minutes means a 5-10 minute delay between email arrival and assignment notification. 3 minutes is a good middle ground -- enough time for manager to manually assign if they're watching, fast enough that assignees get notified promptly.

### ActivityLog Action Types
```python
class Action(models.TextChoices):
    ASSIGNED = "assigned", "Assigned"
    REASSIGNED = "reassigned", "Reassigned"
    AUTO_ASSIGNED = "auto_assigned", "Auto-Assigned"
    CLAIMED = "claimed", "Claimed"
    STATUS_CHANGED = "status_changed", "Status Changed"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    CLOSED = "closed", "Closed"
    SLA_BREACHED = "sla_breached", "SLA Breached"
    PRIORITY_BUMPED = "priority_bumped", "Priority Bumped"
```

### SLA Config Model Design: Dedicated Model (Not JSON in SystemConfig)
**Reasoning:** A dedicated `SLAConfig` model is better because:
1. Django admin/forms give free CRUD without custom JSON serialization
2. Can query efficiently: `SLAConfig.objects.get(priority="HIGH", category="Sales Lead")`
3. unique_together constraint prevents duplicate entries at the DB level
4. Adding fields later (e.g., escalation_hours) is a simple migration

### Emails Arriving Outside Business Hours
**Recommendation:** SLA clock starts at the next business hour opening.
- Email arrives at 11 PM IST Saturday -> SLA clock starts at 8 AM IST Monday
- Email arrives at 6 AM IST Tuesday -> SLA clock starts at 8 AM IST Tuesday
- Email arrives at 2 PM IST Wednesday -> SLA clock starts immediately
This is the fairest approach and matches what the `calculate_deadline` utility naturally produces.

### Rule Test/Preview: Skip for v1
**Reasoning:** A dry-run preview adds UI complexity (modal/panel showing "these 5 emails would match") for minimal value when the team is 3 people with ~8 categories. Admin can see the effect by checking the dashboard after saving rules. Defer to v2 if requested.

### Settings Page Layout
**Recommendation:** Single full-page route `/emails/settings/` with three tabbed sections:
1. **Assignment Rules** -- category dropdown + sortable person list per category
2. **Category Visibility** -- checkbox matrix (users x categories)
3. **SLA Configuration** -- editable table (priority x category -> ack hours + respond hours)

Each tab saves independently via HTMX POST with success toast notification. Consistent with Phase 3 dark sidebar layout.

## Code Examples

### SLA Deadline Calculation (Business Hours)
```python
# Source: Custom utility based on project requirements (8 AM - 8 PM IST, Mon-Sat)
from datetime import timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")
BIZ_START = 8   # 8 AM IST
BIZ_END = 20    # 8 PM IST
BIZ_DAYS = (0, 1, 2, 3, 4, 5)  # Mon-Sat

def calculate_sla_deadline(start_time, hours):
    """Calculate SLA deadline adding only business hours.

    Args:
        start_time: timezone-aware datetime
        hours: float, number of business hours

    Returns:
        timezone-aware datetime (IST) of the deadline
    """
    current = start_time.astimezone(IST)

    # Snap to next business hour if outside business hours
    current = _snap_to_business_hours(current)

    remaining = timedelta(hours=hours)

    while remaining > timedelta(0):
        if current.weekday() not in BIZ_DAYS or current.hour >= BIZ_END:
            # Skip to next business day opening
            current = _next_business_open(current)
            continue

        # Time until end of business day
        eod = current.replace(hour=BIZ_END, minute=0, second=0, microsecond=0)
        available = eod - current

        if remaining <= available:
            current += remaining
            remaining = timedelta(0)
        else:
            remaining -= available
            current = _next_business_open(current)

    return current

def _snap_to_business_hours(dt):
    """If dt is outside business hours, snap to next opening."""
    if dt.weekday() not in BIZ_DAYS or dt.hour >= BIZ_END:
        return _next_business_open(dt)
    if dt.hour < BIZ_START:
        return dt.replace(hour=BIZ_START, minute=0, second=0, microsecond=0)
    return dt

def _next_business_open(dt):
    """Return the next business day at BIZ_START."""
    next_day = (dt + timedelta(days=1)).replace(
        hour=BIZ_START, minute=0, second=0, microsecond=0
    )
    while next_day.weekday() not in BIZ_DAYS:
        next_day += timedelta(days=1)
    return next_day
```

### APScheduler CronTrigger for SLA Summary
```python
# Source: APScheduler 3.11 docs -- CronTrigger for 3x daily
from apscheduler.triggers.cron import CronTrigger

scheduler.add_job(
    _sla_breach_summary_job,
    CronTrigger(hour="9,13,17", minute=0, timezone="Asia/Kolkata"),
    id="sla_breach_summary",
    max_instances=1,
    coalesce=True,
)
```

### Auto-Assignment Batch Job
```python
# Source: Follows established service layer pattern
def auto_assign_batch():
    """Batch auto-assign unassigned emails based on category rules."""
    close_old_connections()

    unassigned = Email.objects.filter(
        assigned_to__isnull=True,
        status=Email.Status.NEW,
        processing_status=Email.ProcessingStatus.COMPLETED,
        is_spam=False,
    ).select_related()

    assigned_count = 0
    for email in unassigned:
        rules = AssignmentRule.objects.filter(
            category=email.category,
            is_active=True,
            assignee__is_active=True,
        ).select_related("assignee").order_by("priority_order")

        if not rules.exists():
            continue

        assignee = rules.first().assignee

        # Optimistic check: re-verify still unassigned (race condition guard)
        updated = Email.objects.filter(
            pk=email.pk, assigned_to__isnull=True
        ).update(
            assigned_to=assignee,
            assigned_at=timezone.now(),
        )
        if updated:
            # Log activity (no assigned_by for auto-assignment)
            ActivityLog.objects.create(
                email=email,
                user=None,
                action=ActivityLog.Action.AUTO_ASSIGNED,
                new_value=_user_display(assignee),
                detail=f"Auto-assigned by category rule: {email.category}",
            )
            # Fire-and-forget notifications
            _notify_assignment(email, assignee)
            assigned_count += 1

    logger.info(f"Auto-assign batch: {assigned_count} emails assigned")
```

### SLA Color Template Filter
```python
# Source: Extends existing email_tags.py pattern
@register.filter
def sla_color(deadline):
    """Return Tailwind color class based on SLA time remaining.

    Green (>50%), amber (25-50%), red (<25%), flashing red (breached).
    """
    if not deadline:
        return "slate"
    now = timezone.now()
    if now >= deadline:
        return "red animate-pulse"  # Breached -- flashing red
    # Need the original duration to compute percentage, but we only have deadline.
    # Simpler: use absolute thresholds
    remaining = (deadline - now).total_seconds()
    if remaining > 7200:    # > 2 hours
        return "emerald"
    elif remaining > 3600:  # 1-2 hours
        return "amber"
    elif remaining > 1800:  # 30min-1hr
        return "orange"
    else:
        return "red"


@register.filter
def sla_countdown(deadline):
    """Return human-readable countdown string (e.g., '2h 15m' or 'BREACHED')."""
    if not deadline:
        return "--"
    now = timezone.now()
    if now >= deadline:
        overdue = now - deadline
        hours = int(overdue.total_seconds() // 3600)
        minutes = int((overdue.total_seconds() % 3600) // 60)
        return f"-{hours}h {minutes}m" if hours else f"-{minutes}m"
    remaining = deadline - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"
```

### Claim Button (HTMX)
```html
<!-- In _email_card.html, shown for unassigned emails where user has category visibility -->
{% if not email.assigned_to and can_claim %}
<button
    hx-post="{% url 'emails:claim_email' email.pk %}"
    hx-target="#email-card-{{ email.pk }}"
    hx-swap="outerHTML"
    class="px-3 py-1 text-xs bg-violet-600 hover:bg-violet-700 text-white rounded-md transition"
>
    Claim
</button>
{% endif %}
```

### AI Suggestion Badge + Accept/Reject
```html
<!-- In _email_detail.html, shown when AI has a suggestion and email is unassigned -->
{% if email.ai_suggested_assignee and not email.assigned_to %}
<div class="flex items-center gap-3 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
    <span class="text-sm text-blue-300">
        AI suggests <strong>{{ email.ai_suggested_assignee }}</strong>
    </span>
    <button
        hx-post="{% url 'emails:accept_ai_suggestion' email.pk %}"
        hx-target="#detail-panel"
        class="px-2 py-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded"
    >
        Accept
    </button>
    <button
        hx-post="{% url 'emails:reject_ai_suggestion' email.pk %}"
        hx-target="#detail-panel"
        class="px-2 py-1 text-xs bg-slate-600 hover:bg-slate-700 text-white rounded"
    >
        Dismiss
    </button>
</div>
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1: Sheet-based SLA with wall-clock time | v2: DB-based SLA with business-hours calculator | Phase 4 | Fair SLA that doesn't penalize overnight arrivals |
| v1: SLA status as text in Sheet column | v2: DateTimeField deadlines with computed remaining | Phase 4 | Real-time countdown display, precise breach detection |
| v1: Manual-only assignment | v2: Rule-based auto-assign + AI fallback + self-claim | Phase 4 | Manager handles exceptions, not every email |
| v1: Single SLA deadline | v2: Two-tier (ack + respond) | Phase 4 | Accountability at two stages, not just response |

## Open Questions

1. **AI Suggestion Structured Storage**
   - What we know: `ai_suggested_assignee` is currently a CharField(max_length=100) storing a plain name string
   - What's unclear: CONTEXT.md says "store structured suggestion with reasoning" -- this could mean a JSONField or a separate related model
   - Recommendation: Change to JSONField storing `{"name": "Rahul", "user_id": 5, "reason": "Handles most Sales Lead emails, currently has 2 open items"}`. Simpler than a separate model, and the detail panel can display the reason.

2. **Default SLA Values for Initial Deployment**
   - What we know: CONTEXT.md specifies ack deadlines (CRITICAL=15min, HIGH=30min, MEDIUM=1hr, LOW=2hr) but respond deadlines are not specified
   - What's unclear: What respond deadline hours to seed
   - Recommendation: Seed with reasonable defaults -- CRITICAL=2hr, HIGH=4hr, MEDIUM=8hr, LOW=24hr respond. Admin can change via settings page.

3. **Personal Breach Alerts per Assignee**
   - What we know: CONTEXT.md says "each assignee gets personal alert (their breached emails only)"
   - What's unclear: Is this a separate Chat message per person, or one message with @mentions?
   - Recommendation: One summary message to the shared Chat space with sections per assignee. Google Chat webhooks don't support @mentions -- a single grouped message is cleaner than N separate messages.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x + pytest-django |
| Config file | `pytest.ini` (DJANGO_SETTINGS_MODULE = config.settings.dev) |
| Quick run command | `pytest apps/emails/tests/test_auto_assignment.py apps/emails/tests/test_sla.py -x` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASGN-03 | Auto-assign by category rule | unit | `pytest apps/emails/tests/test_auto_assignment.py::TestAutoAssignBatch -x` | Wave 0 |
| ASGN-03 | Assignment rule CRUD | unit | `pytest apps/emails/tests/test_auto_assignment.py::TestAssignmentRuleModel -x` | Wave 0 |
| ASGN-04 | AI fallback suggestion | unit | `pytest apps/emails/tests/test_auto_assignment.py::TestAIFallback -x` | Wave 0 |
| SLA-02 | SLA deadline calculation | unit | `pytest apps/emails/tests/test_sla.py::TestSLACalculator -x` | Wave 0 |
| SLA-02 | Business hours math | unit | `pytest apps/emails/tests/test_sla.py::TestBusinessHours -x` | Wave 0 |
| SLA-03 | Breach detection query | unit | `pytest apps/emails/tests/test_sla.py::TestBreachDetection -x` | Wave 0 |
| SLA-03 | 3x daily summary | unit | `pytest apps/emails/tests/test_sla.py::TestBreachSummary -x` | Wave 0 |
| SLA-04 | Breach alerts via Chat | unit | `pytest apps/emails/tests/test_chat_notifier.py::TestBreachSummary -x` | Wave 0 |
| INFR-09 | SLA config admin page | unit | `pytest apps/emails/tests/test_settings_views.py::TestSLAConfigView -x` | Wave 0 |
| INFR-10 | Assignment rule config page | unit | `pytest apps/emails/tests/test_settings_views.py::TestAssignmentRulesView -x` | Wave 0 |
| ASGN-03 | Claim flow | unit | `pytest apps/emails/tests/test_claiming.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_auto_assignment.py apps/emails/tests/test_sla.py apps/emails/tests/test_claiming.py apps/emails/tests/test_settings_views.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_auto_assignment.py` -- covers ASGN-03, ASGN-04
- [ ] `apps/emails/tests/test_sla.py` -- covers SLA-02, SLA-03
- [ ] `apps/emails/tests/test_claiming.py` -- covers ASGN-03 (self-service)
- [ ] `apps/emails/tests/test_settings_views.py` -- covers INFR-09, INFR-10

## Sources

### Primary (HIGH confidence)
- Project codebase: `apps/emails/models.py`, `apps/emails/services/assignment.py`, `apps/emails/services/pipeline.py`, `apps/emails/views.py` -- current implementation reviewed
- Project codebase: `apps/core/models.py` (SystemConfig), `apps/emails/templatetags/email_tags.py` -- established patterns
- Project codebase: `agent/sla_monitor.py` -- v1 SLA pattern (summary-based, not per-ticket)
- Project codebase: `apps/emails/management/commands/run_scheduler.py` -- APScheduler integration pattern
- APScheduler 3.11 installed: CronTrigger verified available via `pip show apscheduler`

### Secondary (MEDIUM confidence)
- Django 4.2 LTS: models, migrations, management commands -- well-established patterns
- Sortable.js: de facto standard for drag-and-drop reordering, CDN available

### Tertiary (LOW confidence)
- None -- all findings verified against existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed, no new pip dependencies
- Architecture: HIGH -- follows established patterns from Phases 1-3 (service layer, HTMX partials, ActivityLog)
- Pitfalls: HIGH -- identified from v1 SLAMonitor experience and codebase review
- SLA business hours: HIGH -- simple utility, well-defined requirements (8-20 IST Mon-Sat)
- Settings UI: MEDIUM -- Sortable.js CDN integration not yet tested in this project

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable -- no fast-moving dependencies)
