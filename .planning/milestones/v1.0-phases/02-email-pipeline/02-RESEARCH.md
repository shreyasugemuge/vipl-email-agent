# Phase 2: Email Pipeline - Research

**Researched:** 2026-03-11
**Domain:** Gmail polling, AI triage, spam filtering, dead letter retry, Django ORM integration
**Confidence:** HIGH

## Summary

Phase 2 ports the proven v1 email processing pipeline (Gmail polling, Claude AI triage, spam filtering, dead letter retry, Chat notifications) from a standalone Python app using Google Sheets to Django services using PostgreSQL via the ORM. The v1 code is well-structured with clean class boundaries, dataclass DTOs, and dependency injection -- making the port straightforward. The core logic (GmailPoller, AIProcessor, ChatNotifier, StateManager) can be adapted with minimal changes: swap Sheet persistence for `Email.objects.create()`, keep Gmail API and Anthropic SDK calls identical.

The Email model already exists with all core fields. Key gaps are: missing fields for dead letter tracking (retry_count, last_error), missing AI metadata fields (language, tags, reasoning, spam_score), and a missing SystemConfig model for feature flags and runtime config. The scheduler runs as a separate Docker Compose service using the same image with a different command (`python manage.py run_scheduler`).

**Primary recommendation:** Port v1 service classes into `apps/emails/services/`, keeping v1's DTO pattern (EmailMessage/TriageResult dataclasses) as the interface between services. Add missing fields to the Email model via migration. Create SystemConfig model in `apps/core/` for feature flags. Run scheduler as a second container in Docker Compose.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Adapt v1 classes into Django service modules -- keep class structure, swap Sheets calls for Django ORM
- Services live in `apps/emails/services/` (gmail_poller.py, ai_processor.py, chat_notifier.py, etc.)
- Keep v1 dataclasses (EmailMessage, TriageResult) as DTOs -- GmailPoller returns EmailMessage, a save step maps it to the Email model
- Adapt v1 triage prompt for v2 -- strip Sheet/ticket references, keep triage logic, categories, priorities, and output format intact. Store in `prompts/` directory
- Single management command (`python manage.py run_scheduler`) running APScheduler with all jobs
- Runs as a second service in Docker Compose -- same image, different command. Two containers: web (Gunicorn) + scheduler
- In-memory StateManager for ephemeral state (cooldowns, failure tracking, EOD dedup) -- resets on restart (acceptable)
- Scheduler writes a heartbeat timestamp to DB every minute; health endpoint checks it
- SystemConfig model in `apps/core/` with key-value pairs (key, value, type, description)
- Scheduler reloads config every poll cycle -- same hot-reload pattern as v1 Sheets
- Port v1's 3 feature flags (AI Triage, Chat Notifications, EOD Email) AND expand with v2 flags as needed
- Django admin for config editing now; dashboard settings page added later (Phase 5)
- Retry pattern should match v1: max 3 attempts, scheduler job triggers retries
- Fallback triage result pattern preserved from v1
- v1's label-after-persist safety pattern MUST be preserved
- v1's circuit breaker pattern should carry over
- v1's two-tier AI (Haiku default, Sonnet for CRITICAL) and spam pre-filter (13 regex patterns) are proven -- port as-is
- Config should be expandable -- new phases will add their own flags without schema changes

### Claude's Discretion
- Dead letter model design (separate model vs fields on Email)
- Exact SystemConfig model schema (beyond key/value/type/description)
- How config validation works (range checks, type coercion)
- Scheduler job intervals and timing
- Error handling patterns for ORM operations
- Test structure and fixture design

### Deferred Ideas (OUT OF SCOPE)
- Dashboard settings page for config editing -- Phase 5 (Admin)
- Auto-assignment toggle flag -- will be added to SystemConfig when Phase 4 is built
- SLA config per category/priority -- Phase 4
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROC-01 | System polls configured Gmail inboxes for new emails every 5 minutes | Port GmailPoller class, map EmailMessage DTO to Email model, dedup via message_id unique constraint |
| PROC-02 | System triages emails with Claude AI (category, priority, summary, draft reply) | Port AIProcessor class with two-tier AI, store TriageResult fields in Email model |
| PROC-03 | System pre-filters spam via regex patterns before AI processing (zero cost) | Port 13 spam regex patterns from v1, mark Email with is_spam flag |
| PROC-04 | System extracts PDF attachment text for triage context | Swap PyMuPDF (AGPL) for pypdf (BSD), port _extract_pdf_text to use PdfReader |
| PROC-05 | System detects email language and writes summary in English | Port language detection (English/Hindi/Marathi/Mixed) from AI tool schema, store in Email.language |
| PROC-06 | System logs failed triages to dead letter queue and retries up to 3 times | Add retry_count/last_error fields to Email model OR create FailedTriage model |
| INFR-08 | Admin can configure polling frequency, quiet hours, and business hours | SystemConfig model with key-value pairs, config hot-reload every poll cycle |
| INFR-11 | Admin can toggle feature flags without redeploy | SystemConfig entries for AI Triage, Chat Notifications, EOD Email flags |
</phase_requirements>

## Standard Stack

### Core (already in v2 requirements.txt)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | >=5.2,<5.3 | Web framework + ORM | Already installed, Phase 1 foundation |
| psycopg[binary] | >=3.2 | PostgreSQL adapter | Already installed |

### New Dependencies for Phase 2
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.49 | Claude AI API calls | Same as v1, proven; supports tool use + prompt caching |
| google-api-python-client | >=2.150 | Gmail API access | Same as v1, domain-wide delegation for inbox impersonation |
| google-auth | >=2.35 | Google service account auth | Required by google-api-python-client |
| tenacity | >=9.0 | Retry with exponential backoff | Same as v1, proven for transient API errors |
| APScheduler | >=3.10,<4.0 | Background job scheduling | Same as v1; v3.x is stable, v4.x is not production-ready |
| httpx | >=0.27 | HTTP client for Chat webhook | Same as v1, async-capable, used by ChatNotifier |
| pypdf | >=5.0 | PDF text extraction (BSD license) | Replaces PyMuPDF (AGPL); pure Python, no C deps |
| pytz | >=2024.1 | IST timezone handling | Same as v1; Django uses zoneinfo but v1 code uses pytz |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler | django-apscheduler | Adds DB job store overhead; v1 uses plain APScheduler, simpler to port |
| APScheduler | Celery + Redis | Massive overkill for 4-5 periodic jobs; adds Redis dependency |
| pypdf | pymupdf (fitz) | Better extraction quality but AGPL license; pypdf is BSD and sufficient |
| httpx | requests | httpx is already used in v1 ChatNotifier; lighter, async-ready |
| pytz | zoneinfo (stdlib) | Could use zoneinfo, but v1 code uses pytz throughout; port as-is, refactor later |

**Installation (add to requirements.txt):**
```bash
# New Phase 2 dependencies
anthropic>=0.49
google-api-python-client>=2.150
google-auth>=2.35
tenacity>=9.0
APScheduler>=3.10,<4.0
httpx>=0.27
pypdf>=5.0
pytz>=2024.1
```

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)
```
apps/
  emails/
    services/               # NEW -- ported v1 modules
      __init__.py
      gmail_poller.py       # GmailPoller class (adapted from agent/gmail_poller.py)
      ai_processor.py       # AIProcessor class (adapted from agent/ai_processor.py)
      chat_notifier.py      # ChatNotifier class (adapted from agent/chat_notifier.py)
      spam_filter.py        # Spam regex patterns + is_spam() (extracted from ai_processor.py)
      pdf_extractor.py      # PDF text extraction (extracted, uses pypdf instead of pymupdf)
      pipeline.py           # Orchestrator: poll -> filter -> triage -> save -> label -> notify
      state.py              # StateManager (adapted from agent/state.py, nearly identical)
    management/
      commands/
        run_scheduler.py    # APScheduler management command
    models.py               # Email + AttachmentMetadata (add missing fields)
  core/
    models.py               # SoftDeleteModel + TimestampedModel + SystemConfig (NEW)
    admin.py                # Register SystemConfig in Django admin

prompts/
  triage_prompt.txt         # Adapted v2 prompt (strip Sheet/ticket references)
```

### Pattern 1: Service Layer with DTOs
**What:** Keep v1's dataclass DTOs (EmailMessage, TriageResult) as the contract between services. GmailPoller returns EmailMessage, pipeline.py maps it to Django's Email model.
**When to use:** Always -- decouples Gmail/AI logic from Django ORM.
**Example:**
```python
# apps/emails/services/pipeline.py
from apps.emails.models import Email, AttachmentMetadata
from apps.emails.services.gmail_poller import GmailPoller, EmailMessage
from apps.emails.services.ai_processor import AIProcessor, TriageResult

def save_email_to_db(email_msg: EmailMessage, triage: TriageResult) -> Email:
    """Map DTOs to Django model. Returns saved Email instance."""
    email, created = Email.objects.update_or_create(
        message_id=email_msg.message_id,
        defaults={
            "gmail_id": email_msg.message_id,
            "gmail_thread_id": email_msg.thread_id,
            "from_address": email_msg.sender_email,
            "from_name": email_msg.sender_name,
            "to_inbox": email_msg.inbox,
            "subject": email_msg.subject,
            "body": email_msg.body,
            "received_at": email_msg.timestamp,
            "gmail_link": email_msg.gmail_link,
            # AI triage fields
            "category": triage.category,
            "priority": triage.priority,
            "ai_summary": triage.summary,
            "ai_draft_reply": triage.draft_reply,
            "language": triage.language,
            "is_spam": triage.model_used == "spam-filter",
            "ai_reasoning": triage.reasoning,
            "ai_model_used": triage.model_used,
            "ai_tags": triage.tags,
        },
    )
    # Save attachment metadata
    for att in email_msg.attachment_details:
        AttachmentMetadata.objects.get_or_create(
            email=email,
            gmail_attachment_id=att.get("attachment_id", ""),
            defaults={
                "filename": att["filename"],
                "size_bytes": att.get("size", 0),
                "mime_type": att.get("mime_type", ""),
            },
        )
    return email
```

### Pattern 2: Label-After-Persist Safety
**What:** Gmail "Agent/Processed" label is applied ONLY after successful DB write. If DB write fails, email stays unlabeled and will be retried on next poll.
**When to use:** Always -- critical data safety pattern from v1.
**Example:**
```python
# In pipeline process_single_email():
email_obj = save_email_to_db(email_msg, triage)  # DB write first
gmail_poller.mark_processed(email_msg)             # Label only after success
```

### Pattern 3: Circuit Breaker
**What:** Track consecutive poll failures. After N failures (default 3), skip poll cycles to avoid hammering broken APIs.
**When to use:** In the main poll loop.
**Example:**
```python
# StateManager (nearly identical to v1)
if state.consecutive_failures >= max_failures:
    logger.critical(f"Circuit breaker OPEN -- {state.consecutive_failures} consecutive failures")
    return
```

### Pattern 4: Scheduler Management Command
**What:** Django management command that starts APScheduler with all background jobs.
**When to use:** Runs as a separate container in Docker Compose.
**Example:**
```python
# apps/emails/management/commands/run_scheduler.py
from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

class Command(BaseCommand):
    help = "Run the email processing scheduler"

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone="Asia/Kolkata")
        # Jobs added here: poll, retry, heartbeat
        scheduler.start()
```

### Pattern 5: SystemConfig Hot-Reload
**What:** Read config from SystemConfig model every poll cycle. Same pattern as v1's Sheet config read.
**When to use:** Before every poll cycle.
**Example:**
```python
# apps/core/models.py
class SystemConfig(TimestampedModel):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(default="")
    value_type = models.CharField(max_length=20, choices=[
        ("str", "String"), ("int", "Integer"), ("bool", "Boolean"),
        ("float", "Float"), ("json", "JSON"),
    ], default="str")
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="general")

    @classmethod
    def get(cls, key, default=None):
        try:
            config = cls.objects.get(key=key)
            return config.typed_value
        except cls.DoesNotExist:
            return default

    @property
    def typed_value(self):
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value
```

### Anti-Patterns to Avoid
- **Running scheduler inside Gunicorn workers:** Each worker would start its own scheduler, causing duplicate job execution. Use a separate container.
- **Direct ORM calls in GmailPoller/AIProcessor:** Keep these services Django-agnostic via DTOs. Only pipeline.py touches the ORM.
- **Polling Gmail with no dedup:** Use message_id unique constraint as primary dedup. Gmail label as secondary.
- **Catching all exceptions silently:** Log errors, track in StateManager, surface in health endpoint.

## Email Model Field Gaps

The existing Email model needs additional fields for Phase 2. These require a migration.

| Field | Type | Purpose | Source |
|-------|------|---------|--------|
| `language` | CharField(max_length=20) | Email language detection | TriageResult.language |
| `is_spam` | BooleanField(default=False) | Spam pre-filter flag | Spam filter result |
| `ai_reasoning` | TextField(blank=True) | AI categorization reasoning | TriageResult.reasoning |
| `ai_model_used` | CharField(max_length=100) | Which Claude model processed it | TriageResult.model_used |
| `ai_tags` | JSONField(default=list) | AI-generated tags | TriageResult.tags |
| `ai_suggested_assignee` | CharField(max_length=100) | AI assignment suggestion | TriageResult.suggested_assignee |
| `gmail_link` | URLField(blank=True) | Deep link to Gmail thread | EmailMessage.gmail_link |
| `retry_count` | PositiveSmallIntegerField(default=0) | Dead letter retry tracking | Pipeline error handling |
| `last_error` | TextField(blank=True) | Last processing error | Pipeline error handling |
| `processing_status` | CharField(choices) | new/processing/completed/failed/exhausted | Pipeline state tracking |
| `ai_input_tokens` | PositiveIntegerField(default=0) | Token usage tracking | TriageResult.input_tokens |
| `ai_output_tokens` | PositiveIntegerField(default=0) | Token usage tracking | TriageResult.output_tokens |
| `body_html` | TextField(blank=True) | HTML body (for future rendering) | Gmail payload |

**Recommendation on dead letter (Claude's discretion):** Use fields on the Email model (retry_count, last_error, processing_status) rather than a separate FailedTriage model. Reasons:
1. Simpler -- one model to query, no cross-references
2. The Email record exists regardless (created at poll time), just needs status tracking
3. Matches v1's pattern where failed triages are retried by re-processing the same email
4. `processing_status` choices: `pending`, `processing`, `completed`, `failed`, `exhausted`
5. Query for retryable: `Email.objects.filter(processing_status="failed", retry_count__lt=3)`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gmail API auth | Custom OAuth flow | google-auth service_account.Credentials | Domain-wide delegation with impersonation is complex; library handles token refresh |
| Structured AI output | JSON parsing from text | Anthropic tool use (tool_choice forced) | Guaranteed schema conformance, v1 already uses this pattern |
| Retry with backoff | Manual retry loops | tenacity @retry decorator | Handles jitter, max attempts, exception filtering; proven in v1 |
| PDF text extraction | Custom PDF parser | pypdf PdfReader.pages[n].extract_text() | Pure Python, BSD license, handles most PDF structures |
| Job scheduling | Custom threading/cron | APScheduler BlockingScheduler | Handles intervals, coalesce, max_instances; v1 uses BackgroundScheduler |
| HTTP webhook calls | urllib/custom client | httpx.post() | Timeout handling, connection pooling, used in v1 |

**Key insight:** The entire v1 pipeline is battle-tested. Don't redesign the processing logic -- port it with minimal changes, swapping only the persistence layer (Sheets to ORM).

## Common Pitfalls

### Pitfall 1: Scheduler Running in Multiple Workers
**What goes wrong:** If APScheduler starts inside Gunicorn, each worker process spawns its own scheduler, causing duplicate email processing.
**Why it happens:** Gunicorn forks multiple workers by default.
**How to avoid:** Run scheduler as a separate Docker Compose service with `command: python manage.py run_scheduler`. Never start scheduler in wsgi.py or apps.py.
**Warning signs:** Duplicate emails in database, emails processed 2-4x.

### Pitfall 2: Database Connections in Scheduler
**What goes wrong:** APScheduler threads may use stale DB connections that Django has closed.
**Why it happens:** Django's connection management is request-scoped; long-running management commands don't follow request lifecycle.
**How to avoid:** Call `django.db.close_old_connections()` at the start of each scheduled job, or use `CONN_MAX_AGE=0` for the scheduler process. The cleanest approach:
```python
from django.db import close_old_connections

def poll_job():
    close_old_connections()
    # ... actual poll logic
```
**Warning signs:** `InterfaceError: connection already closed` or `OperationalError: server closed the connection unexpectedly`.

### Pitfall 3: Gmail Label Race Condition
**What goes wrong:** Email gets labeled as processed but DB write hasn't committed yet. If the process crashes between label and commit, the email is lost.
**Why it happens:** Labeling before persisting.
**How to avoid:** v1's label-after-persist pattern -- label Gmail ONLY after `email.save()` succeeds. This is a locked decision.

### Pitfall 4: PyMuPDF License Trap
**What goes wrong:** Using PyMuPDF (fitz) brings AGPL license obligations.
**Why it happens:** v1 uses `import fitz` for PDF extraction.
**How to avoid:** Use pypdf (BSD license) instead. The STATE.md already records this decision: "Swap PyMuPDF (AGPL) for pypdf (BSD)".

### Pitfall 5: Service Account Key in Docker
**What goes wrong:** Service account JSON key needs to be available inside the Docker container.
**Why it happens:** Gmail API requires a physical key file for domain-wide delegation.
**How to avoid:** Mount the key as a Docker secret or volume. Add to docker-compose.yml:
```yaml
volumes:
  - ./secrets/service-account.json:/app/secrets/service-account.json:ro
```
**Warning signs:** `FileNotFoundError: service-account.json` on scheduler startup.

### Pitfall 6: Timezone Confusion
**What goes wrong:** Mixing naive and aware datetimes, or IST vs UTC confusion.
**Why it happens:** Django uses `Asia/Kolkata` (USE_TZ=True), v1 uses pytz.timezone("Asia/Kolkata"), Gmail returns UTC.
**How to avoid:** Keep USE_TZ=True. Store everything as UTC in DB (Django default). Use `django.utils.timezone.now()` for Django code, `pytz.UTC` for Gmail timestamps (same as v1).

### Pitfall 7: Anthropic SDK Version Mismatch
**What goes wrong:** v1's tool_use/tool_choice API may have changed in newer anthropic SDK versions.
**Why it happens:** SDK evolves; structured output features added.
**How to avoid:** Pin anthropic version range. The tool_use pattern in v1 is stable and well-supported. Test the exact call pattern with current SDK.

## Code Examples

### Gmail Polling with Django ORM (adapted from v1)
```python
# apps/emails/services/pipeline.py
import logging
from django.db import close_old_connections
from apps.emails.models import Email
from apps.emails.services.gmail_poller import GmailPoller, EmailMessage
from apps.emails.services.ai_processor import AIProcessor
from apps.emails.services.spam_filter import is_spam
from apps.core.models import SystemConfig

logger = logging.getLogger(__name__)

def process_poll_cycle(gmail_poller, ai_processor, chat_notifier, state_manager):
    """One poll cycle: fetch -> filter -> triage -> save -> label -> notify."""
    close_old_connections()

    # Hot-reload config
    ai_enabled = SystemConfig.get("ai_triage_enabled", True)
    chat_enabled = SystemConfig.get("chat_notifications_enabled", True)
    poll_inboxes = SystemConfig.get("monitored_inboxes", "info@vidarbhainfotech.com,sales@vidarbhainfotech.com")
    inboxes = [i.strip() for i in poll_inboxes.split(",")]

    # Circuit breaker
    max_failures = int(SystemConfig.get("max_consecutive_failures", 3))
    if state_manager.consecutive_failures >= max_failures:
        logger.critical("Circuit breaker OPEN -- skipping poll")
        return

    try:
        new_emails = gmail_poller.poll_all(inboxes)
        processed_items = []

        for email_msg in new_emails:
            # Dedup via unique message_id
            if Email.objects.filter(message_id=email_msg.message_id).exists():
                continue

            # Spam check
            spam_result = is_spam(email_msg)
            if spam_result:
                triage = spam_result
            elif ai_enabled:
                triage = ai_processor.process(email_msg, gmail_poller=gmail_poller)
            else:
                triage = AIProcessor._fallback_result("AI disabled")

            # Save to DB (label-after-persist pattern)
            email_obj = save_email_to_db(email_msg, triage)
            gmail_poller.mark_processed(email_msg)
            processed_items.append(email_obj)

        # Batch Chat notification
        if processed_items and chat_enabled:
            chat_notifier.notify_poll_summary(format_for_chat(processed_items))

        state_manager.reset_failures()

    except Exception as e:
        logger.error(f"Poll cycle failed: {e}")
        state_manager.record_failure()
```

### Dead Letter Retry
```python
# apps/emails/services/pipeline.py
def retry_failed_emails(gmail_poller, ai_processor, chat_notifier):
    """Retry emails with processing_status='failed' and retry_count < 3."""
    close_old_connections()

    failed = Email.objects.filter(
        processing_status="failed",
        retry_count__lt=3,
    ).order_by("created_at")[:10]  # Process max 10 per cycle

    for email_obj in failed:
        email_obj.retry_count += 1
        try:
            # Re-fetch from Gmail for fresh data
            email_msg = gmail_poller.fetch_thread_message(
                email_obj.to_inbox, email_obj.gmail_thread_id
            )
            if not email_msg:
                raise ValueError("Could not fetch thread from Gmail")

            triage = ai_processor.process(email_msg, gmail_poller=gmail_poller)
            # Update email with triage results
            email_obj.category = triage.category
            email_obj.priority = triage.priority
            email_obj.ai_summary = triage.summary
            email_obj.ai_draft_reply = triage.draft_reply
            email_obj.processing_status = "completed"
            email_obj.last_error = ""
            email_obj.save()
        except Exception as e:
            email_obj.last_error = str(e)[:500]
            if email_obj.retry_count >= 3:
                email_obj.processing_status = "exhausted"
            email_obj.save()
```

### SystemConfig Model
```python
# apps/core/models.py (addition)
class SystemConfig(TimestampedModel):
    """Key-value configuration store with typed values. Hot-reloaded every poll cycle."""

    class ValueType(models.TextChoices):
        STRING = "str", "String"
        INTEGER = "int", "Integer"
        BOOLEAN = "bool", "Boolean"
        FLOAT = "float", "Float"
        JSON = "json", "JSON"

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField(default="")
    value_type = models.CharField(
        max_length=10,
        choices=ValueType.choices,
        default=ValueType.STRING,
    )
    description = models.TextField(blank=True, default="")
    category = models.CharField(
        max_length=50, blank=True, default="general",
        help_text="Group configs: general, polling, feature_flags, notifications, quiet_hours",
    )

    class Meta:
        ordering = ["category", "key"]
        verbose_name = "System Configuration"

    def __str__(self):
        return f"{self.key} = {self.value}"

    @property
    def typed_value(self):
        """Return value cast to its declared type."""
        converters = {
            "int": lambda v: int(v),
            "bool": lambda v: v.lower() in ("true", "1", "yes", "on"),
            "float": lambda v: float(v),
            "json": lambda v: __import__("json").loads(v),
        }
        try:
            return converters.get(self.value_type, lambda v: v)(self.value)
        except (ValueError, TypeError):
            return self.value

    @classmethod
    def get(cls, key, default=None):
        """Get a typed config value by key. Returns default if not found."""
        try:
            return cls.objects.get(key=key).typed_value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_all_by_category(cls, category):
        """Get all configs in a category as a dict."""
        return {c.key: c.typed_value for c in cls.objects.filter(category=category)}
```

### Scheduler Management Command
```python
# apps/emails/management/commands/run_scheduler.py
import logging
import signal
import sys

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run the email processing scheduler (poll, retry, heartbeat)"

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone="Asia/Kolkata")

        # Heartbeat -- write timestamp to SystemConfig every minute
        scheduler.add_job(
            self._heartbeat, IntervalTrigger(minutes=1),
            id="heartbeat", name="Scheduler Heartbeat",
            max_instances=1, coalesce=True,
        )

        # Email polling -- every 5 minutes (configurable via SystemConfig)
        scheduler.add_job(
            self._poll, IntervalTrigger(minutes=5),
            id="email_poll", name="Email Polling",
            max_instances=1, coalesce=True,
        )

        # Dead letter retry -- every 30 minutes
        scheduler.add_job(
            self._retry, IntervalTrigger(minutes=30),
            id="dead_letter_retry", name="Dead Letter Retry",
            max_instances=1, coalesce=True,
        )

        def shutdown(signum, frame):
            logger.info("Shutting down scheduler...")
            scheduler.shutdown(wait=False)
            sys.exit(0)

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)

        logger.info("Scheduler starting...")
        scheduler.start()

    @staticmethod
    def _heartbeat():
        close_old_connections()
        from apps.core.models import SystemConfig
        SystemConfig.objects.update_or_create(
            key="scheduler_heartbeat",
            defaults={"value": timezone.now().isoformat(), "value_type": "str"},
        )

    @staticmethod
    def _poll():
        close_old_connections()
        # Initialize services and run poll cycle
        from apps.emails.services.pipeline import process_poll_cycle
        process_poll_cycle(...)  # Pass initialized services

    @staticmethod
    def _retry():
        close_old_connections()
        from apps.emails.services.pipeline import retry_failed_emails
        retry_failed_emails(...)
```

### PDF Extraction with pypdf (replacing PyMuPDF)
```python
# apps/emails/services/pdf_extractor.py
import logging
from io import BytesIO
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def extract_pdf_text(pdf_bytes: bytes, max_pages: int = 3, max_chars: int = 1000) -> str:
    """Extract text from PDF bytes. Returns first N pages, truncated."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        text_parts = []
        for page_num in range(min(len(reader.pages), max_pages)):
            page_text = reader.pages[page_num].extract_text() or ""
            text_parts.append(page_text)
        full_text = "\n".join(text_parts)
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n[...truncated...]"
        return full_text.strip()
    except Exception as e:
        logger.warning(f"PDF extraction failed: {e}")
        return ""
```

## State of the Art

| Old Approach (v1) | Current Approach (v2) | When Changed | Impact |
|--------------------|-----------------------|--------------|--------|
| Google Sheets persistence | Django ORM + PostgreSQL | Phase 2 | Source of truth moves to DB; faster, queryable, relational |
| PyMuPDF (fitz) for PDF | pypdf (PdfReader) | Phase 2 | BSD license, pure Python, no binary deps |
| Sheet-based dedup (is_thread_logged) | message_id unique constraint | Phase 2 | DB-level dedup, no cache TTL concerns |
| Sheet-based config hot-reload | SystemConfig model + Django admin | Phase 2 | Same hot-reload pattern, better UI via admin |
| Single process (Cloud Run) | Two containers (web + scheduler) | Phase 2 | Gunicorn serves HTTP, scheduler runs jobs independently |
| In-memory ticket counter | No ticket numbers (per REQUIREMENTS.md) | Phase 2 | Ticket numbering removed -- out of scope |

**Deprecated/outdated:**
- PyMuPDF/fitz: AGPL license, replaced by pypdf (BSD)
- Sheet-based dead letter: Replaced by Email model retry fields
- config.yaml for runtime settings: Replaced by SystemConfig model (env vars still used for secrets)

## Open Questions

1. **Service Account Key in Docker**
   - What we know: v1 mounts `/secrets/service-account.json` via Cloud Run secret mount
   - What's unclear: How to securely provide the SA key to the Docker container on the VM
   - Recommendation: Mount via Docker Compose volume from a host directory. Add `secrets/` to `.gitignore`. Document in deployment guide.

2. **Initial SystemConfig Seed Data**
   - What we know: Need default values for feature flags, polling interval, quiet hours
   - What's unclear: Whether to use a data migration or management command for seeding
   - Recommendation: Use a Django data migration to create default SystemConfig entries. This ensures they exist on first deploy.

3. **Chat Notification URL for v2**
   - What we know: v1 uses Google Chat webhook. v2 Chat card "Open Tracker" button currently points to Google Sheet URL
   - What's unclear: Should the button point to the v2 dashboard instead?
   - Recommendation: For Phase 2, keep pointing to the Sheet (dashboard doesn't exist yet). Update in Phase 3 when dashboard is built.

4. **Scheduler Service Health Check**
   - What we know: Scheduler writes heartbeat to DB. Health endpoint needs to check it.
   - What's unclear: Should the scheduler container also expose an HTTP health endpoint?
   - Recommendation: Docker Compose healthcheck can use `python manage.py check_scheduler_health` (a simple command that checks the heartbeat timestamp). No HTTP needed for the scheduler container.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-django 4.9.x |
| Config file | `pytest.ini` (exists, configured) |
| Quick run command | `pytest apps/emails/tests/ -x -q` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROC-01 | Gmail polling returns EmailMessage DTOs | unit (mocked Gmail API) | `pytest apps/emails/tests/test_gmail_poller.py -x` | Wave 0 |
| PROC-01 | Polled emails saved to DB with correct fields | unit | `pytest apps/emails/tests/test_pipeline.py::test_save_email_to_db -x` | Wave 0 |
| PROC-02 | AI triage returns TriageResult with all fields | unit (mocked Anthropic API) | `pytest apps/emails/tests/test_ai_processor.py -x` | Wave 0 |
| PROC-03 | Spam regex filter catches spam patterns | unit | `pytest apps/emails/tests/test_spam_filter.py -x` | Wave 0 |
| PROC-03 | Spam emails marked is_spam=True in DB | unit | `pytest apps/emails/tests/test_pipeline.py::test_spam_email_saved -x` | Wave 0 |
| PROC-04 | PDF text extraction via pypdf | unit | `pytest apps/emails/tests/test_pdf_extractor.py -x` | Wave 0 |
| PROC-05 | Language field stored from AI triage | unit | `pytest apps/emails/tests/test_pipeline.py::test_language_stored -x` | Wave 0 |
| PROC-06 | Failed triage sets processing_status=failed | unit | `pytest apps/emails/tests/test_pipeline.py::test_failed_triage -x` | Wave 0 |
| PROC-06 | Retry increments retry_count up to 3 | unit | `pytest apps/emails/tests/test_pipeline.py::test_dead_letter_retry -x` | Wave 0 |
| INFR-08 | SystemConfig stores and retrieves typed values | unit | `pytest apps/core/tests/test_system_config.py -x` | Wave 0 |
| INFR-11 | Feature flags read from SystemConfig | unit | `pytest apps/emails/tests/test_pipeline.py::test_feature_flag_ai_disabled -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/ apps/core/tests/ -x -q`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_gmail_poller.py` -- covers PROC-01 (mock Gmail API)
- [ ] `apps/emails/tests/test_ai_processor.py` -- covers PROC-02 (mock Anthropic)
- [ ] `apps/emails/tests/test_spam_filter.py` -- covers PROC-03
- [ ] `apps/emails/tests/test_pdf_extractor.py` -- covers PROC-04
- [ ] `apps/emails/tests/test_pipeline.py` -- covers PROC-01/02/03/05/06, INFR-11
- [ ] `apps/core/tests/test_system_config.py` -- covers INFR-08, INFR-11
- [ ] `apps/emails/tests/test_chat_notifier.py` -- covers Chat notification
- [ ] `apps/emails/tests/test_scheduler.py` -- covers scheduler command startup
- [ ] Test fixtures: EmailMessage and TriageResult factory helpers

## Sources

### Primary (HIGH confidence)
- v1 source code (`agent/gmail_poller.py`, `agent/ai_processor.py`, `agent/chat_notifier.py`, `agent/state.py`, `main.py`) -- complete implementation reference
- v2 existing code (`apps/emails/models.py`, `apps/core/models.py`, `config/settings/base.py`) -- target architecture
- Phase 2 CONTEXT.md -- user decisions and constraints
- REQUIREMENTS.md -- requirement definitions

### Secondary (MEDIUM confidence)
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) -- v3.11.x is latest stable
- [pypdf PyPI](https://pypi.org/project/pypdf/) -- v6.8.0, BSD license, pure Python
- [Anthropic SDK GitHub](https://github.com/anthropics/anthropic-sdk-python) -- tool use API stable
- [google-api-python-client PyPI](https://pypi.org/project/google-api-python-client/) -- v2.192.0 latest
- [Django APScheduler common mistakes](https://sepgh.medium.com/common-mistakes-with-using-apscheduler-in-your-python-and-django-applications-100b289b812c) -- DB connection pitfall

### Tertiary (LOW confidence)
- None -- all critical findings verified against source code and official packages

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are same as v1 (proven) or direct replacements (pypdf for pymupdf)
- Architecture: HIGH -- porting proven v1 patterns with Django ORM substitution
- Pitfalls: HIGH -- based on v1 production experience + known Django/APScheduler issues
- Dead letter design: MEDIUM -- recommendation based on analysis, but marked as Claude's discretion

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable stack, no fast-moving dependencies)
