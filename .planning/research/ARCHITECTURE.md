# Architecture Patterns

**Domain:** AI-powered shared inbox management system (v2 rebuild)
**Researched:** 2026-03-09
**Updated:** 2026-03-09 (revised from FastAPI+React to Django+HTMX based on stack research)

## Recommended Architecture

**Pattern:** Monolithic Django application with embedded scheduler, server-rendered templates with HTMX for interactivity, deployed as a single Docker container behind the VM's existing Nginx reverse proxy.

This is NOT a two-application system. With 4-5 users and a single company, a Django monolith is the correct choice. No separate frontend app, no JSON API consumed by an SPA, no CORS, no JWT tokens. Django serves HTML directly.

### High-Level Structure

```
                    Internet
                       |
                Nginx (existing on VM, shared with Taiga)
                       |
        triage.vidarbhainfotech.com
                       |
              +-----------------+
              | Django App      |
              | (Gunicorn)      |
              |                 |
              | - Views (HTML)  |
              | - HTMX partials |
              | - APScheduler   |
              | - Agent modules |
              +-----------------+
                       |
              +------------------+
              | PostgreSQL       |
              | (existing on VM, |
              |  shared w/Taiga) |
              +------------------+
```

**Why 1 container, not 2?** Django serves its own HTML. There is no separate frontend to containerize. Nginx (already running on the VM for Taiga) proxies requests to Gunicorn and serves static files from a shared volume. This is the simplest possible deployment.

**Why NOT a separate PostgreSQL container?** PostgreSQL already runs on the VM for Taiga. Running a second PostgreSQL in Docker is wasteful. Create a new database on the existing instance.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Django Views** | Serve HTML pages and HTMX partial fragments | Django ORM, Templates |
| **Django Templates + HTMX** | Render email tables, filters, assignment controls | Django Views (same-origin HTTP) |
| **Gmail Poller** | Fetches unprocessed emails from Gmail API on schedule | AI Processor, Django ORM |
| **AI Processor** | Triages emails via Claude (spam filter + two-tier model) | Django ORM |
| **Assignment Engine** | Assigns emails to team members (rules + AI fallback) | Django ORM, AI Processor |
| **Thread Monitor** | Watches Gmail threads for assignee responses | Django ORM, Gmail API |
| **SLA Monitor** | Checks deadlines, escalates breaches | Django ORM, Notification Hub |
| **Notification Hub** | Dispatches alerts to Chat, Email, WhatsApp/SMS | External APIs |
| **EOD Reporter** | Generates daily summary reports | Django ORM, Notification Hub |
| **Sheets Sync** | One-way sync of simplified data to Google Sheets | Django ORM, Sheets API |
| **Auth (django-allauth)** | Google OAuth SSO, session management, domain restriction | Google OAuth API, Django sessions |

### Internal Module Structure

```
vipl_email_agent/                  # Django project root
  manage.py
  vipl/                            # Project settings package
    settings.py                    # Django settings + django-environ
    urls.py                        # URL routing
    wsgi.py                        # Gunicorn entry point

  dashboard/                       # Django app: web UI
    views/
      emails.py                    # Email list, detail, filters
      assignments.py               # Assignment controls, reassignment
      analytics.py                 # Stats, charts, response times
    templates/
      dashboard/
        base.html                  # Layout with Tailwind + HTMX
        email_list.html            # Full page: email table
        partials/
          email_table.html         # HTMX partial: table body (for filtering)
          email_row.html           # HTMX partial: single row (for updates)
          email_detail.html        # HTMX partial: slide-out detail panel
          assignment_form.html     # HTMX partial: reassign dropdown
    templatetags/
      dashboard_tags.py            # Custom tags (priority badges, SLA countdown)
    urls.py
    forms.py                       # Django forms for assignment, status changes

  inbox/                           # Django app: data models + business logic
    models/
      email.py                     # Email model (replaces Sheet rows)
      assignment.py                # Assignment + history models
      sla.py                       # SLA config + status models
      config.py                    # Runtime config model
    services/
      gmail_poller.py              # Adapted from v1 agent/gmail_poller.py
      ai_processor.py              # Adapted from v1 agent/ai_processor.py
      assignment_engine.py         # NEW: rules + AI assignment
      thread_monitor.py            # NEW: Gmail thread watch for responses
      sla_monitor.py               # Adapted from v1 agent/sla_monitor.py
      notification_hub.py          # Consolidates v1 chat_notifier + email sending
      eod_reporter.py              # Adapted from v1 agent/eod_reporter.py
      sheets_sync.py               # NEW: one-way DB -> Sheets mirror
    management/
      commands/
        runscheduler.py            # Management command: starts APScheduler
        migrate_from_sheets.py     # One-time: import v1 Sheet data into DB
        init_sla_config.py         # One-time: seed SLA config from v1
    admin.py                       # Django admin for SLA config, users, rules

  prompts/
    triage_prompt.txt              # System prompt (carried from v1)

  templates/
    eod_email.html                 # Jinja2 EOD template (carried from v1)

  static/
    css/output.css                 # Compiled Tailwind CSS
    js/htmx.min.js                 # HTMX (single file, no npm)
    js/alpine.min.js               # Alpine.js for dropdowns/modals
```

## Data Flow

### Email Processing Pipeline (unchanged pattern from v1, new persistence target)

```
Gmail API  -->  GmailPoller.poll_all()
                    |
                    v
            DB dedup check (Django ORM: Email.objects.filter(thread_id=...).exists())
                    |
                    v
            AIProcessor.is_spam() --> skip if spam
                    |
                    v
            AIProcessor.process() --> Claude triage
                    |
                    v
            AssignmentEngine.assign() --> rules check, then AI fallback
                    |
                    v
            Email.objects.create(...) --> Django ORM write
                    |
                    v
            Gmail label "Agent/Processed" (AFTER DB write -- same safety pattern as v1)
                    |
                    v
            NotificationHub.notify() --> Chat webhook + any urgent channels
                    |
                    v
            SheetsSync.sync_email() --> mirror row to Google Sheet (fire-and-forget)
```

### Dashboard Request Flow (HTMX)

```
Browser --> GET /emails/?status=open&assignee=X
                    |
                Django session middleware (checks auth cookie)
                    |
                Django view: EmailListView
                    |
                if request.htmx:
                    return render("partials/email_table.html", ...)  # Just the table body
                else:
                    return render("email_list.html", ...)            # Full page with layout
                    |
                Django ORM query with django-filter
                    |
                HTML response --> browser swaps table body via HTMX
```

This is the key HTMX pattern: the same view handles both full page loads and HTMX partial updates. The `request.htmx` check (provided by django-htmx middleware) determines which template to render.

### Assignment + Reassignment Flow

```
[Automatic on triage]
AIProcessor result --> AssignmentEngine
  1. Check AssignmentRule objects: category "Government/Tender" -> Assignee X
  2. If no rule match: AI fallback (content analysis + workload via ORM aggregate)
  3. Email.objects.create(assignee=..., assignment_reason=...)

[Manual reassignment from dashboard]
User clicks "Reassign" dropdown (HTMX form) --> POST /emails/{id}/reassign/
  1. AssignmentHistory.objects.create(old_assignee=..., new_assignee=..., reason=...)
  2. email.assignee = new_assignee; email.save()
  3. Return HTMX partial: updated email row with new assignee badge
  4. NotificationHub.notify_assignment(new_assignee, email)
```

### Thread Monitoring Flow

```
APScheduler (every 5 min) --> ThreadMonitor.check()
  1. Email.objects.filter(status="assigned", assignee__isnull=False)
  2. For each: check Gmail thread for new messages from assignee
  3. If response found: email.status = "responded"; email.save()
  4. If SLA approaching: NotificationHub.escalate()
```

## Patterns to Follow

### Pattern 1: Management Command for Scheduler

APScheduler runs in a separate process via a Django management command, NOT inside Gunicorn workers. This avoids duplicate jobs when Gunicorn forks multiple workers.

**What:** A management command that starts APScheduler and blocks forever.
**When:** Always. Run alongside Gunicorn in the same Docker container via a process manager or Docker CMD.

```python
# inbox/management/commands/runscheduler.py
from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler

class Command(BaseCommand):
    help = 'Runs the email processing scheduler'

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone="Asia/Kolkata")
        scheduler.add_job(poll_emails, "interval", seconds=300, max_instances=1, coalesce=True)
        scheduler.add_job(check_sla, "interval", seconds=900, max_instances=1, coalesce=True)
        scheduler.add_job(send_eod, CronTrigger(hour=19, minute=0, timezone="Asia/Kolkata"))
        scheduler.add_job(retry_dead_letters, "interval", seconds=1800, max_instances=1)
        scheduler.add_job(monitor_threads, "interval", seconds=300, max_instances=1)
        scheduler.start()  # Blocks forever
```

Docker CMD runs both processes:
```dockerfile
CMD ["sh", "-c", "python manage.py runscheduler & gunicorn vipl.wsgi:application --bind 0.0.0.0:8000 --workers 2"]
```

Or use `supervisord` for cleaner process management inside the container.

### Pattern 2: HTMX Partial Templates

**What:** Every interactive element has a full-page template AND a partial template. Django views check `request.htmx` to decide which to render.
**When:** All dashboard interactions (filtering, assignment, status changes).

```python
# dashboard/views/emails.py
from django_htmx.middleware import HtmxDetails

def email_list(request):
    qs = Email.objects.select_related('assignee').order_by('-received_at')
    f = EmailFilter(request.GET, queryset=qs)

    if request.htmx:
        return render(request, "dashboard/partials/email_table.html", {"emails": f.qs})
    return render(request, "dashboard/email_list.html", {"filter": f, "emails": f.qs})
```

```html
<!-- email_list.html -->
{% extends "dashboard/base.html" %}
{% block content %}
<form hx-get="{% url 'email-list' %}" hx-target="#email-table" hx-trigger="change">
  {{ filter.form }}
</form>
<div id="email-table">
  {% include "dashboard/partials/email_table.html" %}
</div>
{% endblock %}
```

### Pattern 3: Service Layer Separation

**What:** Views are thin -- they call service functions. Services contain business logic. This keeps views testable and allows scheduler jobs to reuse the same logic.
**When:** Always. Both dashboard views and scheduler jobs call the same service functions.

```python
# dashboard/views/assignments.py (thin view)
@login_required
def reassign_email(request, email_id):
    email = get_object_or_404(Email, id=email_id)
    form = ReassignForm(request.POST)
    if form.is_valid():
        assignment_engine.reassign(email, form.cleaned_data['assignee'], request.user)
        return render(request, "dashboard/partials/email_row.html", {"email": email})

# inbox/services/assignment_engine.py (business logic)
def reassign(email, new_assignee, changed_by):
    AssignmentHistory.objects.create(
        email=email, old_assignee=email.assignee,
        new_assignee=new_assignee, changed_by=changed_by
    )
    email.assignee = new_assignee
    email.save()
    notification_hub.notify_assignment(new_assignee, email)
```

### Pattern 4: Label-After-Persist Safety (Carried from v1)

**What:** Gmail "Agent/Processed" label is applied ONLY after the database write succeeds. If DB write fails, the email stays unlabeled and gets retried on next poll.
**When:** Every email processing cycle. This is the most important safety invariant in the system.

### Pattern 5: Django Settings via django-environ

**What:** Replace config.yaml + env vars + Sheet overrides with django-environ for static config, and a database RuntimeConfig model for mutable config.
**When:** Application startup for static config; ORM queries for dynamic config.

```python
# vipl/settings.py
import environ
env = environ.Env()
environ.Env.read_env('.env')

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://vipl:pass@localhost:5432/vipl_email_agent')
}
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY')
GOOGLE_CHAT_WEBHOOK_URL = env('GOOGLE_CHAT_WEBHOOK_URL')
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Celery / Redis for Background Jobs

**What:** Adding Celery and Redis as a task queue for background processing.
**Why bad:** Massive complexity increase (extra container, broker config, worker management) for a system that serves 4-5 users. APScheduler in-process handles everything this system needs.
**Instead:** Use `BlockingScheduler` from APScheduler in a management command alongside Gunicorn.

### Anti-Pattern 2: Separate Frontend Application

**What:** Building a React/Vue/Svelte SPA that consumes a JSON API.
**Why bad:** Doubles the codebase, requires a JS build toolchain, adds CORS, token auth, and a second container. For a table-view dashboard with 5 users, this is massive over-engineering.
**Instead:** Django templates + HTMX. Zero JavaScript build step. Same-origin requests. Session cookies. One container.

### Anti-Pattern 3: WebSocket / SSE for Dashboard Updates

**What:** Real-time push for dashboard data updates.
**Why bad:** For 4-5 users checking a dashboard a few times a day, WebSocket/SSE adds connection management complexity for zero benefit.
**Instead:** HTMX polling: `hx-trigger="every 30s"` on the email table. Simple, reliable, zero infrastructure.

### Anti-Pattern 4: GraphQL

**What:** Using GraphQL instead of simple Django views.
**Why bad:** The dashboard has a fixed set of views. No benefit from flexible querying. GraphQL adds schema complexity and tooling overhead.
**Instead:** Django views shaped to each template. 5-8 views total.

### Anti-Pattern 5: Running a Second PostgreSQL in Docker

**What:** Adding a PostgreSQL container to Docker Compose.
**Why bad:** The VM already runs PostgreSQL for Taiga. A second instance wastes RAM and creates backup/maintenance overhead.
**Instead:** Create a new database (`vipl_email_agent`) on the existing PostgreSQL instance.

### Anti-Pattern 6: Django REST Framework for API

**What:** Adding DRF to serve JSON endpoints for a React frontend.
**Why bad:** If there is no separate frontend, there is no need for a JSON API. Django views return HTML. HTMX consumes HTML. The entire serialization/deserialization layer is unnecessary.
**Instead:** Django views + templates. If a JSON API is ever needed (e.g., for a mobile app -- currently out of scope), add DRF then.

## Database Schema (Key Tables)

```
emails
  id, thread_id, message_id, inbox, sender, sender_name, subject, body_preview,
  category, priority, summary, draft_reply, reasoning, language, tags (JSONB),
  ai_model_used, ai_cost_usd,
  assignee (FK -> auth_user), assignment_reason,
  sla_deadline_ack, sla_deadline_response, sla_status,
  status (new/acknowledged/responded/closed),
  gmail_link, received_at, created_at, updated_at

assignment_history
  id, email (FK), old_assignee (FK), new_assignee (FK), changed_by (FK),
  correction_reason, changed_at
  -- Used for AI feedback loop

assignment_rules
  id, category, priority, assignee (FK -> auth_user), active, order

sla_config
  id, category, ack_hours, response_hours

runtime_config
  key (unique), value, updated_by (FK), updated_at
  -- Replaces Sheet-based Agent Config

notification_log
  id, email (FK), channel (chat/email/sms), sent_at, success

daily_report
  id, report_date (unique), stats (JSONB), ai_cost_usd, created_at

failed_triage
  id, thread_id, inbox, attempt_count, last_error, status, created_at, updated_at
```

Note: Users are Django's built-in `auth.User` model, auto-created on first Google OAuth login via django-allauth. No custom user model needed (use `is_staff` for manager role).

## Docker Compose Layout

```yaml
# docker-compose.yml
services:
  web:
    build: .
    command: >
      sh -c "python manage.py migrate --noop &&
             python manage.py collectstatic --noinput &&
             python manage.py runscheduler &
             gunicorn vipl.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"
    volumes:
      - static_files:/app/staticfiles
      - ./secrets:/secrets:ro
    environment:
      - DATABASE_URL=postgres://vipl:password@host.docker.internal:5432/vipl_email_agent
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GOOGLE_CHAT_WEBHOOK_URL=${GOOGLE_CHAT_WEBHOOK_URL}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  static_files:
```

Nginx on the VM host (already running for Taiga) gets a new server block:
```nginx
server {
    server_name triage.vidarbhainfotech.com;

    location /static/ {
        alias /path/to/shared/static_files/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Django monolith, not FastAPI + React | Batteries included: ORM, migrations, auth, admin, templates. No need for a JSON API or separate frontend for 5 users. |
| HTMX, not React/Vue | Zero JavaScript build step. Server-rendered HTML with dynamic updates. One container, not two. |
| Gunicorn (WSGI), not Uvicorn (ASGI) | No async workload. 5 users. WSGI is simpler and more battle-tested. |
| Host PostgreSQL, not containerized | Already running for Taiga. Zero incremental cost. |
| APScheduler in management command, not Celery | No message broker needed. 4-5 scheduled tasks. Run alongside Gunicorn. |
| Django sessions (cookies), not JWT | Same-origin app. No CORS. No token management. httpOnly session cookie is simpler and more secure. |
| django-allauth, not custom OAuth | De facto standard for Django social auth. Google provider built in. |
| Django admin for config, not custom UI | SLA rules, inbox config, and user management are admin tasks for 1 person (Shreyas). Django admin handles this for free. |
| 1 container, not 2+ | Everything in one Docker image: Gunicorn + APScheduler + static files. Nginx is on the host. |

## Scalability Considerations

| Concern | At 5 users (current) | At 20 users | At 100 users |
|---------|----------------------|-------------|--------------|
| **Web traffic** | Negligible. 2 Gunicorn workers. | Still negligible. | Add workers, still fine. |
| **Email volume** | ~50/day. Single poll cycle handles it. | ~200/day. Still fine. | Reduce poll interval. |
| **Database** | Shared with Taiga. No issues. | Add connection pooling. | Dedicated instance. |
| **Background jobs** | APScheduler in-process. | Still fine. | Consider separate worker. |
| **Dashboard** | HTMX polling every 30s. | Still fine. | Consider SSE. |

**Bottom line:** This system will never reach 100 users. It's a single-company internal tool. Design for 5, tolerate 20, don't think about 100.

## Sources

- [Django + HTMX + Tailwind tutorial (TestDriven.io)](https://testdriven.io/blog/django-htmx-tailwind/)
- [Django Docker deployment guide (2026)](https://medium.com/@sizanmahmud08/production-ready-django-with-docker-in-2026-complete-guide-with-nginx-postgresql-and-best-1fb248e65983)
- [HTMX vs React dashboard comparison (2026)](https://medium.com/@the_atomic_architect/react-vs-htmx-i-built-the-same-dashboard-with-both-one-of-them-is-a-maintenance-nightmare-9f2ef3e84728)
- [django-apscheduler PyPI](https://pypi.org/project/django-apscheduler/)
- [django-allauth Google provider docs](https://docs.allauth.org/en/dev/socialaccount/providers/google.html)
- v1 codebase analysis (`.planning/codebase/ARCHITECTURE.md`) -- HIGH confidence (firsthand)

---

*Architecture analysis: 2026-03-09 (revised for Django+HTMX stack)*
