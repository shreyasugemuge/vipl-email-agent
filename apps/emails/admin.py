"""Email admin configuration."""

from django.contrib import admin
from django.utils.html import format_html

from .models import AttachmentMetadata, Email, Thread


class EmailInline(admin.TabularInline):
    model = Email
    extra = 0
    fields = ("from_address", "subject", "received_at", "status", "processing_status")
    readonly_fields = ("from_address", "subject", "received_at", "status", "processing_status")
    show_change_link = True


class AttachmentInline(admin.TabularInline):
    model = AttachmentMetadata
    extra = 0
    readonly_fields = ("filename", "size_bytes", "mime_type", "gmail_attachment_id")


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = (
        "short_subject",
        "status",
        "priority",
        "category",
        "assigned_to",
        "last_message_at",
        "get_message_count",
    )
    list_filter = ("status", "priority", "category")
    search_fields = ("subject", "gmail_thread_id")
    readonly_fields = (
        "gmail_thread_id",
        "last_message_at",
        "last_sender",
        "last_sender_address",
        "created_at",
        "updated_at",
    )
    inlines = [EmailInline]

    @admin.display(description="Subject")
    def short_subject(self, obj):
        return obj.subject[:60] if obj.subject else "(no subject)"

    @admin.display(description="Messages")
    def get_message_count(self, obj):
        return obj.message_count


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
