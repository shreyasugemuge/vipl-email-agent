"""Tests for thread search functionality."""

import pytest
from datetime import datetime, timezone
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.emails.models import Thread
from conftest import create_thread


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.login(username="admin", password="testpass123")
    return c


@pytest.mark.django_db
class TestThreadSearch:
    def test_search_by_subject(self, admin_client):
        create_thread(gmail_thread_id="t1", subject="Invoice #1234 from vendor")
        create_thread(gmail_thread_id="t2", subject="Meeting tomorrow at 3pm")
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=invoice")
        threads = list(response.context["threads"])
        assert len(threads) == 1
        assert threads[0].subject == "Invoice #1234 from vendor"

    def test_search_by_sender_name(self, admin_client):
        create_thread(gmail_thread_id="t1", last_sender="Raj Kumar")
        create_thread(gmail_thread_id="t2", last_sender="Priya Singh")
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=raj")
        threads = list(response.context["threads"])
        assert len(threads) == 1
        assert threads[0].last_sender == "Raj Kumar"

    def test_search_by_sender_email(self, admin_client):
        create_thread(gmail_thread_id="t1", last_sender_address="billing@vendor.com")
        create_thread(gmail_thread_id="t2", last_sender_address="info@client.org")
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=vendor.com")
        threads = list(response.context["threads"])
        assert len(threads) == 1

    def test_search_by_ai_summary(self, admin_client):
        create_thread(gmail_thread_id="t1", ai_summary="Tender document for road construction")
        create_thread(gmail_thread_id="t2", ai_summary="Customer support request about billing")
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=tender")
        threads = list(response.context["threads"])
        assert len(threads) == 1

    def test_search_case_insensitive(self, admin_client):
        create_thread(gmail_thread_id="t1", subject="URGENT Payment Request")
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=urgent payment")
        threads = list(response.context["threads"])
        assert len(threads) == 1

    def test_empty_search_returns_all(self, admin_client):
        create_thread(gmail_thread_id="t1", subject="Thread A")
        create_thread(gmail_thread_id="t2", subject="Thread B")
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=")
        threads = list(response.context["threads"])
        assert len(threads) == 2

    def test_no_results(self, admin_client):
        create_thread(gmail_thread_id="t1")
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=zzzznonexistent")
        threads = list(response.context["threads"])
        assert len(threads) == 0

    def test_search_preserved_in_context(self, admin_client):
        response = admin_client.get(reverse("emails:thread_list") + "?view=all&q=hello")
        assert response.context["current_search"] == "hello"

    def test_search_combined_with_priority_filter(self, admin_client):
        create_thread(gmail_thread_id="t1", subject="Invoice high", priority="HIGH")
        create_thread(gmail_thread_id="t2", subject="Invoice medium", priority="MEDIUM")
        response = admin_client.get(
            reverse("emails:thread_list") + "?view=all&q=invoice&priority=HIGH"
        )
        threads = list(response.context["threads"])
        assert len(threads) == 1
        assert threads[0].priority == "HIGH"
