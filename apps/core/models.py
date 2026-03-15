"""Base model classes for VIPL Email Agent v2."""

import json
import logging
import time

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that soft-deletes instead of hard-deleting."""

    def delete(self):
        """Soft-delete all records in the queryset."""
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """Actually delete all records in the queryset."""
        return super().delete()


class SoftDeleteManager(models.Manager):
    """Default manager that excludes soft-deleted records."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(deleted_at__isnull=True)


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate cache for this key on save so readers get fresh values
        self.__class__.invalidate_cache(self.key)

    def delete(self, *args, **kwargs):
        key = self.key
        super().delete(*args, **kwargs)
        self.__class__.invalidate_cache(key)

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

    # In-process TTL cache: {key: (value, expiry_timestamp)}
    _cache = {}
    _CACHE_TTL = 60  # seconds

    @classmethod
    def get(cls, key, default=None):
        """Get a typed config value by key. Returns default if not found.

        Uses an in-process TTL cache (60s) to avoid repeated DB hits for
        the same key within a short window (e.g., per-request config reads).
        """
        now = time.monotonic()
        cached = cls._cache.get(key)
        if cached is not None:
            value, expiry = cached
            if now < expiry:
                return value

        try:
            config = cls.objects.get(key=key)
            result = config.typed_value
            # Only cache keys that exist in the DB
            cls._cache[key] = (result, now + cls._CACHE_TTL)
            return result
        except cls.DoesNotExist:
            return default

    @classmethod
    def invalidate_cache(cls, key=None):
        """Clear the in-process config cache. Pass key to clear one entry, or None for all."""
        if key is None:
            cls._cache.clear()
        else:
            cls._cache.pop(key, None)

    @classmethod
    def get_all_by_category(cls, category):
        """Return all config entries in a category as {key: typed_value} dict."""
        configs = cls.objects.filter(category=category)
        return {c.key: c.typed_value for c in configs}
