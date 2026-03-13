"""Email admin configuration."""

from django.contrib import admin

from .models import AttachmentMetadata, Email


class AttachmentInline(admin.TabularInline):
    model = AttachmentMetadata
    extra = 0
    readonly_fields = ("filename", "size_bytes", "mime_type", "gmail_attachment_id")


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = (
        "from_address",
        "subject",
        "to_inbox",
        "category",
        "priority",
        "status",
        "processing_status",
        "assigned_to",
        "received_at",
    )
    list_filter = ("status", "priority", "category", "to_inbox", "processing_status", "is_spam")
    search_fields = ("from_address", "subject", "body")
    readonly_fields = (
        "message_id", "gmail_id", "gmail_thread_id",
        "processing_status", "retry_count", "last_error",
        "ai_reasoning", "ai_model_used", "ai_tags", "ai_suggested_assignee",
        "ai_input_tokens", "ai_output_tokens", "gmail_link",
        "created_at", "updated_at",
    )
    inlines = [AttachmentInline]


@admin.register(AttachmentMetadata)
class AttachmentMetadataAdmin(admin.ModelAdmin):
    list_display = ("filename", "mime_type", "size_bytes", "email")
    list_filter = ("mime_type",)
