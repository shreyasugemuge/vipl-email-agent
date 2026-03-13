"""Core admin configuration."""

from django.contrib import admin

from .models import SystemConfig


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "value_type", "category", "updated_at")
    list_filter = ("category", "value_type")
    search_fields = ("key", "description")
    readonly_fields = ("created_at", "updated_at")
