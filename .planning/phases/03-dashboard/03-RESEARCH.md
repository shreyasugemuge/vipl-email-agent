# Phase 3: Dashboard - Research

**Researched:** 2026-03-11
**Domain:** Django server-rendered dashboard with HTMX interactivity + Tailwind CSS styling
**Confidence:** HIGH

## Summary

Phase 3 builds the core dashboard -- the first user-facing feature of v2. The existing codebase has all the data models ready (Email, User with roles, AttachmentMetadata), a dev inspector template at `/emails/inspect/`, fake data seeding via `test_pipeline` command, and a ChatNotifier service for assignment notifications. The dashboard needs a full `base.html` rebuild with sidebar/topbar layout, email card list with HTMX-powered filtering/sorting/pagination, a slide-out detail panel, assignment controls, and an activity log.

The stack is Django 4.2 (actual installed version, despite CLAUDE.md saying 5.2) with HTMX 2.0 via CDN, Tailwind CSS v4 via CDN play script, and django-htmx middleware for detecting HTMX requests. No build step needed. Activity logging should use a simple custom ActivityLog model rather than a third-party library -- the scope is narrow (assignments, status changes) and doesn't need full model history tracking.

**Primary recommendation:** Use django-htmx middleware to serve partials for HTMX requests and full pages for normal requests. Structure templates as base layout + page templates + HTMX partial fragments. Keep all business logic in service functions, views stay thin.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Card-based layout (not table rows) -- each email is a card like Linear/Trello
- Each card shows: priority badge (colored), category badge, sender, subject, AI summary (1-2 lines), assignee name, time-ago / SLA countdown
- Newest first, flat list as default sort
- Paginated at 25 per page (not infinite scroll)
- Click card opens a slide-out detail panel on the right (40% list / 60% detail)
- Detail panel shows: full email body, draft reply, attachment metadata, activity log, "Open in Gmail" link, assign/status controls
- Assignee dropdown directly on each card -- one click to open, one click to assign
- Reassignment: pick new person from same dropdown, optional note field appears for context
- Assignment notification: Google Chat message only (subject, sender, priority, dashboard link)
- Team members can change status on their own assigned emails: Acknowledge and Close
- Only admins can assign/reassign
- 4 statuses: New -> Acknowledged -> Replied -> Closed (Replied auto-detection deferred to Phase 4)
- Default manager view: Unassigned queue only (emails with no assignee)
- Default team member view: My assigned emails only (respects `can_see_all_emails` User flag)
- Toolbar navigation: tab bar [All] [Unassigned] [My Emails] + per-assignee tabs
- Dropdown filters: Status, Priority, Category, Inbox
- Sort by any visible field (date, priority, status, assignee)
- URL-based filter state (shareable, bookmarkable)
- Filter counts shown (e.g., "12 emails matching")
- Clean minimal style -- white background, subtle borders, colored priority/status badges
- Tailwind CSS via CDN play script (zero build step)
- Left sidebar + top bar navigation
- Priority badge colors: CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=gray
- Font: Inter or system-ui
- Desktop-first, mobile-usable (responsive cards stack vertically on small screens)
- Dashboard must work with fake data from `fake_data.py` without a running pipeline
- `test_pipeline` command should seed the database with fake emails for dashboard development

### Claude's Discretion
- Exact card spacing, typography, and shadow values
- Sidebar width and collapse behavior
- Detail panel animation (slide vs instant)
- Empty state illustrations/messages
- Mobile breakpoint behavior
- HTMX swap strategies (innerHTML vs outerHTML, push URL, etc.)
- Activity log model design (separate model or JSON field)
- How to structure Django templates (one big template vs partials)

### Deferred Ideas (OUT OF SCOPE)
- Auto-assignment (category -> person rules) -- Phase 4
- SLA deadline calculation and breach detection -- Phase 4
- "Replied" status auto-detection from Gmail thread -- Phase 4
- Dashboard settings/config page -- Phase 5
- Analytics charts (response times, volume trends) -- Phase 5
- Google Sheets sync mirror -- Phase 5
- Dark mode toggle -- future enhancement

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Dashboard shows all emails with date, from, subject, assignee, priority, status, SLA remaining | Card layout pattern + Email model fields already exist. SLA remaining is display-only (calculated from `assigned_at` or `received_at`). |
| DASH-02 | Dashboard supports filtering by status, assignee, priority, inbox | URL query params + Django ORM filtering + HTMX partial swap pattern |
| DASH-03 | Dashboard supports sorting by any column | Django `order_by` + URL params + HTMX table swap |
| DASH-04 | Dashboard shows unassigned queue as default manager view | `Email.objects.filter(assigned_to__isnull=True)` + role-based default view |
| DASH-05 | Dashboard has activity log showing who did what | ActivityLog model with HTMX-loaded partial in detail panel |
| DASH-06 | Dashboard is desktop-first, usable on mobile | Tailwind responsive classes, card layout stacks naturally |
| SLA-01 | Each email has a status: New, Acknowledged, Replied, Closed | Already defined as `Email.Status` choices in model. Status transitions via view endpoints. |
| ASGN-01 | Manager can manually assign an email to a team member | Admin-only dropdown + HTMX POST to assign endpoint |
| ASGN-02 | Manager can reassign an email to a different team member | Same dropdown, update `assigned_to` + log activity |
| ASGN-05 | Assignment triggers notification to assignee via Google Chat | Reuse ChatNotifier with new assignment card format |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2.x (installed) | Web framework | Already installed, all models ready |
| HTMX | 2.0.x (CDN) | Dynamic page updates without JS | Project decision: server-rendered + HTMX |
| Tailwind CSS | v4 (CDN play script) | Utility-first CSS | Project decision: zero build step |
| django-htmx | 1.27.x | Middleware for `request.htmx` detection | Standard Django+HTMX integration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | already installed | Chat webhook calls | Assignment notifications |
| pytz | already installed | IST timezone handling | Time-ago display |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom activity log model | django-simple-history / django-auditlog | Overkill -- we only need assignment/status change logging, not full model history |
| django-tables2 + django-filter | Custom querysets + URL params | Card layout doesn't fit table library paradigm; custom is simpler |
| Alpine.js | Vanilla JS or no JS | Could help with dropdown behavior, but HTMX + minimal inline JS is sufficient for this scope |

**Installation:**
```bash
pip install django-htmx
```

**CDN (in base.html):**
```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"></script>
```

## Architecture Patterns

### Recommended Project Structure
```
templates/
  base.html                    # Full layout: sidebar + topbar + content area + HTMX/Tailwind CDN
  emails/
    email_list.html            # Full page: tab bar + filters + card list + pagination
    _email_card.html           # Partial: single email card (reused in list)
    _email_list_body.html      # Partial: card list + pagination (HTMX swap target)
    _email_detail.html         # Partial: slide-out detail panel content
    _assign_dropdown.html      # Partial: assignee dropdown for a card
    _activity_log.html         # Partial: activity entries for detail panel
    inspect.html               # Existing dev inspector (keep as-is)

apps/emails/
  views.py                     # Add dashboard views alongside existing inspect view
  urls.py                      # Add dashboard URL routes
  services/
    assignment.py              # Assignment logic: assign, reassign, notify
    chat_notifier.py           # Existing -- add assignment notification card method
  models.py                    # Add ActivityLog model
  templatetags/
    email_tags.py              # Custom template tags (time_ago, priority_color, etc.)
```

### Pattern 1: HTMX Partial Detection
**What:** Serve full page for normal requests, HTML fragment for HTMX requests
**When to use:** Every dashboard view
**Example:**
```python
# Source: django-htmx docs
from django_htmx.middleware import HtmxMiddleware  # add to MIDDLEWARE

def email_list(request):
    emails = get_filtered_emails(request)
    context = {"emails": emails, "filters": get_active_filters(request)}

    if request.htmx:
        return render(request, "emails/_email_list_body.html", context)
    return render(request, "emails/email_list.html", context)
```

### Pattern 2: URL-Based Filter State
**What:** All filter/sort/page state in URL query params, bookmarkable
**When to use:** Email list filtering, sorting, pagination
**Example:**
```python
# URL: /emails/?status=new&priority=HIGH&sort=-received_at&page=2
def get_filtered_emails(request):
    qs = Email.objects.filter(processing_status="completed")

    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)

    priority = request.GET.get("priority")
    if priority:
        qs = qs.filter(priority=priority)

    assignee = request.GET.get("assignee")
    if assignee == "unassigned":
        qs = qs.filter(assigned_to__isnull=True)
    elif assignee == "me":
        qs = qs.filter(assigned_to=request.user)
    elif assignee:
        qs = qs.filter(assigned_to_id=assignee)

    sort = request.GET.get("sort", "-received_at")
    qs = qs.order_by(sort)

    return qs
```

### Pattern 3: HTMX Card Click -> Detail Panel
**What:** Click card, HTMX loads detail panel into right side
**When to use:** Email detail view
**Example:**
```html
<!-- In _email_card.html -->
<div class="email-card"
     hx-get="/emails/{{ email.pk }}/detail/"
     hx-target="#detail-panel"
     hx-swap="innerHTML"
     hx-push-url="/emails/?selected={{ email.pk }}">
  ...card content...
</div>

<!-- In email_list.html -->
<div class="flex">
  <div class="w-2/5" id="email-list">
    {% include "emails/_email_list_body.html" %}
  </div>
  <div class="w-3/5 border-l" id="detail-panel">
    <!-- Loaded via HTMX on card click -->
  </div>
</div>
```

### Pattern 4: Inline Assignment via HTMX
**What:** Dropdown on card triggers HTMX POST, updates card and detail panel
**When to use:** Assignment and reassignment
**Example:**
```html
<!-- Assign dropdown triggers POST -->
<select hx-post="/emails/{{ email.pk }}/assign/"
        hx-target="#card-{{ email.pk }}"
        hx-swap="outerHTML"
        name="assignee">
  <option value="">Unassigned</option>
  {% for user in team_members %}
  <option value="{{ user.pk }}" {% if email.assigned_to_id == user.pk %}selected{% endif %}>
    {{ user.get_full_name }}
  </option>
  {% endfor %}
</select>
```

### Pattern 5: Tab Navigation with HTMX
**What:** Tab bar swaps the card list without full page reload
**When to use:** All / Unassigned / My Emails tabs
**Example:**
```html
<nav class="flex gap-2 mb-4">
  <a hx-get="/emails/?view=all"
     hx-target="#email-list"
     hx-push-url="true"
     class="tab {% if view == 'all' %}tab-active{% endif %}">All</a>
  <a hx-get="/emails/?view=unassigned"
     hx-target="#email-list"
     hx-push-url="true"
     class="tab {% if view == 'unassigned' %}tab-active{% endif %}">Unassigned</a>
  <a hx-get="/emails/?view=mine"
     hx-target="#email-list"
     hx-push-url="true"
     class="tab {% if view == 'mine' %}tab-active{% endif %}">My Emails</a>
</nav>
```

### Anti-Patterns to Avoid
- **Putting business logic in views:** Keep assignment logic, notification sending, and activity logging in service functions under `apps/emails/services/`
- **Over-nesting HTMX targets:** Keep swap targets simple -- `#email-list` for card list, `#detail-panel` for detail, `#card-{id}` for individual card updates
- **Building custom JS for things HTMX handles:** Use `hx-trigger`, `hx-swap`, `hx-push-url` instead of writing JavaScript event handlers
- **Not handling the non-HTMX case:** Every HTMX endpoint should also work as a full-page load (for bookmarked URLs, refresh, etc.)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTMX request detection | Manual header checking | django-htmx middleware (`request.htmx`) | Handles all edge cases, well-tested |
| Pagination | Custom page math | Django's `Paginator` | Built-in, battle-tested, handles edge cases |
| CSRF with HTMX | Custom token passing | `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` on body tag | Standard HTMX+Django CSRF pattern |
| Time-ago display | Custom JS | Django `timesince` template filter or custom `naturaltime` | Server-rendered, no JS needed |
| Query param building | String concatenation | `urllib.parse.urlencode` in template tag | Handles encoding correctly |

**Key insight:** The entire dashboard can be built with zero custom JavaScript. HTMX handles all dynamic behavior. The only JS is the Tailwind and HTMX CDN script tags.

## Common Pitfalls

### Pitfall 1: CSRF Token Not Sent with HTMX POST Requests
**What goes wrong:** HTMX POST/PUT/DELETE requests fail with 403 Forbidden
**Why it happens:** HTMX doesn't automatically include Django's CSRF token
**How to avoid:** Add `hx-headers` to the body tag:
```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
```
**Warning signs:** 403 errors on any HTMX mutation request

### Pitfall 2: Forgetting Non-HTMX Fallback
**What goes wrong:** Bookmarked URLs or page refresh shows broken partial HTML
**Why it happens:** View only returns partial template, not wrapped in base layout
**How to avoid:** Always check `request.htmx` and serve full page for non-HTMX:
```python
template = "emails/_partial.html" if request.htmx else "emails/full_page.html"
```
**Warning signs:** Refreshing page shows unstyled HTML fragment

### Pitfall 3: Stale Card After Assignment
**What goes wrong:** User assigns email but the card doesn't visually update
**Why it happens:** HTMX response doesn't include the updated card HTML
**How to avoid:** Return the updated card partial as the HTMX response, target the specific card with `hx-target="#card-{id}"` and `hx-swap="outerHTML"`
**Warning signs:** Need to refresh page to see assignment changes

### Pitfall 4: N+1 Queries on Card List
**What goes wrong:** Dashboard loads slowly with many emails
**Why it happens:** Each card accesses `email.assigned_to.get_full_name()` causing separate DB queries
**How to avoid:** Use `select_related("assigned_to")` in the queryset:
```python
Email.objects.select_related("assigned_to").filter(...)
```
**Warning signs:** Slow page loads, many SQL queries in Django Debug Toolbar

### Pitfall 5: Tailwind CDN Performance in Production
**What goes wrong:** Slight FOUC (flash of unstyled content) on page load
**Why it happens:** Tailwind CDN play script compiles CSS at runtime in the browser
**How to avoid:** This is acceptable for 4-5 users (per user decision). If it becomes an issue later, switch to Tailwind CLI build step. Not a blocker.
**Warning signs:** Brief flash of unstyled content on first load

### Pitfall 6: Race Condition on Concurrent Assignment
**What goes wrong:** Two admins assign the same email to different people simultaneously
**Why it happens:** No optimistic locking on the Email model
**How to avoid:** Use `select_for_update()` in the assignment service function. For 4-5 users this is extremely unlikely, but the pattern is simple to implement.
**Warning signs:** Activity log shows rapid reassignment with no human context

## Code Examples

### ActivityLog Model Design (Recommended: Separate Model)
```python
# Recommendation: Use a separate model, not JSON field
# Reasons: queryable, indexable, can filter by action/user, simple schema

class ActivityLog(TimestampedModel):
    """Tracks assignment and status changes on emails."""

    class Action(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        REASSIGNED = "reassigned", "Reassigned"
        STATUS_CHANGED = "status_changed", "Status Changed"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        CLOSED = "closed", "Closed"

    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name="activity_logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    detail = models.TextField(blank=True, default="")
    # Snapshot fields for when referenced objects change
    old_value = models.CharField(max_length=255, blank=True, default="")
    new_value = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.action} on {self.email_id}"
```

### Assignment Service Function
```python
# apps/emails/services/assignment.py
from django.utils import timezone
from apps.emails.models import Email, ActivityLog

def assign_email(email: Email, assignee, assigned_by, note: str = "") -> Email:
    """Assign or reassign an email. Logs activity and sends notification."""
    old_assignee = email.assigned_to

    email.assigned_to = assignee
    email.assigned_by = assigned_by
    email.assigned_at = timezone.now()
    email.save(update_fields=["assigned_to", "assigned_by", "assigned_at", "updated_at"])

    # Log activity
    action = ActivityLog.Action.REASSIGNED if old_assignee else ActivityLog.Action.ASSIGNED
    ActivityLog.objects.create(
        email=email,
        user=assigned_by,
        action=action,
        old_value=str(old_assignee) if old_assignee else "",
        new_value=str(assignee),
        detail=note,
    )

    # Send Chat notification (fire-and-forget)
    _notify_assignment(email, assignee)

    return email
```

### Chat Assignment Notification Card
```python
# Add to ChatNotifier class
def notify_assignment(self, email, assignee) -> bool:
    """Notify assignee about a new assignment via Chat."""
    if self._is_quiet_hours():
        return False

    tracker_url = SystemConfig.get("tracker_url", "https://triage.vidarbhainfotech.com")
    pri = email.priority or "MEDIUM"
    emoji = PRIORITY_EMOJI.get(pri, PRIORITY_EMOJI["MEDIUM"])

    card = {
        "header": {
            "title": f"Assigned to you: {email.subject[:50]}",
            "subtitle": f"{emoji} {pri} | {email.category}",
        },
        "sections": [{
            "widgets": [
                {"decoratedText": {"topLabel": "From", "text": f"{email.from_name} <{email.from_address}>"}},
                {"decoratedText": {"topLabel": "Summary", "text": email.ai_summary or "(none)"}},
                {"buttonList": {"buttons": [
                    {"text": "Open in Dashboard", "onClick": {"openLink": {"url": f"{tracker_url}/emails/?selected={email.pk}"}}}
                ]}},
            ]
        }],
    }

    payload = {"cardsV2": [{"cardId": f"assign-{email.pk}", "card": card}]}
    return self._post(payload)
```

### Base Layout Template Pattern
```html
<!-- templates/base.html (rebuild) -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}VIPL Email Triage{% endblock %}</title>
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
  <script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"></script>
  <style type="text/tailwindcss">
    @theme {
      --font-sans: 'Inter', system-ui, sans-serif;
    }
  </style>
  {% block extra_head %}{% endblock %}
</head>
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}' class="bg-white text-gray-900 font-sans">
  <div class="flex h-screen">
    <!-- Sidebar -->
    <aside class="w-56 bg-gray-50 border-r border-gray-200 flex flex-col">
      {% block sidebar %}
      <div class="p-4 font-semibold text-lg">VIPL Triage</div>
      <nav class="flex-1 px-2">
        <a href="/emails/" class="block px-3 py-2 rounded hover:bg-gray-100">Emails</a>
        <a href="/emails/activity/" class="block px-3 py-2 rounded hover:bg-gray-100">Activity</a>
        {% if user.is_admin_role %}
        <a href="/admin/" class="block px-3 py-2 rounded hover:bg-gray-100 text-sm text-gray-500 mt-4">Admin</a>
        {% endif %}
      </nav>
      {% endblock %}
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col">
      <!-- Top bar -->
      <header class="h-14 border-b border-gray-200 flex items-center justify-between px-6">
        <div>{% block page_title %}{% endblock %}</div>
        <div class="text-sm text-gray-500">
          {{ user.get_full_name|default:user.username }} |
          <a href="/accounts/logout/" class="hover:underline">Logout</a>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-hidden">
        {% block content %}{% endblock %}
      </main>
    </div>
  </div>
</body>
</html>
```

### HTMX Filter Pattern
```html
<!-- Filter toolbar that swaps the card list -->
<div class="flex gap-2 items-center">
  <select hx-get="/emails/"
          hx-target="#email-list"
          hx-include="[name='sort'],[name='priority'],[name='status'],[name='inbox']"
          hx-push-url="true"
          name="status"
          class="border rounded px-2 py-1 text-sm">
    <option value="">All Statuses</option>
    <option value="new">New</option>
    <option value="acknowledged">Acknowledged</option>
    <option value="replied">Replied</option>
    <option value="closed">Closed</option>
  </select>
  <!-- Similar dropdowns for priority, inbox, etc. -->
</div>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| django-tables2 for list views | HTMX + custom cards | 2023+ | Card layout doesn't fit table paradigm |
| jQuery for AJAX | HTMX attributes | 2020+ | Zero custom JS needed |
| Tailwind CLI build step | Tailwind v4 CDN play script | 2025 | Fine for small user base (4-5 users) |
| django-simple-history for audit | Custom ActivityLog model | N/A | Simpler for narrow scope (assignments only) |

**Deprecated/outdated:**
- HTMX 1.x: Use 2.0.x (dropped IE support, cleaner API)
- Tailwind v3 CDN (`cdn.tailwindcss.com`): Use v4 CDN (`@tailwindcss/browser@4`)

## Open Questions

1. **LOGIN_REDIRECT_URL currently points to `/accounts/dashboard/`**
   - What we know: The accounts DashboardView is a placeholder. Phase 3 dashboard should be the main view.
   - What's unclear: Should we change LOGIN_REDIRECT_URL to `/emails/` or keep `/accounts/dashboard/` and redirect from there?
   - Recommendation: Change `LOGIN_REDIRECT_URL` to `/emails/` since that's the real dashboard now. Redirect `/accounts/dashboard/` to `/emails/` for any bookmarks.

2. **Django version discrepancy**
   - What we know: CLAUDE.md says Django 5.2 LTS, but `requirements.txt` pins `django>=4.2,<4.3` and actual installed version is 4.2.29
   - What's unclear: Whether upgrading to 5.2 is planned for a future phase
   - Recommendation: Build for Django 4.2 (what's installed). No 5.2-specific features needed for the dashboard.

3. **Tailwind v4 CDN browser support**
   - What we know: v4 CDN targets modern browsers only (Safari 16.4+, Chrome 111+, Firefox 128)
   - What's unclear: What browsers the 4-5 users actually use
   - Recommendation: Acceptable risk. Internal tool, modern browsers assumed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-django 4.9.x |
| Config file | `pytest.ini` (DJANGO_SETTINGS_MODULE = config.settings.dev) |
| Quick run command | `pytest apps/emails/tests/ -x -q` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Email list view shows cards with correct fields | unit | `pytest apps/emails/tests/test_views.py::test_email_list_shows_cards -x` | No -- Wave 0 |
| DASH-02 | Filters by status/assignee/priority/inbox | unit | `pytest apps/emails/tests/test_views.py::test_email_list_filters -x` | No -- Wave 0 |
| DASH-03 | Sort by any column via URL param | unit | `pytest apps/emails/tests/test_views.py::test_email_list_sorting -x` | No -- Wave 0 |
| DASH-04 | Default manager view = unassigned queue | unit | `pytest apps/emails/tests/test_views.py::test_default_view_admin -x` | No -- Wave 0 |
| DASH-05 | Activity log records assignments/status changes | unit | `pytest apps/emails/tests/test_activity.py::test_activity_log_creation -x` | No -- Wave 0 |
| DASH-06 | Dashboard renders on mobile viewport | manual-only | Visual check in browser devtools | N/A |
| SLA-01 | Status field transitions correctly | unit | `pytest apps/emails/tests/test_views.py::test_status_change -x` | No -- Wave 0 |
| ASGN-01 | Admin can assign email | unit | `pytest apps/emails/tests/test_assignment.py::test_assign_email -x` | No -- Wave 0 |
| ASGN-02 | Admin can reassign email | unit | `pytest apps/emails/tests/test_assignment.py::test_reassign_email -x` | No -- Wave 0 |
| ASGN-05 | Assignment triggers Chat notification | unit | `pytest apps/emails/tests/test_assignment.py::test_assignment_notification -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/ -x -q`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_views.py` -- dashboard view tests (DASH-01 through DASH-04, DASH-06, SLA-01)
- [ ] `apps/emails/tests/test_assignment.py` -- assignment service + notification tests (ASGN-01, ASGN-02, ASGN-05)
- [ ] `apps/emails/tests/test_activity.py` -- activity log model + creation tests (DASH-05)
- [ ] ActivityLog model + migration must exist before tests can run

## Sources

### Primary (HIGH confidence)
- Existing codebase: `apps/emails/models.py`, `apps/accounts/models.py`, `apps/emails/views.py`, `config/settings/base.py`
- [django-htmx docs](https://django-htmx.readthedocs.io/en/latest/) -- middleware installation, `request.htmx` usage
- [HTMX reference](https://htmx.org/reference/) -- attribute reference for hx-get, hx-target, hx-swap, hx-push-url
- [Tailwind CSS v4 CDN](https://tailwindcss.com/docs/installation/play-cdn) -- browser script setup

### Secondary (MEDIUM confidence)
- [django-htmx-patterns](https://github.com/spookylukey/django-htmx-patterns) -- partial template patterns
- [Task Badger: Django Tables and htmx](https://taskbadger.net/blog/tables.html) -- table filtering/sorting patterns

### Tertiary (LOW confidence)
- Tailwind v4 CDN performance characteristics -- limited production data available

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are well-established, most already installed
- Architecture: HIGH -- HTMX+Django partial pattern is well-documented with multiple authoritative sources
- Pitfalls: HIGH -- common gotchas are well-known (CSRF, N+1, partial fallback)
- Activity log design: MEDIUM -- custom model is straightforward but design is discretionary

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable libraries, no fast-moving concerns)
