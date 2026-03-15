"""Email models for VIPL Email Agent v2."""

from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimestampedModel


class Thread(SoftDeleteModel, TimestampedModel):
    """Groups related emails by gmail_thread_id with thread-level status, assignment, and triage."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        CLOSED = "closed", "Closed"
        IRRELEVANT = "irrelevant", "Irrelevant"

    # Thread identity
    gmail_thread_id = models.CharField(max_length=255, unique=True, db_index=True)
    subject = models.CharField(max_length=500, blank=True, default="")

    # Latest message preview (denormalized for list display)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_sender = models.CharField(max_length=500, blank=True, default="")
    last_sender_address = models.EmailField(blank=True, default="")

    # Thread-level status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)

    # Thread-level assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_threads",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_by_threads",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)

    # SLA deadlines (thread-level)
    sla_ack_deadline = models.DateTimeField(null=True, blank=True)
    sla_respond_deadline = models.DateTimeField(null=True, blank=True)

    # Latest triage fields (copied from most recent email's triage)
    category = models.CharField(max_length=100, blank=True, default="", db_index=True)
    priority = models.CharField(max_length=50, blank=True, default="", db_index=True)
    ai_summary = models.TextField(blank=True, default="")
    ai_draft_reply = models.TextField(blank=True, default="")

    # Override flags (v2.5.0) -- prevent pipeline from overwriting user edits
    category_overridden = models.BooleanField(default=False)
    priority_overridden = models.BooleanField(default=False)

    # AI confidence tier (v2.5.0) -- HIGH/MEDIUM/LOW
    ai_confidence = models.CharField(max_length=10, blank=True, default="")

    # Auto-assignment tracking (v2.5.0)
    is_auto_assigned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-last_message_at"]

    def __str__(self):
        return f"Thread {self.gmail_thread_id[:12]}: {self.subject[:50]}"

    @property
    def message_count(self):
        return self.emails.count()

    @property
    def latest_message_at(self):
        latest = self.emails.order_by("-received_at").values_list("received_at", flat=True).first()
        return latest


class Email(SoftDeleteModel, TimestampedModel):
    """Represents an email received in a monitored inbox."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        REPLIED = "replied", "Replied"
        CLOSED = "closed", "Closed"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXHAUSTED = "exhausted", "Exhausted"

    # Thread reference
    thread = models.ForeignKey(
        "Thread",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emails",
    )

    # Gmail identifiers
    message_id = models.CharField(max_length=255, unique=True)
    gmail_id = models.CharField(max_length=255, blank=True, default="")
    gmail_thread_id = models.CharField(max_length=255, blank=True, default="")
    gmail_labels = models.JSONField(default=list, blank=True)

    # Email content
    from_address = models.EmailField()
    from_name = models.CharField(max_length=500, blank=True, default="")
    to_inbox = models.EmailField(db_index=True)
    subject = models.CharField(max_length=500, blank=True, default="")
    body = models.TextField(blank=True, default="")
    headers = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField()

    # HTML body (separate from plain text body)
    body_html = models.TextField(blank=True, default="")

    # AI triage fields
    category = models.CharField(max_length=100, blank=True, default="")
    priority = models.CharField(max_length=50, blank=True, default="", db_index=True)
    ai_summary = models.TextField(blank=True, default="")
    ai_draft_reply = models.TextField(blank=True, default="")

    # AI metadata (Phase 2)
    language = models.CharField(max_length=20, blank=True, default="")
    is_spam = models.BooleanField(default=False, db_index=True)
    spam_score = models.FloatField(default=0.0)
    ai_reasoning = models.TextField(blank=True, default="")
    ai_model_used = models.CharField(max_length=100, blank=True, default="")
    ai_tags = models.JSONField(default=list, blank=True)
    ai_suggested_assignee = models.JSONField(default=dict, blank=True)
    ai_confidence = models.CharField(max_length=10, blank=True, default="")  # v2.5.0
    ai_input_tokens = models.PositiveIntegerField(default=0)
    ai_output_tokens = models.PositiveIntegerField(default=0)
    gmail_link = models.URLField(max_length=500, blank=True, default="")

    # Dead letter / retry tracking (Phase 2)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    # Assignment
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_emails",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_by_emails",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)

    # SLA deadlines (Phase 4)
    sla_ack_deadline = models.DateTimeField(null=True, blank=True)
    sla_respond_deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.from_address}: {self.subject[:50]}"


class ActivityLog(TimestampedModel):
    """Append-only log of actions taken on an email (assignment, status change, etc.)."""

    class Action(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        REASSIGNED = "reassigned", "Reassigned"
        STATUS_CHANGED = "status_changed", "Status Changed"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        CLOSED = "closed", "Closed"
        AUTO_ASSIGNED = "auto_assigned", "Auto-Assigned"
        CLAIMED = "claimed", "Claimed"
        SLA_BREACHED = "sla_breached", "SLA Breached"
        PRIORITY_BUMPED = "priority_bumped", "Priority Bumped"
        NEW_EMAIL_RECEIVED = "new_email_received", "New Email Received"
        REOPENED = "reopened", "Reopened"
        THREAD_CREATED = "thread_created", "Thread Created"
        NOTE_ADDED = "note_added", "Note Added"
        MENTIONED = "mentioned", "Mentioned"
        AI_SUMMARY_EDITED = "ai_summary_edited", "AI Summary Edited"
        SPAM_MARKED = "spam_marked", "Spam Marked"
        SPAM_UNMARKED = "spam_unmarked", "Spam Unmarked"
        PRIORITY_CHANGED = "priority_changed", "Priority Changed"
        CATEGORY_CHANGED = "category_changed", "Category Changed"
        MARKED_IRRELEVANT = "marked_irrelevant", "Marked Irrelevant"
        REVERTED_IRRELEVANT = "reverted_irrelevant", "Reverted to New"

    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )
    detail = models.TextField(blank=True, default="")
    old_value = models.CharField(max_length=255, blank=True, default="")
    new_value = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.email_id} by {self.user_id}"


class InternalNote(SoftDeleteModel, TimestampedModel):
    """Internal team note on a thread -- never visible to the email sender."""

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="internal_notes",
    )
    body = models.TextField()
    mentioned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="mentioned_in_notes",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Note by {self.author} on {self.thread_id}"


class ThreadViewer(models.Model):
    """Tracks which users currently have a thread open (ephemeral presence, not soft-deleted)."""

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="viewers")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="viewing_threads")
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("thread", "user")]

    def __str__(self):
        return f"{self.user} viewing {self.thread_id}"


class ThreadReadState(SoftDeleteModel, TimestampedModel):
    """Per-user read/unread state for each thread."""

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="read_states")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="thread_read_states"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("thread", "user")]

    def __str__(self):
        status = "read" if self.is_read else "unread"
        return f"{self.user} - {self.thread_id} ({status})"


class SpamFeedback(SoftDeleteModel, TimestampedModel):
    """Records each spam/not-spam correction by a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="spam_feedbacks"
    )
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, null=True, blank=True, related_name="spam_feedbacks"
    )
    email = models.ForeignKey(
        Email, on_delete=models.CASCADE, null=True, blank=True, related_name="spam_feedbacks"
    )
    original_verdict = models.BooleanField()  # True=was spam, False=was not spam
    user_verdict = models.BooleanField()  # True=user says spam, False=user says not spam

    def __str__(self):
        verdict = "spam" if self.user_verdict else "not-spam"
        return f"{self.user} marked {self.thread_id or self.email_id} as {verdict}"


class SenderReputation(SoftDeleteModel, TimestampedModel):
    """Tracks per-sender spam ratio for auto-blocking."""

    sender_address = models.EmailField(unique=True, db_index=True)
    total_count = models.PositiveIntegerField(default=0)
    spam_count = models.PositiveIntegerField(default=0)
    is_blocked = models.BooleanField(default=False)

    def __str__(self):
        ratio = f"{self.spam_count}/{self.total_count}"
        blocked = " [BLOCKED]" if self.is_blocked else ""
        return f"{self.sender_address} ({ratio}){blocked}"

    @property
    def spam_ratio(self):
        if self.total_count == 0:
            return 0.0
        return self.spam_count / self.total_count


class AssignmentFeedback(SoftDeleteModel, TimestampedModel):
    """Records user feedback on AI assignment suggestions."""

    class FeedbackAction(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        REASSIGNED = "reassigned", "Reassigned"
        AUTO_ASSIGNED = "auto_assigned", "Auto-Assigned"

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="assignment_feedbacks")
    email = models.ForeignKey(
        Email, on_delete=models.CASCADE, null=True, blank=True, related_name="assignment_feedbacks"
    )
    suggested_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_assignments",
    )
    actual_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actual_assignments",
    )
    action = models.CharField(max_length=20, choices=FeedbackAction.choices)
    confidence_at_time = models.CharField(max_length=10, blank=True, null=True)
    user_who_acted = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assignment_actions",
    )

    def __str__(self):
        return f"{self.action} on {self.thread_id} by {self.user_who_acted_id}"


class AttachmentMetadata(TimestampedModel):
    """Stores metadata about email attachments (actual files stay in Gmail)."""

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    filename = models.CharField(max_length=500)
    size_bytes = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    gmail_attachment_id = models.CharField(max_length=512, blank=True, default="")

    def __str__(self):
        return f"{self.filename} ({self.mime_type})"


class AssignmentRule(TimestampedModel):
    """Category-to-person assignment rule with priority ordering.

    Rules are matched by category. Within a category, the lowest
    priority_order wins (first person in the list gets the email).
    """

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

    def __str__(self):
        return f"{self.category} -> {self.assignee} (order={self.priority_order})"


class SLAConfig(TimestampedModel):
    """SLA configuration per priority x category combination.

    Defines acknowledge and respond hours for business-hours SLA calculation.
    """

    priority = models.CharField(max_length=20)
    category = models.CharField(max_length=100)
    ack_hours = models.FloatField(default=1.0)
    respond_hours = models.FloatField(default=24.0)

    class Meta:
        unique_together = [("priority", "category")]

    def __str__(self):
        return f"SLA {self.priority}/{self.category}: ack={self.ack_hours}h, respond={self.respond_hours}h"


class SpamWhitelist(SoftDeleteModel, TimestampedModel):
    """Email/domain entries that should bypass spam regex filter.

    Whitelisted senders skip the spam pre-filter but always go through
    AI triage (they are trusted, not auto-approved).
    """

    class EntryType(models.TextChoices):
        EMAIL = "email", "Email"
        DOMAIN = "domain", "Domain"

    entry = models.CharField(max_length=255, db_index=True)
    entry_type = models.CharField(
        max_length=10,
        choices=EntryType.choices,
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whitelist_entries",
    )
    reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("entry", "entry_type")]

    def __str__(self):
        return f"{self.entry} ({self.entry_type})"


class CategoryVisibility(TimestampedModel):
    """Which categories a team member can see and claim emails from."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visible_categories",
    )
    category = models.CharField(max_length=100)

    class Meta:
        unique_together = [("user", "category")]

    def __str__(self):
        return f"{self.user} can see {self.category}"


class PollLog(TimestampedModel):
    """Log of each poll cycle for monitoring and debugging."""

    started_at = models.DateTimeField()
    status = models.CharField(max_length=20, db_index=True)  # success, skipped, error
    emails_found = models.IntegerField(default=0)
    emails_processed = models.IntegerField(default=0)
    spam_filtered = models.IntegerField(default=0)
    duration_ms = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default="")
    skipped_reason = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Poll {self.started_at:%Y-%m-%d %H:%M} — {self.status}"
