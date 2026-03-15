"""Tests for spam badge annotation and force_poll fixes (SPAM-06, FIX-03).

Spam badge annotation: Email.objects uses SoftDeleteManager which filters
deleted_at__isnull=True. The Exists subquery in thread_list correctly excludes
soft-deleted emails. The detail panel uses thread.emails (same manager).
Both are consistent -- no annotation bug.

Force poll fixes:
- Production mode restriction removed (works in all modes)
- Hardcoded cwd replaced with settings.BASE_DIR
"""

from unittest.mock import patch, MagicMock

import pytest
from django.test import Client

from conftest import create_thread, create_email


@pytest.mark.django_db
class TestHasSpamAnnotation:
    """Verify has_spam annotation on Thread queryset."""

    def _get_annotated_qs(self):
        from django.db.models import Exists, OuterRef
        from apps.emails.models import Email, Thread

        return Thread.objects.annotate(
            has_spam=Exists(Email.objects.filter(thread=OuterRef("pk"), is_spam=True)),
        )

    def test_has_spam_annotation_true(self):
        """Thread with at least one Email(is_spam=True) has has_spam=True."""
        thread = create_thread()
        create_email(thread=thread, is_spam=True)
        create_email(thread=thread, is_spam=False)

        qs = self._get_annotated_qs()
        t = qs.get(pk=thread.pk)
        assert t.has_spam is True

    def test_has_spam_annotation_false(self):
        """Thread with all Email(is_spam=False) has has_spam=False."""
        thread = create_thread()
        create_email(thread=thread, is_spam=False)
        create_email(thread=thread, is_spam=False)

        qs = self._get_annotated_qs()
        t = qs.get(pk=thread.pk)
        assert t.has_spam is False

    def test_has_spam_annotation_soft_deleted(self):
        """Thread where spam email is soft-deleted -- annotation excludes it.

        Email.objects uses SoftDeleteManager (filters deleted_at__isnull=True),
        so a soft-deleted spam email should NOT make has_spam=True.
        """
        from django.utils import timezone as tz

        thread = create_thread()
        spam_email = create_email(thread=thread, is_spam=True)
        create_email(thread=thread, is_spam=False)

        # Soft-delete the spam email
        spam_email.deleted_at = tz.now()
        spam_email.save(update_fields=["deleted_at"])

        qs = self._get_annotated_qs()
        t = qs.get(pk=thread.pk)
        assert t.has_spam is False

    def test_has_spam_annotation_after_feedback_change(self):
        """After changing Email.is_spam from False to True, annotation reflects it."""
        thread = create_thread()
        email = create_email(thread=thread, is_spam=False)

        qs = self._get_annotated_qs()
        t = qs.get(pk=thread.pk)
        assert t.has_spam is False

        # User marks email as spam
        email.is_spam = True
        email.save(update_fields=["is_spam"])

        # Re-query
        qs = self._get_annotated_qs()
        t = qs.get(pk=thread.pk)
        assert t.has_spam is True


@pytest.mark.django_db
class TestForcePoll:
    """Test force_poll view fixes."""

    def test_force_poll_production_mode_allowed(self, admin_user, client):
        """POST to force_poll with operating_mode='production' returns 200 (not 403)."""
        from apps.core.models import SystemConfig

        client.login(username="admin", password="testpass123")
        SystemConfig.objects.update_or_create(
            key="operating_mode", defaults={"value": "production", "value_type": "str"}
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Poll complete", stderr="")
            response = client.post("/emails/inspect/force-poll/")

        assert response.status_code == 200

    def test_force_poll_uses_base_dir(self, admin_user, client):
        """force_poll subprocess.run uses settings.BASE_DIR for cwd."""
        from django.conf import settings
        from apps.core.models import SystemConfig

        client.login(username="admin", password="testpass123")
        SystemConfig.objects.update_or_create(
            key="operating_mode", defaults={"value": "off", "value_type": "str"}
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Poll complete", stderr="")
            client.post("/emails/inspect/force-poll/")

        call_kwargs = mock_run.call_args
        assert call_kwargs[1]["cwd"] == str(settings.BASE_DIR)
