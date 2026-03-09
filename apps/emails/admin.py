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
        "assigned_to",
        "received_at",
    )
    list_filter = ("status", "priority", "category", "to_inbox")
    search_fields = ("from_address", "subject", "body")
    readonly_fields = ("message_id", "gmail_id", "gmail_thread_id", "created_at", "updated_at")
    inlines = [AttachmentInline]


@admin.register(AttachmentMetadata)
class AttachmentMetadataAdmin(admin.ModelAdmin):
    list_display = ("filename", "mime_type", "size_bytes", "email")
    list_filter = ("mime_type",)
