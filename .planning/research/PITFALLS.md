# Domain Pitfalls

**Domain:** AI-powered shared inbox management system (v1 -> v2 migration)
**Researched:** 2026-03-09
**Updated:** 2026-03-09 (revised for Django+HTMX stack)

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or prolonged outages.

### Pitfall 1: Sheets-to-PostgreSQL Migration Data Loss from Type Coercion

**What goes wrong:** Google Sheets stores everything as strings with per-cell typing. Dates like "2026-03-09" vs "03/09/2026" vs "March 9, 2026" can coexist in the same column. Ticket numbers may have leading zeros that disappear. SLA deadlines stored as "2026-03-10 17:00 IST" need timezone-aware parsing. The v1 `parse_sheet_datetime` utility in `agent/utils.py` already handles multiple formats -- but a bulk migration script that doesn't replicate all those format variations will silently corrupt data.

**Why it happens:** Developers write migration scripts against "clean" test data, not against 6+ months of production Sheet data that has accumulated format drift, manual edits, and edge cases (empty cells, "ERROR" markers in SLA columns, partially-filled rows from failed writes).

**Consequences:** Corrupted timestamps break SLA calculations. Lost ticket numbers break dedup. Missing thread IDs cause duplicate processing of old emails. If discovered after v1 is shut down, recovery requires manual Sheet inspection.

**Prevention:**
- Export the real production Sheet (all tabs) as CSV before writing any migration code
- Write migration with explicit handling for every format variant found in production data
- Validate row counts and spot-check critical fields (ticket numbers, thread IDs, SLA deadlines) post-migration
- Run v1 and v2 in parallel for at least one week with both writing to their respective stores, comparing outputs
- Keep the Sheet as a read-only archive indefinitely (never delete it)

**Detection:** Row count mismatch between Sheet and PostgreSQL. NULL values in columns that should never be NULL. SLA breach counts diverging between v1 and v2 during parallel run.

---

### Pitfall 2: Google OAuth Domain Restriction Fails Silently on Edge Cases

**What goes wrong:** You restrict login to `@vidarbhainfotech.com` by passing `hd` in django-allauth's `auth_params`. But: (a) the `hd` parameter is a client-side hint only -- Google shows the domain-restricted login page, but a determined user can still complete OAuth with a different account; (b) personal Gmail accounts have no `hd` claim at all; (c) Google Workspace aliases and group email addresses can produce unexpected `hd` values.

**Why it happens:** Tutorials show the happy path. Developers test with their own `@vidarbhainfotech.com` account and never try a personal Gmail or a Google account from another Workspace domain.

**Consequences:** Either unauthorized users can log in (security breach) or legitimate users get unhelpful error messages.

**Prevention:**
- Domain restriction MUST be enforced server-side via a custom django-allauth adapter (`pre_social_login` hook) that checks the email domain
- Check `hd` claim exists AND equals `vidarbhainfotech.com` AND `email_verified` is true
- Return a clear error page: "Only @vidarbhainfotech.com accounts can access this system"
- Test with: a personal Gmail, a different Workspace domain, an account with `email+alias@vidarbhainfotech.com`
- Django-allauth handles the OAuth flow and creates Django User objects automatically -- verify that rejected users don't get User objects created

**Detection:** Login succeeds with a non-VIPL Google account. A User object exists in Django admin for a non-VIPL email.

---

### Pitfall 3: Running v1 and v2 Simultaneously Causes Duplicate Email Processing

**What goes wrong:** During the migration period, both v1 (Cloud Run) and v2 (VM) are running. Both poll the same Gmail inboxes. Both apply the same "Agent/Processed" label. Race condition: both pick up the same email before either labels it. Result: duplicate tickets, duplicate Chat notifications, duplicate AI costs.

**Why it happens:** The migration plan naturally requires a parallel-run period to validate v2. But Gmail polling with label-based dedup is not designed for multi-consumer scenarios.

**Consequences:** Duplicate tickets confuse the team. Duplicate Chat notifications erode trust in the system. Double AI API costs.

**Prevention:**
- Never run both v1 and v2 polling the same inboxes simultaneously
- Migration strategy: cut over inbox-by-inbox (e.g., move `info@` to v2 first, keep `sales@` on v1)
- Or: stop v1 polling, start v2, validate, then shut down v1 entirely -- a hard cutover with a brief monitoring gap
- If parallel validation is needed, have v2 run in "shadow mode" (read-only, no label application, no notifications) and compare its triage output against v1's Sheet entries

**Detection:** Same thread ID appears in both Sheet and PostgreSQL with different ticket numbers. Chat notifications fire twice for the same email.

---

### Pitfall 4: Docker Compose Port and Resource Conflicts with Taiga

**What goes wrong:** The VM already runs Taiga (likely its own Docker Compose or direct deployment) with PostgreSQL, Nginx, and potentially other services. Adding a second Docker Compose project causes: (a) port conflicts if Taiga already binds common ports; (b) PostgreSQL connection exhaustion if v2 creates a pool without considering Taiga's connections; (c) Docker network name collisions; (d) memory/CPU contention on a shared VM.

**Why it happens:** Developers treat the VM as a blank slate and write a docker-compose.yml that works in isolation but fails when deployed alongside existing services.

**Consequences:** Taiga goes down (breaking the team's project management tool). Or v2 containers fail to start. Or intermittent PostgreSQL connection errors.

**Prevention:**
- Audit the VM before writing docker-compose.yml: `docker ps`, `docker network ls`, `netstat -tlnp`, `pg_stat_activity` connection count, available RAM/CPU
- Use the EXISTING Nginx reverse proxy to route `triage.vidarbhainfotech.com` to the v2 container -- do not deploy a second Nginx
- Share the existing PostgreSQL instance but use a SEPARATE DATABASE with explicit connection pool limits (e.g., 10 connections for v2)
- Use distinct Docker Compose project names and network names
- Set memory limits on v2 container (`mem_limit` in docker-compose.yml)

**Detection:** `docker ps` shows port conflicts. Taiga becomes unreachable after v2 deployment. PostgreSQL logs show "too many connections."

---

### Pitfall 5: APScheduler Runs Multiple Times with Gunicorn Workers

**What goes wrong:** Gunicorn forks multiple worker processes. If APScheduler starts inside the Django WSGI application (e.g., in `AppConfig.ready()` or `wsgi.py`), each worker gets its own scheduler instance. With 2 workers, every job runs twice: double email polling, double SLA checks, double EOD reports, double Chat notifications.

**Why it happens:** This is a classic Django + Gunicorn + background task gotcha. It works fine in development with `runserver` (single process) but breaks in production with Gunicorn (multiple workers).

**Consequences:** Duplicate email processing, duplicate notifications, duplicate AI costs. Potentially corrupt data if two pollers process the same email simultaneously.

**Prevention:**
- Run APScheduler in a SEPARATE process via a Django management command (`python manage.py runscheduler`)
- The scheduler process and Gunicorn workers both run inside the same Docker container (via `supervisord` or a shell script)
- The management command uses `BlockingScheduler`, not `BackgroundScheduler` (it's its own dedicated process)
- django-apscheduler stores job state in the database, which helps with single-instance enforcement
- Alternative: Gunicorn `--preload` flag with `--workers 1` (but then you lose worker redundancy)

**Detection:** Chat notifications fire twice for the same email. Poll logs show two concurrent poll cycles. AI costs double unexpectedly.

## Moderate Pitfalls

### Pitfall 6: AI Assignment Feedback Loop Creates Confirmation Bias

**What goes wrong:** The plan is to log manual reassignments as corrections to improve future AI assignments. But if the AI's initial assignment is visible to the person doing reassignment, they anchor on it. The model converges on a local optimum that reflects human laziness rather than actual expertise matching.

**Why it happens:** Human-in-the-loop systems suffer from automation bias. When the AI says "assign to Rahul," the manager is more likely to leave it with Rahul even if Priya would be better.

**Prevention:**
- Log BOTH the AI suggestion AND the final assignment, with a boolean `was_overridden` flag
- Track override rates per category
- Start with simple rule-based assignment (category -> person mapping) before adding AI
- Periodically audit a random sample of assignments

**Detection:** Override rate drops to near-zero suspiciously fast. One team member gets disproportionate assignments.

---

### Pitfall 7: Google Sheets Read-Only Mirror Becomes a Maintenance Burden

**What goes wrong:** Syncing PostgreSQL to Sheets sounds simple but becomes complex: Sheets API rate limits (100 req/100s), batch update formatting, handling Sheet structure changes if someone manually edits the Sheet, retry logic for transient Sheets API failures. The sync becomes a second critical path.

**Why it happens:** "Read-only mirror" sounds low-risk. But the Sheets API is unreliable enough that the sync job generates constant noise.

**Prevention:**
- Sync on a schedule (every 5-10 min batch), not per-event
- Label the Sheet explicitly: "MIRROR - Updated every 5 min - DO NOT EDIT"
- Protect the Sheet (lock all cells)
- Use a dead-simple schema: date, from, subject, assignee, status, priority
- Build the mirror as the LAST feature
- If sync fails, log a warning but do NOT block the main pipeline

**Detection:** Sheets API rate limit errors. Sheet data stale by > 30 minutes.

---

### Pitfall 8: Django Static Files Not Serving in Production

**What goes wrong:** Django's development server serves static files automatically. In production with Gunicorn, static files return 404. Developers forget to run `collectstatic`, configure Nginx to serve the static directory, or set `STATIC_ROOT` correctly. With HTMX and Tailwind as static files, this means the entire UI breaks.

**Why it happens:** Django's dev server hides the static files problem. It "just works" until you deploy with Gunicorn.

**Prevention:**
- Add `python manage.py collectstatic --noinput` to the Docker build or entrypoint
- Configure Nginx to serve `/static/` from the collected files directory
- Use WhiteNoise as a fallback (serves static files from Gunicorn, slower but works without Nginx config)
- Test the Docker image locally before deploying to the VM
- Set `STATIC_ROOT = '/app/staticfiles'` in settings.py

**Detection:** Dashboard loads with no CSS/JS. Browser console shows 404 for htmx.min.js and output.css.

---

### Pitfall 9: SLA Calculation Breaks During Timezone Mishandling

**What goes wrong:** India doesn't observe DST, so IST-only seems safe -- until timestamps are stored ambiguously. Gmail API returns UTC, PostgreSQL stores TIMESTAMPTZ, Python datetime objects may be naive or aware. Mixing these silently produces wrong SLA calculations.

**Why it happens:** "India doesn't have DST" creates false confidence. The issue is how timestamps are stored and compared across systems.

**Prevention:**
- Store ALL timestamps as UTC in PostgreSQL (`TIMESTAMPTZ` columns, always)
- Set `USE_TZ = True` in Django settings (default in Django 5.2)
- Use `timezone.now()` everywhere in Python, never `datetime.now()`
- Convert to IST only in templates (Django's `{% load tz %}` and `{% localtime on %}`)
- Set the VM and Docker containers to UTC timezone
- Test SLA calculations with emails received at IST midnight and near business-hours boundaries

**Detection:** SLA deadlines don't match manual calculation. Business-hours-only SLA produces wrong results.

---

### Pitfall 10: Service Account Key Management on Self-Hosted VM

**What goes wrong:** v1 uses Google Secret Manager. On a self-hosted VM, there's no managed secret service. The key file gets committed to the repo, stored with open permissions, never rotated, or shared with Taiga's service account.

**Why it happens:** Cloud Run's secret management was transparent. Self-hosting means manually implementing what was previously handled by infrastructure.

**Prevention:**
- Store the SA key file with `chmod 600`, owned by the container's user
- Mount as a bind-mount volume, NOT bake into the Docker image
- Use a SEPARATE service account for v2 (not the same one as v1 or Taiga)
- Add the SA key path to `.gitignore` AND `.dockerignore`
- Set up key rotation reminders (Google recommends 90-day rotation)

**Detection:** `git log` shows a commit containing `service-account.json`. The key file has `644` permissions.

---

### Pitfall 11: Gmail Thread Monitoring Misses Responses Due to History API Gaps

**What goes wrong:** Gmail's push notification system (Pub/Sub) is documented as best-effort. History IDs can be returned with no actual history listings. The `watch()` call must be renewed every 7 days. If the assignee responds from a different account, thread monitoring never sees it.

**Why it happens:** Developers build against the happy path then discover hours-long notification gaps in production.

**Consequences:** Assignee responds but system shows "awaiting response." False SLA breach alerts fire.

**Prevention:**
- Hybrid approach: Pub/Sub for near-real-time + periodic polling (every 15 min) as fallback
- Auto-renew `watch()` daily
- Poll the shared inbox thread (not the assignee's personal mailbox)
- Provide a manual "mark as responded" button in the dashboard as an escape hatch
- Accept that response detection will never be 100% automatic

**Detection:** Dashboard shows "awaiting response" for emails the team knows were answered.

## Minor Pitfalls

### Pitfall 12: HTMX Partial Swaps Break When Template Context Is Incomplete

**What goes wrong:** An HTMX partial template expects certain context variables that the view forgot to include. The full-page view works because the base template provides defaults, but the partial render crashes with a TemplateSyntaxError or renders broken HTML.

**Why it happens:** When views serve both full pages and partials via `request.htmx`, developers test the full page but not the partial path.

**Prevention:**
- Test both request paths in every view test: with and without `HTTP_HX_REQUEST: "true"` header
- Keep partial templates self-contained (don't rely on parent template context)
- Use `{% include %}` in full-page templates to render the same partial, ensuring they always match

**Detection:** HTMX request returns a 500 or an empty div. Dashboard element disappears after an interaction.

---

### Pitfall 13: PyMuPDF AGPL License Risk

**What goes wrong:** v1 uses PyMuPDF for PDF text extraction. Recent versions are AGPL-3.0, which has copyleft implications for proprietary/commercial code.

**Prevention:** Switch to `pypdf` (BSD license) or `pdfminer.six` (MIT license) in v2. Both handle text extraction adequately for the use case (first 3 pages, max 1000 chars).

---

### Pitfall 14: Django Admin Exposes Sensitive Data Without Access Control

**What goes wrong:** Django admin is accessible at `/admin/` by default. If any user with `is_staff=True` can access it, they can see and modify SLA configs, assignment rules, runtime config, and all email records. For this project, only the manager (Shreyas) should have admin access.

**Prevention:**
- Set `is_staff=True` only for the manager, not regular team members
- Change the admin URL from `/admin/` to something less guessable (e.g., `/manage/`)
- Use `@admin.register` with `ModelAdmin` classes to restrict what's editable
- Regular dashboard users should NEVER need Django admin -- their interface is the dashboard views

**Detection:** A non-manager user accesses `/admin/` and can modify SLA rules.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Database schema & migration | Type coercion data loss (Pitfall 1) | Export production Sheet, validate every column type, parallel-run comparison |
| Auth (Google OAuth) | Domain restriction bypass (Pitfall 2) | Server-side enforcement via allauth adapter, test with non-VIPL accounts |
| Infrastructure (Docker Compose) | Port/resource conflicts with Taiga (Pitfall 4), SA key management (Pitfall 10) | Audit VM before writing compose file, share existing Nginx and PostgreSQL |
| Background tasks | APScheduler duplicate jobs with Gunicorn workers (Pitfall 5) | Separate management command process, NOT inside WSGI app |
| Dashboard UI | Static files not serving (Pitfall 8), partial template errors (Pitfall 12) | collectstatic in Dockerfile, Nginx static config, test both render paths |
| Gmail thread monitoring | History API gaps (Pitfall 11), dual-system dedup (Pitfall 3) | Hybrid push+poll, manual status button, never run two pollers simultaneously |
| Assignment engine | AI feedback bias (Pitfall 6) | Rules-based first, log overrides separately, audit assignment distribution |
| Sheets mirror | Sync becomes critical path (Pitfall 7) | Batch sync, build last, lock Sheet from edits, simplified schema |
| SLA calculations | Timezone bugs (Pitfall 9) | UTC everywhere, USE_TZ=True, convert at display time |
| Admin access | Data exposure (Pitfall 14) | Restrict is_staff, custom admin URL |
| PDF handling | AGPL license (Pitfall 13) | Swap to pypdf or pdfminer.six |

## Sources

- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) -- HIGH confidence
- [django-allauth domain restriction](https://docs.allauth.org/en/dev/socialaccount/providers/google.html) -- HIGH confidence
- [APScheduler + Django/Gunicorn worker issue](https://github.com/jcass77/django-apscheduler#quick-start) -- HIGH confidence
- [Django static files deployment](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/) -- HIGH confidence
- [Gmail Push Notifications](https://developers.google.com/workspace/gmail/api/guides/push) -- HIGH confidence (official docs)
- [Gmail Push Notifications Bug at Hiver](https://medium.com/hiver-engineering/gmail-apis-push-notifications-bug-and-how-we-worked-around-it-at-hiver-a0a114df47b4) -- MEDIUM confidence
- v1 codebase analysis: `CLAUDE.md`, `.planning/codebase/CONCERNS.md` -- HIGH confidence (direct inspection)

---

*Pitfalls audit: 2026-03-09 (revised for Django+HTMX stack)*
