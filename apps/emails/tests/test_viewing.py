"""Tests for viewing presence: ThreadViewer model, heartbeat endpoint, clear-viewer, active viewers."""

import pytest
from datetime import timedelta
from unittest.mock import patch

from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import Thread, ThreadViewer
from apps.emails.views import viewer_heartbeat, clear_viewer, get_active_viewers


def _create_user(db, username="testuser", **overrides):
    """Helper to create a User."""
    defaults = {
        "username": username,
        "email": f"{username}@vidarbhainfotech.com",
        "first_name": username.capitalize(),
        "last_name": "User",
    }
    defaults.update(overrides)
    return User.objects.create_user(password="testpass123", **defaults)


def _create_thread(db, **overrides):
    """Helper to create a Thread record."""
    defaults = {
        "gmail_thread_id": f"thread_{id(overrides)}",
        "subject": "Test Thread",
        "status": Thread.Status.NEW,
    }
    defaults.update(overrides)
    return Thread.objects.create(**defaults)


# ===========================================================================
# ThreadViewer model tests
# ===========================================================================


@pytest.mark.django_db
def test_threadviewer_creation(db):
    """ThreadViewer can be created with thread and user."""
    user = _create_user(db, username="alice")
    thread = _create_thread(db)
    viewer = ThreadViewer.objects.create(thread=thread, user=user)
    assert viewer.pk is not None
    assert viewer.thread == thread
    assert viewer.user == user
    assert viewer.last_seen is not None


@pytest.mark.django_db
def test_threadviewer_unique_constraint(db):
    """Only one viewer record per (thread, user) pair."""
    from django.db import IntegrityError

    user = _create_user(db, username="bob")
    thread = _create_thread(db)
    ThreadViewer.objects.create(thread=thread, user=user)
    with pytest.raises(IntegrityError):
        ThreadViewer.objects.create(thread=thread, user=user)


@pytest.mark.django_db
def test_threadviewer_str(db):
    """ThreadViewer __str__ returns readable representation."""
    user = _create_user(db, username="carol")
    thread = _create_thread(db)
    viewer = ThreadViewer.objects.create(thread=thread, user=user)
    assert "carol" in str(viewer)
    assert str(thread.pk) in str(viewer)


# ===========================================================================
# get_active_viewers tests
# ===========================================================================


@pytest.mark.django_db
def test_get_active_viewers_returns_recent(db):
    """Active viewers within 30s cutoff are returned."""
    user = _create_user(db, username="dave")
    thread = _create_thread(db)
    ThreadViewer.objects.create(thread=thread, user=user)
    viewers = get_active_viewers(thread.pk)
    assert viewers.count() == 1
    assert viewers.first().user == user


@pytest.mark.django_db
def test_get_active_viewers_excludes_stale(db):
    """Viewers with last_seen > 30s ago are excluded."""
    user = _create_user(db, username="eve")
    thread = _create_thread(db)
    viewer = ThreadViewer.objects.create(thread=thread, user=user)
    # Manually set last_seen to 60 seconds ago
    stale_time = timezone.now() - timedelta(seconds=60)
    ThreadViewer.objects.filter(pk=viewer.pk).update(last_seen=stale_time)
    viewers = get_active_viewers(thread.pk)
    assert viewers.count() == 0


@pytest.mark.django_db
def test_get_active_viewers_excludes_user(db):
    """Active viewers can exclude a specific user."""
    user1 = _create_user(db, username="frank")
    user2 = _create_user(db, username="grace")
    thread = _create_thread(db)
    ThreadViewer.objects.create(thread=thread, user=user1)
    ThreadViewer.objects.create(thread=thread, user=user2)
    viewers = get_active_viewers(thread.pk, exclude_user_id=user1.pk)
    assert viewers.count() == 1
    assert viewers.first().user == user2


# ===========================================================================
# Heartbeat endpoint tests
# ===========================================================================


@pytest.mark.django_db
def test_heartbeat_creates_viewer(db):
    """POST to heartbeat creates a ThreadViewer record."""
    user = _create_user(db, username="hank")
    thread = _create_thread(db)
    factory = RequestFactory()
    request = factory.post(f"/emails/threads/{thread.pk}/heartbeat/")
    request.user = user
    response = viewer_heartbeat(request, thread.pk)
    assert response.status_code == 200
    assert ThreadViewer.objects.filter(thread=thread, user=user).exists()


@pytest.mark.django_db
def test_heartbeat_updates_existing_viewer(db):
    """Repeated heartbeat updates last_seen, not creates duplicate."""
    user = _create_user(db, username="iris")
    thread = _create_thread(db)
    old_time = timezone.now() - timedelta(seconds=20)
    ThreadViewer.objects.create(thread=thread, user=user)
    ThreadViewer.objects.filter(thread=thread, user=user).update(last_seen=old_time)

    factory = RequestFactory()
    request = factory.post(f"/emails/threads/{thread.pk}/heartbeat/")
    request.user = user
    viewer_heartbeat(request, thread.pk)

    viewer = ThreadViewer.objects.get(thread=thread, user=user)
    assert viewer.last_seen > old_time


@pytest.mark.django_db
def test_heartbeat_cleans_stale_records(db):
    """Heartbeat opportunistically cleans up stale viewer records."""
    user1 = _create_user(db, username="jack")
    user2 = _create_user(db, username="kate")
    thread = _create_thread(db)

    # Create stale viewer
    viewer = ThreadViewer.objects.create(thread=thread, user=user2)
    stale_time = timezone.now() - timedelta(seconds=60)
    ThreadViewer.objects.filter(pk=viewer.pk).update(last_seen=stale_time)

    factory = RequestFactory()
    request = factory.post(f"/emails/threads/{thread.pk}/heartbeat/")
    request.user = user1
    viewer_heartbeat(request, thread.pk)

    # Stale viewer should be cleaned up
    assert not ThreadViewer.objects.filter(thread=thread, user=user2).exists()
    # Current user should exist
    assert ThreadViewer.objects.filter(thread=thread, user=user1).exists()


# ===========================================================================
# Clear viewer endpoint tests
# ===========================================================================


@pytest.mark.django_db
def test_clear_viewer_deletes_record(db):
    """DELETE to clear-viewer removes the user's viewer record."""
    user = _create_user(db, username="leo")
    thread = _create_thread(db)
    ThreadViewer.objects.create(thread=thread, user=user)

    factory = RequestFactory()
    request = factory.delete(f"/emails/threads/{thread.pk}/clear-viewer/")
    request.user = user
    response = clear_viewer(request, thread.pk)

    assert response.status_code == 204
    assert not ThreadViewer.objects.filter(thread=thread, user=user).exists()


@pytest.mark.django_db
def test_clear_viewer_noop_if_not_viewing(db):
    """DELETE when not viewing returns 204 without error."""
    user = _create_user(db, username="mia")
    thread = _create_thread(db)

    factory = RequestFactory()
    request = factory.delete(f"/emails/threads/{thread.pk}/clear-viewer/")
    request.user = user
    response = clear_viewer(request, thread.pk)

    assert response.status_code == 204
