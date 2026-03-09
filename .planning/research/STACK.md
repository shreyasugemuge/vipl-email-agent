# Technology Stack

**Project:** VIPL Email Agent v2
**Researched:** 2026-03-09
**Overall Confidence:** HIGH

## Recommendation: Django + HTMX (Not FastAPI + React)

The user said they are not married to FastAPI + React. After research, the best fit for this project is **Django + HTMX + Tailwind CSS** -- a single deployable unit with no JavaScript build toolchain, no separate frontend container, and batteries included for auth, ORM, admin, and migrations.

**Why not FastAPI + React?**

FastAPI + React is two separate applications: a JSON API backend and a JavaScript SPA frontend. This means two containers, two build systems, two sets of dependencies, CORS configuration, token-based auth between frontend and backend, and a JavaScript bundler (Vite/webpack). For 4-5 users viewing an email dashboard, this is massive over-engineering.

**Why Django + HTMX?**

Django is purpose-built for exactly this: CRUD dashboards with auth, an ORM, migrations, and admin. HTMX adds dynamic interactivity (table filtering, inline editing, live updates) without writing JavaScript. The result is one Python application, one container, zero JavaScript build steps, and a fraction of the code.

## Recommended Stack

### Web Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Django | 5.2 LTS | Web framework | LTS until April 2028. Includes ORM, migrations, auth, admin, templating, CSRF protection, session management. Everything this project needs out of the box. The "boring technology" choice -- proven at scale, massive ecosystem, excellent docs. | HIGH |

**Why not FastAPI:** FastAPI excels at high-throughput async APIs. This project is a CRUD dashboard for 5 users. FastAPI would require assembling auth, ORM, migrations, and admin from scratch (SQLAlchemy + Alembic + custom auth middleware + no admin panel). Django includes all of these.

**Why not Flask:** Flask is too minimal. You'd need Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-Admin -- reassembling Django from parts. At that point, just use Django.

### Frontend (No Separate App)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| HTMX | 2.0.x | Dynamic UI interactions | Adds AJAX, partial page updates, and interactivity via HTML attributes. No JavaScript build step, no npm, no node_modules. 14KB gzipped. Served as a static file. | HIGH |
| Tailwind CSS | 3.4.x | Utility-first styling | Rapid UI development without writing custom CSS. Use standalone CLI binary (no Node.js needed). | HIGH |
| Alpine.js | 3.x | Minimal client-side state | For the 5% of UI that needs client-side logic (dropdowns, modals, toggle states). 15KB. Complements HTMX. | MEDIUM |

**Why not React:** React requires a separate build toolchain (Node.js, npm, Vite/webpack), a separate Docker container or build stage, state management (Redux/Zustand), a router, API client (axios/fetch), and CORS configuration. For a table-view dashboard with filters, this is extreme overkill. Multiple production comparisons in 2025-2026 show HTMX dashboards ship faster and are easier to maintain for small teams.

**Why not Streamlit/Dash:** These are data visualization tools, not application frameworks. No auth, no custom workflows, no assignment engine, no fine-grained UI control. Wrong tool for the job.

### Database & ORM

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PostgreSQL | (existing on VM) | Primary database | Already running on the VM for Taiga. Zero incremental cost. Proper relational DB with joins, indexes, constraints, JSONB. | HIGH |
| Django ORM | (bundled with Django 5.2) | Object-relational mapping | Integrated with Django. Migrations are automatic (`makemigrations` / `migrate`). Simpler than SQLAlchemy for this use case (no Unit of Work pattern needed). Active Record pattern is perfectly fine for a CRUD app. | HIGH |

**Why not SQLAlchemy + Alembic:** SQLAlchemy is more powerful and flexible, but that power is unnecessary here. The data model is straightforward (emails, assignments, users, SLA configs). Django ORM handles this trivially and migrations are automatic. SQLAlchemy + Alembic would require more boilerplate for zero benefit.

### Authentication

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| django-allauth | 65.14.x | Google OAuth SSO | Mature, actively maintained (latest release Feb 2026). Native Google OAuth support with `hd` parameter for domain restriction to @vidarbhainfotech.com. Handles the full OAuth flow: redirect, callback, token exchange, session creation. | HIGH |

**Configuration for domain restriction:**
```python
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APPS': [{
            'client_id': '...',
            'secret': '...',
            'settings': {
                'auth_params': {'hd': 'vidarbhainfotech.com'}
            }
        }],
        'SCOPE': ['profile', 'email'],
    }
}
```

Plus a custom adapter to reject non-@vidarbhainfotech.com emails server-side (the `hd` param is client-side only and can be bypassed):

```python
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import PermissionDenied

class VIPLAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get('email', '')
        if not email.endswith('@vidarbhainfotech.com'):
            raise PermissionDenied("Only @vidarbhainfotech.com accounts allowed")
```

**Why not authlib / python-social-auth:** django-allauth is the de facto standard for Django social auth. 65+ versions, active maintenance, first-class Google support. No reason to use anything else.

### Background Tasks (Email Processing)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| APScheduler | 3.10.x | Background job scheduling | Already proven in v1. Runs email polling, SLA checks, EOD reports, dead letter retry. Integrates with Django via django-apscheduler or manual startup in management command. | HIGH |
| django-apscheduler | 0.7.x | Django integration for APScheduler | Provides database-backed job storage and admin console visibility for scheduled jobs. Ensures single-scheduler constraint. | MEDIUM |

**Why not Celery:** Celery requires Redis or RabbitMQ as a message broker -- another service to deploy and maintain. The workload is 4-5 scheduled tasks (poll every 5 min, SLA every 15 min, EOD daily, retry every 30 min). APScheduler handles this trivially in-process. Celery is for distributed task queues with thousands of tasks -- not this.

**Why not Django-Q2:** Newer alternative to Celery but still requires a broker. Same over-engineering concern.

### HTTP Server

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Gunicorn | 22.x | WSGI server | Standard production Django server. Handles concurrent requests, worker management, graceful restarts. | HIGH |
| Nginx | (existing on VM) | Reverse proxy + static files | Already on the VM for Taiga. Serves static files (CSS, JS, images), terminates SSL, proxies to Gunicorn. | HIGH |

**Why not Uvicorn/Daphne (ASGI):** Django 5.2 supports ASGI, but there is no async workload in this app. The dashboard serves 4-5 users. Gunicorn with sync workers is simpler, more battle-tested, and perfectly adequate. ASGI adds complexity for zero benefit here.

### Deployment

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Docker | (existing) | Containerization | Single Dockerfile for the Django app. Includes Gunicorn, static file collection, and APScheduler startup. | HIGH |
| Docker Compose | (existing) | Multi-container orchestration | Defines Django app container + Nginx container. PostgreSQL is already running on the VM (shared with Taiga), so it is NOT containerized -- connect via host network. | HIGH |

**Key architecture decision:** PostgreSQL stays as a host service (already managed for Taiga), not a Docker container. The Django app connects to it via `host.docker.internal` or the host's IP.

**Docker Compose structure (2 containers, not 3):**
```
nginx (reverse proxy + static files)
  -> django-app (Gunicorn + APScheduler)
  -> PostgreSQL (host service, shared with Taiga)
```

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| django-htmx | 1.19.x | HTMX middleware for Django | Always. Adds `request.htmx` attribute for detecting HTMX requests and returning partials vs full pages. | HIGH |
| django-filter | 24.x | Queryset filtering from URL params | Dashboard table filters (by status, priority, assignee, date range). | HIGH |
| django-tables2 | 2.7.x | HTML table rendering with sorting/pagination | Email list table with sortable columns and pagination. | MEDIUM |
| whitenoise | 6.x | Static file serving | Serve Django static files without Nginx in development. Optional in production (Nginx handles it). | HIGH |
| psycopg | 3.2.x | PostgreSQL adapter | Django 5.2 supports psycopg3 natively. Faster than psycopg2. | HIGH |
| django-environ | 0.11.x | Environment variable parsing | Clean `.env` file support for local dev and Docker. | MEDIUM |
| anthropic | 0.42+ | Claude AI SDK | Already in v1. Unchanged. | HIGH |
| google-api-python-client | 2.114+ | Gmail + Sheets API | Already in v1. Gmail polling unchanged. Sheets becomes write-only sync mirror. | HIGH |
| tenacity | 8.2+ | Retry with backoff | Already in v1. Unchanged. | HIGH |
| httpx | 0.27+ | HTTP client | Already in v1. Google Chat webhooks. | HIGH |

### Development Tools

| Tool | Version | Purpose | Confidence |
|------|---------|---------|------------|
| pytest + pytest-django | 8.x + 4.x | Testing | Django test client + existing pytest patterns from v1. | HIGH |
| ruff | 0.9.x | Linting + formatting | Replaces flake8 + black + isort. Single tool, fast. | MEDIUM |
| django-debug-toolbar | 4.x | Dev-only SQL query inspection | Catch N+1 queries during development. | MEDIUM |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web Framework | Django 5.2 LTS | FastAPI | No built-in ORM, migrations, auth, admin, or templating. Requires assembling from parts (SQLAlchemy + Alembic + custom auth + custom admin). More code, more complexity, zero benefit for a 5-user CRUD dashboard. |
| Web Framework | Django 5.2 LTS | Flask | Too minimal. Requires Flask-SQLAlchemy + Flask-Migrate + Flask-Login + Flask-Admin. Basically reassembling Django from extensions. |
| Frontend | HTMX + Tailwind | React | Requires separate build toolchain, separate container, CORS, token auth, 10x more code. Massive overkill for a table-view dashboard. |
| Frontend | HTMX + Tailwind | Vue.js | Same concerns as React. Slightly simpler but still requires a JS build step and separate deployment. |
| Frontend | HTMX + Tailwind | Svelte | Same SPA concerns. Smaller bundle but still requires Node.js toolchain. |
| ORM | Django ORM | SQLAlchemy 2.0 | More powerful but unnecessary complexity. Data model is simple CRUD. Django ORM migrations are automatic. |
| Auth | django-allauth | Authlib | Less Django-native. django-allauth is the standard for Django social auth. |
| Background Tasks | APScheduler | Celery + Redis | Requires a message broker (Redis). Overkill for 4-5 scheduled tasks. APScheduler is already proven in v1. |
| CSS | Tailwind CSS | Bootstrap | Bootstrap's opinionated components fight customization. Tailwind's utility classes give full control. |
| DB Adapter | psycopg3 | psycopg2-binary | psycopg3 is the modern replacement, natively supported in Django 5.2. Better performance, proper async support if ever needed. |

## What This Eliminates

Choosing Django + HTMX over FastAPI + React eliminates:

- **Node.js** -- not needed anywhere in the stack
- **npm / yarn / pnpm** -- no JavaScript package manager
- **Vite / webpack** -- no JavaScript bundler
- **React / Vue / Svelte** -- no JavaScript framework
- **Redux / Zustand** -- no client-side state management
- **React Router** -- no client-side routing
- **CORS configuration** -- no cross-origin requests (everything is same-origin)
- **JWT tokens** -- Django sessions handle auth (cookies, not tokens)
- **Separate frontend container** -- one container, not two
- **SQLAlchemy + Alembic** -- Django ORM + built-in migrations
- **Redis / RabbitMQ** -- no message broker needed
- **Celery** -- APScheduler suffices

## Installation

```bash
# Core
pip install django==5.2.12 \
  gunicorn==22.0.0 \
  psycopg[binary]==3.2.5 \
  django-allauth==65.14.1 \
  django-htmx==1.19.0 \
  django-filter==24.3 \
  django-tables2==2.7.0 \
  django-environ==0.11.2 \
  django-apscheduler==0.7.0 \
  whitenoise==6.8.2

# Carried from v1 (unchanged)
pip install anthropic==0.42.0 \
  google-api-python-client==2.114.0 \
  google-auth==2.27.0 \
  google-auth-httplib2==0.2.0 \
  httpx==0.27.0 \
  tenacity==8.2.3 \
  jinja2==3.1.3 \
  pymupdf==1.24.3 \
  pyyaml==6.0.1 \
  pytz==2024.1

# Tailwind CSS (standalone CLI, no Node.js)
# Download binary: https://github.com/tailwindlabs/tailwindcss/releases
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
chmod +x tailwindcss-macos-arm64
mv tailwindcss-macos-arm64 /usr/local/bin/tailwindcss

# HTMX (static file, no npm)
curl -sLO https://unpkg.com/htmx.org@2.0.8/dist/htmx.min.js
# Place in Django's staticfiles directory

# Dev dependencies
pip install pytest==8.3.4 \
  pytest-django==4.9.0 \
  pytest-cov==5.0.0 \
  django-debug-toolbar==4.4.6 \
  ruff==0.9.3
```

## Version Verification Notes

| Package | Verified Version | Source | Date Checked |
|---------|-----------------|--------|--------------|
| Django | 5.2.12 LTS | djangoproject.com/download | 2026-03-09 |
| django-allauth | 65.14.1 | allauth.org/news | 2026-03-09 |
| HTMX | 2.0.8 | htmx.org | 2026-03-09 |
| SQLAlchemy (not used) | 2.0.48 | sqlalchemy.org | 2026-03-09 |
| Alembic (not used) | 1.18.4 | pypi.org | 2026-03-09 |
| psycopg3 | 3.2.x | pypi.org | 2026-03-09 |
| APScheduler | 3.10.x (3.x series) | pypi.org | 2026-03-09 |

**Note on Django version:** Django 5.2 LTS was released April 2, 2025, with support until April 2028. Patch versions (5.2.10, 5.2.11, 5.2.12) are security/bugfix releases. Pin to latest patch at time of development.

## Migration Strategy: v1 Modules into Django

The v1 `agent/` modules (gmail_poller, ai_processor, chat_notifier, sla_monitor, eod_reporter) are pure Python classes with no framework dependency. They integrate into Django as follows:

1. **Create a Django app** called `agent` (or `inbox`)
2. **Import v1 modules** directly -- they don't depend on any web framework
3. **Replace SheetLogger** with Django ORM models (Email, Assignment, SLAConfig, etc.)
4. **Keep APScheduler** running inside the Django process via a management command (`python manage.py runscheduler`)
5. **Add Django views** that query the ORM and render HTMX templates for the dashboard

The v1 code does NOT need a rewrite. It needs a new persistence layer (Django models instead of SheetLogger) and a web UI on top.

## Sources

- [Django 5.2 LTS release](https://www.djangoproject.com/weblog/2025/apr/02/django-52-released/)
- [Django download page](https://www.djangoproject.com/download/)
- [django-allauth Google provider docs](https://docs.allauth.org/en/dev/socialaccount/providers/google.html)
- [django-allauth 65.14.1 release](https://allauth.org/news/2026/02/django-allauth-65.14.1-released/)
- [HTMX official site](https://htmx.org/)
- [HTMX vs React dashboard comparison (2026)](https://medium.com/@the_atomic_architect/react-vs-htmx-i-built-the-same-dashboard-with-both-one-of-them-is-a-maintenance-nightmare-9f2ef3e84728)
- [FastAPI + HTMX + Jinja2 dashboard pattern](https://www.johal.in/fastapi-templating-jinja2-server-rendered-ml-dashboards-with-htmx-2025/)
- [Django + HTMX + Tailwind tutorial (TestDriven.io)](https://testdriven.io/blog/django-htmx-tailwind/)
- [Django Docker deployment guide (2026)](https://medium.com/@sizanmahmud08/production-ready-django-with-docker-in-2026-complete-guide-with-nginx-postgresql-and-best-1fb248e65983)
- [django-apscheduler PyPI](https://pypi.org/project/django-apscheduler/)
- [FastAPI vs Django comparison (Better Stack)](https://betterstack.com/community/guides/scaling-python/django-vs-fastapi/)
- [SQLAlchemy 2.0.48 release](https://www.sqlalchemy.org/download.html)

---

*Stack research: 2026-03-09*
