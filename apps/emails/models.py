"""Email models for VIPL Email Agent v2."""

from django.conf import settings
from django.db import models

from apps.core.models import SoftDeleteModel, TimestampedModel


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

    # Gmail identifiers
    message_id = models.CharField(max_length=255, unique=True)
    gmail_id = models.CharField(max_length=255, blank=True, default="")
    gmail_thread_id = models.CharField(max_length=255, blank=True, default="")
    gmail_labels = models.JSONField(default=list, blank=True)

    # Email content
    from_address = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True, default="")
    to_inbox = models.EmailField()
    subject = models.CharField(max_length=500, blank=True, default="")
    body = models.TextField(blank=True, default="")
    headers = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField()

    # HTML body (separate from plain text body)
    body_html = models.TextField(blank=True, default="")

    # AI triage fields
    category = models.CharField(max_length=100, blank=True, default="")
    priority = models.CharField(max_length=50, blank=True, default="")
    ai_summary = models.TextField(blank=True, default="")
    ai_draft_reply = models.TextField(blank=True, default="")

    # AI metadata (Phase 2)
    language = models.CharField(max_length=20, blank=True, default="")
    is_spam = models.BooleanField(default=False)
    spam_score = models.FloatField(default=0.0)
    ai_reasoning = models.TextField(blank=True, default="")
    ai_model_used = models.CharField(max_length=100, blank=True, default="")
    ai_tags = models.JSONField(default=list, blank=True)
    ai_suggested_assignee = models.JSONField(default=dict, blank=True)
    ai_input_tokens = models.PositiveIntegerField(default=0)
    ai_output_tokens = models.PositiveIntegerField(default=0)
    gmail_link = models.URLField(max_length=500, blank=True, default="")

    # Dead letter / retry tracking (Phase 2)
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    retry_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")

    # Assignment
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
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

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
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


class AttachmentMetadata(TimestampedModel):
    """Stores metadata about email attachments (actual files stay in Gmail)."""

    email = models.ForeignKey(
        Email,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    filename = models.CharField(max_length=255)
    size_bytes = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    gmail_attachment_id = models.CharField(max_length=255, blank=True, default="")

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
