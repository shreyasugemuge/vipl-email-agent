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
    ai_suggested_assignee = models.CharField(max_length=100, blank=True, default="")
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

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.from_address}: {self.subject[:50]}"


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
