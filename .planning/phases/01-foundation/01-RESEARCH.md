# Phase 1: Foundation - Research

**Researched:** 2026-03-09
**Domain:** Django project setup, PostgreSQL, Docker Compose deployment, CI/CD
**Confidence:** HIGH

## Summary

Phase 1 establishes the Django 5.2 LTS skeleton with PostgreSQL, simple password authentication, team management via Django admin, Docker Compose deployment on the existing VM (alongside Taiga), an Nginx server block, a health endpoint, and a tag-based CI/CD pipeline via GitHub Actions SSH deploy.

The VM already runs Taiga in Docker Compose behind Nginx with SSL (Let's Encrypt), and PostgreSQL is already available on the host. The v2 application connects to the same PostgreSQL instance via Docker networking but uses a separate `vipl_email_agent` database. The architecture is a single Django + Gunicorn container (no frontend container -- HTMX is server-rendered), with the existing Nginx on the host handling SSL termination and reverse proxy.

**Primary recommendation:** Use Django 5.2 LTS with a custom user model extending AbstractUser, psycopg (v3) as the database adapter, Gunicorn as the application server, and SSH-based deployment from GitHub Actions. Keep the project structure simple with a multi-app layout under an `apps/` directory. Do NOT use django-health-check for the health endpoint -- a simple custom view returning JSON is sufficient for 4-5 users.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- VM already runs Taiga in Docker Compose behind Nginx with SSL (Let's Encrypt)
- Add Nginx server block for `triage.vidarbhainfotech.com` proxying to the email agent container
- Use same PostgreSQL instance as Taiga (separate database, not separate container)
- Single Docker container: Django + Gunicorn (no separate frontend container -- HTMX is server-rendered)
- APScheduler runs as a separate Django management command process within the same container
- Tag-based deployment via GitHub Actions (same pattern as v1)
- Store full email body + headers + metadata (not just summary)
- Attachment metadata only (filename, size, MIME type) -- actual files stay in Gmail
- Soft delete for all records (never lose data)
- Connect to host PostgreSQL via Docker network (same instance as Taiga, separate `vipl_email_agent` database)
- Simple password auth (Django's built-in auth system)
- Two roles: Admin and Team Member
- Visibility is configurable per-user: admin can set whether a team member sees all emails or only their assigned ones
- Team member creation starts via Django admin panel (dashboard UI for this is a later phase)
- Same repo, v2 branch -- will merge to main once v2 is proven in production
- v1 code on main branch stays untouched until cutover (Phase 6)

### Claude's Discretion
- CI/CD mechanism (SSH deploy vs registry pull)
- Agent module placement (Django app vs standalone package)
- Attachment handling approach (metadata-only for now)
- Django project layout (single app vs multi-app)
- Gunicorn worker count and configuration

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | Dashboard requires login (simple password auth for v1) | Django's built-in auth system with custom user model extending AbstractUser; LoginRequiredMixin for views |
| AUTH-02 | Admin role (manager) can assign, reassign, configure | Custom `role` field on user model with `ADMIN`/`MEMBER` choices; Django admin for management in Phase 1 |
| AUTH-03 | User role (team member) sees their assignments and can acknowledge | `can_see_all_emails` boolean field on user model; view-level filtering in later phases |
| INFR-01 | PostgreSQL is the source of truth for all email and assignment data | Django ORM with psycopg3, connect to host PostgreSQL via Docker network; models defined with soft delete |
| INFR-02 | System deployed via Docker Compose on existing VM | Single-service docker-compose.yml for Django+Gunicorn; Nginx config on host; SSL via existing Let's Encrypt |
| INFR-03 | CI/CD via GitHub Actions triggered by version tags | SSH-based deploy: build image on VM, docker compose up; tag pattern same as v1 |
| INFR-06 | Health endpoint reports system status (uptime, version) | Custom Django view returning JSON with uptime, version, db connectivity |
| INFR-12 | Admin can manage team members (add/remove, set roles) | Django admin panel with custom UserAdmin; role field exposed in admin UI |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 5.2 LTS | Web framework | LTS until April 2028, supports Python 3.10-3.14, PostgreSQL 14+ |
| psycopg | 3.2+ | PostgreSQL adapter | Native Django 5.2 support, connection pooling, replaces psycopg2 |
| gunicorn | 23+ | WSGI application server | Standard production Django server, pre-fork worker model |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.0+ | Load .env files | Local development; production uses env vars directly |
| whitenoise | 6.8+ | Static file serving | Serve static files from Gunicorn without Nginx static location (simpler setup) |
| dj-database-url | 2.3+ | Database URL parsing | Parse `DATABASE_URL` env var into Django DATABASES config |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psycopg (v3) | psycopg2-binary | v2 still supported in Django 5.2 but likely to be deprecated; v3 has connection pooling |
| python-dotenv | django-environ | django-environ does type casting magic that has caused parsing bugs (especially with `#` in SECRET_KEY); python-dotenv is simpler and more predictable |
| whitenoise | Nginx static serving | Nginx static is faster but adds config complexity; whitenoise is fine for 4-5 users |
| dj-database-url | manual DATABASES dict | dj-database-url is cleaner for Docker/env-var-based config |

**Installation:**
```bash
pip install django==5.2.* psycopg[binary] gunicorn whitenoise dj-database-url python-dotenv
```

## Architecture Patterns

### Recommended Project Structure

The v2 code lives in the repo root on the `v2` branch. The v1 code (`agent/`, `main.py`, etc.) remains on `main` branch untouched.

```
vipl-email-agent/              # repo root (v2 branch)
├── config/                    # Django project config (replaces default "project_name/" dir)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py            # Shared settings
│   │   ├── dev.py             # Local dev overrides
│   │   └── prod.py            # Production settings
│   ├── urls.py                # Root URL configuration
│   ├── wsgi.py
│   └── asgi.py
├── apps/                      # All Django apps
│   ├── __init__.py
│   ├── accounts/              # Custom user model, auth views, team management
│   │   ├── models.py          # User model with role field
│   │   ├── admin.py           # Custom UserAdmin
│   │   ├── views.py           # Login/logout views
│   │   ├── urls.py
│   │   └── tests/
│   ├── emails/                # Email models (Phase 2 populates, but models defined now)
│   │   ├── models.py          # Email, Attachment metadata, etc.
│   │   ├── admin.py
│   │   └── tests/
│   └── core/                  # Health endpoint, shared utilities, base models
│       ├── models.py          # SoftDeleteModel base, TimestampedModel base
│       ├── views.py           # Health check endpoint
│       ├── urls.py
│       └── tests/
├── templates/                 # Project-level templates
│   ├── base.html
│   └── registration/          # Django auth templates
│       └── login.html
├── static/                    # Project-level static files
├── manage.py
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Dev/test dependencies
├── Dockerfile                 # Django + Gunicorn
├── docker-compose.yml         # Single service + network config
├── gunicorn.conf.py           # Gunicorn configuration
├── .env.example               # Template for environment variables
└── nginx/                     # Nginx server block config (deployed to VM)
    └── triage.conf
```

**Rationale for multi-app layout:**
- `accounts` owns the user model and auth -- clean separation from email domain
- `emails` owns all email-related models -- this grows significantly in Phase 2-4
- `core` owns shared infrastructure (health endpoint, base models, utilities)
- Apps under `apps/` directory keeps the root clean
- Each app is in `INSTALLED_APPS` as `apps.accounts`, `apps.emails`, `apps.core`

### Pattern 1: Custom User Model with Role Field

**What:** Extend AbstractUser with a `role` choice field and visibility flag.
**When to use:** Always -- must be done before first migration.

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Team Member"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    can_see_all_emails = models.BooleanField(
        default=False,
        help_text="If False, user only sees emails assigned to them",
    )

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

# config/settings/base.py
AUTH_USER_MODEL = "accounts.User"
```

### Pattern 2: Soft Delete Base Model

**What:** Abstract model that overrides `delete()` to set a `deleted_at` timestamp instead of removing the row.
**When to use:** All models that store business data (emails, assignments, etc.).

```python
# apps/core/models.py
from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()  # Default: excludes soft-deleted
    all_objects = models.Manager()  # Includes soft-deleted

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

### Pattern 3: Split Settings

**What:** Base/dev/prod settings files instead of a single `settings.py`.
**When to use:** Always for projects with Docker deployment.

```python
# config/settings/base.py
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# config/settings/dev.py
from .base import *
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")
DEBUG = True

# config/settings/prod.py
from .base import *
DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
DATABASES = {"default": dj_database_url.config(conn_max_age=600)}
```

### Pattern 4: Health Endpoint

**What:** Simple JSON view returning system status.
**When to use:** Phase 1 -- no external library needed.

```python
# apps/core/views.py
import time
from django.http import JsonResponse
from django.db import connection

_start_time = time.time()
VERSION = os.environ.get("APP_VERSION", "dev")

def health_check(request):
    db_ok = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:
        pass

    status = {
        "status": "healthy" if db_ok else "degraded",
        "version": VERSION,
        "uptime_seconds": int(time.time() - _start_time),
        "database": "connected" if db_ok else "error",
    }
    status_code = 200 if db_ok else 503
    return JsonResponse(status, status=status_code)
```

### Anti-Patterns to Avoid
- **Using default `User` model:** Django makes it extremely painful to switch to a custom user model after migrations exist. Always start with `AbstractUser` even if you don't need extra fields yet.
- **Single settings.py with `if DEBUG`:** Leads to production secrets in development config. Split settings are cleaner.
- **Running migrations in Docker CMD:** Migrations should run as a one-time step (entrypoint script or separate command), not on every container start in production.
- **Storing static files inside the container without collectstatic:** Django's `STATICFILES_DIRS` and `STATIC_ROOT` must be configured, and `collectstatic` must run during Docker build.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database URL parsing | Manual dict construction from env vars | `dj-database-url` | Handles all PostgreSQL URL formats, connection pooling params, SSL mode |
| Password hashing | Custom auth | Django's built-in `AbstractUser` + `auth` app | PBKDF2 by default, argon2 optional, timing-attack safe |
| CSRF protection | Custom middleware | Django's built-in CSRF middleware | Already enabled by default, handles edge cases |
| Static file serving | Custom view or manual Nginx config | `whitenoise` | Compression, caching headers, zero-config with Django |
| Session management | Custom session logic | Django's `django.contrib.sessions` | DB-backed sessions, secure cookie signing, built-in |

**Key insight:** Django's auth system is battle-tested and covers login, logout, password hashing, session management, and admin UI out of the box. The only customization needed is the user model (add role field) and admin registration.

## Common Pitfalls

### Pitfall 1: Forgetting AUTH_USER_MODEL Before First Migration
**What goes wrong:** You run `makemigrations` with the default `auth.User`, then try to switch to a custom model later. Django cannot auto-migrate existing user data.
**Why it happens:** It feels like you can "add it later" but Django's auth migrations are tightly coupled.
**How to avoid:** Set `AUTH_USER_MODEL = "accounts.User"` in settings BEFORE running any migrations. This is the very first thing to configure.
**Warning signs:** You see `auth.User` referenced in any migration file.

### Pitfall 2: Docker Container Cannot Reach Host PostgreSQL
**What goes wrong:** Django container can't connect to PostgreSQL running on the VM host.
**Why it happens:** `localhost` inside a Docker container refers to the container itself, not the host.
**How to avoid:** Use `host.docker.internal` (Docker Desktop) or the Docker bridge gateway IP. On Linux, use `extra_hosts: ["host.docker.internal:host-gateway"]` in docker-compose.yml, or connect via the host's Docker bridge network IP. The simplest approach: configure PostgreSQL to listen on the Docker bridge network and use the gateway IP.
**Warning signs:** `connection refused` errors in Django logs.

### Pitfall 3: PostgreSQL pg_hba.conf Blocking Docker Connections
**What goes wrong:** Even with the right host, PostgreSQL rejects connections from the Docker network subnet.
**Why it happens:** Default pg_hba.conf only allows local connections. Docker containers come from a different subnet (typically `172.17.0.0/16` or `172.18.0.0/16`).
**How to avoid:** Add a line to `pg_hba.conf`: `host vipl_email_agent vipl_agent 172.0.0.0/8 md5` (adjust subnet). Also ensure `postgresql.conf` has `listen_addresses = '*'` or includes the Docker bridge IP. Create a dedicated PostgreSQL user for the email agent (don't reuse the Taiga user).
**Warning signs:** `pg_hba.conf rejects connection` in PostgreSQL logs.

### Pitfall 4: Nginx Config Conflicts with Existing Taiga Setup
**What goes wrong:** Adding a new server block breaks the existing Taiga site.
**Why it happens:** Nginx config includes are order-sensitive; duplicate `default_server` directives or conflicting SSL configs cause failures.
**How to avoid:** Add a separate file in `/etc/nginx/sites-available/triage.vidarbhainfotech.com` and symlink to `sites-enabled/`. Use `certbot --nginx -d triage.vidarbhainfotech.com` to add SSL (it modifies the server block in place). Never touch the Taiga server block.
**Warning signs:** `nginx -t` fails after adding the new config.

### Pitfall 5: Gunicorn Workers and Memory on a Shared VM
**What goes wrong:** Too many Gunicorn workers consume memory needed by Taiga and other services.
**Why it happens:** The default formula `(2 * CPU) + 1` assumes dedicated resources.
**How to avoid:** Start with 2 workers (sufficient for 4-5 users). Monitor memory usage. Configure via `gunicorn.conf.py` so it's explicit and documented.
**Warning signs:** OOM kills in dmesg, Taiga becoming slow.

### Pitfall 6: Forgetting collectstatic in Docker Build
**What goes wrong:** Static files (CSS, JS for admin and login pages) return 404 in production.
**Why it happens:** Django doesn't serve static files in production mode (`DEBUG=False`). You need `collectstatic` to gather them and whitenoise to serve them.
**How to avoid:** Add `RUN python manage.py collectstatic --noinput` in the Dockerfile after copying source code. Configure whitenoise in middleware.
**Warning signs:** Admin panel and login page have no styling.

## Code Examples

### Docker Compose Configuration
```yaml
# docker-compose.yml
services:
  web:
    build: .
    container_name: vipl-email-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
    ports:
      - "8100:8000"  # Map to unused host port; Nginx proxies to this
    extra_hosts:
      - "host.docker.internal:host-gateway"  # Access host PostgreSQL
    volumes:
      - static_files:/app/staticfiles
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  static_files:
```

### Nginx Server Block
```nginx
# nginx/triage.conf
# Deploy to /etc/nginx/sites-available/triage.vidarbhainfotech.com
# Then: ln -s /etc/nginx/sites-available/triage.vidarbhainfotech.com /etc/nginx/sites-enabled/
# Then: certbot --nginx -d triage.vidarbhainfotech.com

server {
    listen 80;
    server_name triage.vidarbhainfotech.com;

    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files at build time
RUN DJANGO_SETTINGS_MODULE=config.settings.prod \
    SECRET_KEY=build-placeholder \
    DATABASE_URL=sqlite:///placeholder.db \
    python manage.py collectstatic --noinput

# Non-root user
RUN groupadd -r agent && useradd -r -g agent agent
RUN chown -R agent:agent /app
USER agent

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
```

### Gunicorn Configuration
```python
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 2  # Small app, shared VM -- keep low
threads = 2
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

### GitHub Actions CI/CD (SSH Deploy)
```yaml
# .github/workflows/deploy.yml (v2 -- replaces Cloud Run deploy)
name: Deploy & Release

on:
  push:
    tags:
      - 'v*.*.*'
  pull_request:
    branches: [v2]

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest --tb=short -q

  deploy:
    name: Deploy to VM
    needs: test
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VM_HOST }}
          username: ${{ secrets.VM_USER }}
          key: ${{ secrets.VM_SSH_KEY }}
          script: |
            cd /opt/vipl-email-agent
            git fetch --tags
            git checkout ${{ github.ref_name }}
            docker compose build --no-cache
            docker compose up -d
            docker compose exec web python manage.py migrate --noinput
            echo "Deployed ${{ github.ref_name }}"
```

**Recommendation on CI/CD mechanism (Claude's Discretion):** Use SSH deploy with `appleboy/ssh-action`. The VM pulls from the git repo and builds locally. This is simpler than setting up a Docker registry for a single-instance app. The VM already has Docker and git. No registry infrastructure needed. The tradeoff: builds happen on the VM (uses VM CPU for ~1-2 min), but for a small Django app this is negligible.

**Recommendation on Django project layout (Claude's Discretion):** Multi-app under `apps/` directory. Three apps: `accounts` (user/auth), `emails` (email models), `core` (health, utilities, base models). This separates concerns cleanly and scales well as phases add features.

**Recommendation on Gunicorn configuration (Claude's Discretion):** 2 sync workers, 2 threads each. This handles 4-5 concurrent users easily while keeping memory low on the shared VM. Total: 4 effective threads, well under 100MB additional memory.

**Recommendation on agent module placement (Claude's Discretion):** Keep agent modules as a Django app (`apps/agent/`) in Phase 2. The v1 modules (`agent/*.py`) need significant refactoring to use Django ORM instead of Google Sheets, so a clean rewrite within the Django app structure is cleaner than trying to import standalone modules. The `apps/agent/` app will contain management commands for the scheduler and ported service classes.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| psycopg2 | psycopg (v3) | Django 4.2+ (2023) | Connection pooling, async support, server-side binding |
| Single settings.py | Split settings (base/dev/prod) | Convention since ~2015, widely adopted | Cleaner env separation, no `if DEBUG` conditionals |
| django-environ | python-dotenv + dj-database-url | 2024+ trend | Avoids django-environ parsing bugs, more predictable |
| runserver in Docker | Gunicorn always | Always, but Django 5.2 now warns | Django 5.2 shows production warning for runserver |

**Deprecated/outdated:**
- `psycopg2`: Still works in Django 5.2 but will be deprecated. Use `psycopg` (v3) for new projects.
- `django.db.backends.postgresql_psycopg2`: Use `django.db.backends.postgresql` (works with both v2 and v3).

## Open Questions

1. **VM Resource Audit**
   - What we know: VM hosts Taiga + PostgreSQL + other internal tools
   - What's unclear: Available RAM, CPU cores, disk space, PostgreSQL version, Docker version
   - Recommendation: Run a quick audit before deployment (`free -h`, `nproc`, `df -h`, `psql --version`, `docker --version`). This is an operational step during Plan 01-02 execution, not a blocker for planning.

2. **DNS for triage.vidarbhainfotech.com**
   - What we know: Subdomain is decided
   - What's unclear: Whether the DNS A record already points to the VM
   - Recommendation: User needs to add DNS record before deployment. This is a prerequisite for Plan 01-02.

3. **PostgreSQL Authentication Method on VM**
   - What we know: PostgreSQL runs on the VM for Taiga
   - What's unclear: Whether it uses peer auth, md5, or scram-sha-256; whether `pg_hba.conf` allows TCP connections from Docker subnet
   - Recommendation: Check during Plan 01-02 execution. Likely needs a new database user and pg_hba.conf entry.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` (exists for v1, needs updating for v2 Django settings) |
| Quick run command | `pytest apps/ --tb=short -q` |
| Full suite command | `pytest apps/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Login with username/password | unit | `pytest apps/accounts/tests/test_auth.py -x` | Wave 0 |
| AUTH-02 | Admin role can be set on users | unit | `pytest apps/accounts/tests/test_models.py -x` | Wave 0 |
| AUTH-03 | User visibility flag filters correctly | unit | `pytest apps/accounts/tests/test_models.py -x` | Wave 0 |
| INFR-01 | Django ORM connects to PostgreSQL | integration | `pytest apps/core/tests/test_db.py -x` | Wave 0 |
| INFR-02 | Docker Compose starts successfully | smoke | `docker compose up -d && docker compose exec web python manage.py check` | Manual |
| INFR-03 | CI/CD deploys on version tag | smoke | `gh workflow run deploy.yml` (manual trigger test) | Manual |
| INFR-06 | Health endpoint returns JSON status | unit | `pytest apps/core/tests/test_health.py -x` | Wave 0 |
| INFR-12 | Admin can manage team members | unit | `pytest apps/accounts/tests/test_admin.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/ --tb=short -q`
- **Per wave merge:** `pytest apps/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pytest.ini` -- update for Django settings module (`DJANGO_SETTINGS_MODULE=config.settings.dev`)
- [ ] `conftest.py` -- shared fixtures for Django test client, admin user factory, member user factory
- [ ] `apps/accounts/tests/` -- test directory and `__init__.py`
- [ ] `apps/core/tests/` -- test directory and `__init__.py`
- [ ] `apps/emails/tests/` -- test directory and `__init__.py`
- [ ] Framework install: `pip install pytest pytest-django factory-boy` added to `requirements-dev.txt`

## Sources

### Primary (HIGH confidence)
- [Django 5.2 release notes](https://docs.djangoproject.com/en/6.0/releases/5.2/) - LTS status, Python/PostgreSQL version support, new features
- [Django custom user model docs](https://docs.djangoproject.com/en/5.0/topics/auth/customizing/) - AbstractUser extension pattern
- [Django Forum: psycopg2 support in 5.2](https://forum.djangoproject.com/t/is-psycopg2-still-supported-in-django-5-2/41032) - psycopg v3 migration guidance
- [dj-database-url PyPI](https://pypi.org/project/dj-database-url/) - Database URL parsing for Django

### Secondary (MEDIUM confidence)
- [TestDriven.io: Dockerizing Django](https://testdriven.io/blog/dockerizing-django-with-postgres-gunicorn-and-nginx/) - Docker Compose + Gunicorn + Nginx patterns
- [appleboy/ssh-action GitHub](https://github.com/marketplace/actions/docker-compose-deployment-ssh) - GitHub Actions SSH deployment
- [Django Forum: project structure best practices](https://forum.djangoproject.com/t/best-practices-for-structuring-django-projects/39835) - Multi-app layout conventions

### Tertiary (LOW confidence)
- Gunicorn worker count recommendation (2 workers for shared VM) -- based on general guidance, should be validated with actual VM resource audit

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Django 5.2 LTS, psycopg3, gunicorn are well-documented and stable
- Architecture: HIGH - Multi-app Django layout is a proven pattern; Docker Compose + Nginx reverse proxy is standard
- Pitfalls: HIGH - PostgreSQL Docker networking and pg_hba.conf issues are well-known; custom user model requirement is in official Django docs
- CI/CD: MEDIUM - SSH deploy with appleboy/ssh-action is common but the exact VM setup needs runtime validation
- VM compatibility: LOW - Cannot verify VM resources, PostgreSQL version, or Docker version without access

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable stack, 30-day validity)
