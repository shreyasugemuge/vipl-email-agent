# Phase 5: Reporting + Admin + Sheets Mirror - Research

**Researched:** 2026-03-12
**Domain:** EOD reporting, admin config UI, Google Sheets API sync
**Confidence:** HIGH

## Summary

Phase 5 has three distinct deliverables: (1) a daily EOD report ported from v1 but pulling stats from PostgreSQL instead of Google Sheets, (2) two new admin settings tabs (Inboxes management + SystemConfig editor), and (3) a read-only Sheets sync mirror that appends/updates email rows to a "v2 Mirror" tab. All three features build on well-established patterns already in the codebase -- the existing ChatNotifier for Chat cards, the existing settings page HTMX tabs pattern, and the v1 SheetLogger for Sheets API patterns.

The primary technical risk is the Sheets sync: it must be fire-and-forget (never block the pipeline), handle row lookups by message_id efficiently, and deal with Sheets API rate limits (100 requests/100 seconds per user). The EOD reporter is straightforward -- aggregate Django ORM queries, render a Django template, send via Gmail API. The settings tabs are the simplest piece -- extending the existing tab pattern with 2 more tabs.

**Primary recommendation:** Port v1's EOD reporter to Django ORM queries + Django template (not Jinja2), add `notify_eod_summary` to the v2 ChatNotifier, extend settings.html with Inboxes and Config tabs using existing HTMX patterns, and create a lightweight `SheetsSyncService` using `google-api-python-client` (already a dependency) with batch operations and row-index caching.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- EOD stats include v1 parity PLUS SLA metrics: total emails today, by priority/category breakdown, open/unresolved count, response time averages, SLA breach count, worst overdue emails, avg time-to-acknowledge, avg time-to-respond
- Delivery: HTML email to configured recipients + Chat card to webhook (same as v1)
- Timing: 7 PM IST daily, with startup catch-up during business hours (deduplicated within 10 min, same as v1)
- Recipients: comma-separated email list in SystemConfig key `eod_recipients`, editable from Settings page
- Feature flags: respects `eod_email_enabled` (email) and `chat_notifications_enabled` (Chat)
- Inbox Management lives as a 4th tab ("Inboxes") on the existing Settings page at `/emails/settings/`
- Changes take effect on next poll cycle (no validation against Gmail API)
- Reads/writes the `monitored_inboxes` SystemConfig key (comma-separated string)
- Sheets sync columns: Date, From, Subject, Inbox, Category, Priority, Assignee, Status, SLA Deadline
- Sync strategy: append new emails as rows + update existing rows on status/assignee change (match by message_id)
- Sync frequency: after each pipeline poll cycle (every 5 min)
- Target: same Google Sheet as v1 (GOOGLE_SHEET_ID env var), add a new "v2 Mirror" tab
- Error handling: fire-and-forget (log warning on Sheets API failure, never block pipeline)
- Full SystemConfig editor as a 5th tab on Settings page
- Shows ALL SystemConfig keys grouped by category
- Inline edit with save button per group
- Edit existing keys only -- no adding/deleting from UI

### Claude's Discretion
- EOD email HTML template design (can reference v1's `templates/eod_email.html`)
- EOD Chat card layout (Cards v2 format, can reference existing breach summary card)
- Sheets sync implementation details (batch vs row-by-row, caching strategy)
- Config editor visual design within the existing settings page style
- Whether to add a "last synced" indicator for Sheets status
- Scheduler job organization (new jobs for EOD + Sheets sync)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFR-04 | Google Sheets receives read-only sync (date, from, subject, assignee, status) | SheetsSyncService using google-api-python-client, "v2 Mirror" tab, append+update by message_id, fire-and-forget after poll cycle |
| INFR-05 | Daily EOD report sent via email + Chat card with stats from database | EODReporter service with Django ORM aggregation, Gmail API for email send, ChatNotifier.notify_eod_summary for Chat card |
| INFR-07 | Admin can configure monitored inboxes without code changes | Inboxes tab on Settings page, reads/writes `monitored_inboxes` SystemConfig key, HTMX add/remove pattern |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django 4.2 LTS | 4.2.x | ORM queries for EOD stats, template rendering | Already in use |
| google-api-python-client | >=2.150 | Sheets API v4 for mirror sync + Gmail API for email send | Already a dependency |
| google-auth | >=2.35 | Service account credentials | Already a dependency |
| httpx | >=0.27 | Chat webhook POST (via ChatNotifier) | Already a dependency |
| APScheduler | >=3.10,<4.0 | EOD cron job + Sheets sync scheduling | Already a dependency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | >=9.0 | Retry on Sheets API transient errors | Already a dependency, use for Sheets writes |
| pytz | >=2024.1 | IST timezone for EOD timing | Already a dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| google-api-python-client | gspread | gspread is simpler API but adds a new dependency; project already uses google-api-python-client |
| Django templates | Jinja2 (like v1) | v1 uses Jinja2 but v2 is all Django templates; stay consistent |

**Installation:**
No new dependencies required. All libraries already in `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
apps/emails/services/
    eod_reporter.py          # NEW: EOD stats aggregation + email send + Chat card
    sheets_sync.py           # NEW: Sheets mirror sync service

templates/
    emails/
        eod_email.html       # NEW: Django template for EOD HTML email
        _inboxes_tab.html    # NEW: Inboxes management partial
        _config_editor.html  # NEW: SystemConfig editor partial
```

### Pattern 1: EOD Reporter as Service Module
**What:** A service class that aggregates stats from Django ORM, renders HTML email via Django template, sends via Gmail API, and posts Chat card via ChatNotifier.
**When to use:** Called by scheduler at 7 PM IST + startup catch-up.
**Example:**
```python
# apps/emails/services/eod_reporter.py
class EODReporter:
    def __init__(self, chat_notifier, service_account_key_path, sender_email):
        self.chat = chat_notifier
        self.sa_key_path = service_account_key_path
        self.sender_email = sender_email

    def generate_stats(self) -> dict:
        """Aggregate from Django ORM -- all stats from PostgreSQL."""
        from apps.emails.models import Email
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        completed = Email.objects.filter(processing_status="completed")
        today = completed.filter(received_at__gte=today_start)

        # v1 parity stats
        stats = {
            "date": now.strftime("%d %b %Y"),
            "received_today": today.count(),
            "closed_today": today.filter(status="closed").count(),
            "total_open": completed.exclude(status__in=["closed"]).filter(is_spam=False).count(),
            "unassigned": completed.filter(assigned_to__isnull=True, is_spam=False).exclude(status="closed").count(),
        }

        # SLA metrics (new in v2)
        breached = completed.filter(
            sla_respond_deadline__lt=now,
            status__in=["new", "acknowledged"],
        )
        stats["sla_breaches"] = breached.count()

        # Priority/category breakdowns, response time averages, etc.
        return stats

    def send_report(self):
        """Generate + send email + Chat card. Respects feature flags."""
        eod_enabled = SystemConfig.get("eod_email_enabled", True)
        chat_enabled = SystemConfig.get("chat_notifications_enabled", False)
        # ... (see v1 pattern)
```

### Pattern 2: Sheets Sync as Fire-and-Forget Service
**What:** A service that syncs completed emails to a "v2 Mirror" tab in Google Sheets. Appends new rows, updates existing rows on status/assignee change.
**When to use:** Called after each poll cycle completes, or as a separate scheduler job.
**Example:**
```python
# apps/emails/services/sheets_sync.py
class SheetsSyncService:
    TAB_NAME = "v2 Mirror"
    COLUMNS = ["Date", "From", "Subject", "Inbox", "Category",
               "Priority", "Assignee", "Status", "SLA Deadline"]

    def __init__(self, service_account_key_path, spreadsheet_id):
        # Build Sheets API service
        credentials = service_account.Credentials.from_service_account_file(
            service_account_key_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        service = build("sheets", "v4", credentials=credentials)
        self.sheets = service.spreadsheets()
        self.spreadsheet_id = spreadsheet_id
        self._row_index = {}  # message_id -> row_number cache

    def sync_emails(self, emails):
        """Sync a list of Email model instances to the Sheet."""
        # Batch: separate new (append) from existing (update)
        # Use _row_index cache to avoid re-scanning the sheet each cycle
```

### Pattern 3: Settings Tab Extension (HTMX)
**What:** Add 2 more tabs to the existing settings page following the exact same pattern as Rules/Visibility/SLA tabs.
**When to use:** For Inboxes tab and Config editor tab.
**Example:**
```python
# In views.py -- same pattern as settings_sla_save
@login_required
@require_POST
def settings_inboxes_save(request):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")
    action = request.POST.get("action", "")
    if action == "add":
        email = request.POST.get("inbox_email", "").strip()
        current = SystemConfig.get("monitored_inboxes", "")
        inboxes = [i.strip() for i in current.split(",") if i.strip()]
        if email and email not in inboxes:
            inboxes.append(email)
            SystemConfig.objects.filter(key="monitored_inboxes").update(
                value=",".join(inboxes)
            )
    elif action == "remove":
        # similar
        pass
    # Return updated partial
    return render(request, "emails/_inboxes_tab.html", {...})
```

### Anti-Patterns to Avoid
- **Blocking pipeline on Sheets failure:** Sheets sync MUST be wrapped in try/except. Pipeline continues regardless. This is a locked decision.
- **Scanning entire Sheet for row lookup:** Cache row indices in memory. Refresh cache only when a row is not found (new email added externally).
- **Using Jinja2 for EOD template:** v2 uses Django templates everywhere. Use Django template engine, not Jinja2.
- **Adding/deleting SystemConfig keys from UI:** Locked decision -- edit existing keys only. Adding/deleting is Django admin territory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email sending | Custom SMTP client | Gmail API via service account (same as v1) | Domain-wide delegation already configured, avoids SMTP credential management |
| Sheets API retries | Manual retry loops | `tenacity` decorator (same as v1 `sheet_logger.py`) | Already proven in v1, handles HttpError 429/500/503 |
| Chat card formatting | Raw JSON construction from scratch | Extend existing `ChatNotifier` class with `notify_eod_summary` | Reuse `_post()`, quiet hours, consistent format |
| Config grouping | Manual category logic | `SystemConfig.get_all_by_category()` | Already exists and handles type casting |
| EOD dedup | Custom timestamp tracking | `StateManager.can_send_eod()` / `record_eod_sent()` | Already ported from v1, 10-min dedup window |

**Key insight:** Every component in Phase 5 has a v1 counterpart or an existing v2 pattern to extend. Zero new libraries needed.

## Common Pitfalls

### Pitfall 1: Sheets API Rate Limits
**What goes wrong:** Exceeding 100 requests per 100 seconds per user causes 429 errors.
**Why it happens:** Row-by-row updates on 50+ emails in a single poll cycle.
**How to avoid:** Use `batchUpdate` for multiple row updates. Append new rows in a single `values().append()` call with multiple rows. Cache row indices to avoid repeated `values().get()` calls.
**Warning signs:** 429 errors in logs, increasing retry counts.

### Pitfall 2: Sheets Tab Not Existing on First Run
**What goes wrong:** `values().append()` fails if the "v2 Mirror" tab doesn't exist.
**Why it happens:** First-time setup or Sheet was recreated.
**How to avoid:** Check if tab exists at init time, create it with header row if missing. Use `spreadsheets().get()` to list sheets, then `batchUpdate` with `addSheet` request if needed.
**Warning signs:** `HttpError 400: Unable to parse range` on first sync.

### Pitfall 3: Gmail API Sender Email Mismatch
**What goes wrong:** Gmail API `users().messages().send()` fails with 403.
**Why it happens:** Service account must impersonate a real user email (domain-wide delegation `subject` parameter). Using the SA email itself doesn't work.
**How to avoid:** Use `sender_email` from SystemConfig or env var (same as v1: admin email with `gmail.send` scope).
**Warning signs:** `Error 403: Delegation denied` in EOD send logs.

### Pitfall 4: Concurrent Settings Tab Saves
**What goes wrong:** Two admins editing the same inbox list simultaneously -- one overwrites the other.
**Why it happens:** Read-modify-write on a comma-separated string is not atomic.
**How to avoid:** For inboxes, use `F()` expressions or `update_or_create` patterns. In practice: this is a 3-person team, concurrency is rare. Log changes to ActivityLog for audit.
**Warning signs:** Inbox disappearing from monitored list after concurrent edits.

### Pitfall 5: EOD Startup Catch-Up Sending Multiple Reports
**What goes wrong:** On scheduler restart during business hours, EOD fires immediately and again at 7 PM.
**Why it happens:** v1 has startup catch-up logic that checks if EOD was "missed" today.
**How to avoid:** Use `StateManager.can_send_eod()` for 10-min dedup. Also consider storing last EOD send timestamp in SystemConfig (persists across restarts, unlike in-memory StateManager).
**Warning signs:** Duplicate EOD emails received.

### Pitfall 6: Sheets Sync Row Index Drift
**What goes wrong:** Cached row indices become stale if someone manually edits the Sheet (inserts/deletes rows).
**Why it happens:** Row-based addressing shifts when rows are inserted above.
**How to avoid:** Use message_id as a lookup column. On cache miss, re-scan the message_id column to rebuild the index. Accept that manual Sheet edits may cause a one-cycle delay.
**Warning signs:** Status updates appearing on wrong rows.

## Code Examples

### EOD Stats Aggregation (Django ORM)
```python
# Source: Django ORM patterns applied to existing Email model
from django.db.models import Avg, Count, F, Q
from django.utils import timezone

now = timezone.now()
today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
completed = Email.objects.filter(
    processing_status=Email.ProcessingStatus.COMPLETED, is_spam=False
)
today = completed.filter(received_at__gte=today_start)

# Priority breakdown
priority_counts = dict(
    today.values_list("priority").annotate(count=Count("id")).values_list("priority", "count")
)

# Average time-to-acknowledge (for emails acknowledged today)
avg_ack = completed.filter(
    status__in=["acknowledged", "replied", "closed"],
    assigned_at__isnull=False,
).annotate(
    ack_time=F("assigned_at") - F("received_at")
).aggregate(avg=Avg("ack_time"))

# SLA breached emails (respond deadline passed, not closed)
breached = completed.filter(
    sla_respond_deadline__lt=now,
    status__in=["new", "acknowledged"],
)
```

### Sheets API: Create Tab If Missing
```python
# Source: google-api-python-client Sheets API v4 patterns from v1 sheet_logger.py
def _ensure_tab_exists(self):
    """Create 'v2 Mirror' tab if it doesn't exist."""
    try:
        sheet_meta = self.sheets.get(spreadsheetId=self.spreadsheet_id).execute()
        tab_names = [s["properties"]["title"] for s in sheet_meta.get("sheets", [])]
        if self.TAB_NAME not in tab_names:
            self.sheets.batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": self.TAB_NAME}}}]},
            ).execute()
            # Write header row
            self.sheets.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.TAB_NAME}'!A1",
                valueInputOption="RAW",
                body={"values": [self.COLUMNS]},
            ).execute()
    except Exception as e:
        logger.warning(f"Failed to ensure tab exists: {e}")
```

### Sheets API: Batch Append + Update
```python
# Source: google-api-python-client patterns, adapted from v1 sheet_logger.py
def _append_rows(self, rows: list[list]):
    """Append multiple rows in a single API call."""
    if not rows:
        return
    self.sheets.values().append(
        spreadsheetId=self.spreadsheet_id,
        range=f"'{self.TAB_NAME}'!A:I",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()

def _batch_update_rows(self, updates: dict[int, list]):
    """Update multiple rows by row number in a single batchUpdate."""
    if not updates:
        return
    data = []
    for row_num, values in updates.items():
        data.append({
            "range": f"'{self.TAB_NAME}'!A{row_num}:I{row_num}",
            "values": [values],
        })
    self.sheets.values().batchUpdate(
        spreadsheetId=self.spreadsheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()
```

### Gmail API: Send HTML Email
```python
# Source: v1 agent/eod_reporter.py _send_email method
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2 import service_account
from googleapiclient.discovery import build

def _send_eod_email(self, subject, html_body, recipients):
    credentials = service_account.Credentials.from_service_account_file(
        self.sa_key_path,
        scopes=["https://www.googleapis.com/auth/gmail.send"],
        subject=self.sender_email,  # Impersonate admin for sending
    )
    service = build("gmail", "v1", credentials=credentials)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = self.sender_email
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
```

### Settings Tab: Inboxes Management (HTMX)
```html
<!-- templates/emails/_inboxes_tab.html -->
<div class="space-y-4">
    <div class="flex gap-2">
        <input type="email" name="inbox_email" placeholder="email@example.com"
               class="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm">
        <button hx-post="{% url 'emails:settings_inboxes_save' %}"
                hx-target="#inboxes-list" hx-swap="innerHTML"
                hx-include="[name='inbox_email']"
                hx-vals='{"action": "add"}'
                class="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium">
            Add
        </button>
    </div>
    <div id="inboxes-list">
        {% for inbox in monitored_inboxes %}
        <div class="flex items-center justify-between py-2 px-3 bg-white rounded-lg border">
            <span class="text-sm">{{ inbox }}</span>
            <button hx-post="{% url 'emails:settings_inboxes_save' %}"
                    hx-target="#inboxes-list" hx-swap="innerHTML"
                    hx-vals='{"action": "remove", "inbox_email": "{{ inbox }}"}'
                    class="text-red-500 text-xs">Remove</button>
        </div>
        {% endfor %}
    </div>
</div>
```

## State of the Art

| Old Approach (v1) | Current Approach (v2) | When Changed | Impact |
|--------------------|-----------------------|--------------|--------|
| Jinja2 template for EOD email | Django template engine | v2 migration | Consistent with all other v2 templates |
| Stats from Google Sheets | Stats from Django ORM | v2 migration | Faster, more reliable, richer aggregation |
| Sheet is source of truth | Sheet is read-only mirror | v2 architecture | PostgreSQL is authoritative, Sheet is convenience |
| Config from Agent Config tab | Config from SystemConfig model | v2 Phase 2 | DB-backed, typed, editable from dashboard |
| gspread-style patterns | google-api-python-client | v1 already uses this | No change needed, same library |

**Deprecated/outdated:**
- v1's `SheetLogger` class: replaced by `SheetsSyncService` (write-only mirror, not source of truth)
- v1's Jinja2 `eod_email.html`: reference for design, but v2 uses Django template syntax
- v1's `config.yaml` feature flags: replaced by SystemConfig model

## Open Questions

1. **Persist EOD send timestamp across restarts?**
   - What we know: `StateManager` is in-memory -- restarting the scheduler loses the EOD dedup timestamp
   - What's unclear: Whether to add a `last_eod_sent` SystemConfig key for persistence
   - Recommendation: Add a `last_eod_sent` SystemConfig key. Write it after each EOD send. Check it + `StateManager` for dedup. Cost is one DB read, benefit is no duplicate EODs after restart.

2. **Sheets sync: separate scheduler job vs pipeline hook?**
   - What we know: CONTEXT.md says "after each pipeline poll cycle"
   - What's unclear: Whether to call sync directly from `process_poll_cycle()` or as a separate job
   - Recommendation: Call from a separate 5-minute interval job (not from inside `process_poll_cycle`). Reason: sync should also catch status/assignee changes made from the dashboard between poll cycles. A separate job can query `updated_at > last_sync_time` to find all changes.

3. **"Last synced" indicator for Sheets status**
   - What we know: CONTEXT.md lists this as Claude's discretion
   - What's unclear: Whether it's worth the UI space
   - Recommendation: Yes, add it. Write `sheets_last_synced` to SystemConfig after each successful sync. Display as a small badge on the Settings page or health endpoint. Minimal effort, useful for debugging.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails -v -x` |
| Full suite command | `pytest -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFR-04 | Sheets sync appends new emails and updates existing rows | unit | `pytest apps/emails/tests/test_sheets_sync.py -x` | Wave 0 |
| INFR-04 | Sheets sync is fire-and-forget (never crashes pipeline) | unit | `pytest apps/emails/tests/test_sheets_sync.py::test_sync_failure_does_not_crash -x` | Wave 0 |
| INFR-04 | Tab creation on first sync | unit | `pytest apps/emails/tests/test_sheets_sync.py::test_ensure_tab_exists -x` | Wave 0 |
| INFR-05 | EOD stats aggregation returns correct counts from DB | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_generate_stats -x` | Wave 0 |
| INFR-05 | EOD email renders via Django template | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_render_email -x` | Wave 0 |
| INFR-05 | EOD Chat card posts via ChatNotifier | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_chat_notification -x` | Wave 0 |
| INFR-05 | EOD respects feature flags (eod_email_enabled, chat_notifications_enabled) | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_feature_flags -x` | Wave 0 |
| INFR-05 | EOD dedup prevents double-send within 10 min | unit | `pytest apps/emails/tests/test_eod_reporter.py::test_dedup -x` | Wave 0 |
| INFR-07 | Inboxes tab add/remove updates SystemConfig | unit | `pytest apps/emails/tests/test_settings_views.py::test_inboxes_add -x` | Wave 0 |
| INFR-07 | Config editor shows grouped keys and saves edits | unit | `pytest apps/emails/tests/test_settings_views.py::test_config_editor -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails -v -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_eod_reporter.py` -- covers INFR-05 (EOD stats, email send, Chat card, feature flags, dedup)
- [ ] `apps/emails/tests/test_sheets_sync.py` -- covers INFR-04 (tab creation, append, update, fire-and-forget, row index cache)
- [ ] Extend `apps/emails/tests/test_settings_views.py` -- covers INFR-07 (add inbox, remove inbox, config editor save)

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `apps/emails/views.py`, `apps/emails/services/chat_notifier.py`, `apps/core/models.py`, `apps/emails/services/pipeline.py`, `apps/emails/services/state.py`
- v1 reference: `agent/eod_reporter.py`, `agent/sheet_logger.py`, `agent/chat_notifier.py`, `templates/eod_email.html`
- CONTEXT.md: locked decisions, discretion areas

### Secondary (MEDIUM confidence)
- Google Sheets API v4 rate limits: 100 requests/100 seconds per user (Google Cloud documentation)
- Gmail API send via service account: domain-wide delegation pattern (proven in v1)

### Tertiary (LOW confidence)
- None -- all patterns are proven in v1 or already implemented in v2

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all libraries already in use
- Architecture: HIGH -- extends existing patterns (settings tabs, ChatNotifier, service layer)
- Pitfalls: HIGH -- v1 encountered and solved most of these (rate limits, sender email, Sheet tab creation)

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (stable domain, no fast-moving dependencies)
