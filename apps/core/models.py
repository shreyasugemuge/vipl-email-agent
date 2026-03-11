"""Base model classes for VIPL Email Agent v2."""

import json
import logging

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class SoftDeleteManager(models.Manager):
    """Default manager that excludes soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    """Abstract model that overrides delete() to set deleted_at instead of removing the row."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Abstract model with auto-managed created_at and updated_at fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SystemConfig(TimestampedModel):
    """Key-value configuration store with typed values.

    Used for feature flags, polling config, quiet hours, and other
    runtime settings that can be changed without redeployment.
    """

    class ValueType(models.TextChoices):
        STR = "str", "String"
        INT = "int", "Integer"
        BOOL = "bool", "Boolean"
        FLOAT = "float", "Float"
        JSON = "json", "JSON"

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(default="")
    value_type = models.CharField(
        max_length=10,
        choices=ValueType.choices,
        default=ValueType.STR,
    )
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="general")

    class Meta:
        ordering = ["category", "key"]
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configurations"

    def __str__(self):
        return f"{self.category}/{self.key} = {self.value}"

    @property
    def typed_value(self):
        """Return value cast to the declared type. Returns raw string on error."""
        try:
            if self.value_type == self.ValueType.INT:
                return int(self.value)
            elif self.value_type == self.ValueType.BOOL:
                return self.value.lower() in ("true", "1", "yes")
            elif self.value_type == self.ValueType.FLOAT:
                return float(self.value)
            elif self.value_type == self.ValueType.JSON:
                return json.loads(self.value)
            else:
                return self.value
        except (ValueError, TypeError, json.JSONDecodeError):
            logger.warning(f"SystemConfig: failed to cast '{self.key}' as {self.value_type}")
            return self.value

    @classmethod
    def get(cls, key, default=None):
        """Get a typed config value by key. Returns default if not found."""
        try:
            config = cls.objects.get(key=key)
            return config.typed_value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_all_by_category(cls, category):
        """Return all config entries in a category as {key: typed_value} dict."""
        configs = cls.objects.filter(category=category)
        return {c.key: c.typed_value for c in configs}
