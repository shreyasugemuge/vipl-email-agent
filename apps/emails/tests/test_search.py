"""Tests for email search functionality."""

import pytest
from datetime import datetime, timezone
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.emails.models import Email


def _email(**overrides):
    defaults = {
        "message_id": f"msg_{id(overrides)}",
        "from_address": "sender@example.com",
        "from_name": "Test Sender",
        "to_inbox": "info@vidarbhainfotech.com",
        "subject": "Test Subject",
        "body": "Test body content",
        "received_at": datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
        "category": "General Inquiry",
        "priority": "MEDIUM",
        "ai_summary": "A test email summary.",
        "processing_status": Email.ProcessingStatus.COMPLETED,
        "status": Email.Status.NEW,
    }
    defaults.update(overrides)
    return Email.objects.create(**defaults)


@pytest.fixture
def admin_client(admin_user):
    c = Client()
    c.login(username="admin", password="testpass123")
    return c


@pytest.mark.django_db
class TestEmailSearch:
    def test_search_by_subject(self, admin_client):
        _email(message_id="m1", subject="Invoice #1234 from vendor")
        _email(message_id="m2", subject="Meeting tomorrow at 3pm")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=invoice")
        emails = list(response.context["emails"])
        assert len(emails) == 1
        assert emails[0].subject == "Invoice #1234 from vendor"

    def test_search_by_sender_name(self, admin_client):
        _email(message_id="m1", from_name="Raj Kumar")
        _email(message_id="m2", from_name="Priya Singh")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=raj")
        emails = list(response.context["emails"])
        assert len(emails) == 1
        assert emails[0].from_name == "Raj Kumar"

    def test_search_by_sender_email(self, admin_client):
        _email(message_id="m1", from_address="billing@vendor.com")
        _email(message_id="m2", from_address="info@client.org")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=vendor.com")
        emails = list(response.context["emails"])
        assert len(emails) == 1

    def test_search_by_body(self, admin_client):
        _email(message_id="m1", body="Please send the payment immediately")
        _email(message_id="m2", body="Here are the meeting notes")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=payment")
        emails = list(response.context["emails"])
        assert len(emails) == 1

    def test_search_by_ai_summary(self, admin_client):
        _email(message_id="m1", ai_summary="Tender document for road construction")
        _email(message_id="m2", ai_summary="Customer support request about billing")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=tender")
        emails = list(response.context["emails"])
        assert len(emails) == 1

    def test_search_case_insensitive(self, admin_client):
        _email(message_id="m1", subject="URGENT Payment Request")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=urgent payment")
        emails = list(response.context["emails"])
        assert len(emails) == 1

    def test_empty_search_returns_all(self, admin_client):
        _email(message_id="m1", subject="Email A")
        _email(message_id="m2", subject="Email B")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=")
        emails = list(response.context["emails"])
        assert len(emails) == 2

    def test_no_results(self, admin_client):
        _email(message_id="m1")
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=zzzznonexistent")
        emails = list(response.context["emails"])
        assert len(emails) == 0

    def test_search_preserved_in_context(self, admin_client):
        response = admin_client.get(reverse("emails:email_list") + "?view=all&q=hello")
        assert response.context["current_search"] == "hello"

    def test_search_combined_with_priority_filter(self, admin_client):
        _email(message_id="m1", subject="Invoice high", priority="HIGH")
        _email(message_id="m2", subject="Invoice medium", priority="MEDIUM")
        response = admin_client.get(
            reverse("emails:email_list") + "?view=all&q=invoice&priority=HIGH"
        )
        emails = list(response.context["emails"])
        assert len(emails) == 1
        assert emails[0].priority == "HIGH"
