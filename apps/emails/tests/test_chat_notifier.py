"""Tests for ChatNotifier -- Google Chat webhook notifications."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.emails.services.chat_notifier import ChatNotifier, VIPL_FOOTER_SECTION


class TestChatNotifierInit:
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_init_with_webhook_url(self, mock_config_cls):
        mock_config_cls.get.return_value = "https://triage.vidarbhainfotech.com"
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier.webhook_url == "https://chat.googleapis.com/test"

    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_init_strips_whitespace(self, mock_config_cls):
        mock_config_cls.get.return_value = "https://triage.vidarbhainfotech.com"
        notifier = ChatNotifier(webhook_url="  https://chat.googleapis.com/test  ")
        assert notifier.webhook_url == "https://chat.googleapis.com/test"

    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_init_empty_url(self, mock_config_cls):
        mock_config_cls.get.return_value = "https://triage.vidarbhainfotech.com"
        notifier = ChatNotifier(webhook_url="")
        assert notifier.webhook_url == ""

    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_init_sets_tracker_url(self, mock_config_cls):
        mock_config_cls.get.return_value = "https://custom.example.com/"
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        assert notifier._tracker_url == "https://custom.example.com"  # trailing slash stripped


@pytest.mark.django_db
class TestNotifyNewEmails:
    def _make_email(self, **kwargs):
        """Create a mock Email model instance."""
        defaults = {
            "subject": "Test Email Subject",
            "from_address": "sender@example.com",
            "to_inbox": "info@vidarbhainfotech.com",
            "priority": "HIGH",
            "category": "Sales Lead",
            "ai_suggested_assignee": "Shreyas",
            "ai_summary": "A test summary",
        }
        defaults.update(kwargs)
        mock_email = MagicMock()
        for k, v in defaults.items():
            setattr(mock_email, k, v)
        return mock_email

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_new_emails_posts_to_webhook(self, mock_config_cls, mock_post):
        """Verify httpx.post is called with correct webhook URL and Cards v2 payload."""
        mock_config_cls.get.return_value = None  # No quiet hours
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        emails = [self._make_email(), self._make_email(priority="CRITICAL")]
        result = notifier.notify_new_emails(emails)

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.args[0] == "https://chat.googleapis.com/test"
        payload = call_kwargs.kwargs["json"]
        assert "cardsV2" in payload

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_quiet_hours_suppresses_notification(self, mock_config_cls, mock_post):
        """Verify httpx.post is NOT called during quiet hours."""
        # Simulate quiet hours: 20:00 to 08:00 IST
        def config_side_effect(key, default=None):
            mapping = {
                "quiet_hours_start": "20:00",
                "quiet_hours_end": "08:00",
                "tracker_url": "https://triage.vidarbhainfotech.com",
            }
            return mapping.get(key, default)

        mock_config_cls.get.side_effect = config_side_effect

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        # Patch _is_quiet_hours to return True
        with patch.object(notifier, "_is_quiet_hours", return_value=True):
            result = notifier.notify_new_emails([self._make_email()])

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_webhook_failure_logged_not_raised(self, mock_config_cls, mock_post):
        """Verify webhook failure is logged but no exception propagated."""
        mock_config_cls.get.return_value = None
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        # Should not raise
        result = notifier.notify_new_emails([self._make_email()])
        assert result is False

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_card_format_has_required_fields(self, mock_config_cls, mock_post):
        """Verify the Cards v2 structure has header, sections, and button."""
        mock_config_cls.get.return_value = None
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_new_emails([
            self._make_email(priority="CRITICAL"),
            self._make_email(priority="HIGH"),
        ])

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        assert "header" in card
        assert "sections" in card
        # Button section should have "Open Tracker"
        sections = card["sections"]
        button_found = False
        for section in sections:
            for widget in section.get("widgets", []):
                if "buttonList" in widget:
                    buttons = widget["buttonList"]["buttons"]
                    for btn in buttons:
                        if "Open Tracker" in btn.get("text", ""):
                            button_found = True
        assert button_found, "Expected 'Open Tracker' button in card"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_empty_emails_list_skips(self, mock_config_cls, mock_post):
        """No notification for empty list."""
        mock_config_cls.get.return_value = None
        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        result = notifier.notify_new_emails([])
        assert result is True
        mock_post.assert_not_called()


@pytest.mark.django_db
class TestChatCardBranding:
    """Verify VIPL branding (header icon + footer) on all 5 card types."""

    TRACKER_URL = "https://triage.vidarbhainfotech.com"

    def _make_email(self, **kwargs):
        """Create a mock Email model instance."""
        defaults = {
            "pk": 42,
            "subject": "Test Email Subject",
            "from_address": "sender@example.com",
            "from_name": "Test Sender",
            "to_inbox": "info@vidarbhainfotech.com",
            "priority": "HIGH",
            "category": "Sales Lead",
            "ai_suggested_assignee": "Shreyas",
            "ai_summary": "A test summary",
        }
        defaults.update(kwargs)
        mock_email = MagicMock()
        for k, v in defaults.items():
            setattr(mock_email, k, v)
        return mock_email

    def _make_assignee(self, **kwargs):
        """Create a mock User model instance."""
        defaults = {"username": "shreyas", "get_full_name": lambda: "Shreyas Uge"}
        defaults.update(kwargs)
        mock_user = MagicMock()
        for k, v in defaults.items():
            if callable(v):
                getattr(mock_user, k).return_value = v()
            else:
                setattr(mock_user, k, v)
        return mock_user

    def _config_side_effect(self, key, default=None):
        """SystemConfig.get mock that returns tracker_url and no quiet hours."""
        mapping = {
            "tracker_url": self.TRACKER_URL,
        }
        return mapping.get(key, default)

    def _extract_card(self, mock_post):
        """Extract the card dict from the httpx.post mock call."""
        payload = mock_post.call_args.kwargs["json"]
        return payload["cardsV2"][0]["card"]

    def _assert_branded_header(self, card):
        """Assert card header has VIPL icon branding."""
        header = card["header"]
        assert "imageUrl" in header, "Card header missing imageUrl"
        assert "vipl-icon.jpg" in header["imageUrl"], (
            f"imageUrl should contain vipl-icon.jpg, got: {header['imageUrl']}"
        )
        assert header["imageType"] == "CIRCLE", (
            f"imageType should be CIRCLE, got: {header.get('imageType')}"
        )
        assert header["imageAltText"] == "VIPL Logo", (
            f"imageAltText should be 'VIPL Logo', got: {header.get('imageAltText')}"
        )

    def _assert_footer_section(self, card):
        """Assert the last section contains the VIPL footer textParagraph."""
        sections = card["sections"]
        last_section = sections[-1]
        widgets = last_section.get("widgets", [])
        footer_found = False
        for widget in widgets:
            tp = widget.get("textParagraph", {})
            if "Sent by VIPL Email Triage" in tp.get("text", ""):
                footer_found = True
                break
        assert footer_found, (
            f"Last section should contain 'Sent by VIPL Email Triage' footer. "
            f"Last section widgets: {widgets}"
        )

    def _assert_imageurl_uses_tracker_url(self, card):
        """Assert imageUrl is built from tracker_url, not hardcoded localhost."""
        header = card["header"]
        assert header["imageUrl"].startswith(self.TRACKER_URL), (
            f"imageUrl should start with tracker_url ({self.TRACKER_URL}), "
            f"got: {header['imageUrl']}"
        )

    # --- notify_assignment ---

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_assignment_has_branded_header(self, mock_config_cls, mock_post):
        """notify_assignment card header contains imageUrl with vipl-icon.jpg."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_assignment(self._make_email(), self._make_assignee())

        card = self._extract_card(mock_post)
        self._assert_branded_header(card)
        self._assert_imageurl_uses_tracker_url(card)

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_assignment_has_footer(self, mock_config_cls, mock_post):
        """notify_assignment card has footer section with 'Sent by VIPL Email Triage'."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_assignment(self._make_email(), self._make_assignee())

        card = self._extract_card(mock_post)
        self._assert_footer_section(card)

    # --- notify_new_emails ---

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_new_emails_has_branded_header(self, mock_config_cls, mock_post):
        """notify_new_emails card header contains imageUrl with vipl-icon.jpg."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_new_emails([self._make_email()])

        card = self._extract_card(mock_post)
        self._assert_branded_header(card)
        self._assert_imageurl_uses_tracker_url(card)

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_new_emails_has_footer(self, mock_config_cls, mock_post):
        """notify_new_emails card has footer section with 'Sent by VIPL Email Triage'."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_new_emails([self._make_email()])

        card = self._extract_card(mock_post)
        self._assert_footer_section(card)

    # --- notify_breach_summary ---

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_breach_summary_has_branded_header(self, mock_config_cls, mock_post):
        """notify_breach_summary card header contains imageUrl."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_breach_summary({
            "total_respond_breached": 2,
            "total_ack_breached": 1,
            "top_offenders": [],
            "per_assignee": {},
        })

        card = self._extract_card(mock_post)
        self._assert_branded_header(card)

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_breach_summary_has_footer(self, mock_config_cls, mock_post):
        """notify_breach_summary card has footer section."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_breach_summary({
            "total_respond_breached": 2,
            "total_ack_breached": 1,
            "top_offenders": [],
            "per_assignee": {},
        })

        card = self._extract_card(mock_post)
        self._assert_footer_section(card)

    # --- notify_eod_summary ---

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_eod_summary_has_branded_header(self, mock_config_cls, mock_post):
        """notify_eod_summary card header contains imageUrl."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_eod_summary({
            "date": "2026-03-14",
            "received_today": 10,
            "closed_today": 5,
            "total_open": 15,
            "unassigned": 3,
            "sla_breaches": 1,
            "avg_time_to_acknowledge": "12m",
            "avg_time_to_respond": "45m",
            "worst_overdue": [],
        })

        card = self._extract_card(mock_post)
        self._assert_branded_header(card)

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_eod_summary_has_footer(self, mock_config_cls, mock_post):
        """notify_eod_summary card has footer section."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_eod_summary({
            "date": "2026-03-14",
            "received_today": 10,
            "closed_today": 5,
            "total_open": 15,
            "unassigned": 3,
            "sla_breaches": 1,
            "avg_time_to_acknowledge": "12m",
            "avg_time_to_respond": "45m",
            "worst_overdue": [],
        })

        card = self._extract_card(mock_post)
        self._assert_footer_section(card)

    # --- notify_personal_breach ---

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_personal_breach_has_branded_header(self, mock_config_cls, mock_post):
        """notify_personal_breach card header contains imageUrl."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_personal_breach("Shreyas", [
            {"subject": "Overdue email", "priority": "HIGH", "overdue_minutes": 120},
        ])

        card = self._extract_card(mock_post)
        self._assert_branded_header(card)

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_notify_personal_breach_has_footer(self, mock_config_cls, mock_post):
        """notify_personal_breach card has footer section."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_personal_breach("Shreyas", [
            {"subject": "Overdue email", "priority": "HIGH", "overdue_minutes": 120},
        ])

        card = self._extract_card(mock_post)
        self._assert_footer_section(card)

    # --- Cross-cutting: imageUrl uses tracker_url ---

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_imageurl_uses_tracker_url_not_hardcoded(self, mock_config_cls, mock_post):
        """imageUrl uses tracker_url from SystemConfig (not hardcoded localhost)."""
        custom_url = "https://custom.example.com"

        def config_side_effect(key, default=None):
            if key == "tracker_url":
                return custom_url
            return default

        mock_config_cls.get.side_effect = config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_new_emails([self._make_email()])

        card = self._extract_card(mock_post)
        assert card["header"]["imageUrl"] == f"{custom_url}/static/img/vipl-icon.jpg"

    # --- VIPL_FOOTER_SECTION constant ---

    def test_vipl_footer_section_constant_exists(self):
        """VIPL_FOOTER_SECTION constant is importable and has correct structure."""
        assert "widgets" in VIPL_FOOTER_SECTION
        widgets = VIPL_FOOTER_SECTION["widgets"]
        assert len(widgets) == 1
        assert "textParagraph" in widgets[0]
        assert "Sent by VIPL Email Triage" in widgets[0]["textParagraph"]["text"]


# ===========================================================================
# SLA Urgency Label Helper Tests (NEW -- Plan 04-01)
# ===========================================================================


class TestSlaUrgencyLabel:
    """Test the _sla_urgency_label helper function."""

    def test_with_overdue_hours_and_minutes(self):
        """_sla_urgency_label('HIGH', 150) returns emoji + 'HIGH | 2h 30m overdue'."""
        from apps.emails.services.chat_notifier import _sla_urgency_label, PRIORITY_EMOJI

        result = _sla_urgency_label("HIGH", 150)
        expected = f"{PRIORITY_EMOJI['HIGH']} HIGH | 2h 30m overdue"
        assert result == expected

    def test_without_overdue(self):
        """_sla_urgency_label('MEDIUM') returns emoji + 'MEDIUM' (no overdue suffix)."""
        from apps.emails.services.chat_notifier import _sla_urgency_label, PRIORITY_EMOJI

        result = _sla_urgency_label("MEDIUM")
        expected = f"{PRIORITY_EMOJI['MEDIUM']} MEDIUM"
        assert result == expected

    def test_minutes_only(self):
        """_sla_urgency_label('LOW', 45) returns emoji + 'LOW | 45m overdue'."""
        from apps.emails.services.chat_notifier import _sla_urgency_label, PRIORITY_EMOJI

        result = _sla_urgency_label("LOW", 45)
        expected = f"{PRIORITY_EMOJI['LOW']} LOW | 45m overdue"
        assert result == expected

    def test_exact_hours(self):
        """_sla_urgency_label('CRITICAL', 120) returns emoji + 'CRITICAL | 2h overdue'."""
        from apps.emails.services.chat_notifier import _sla_urgency_label, PRIORITY_EMOJI

        result = _sla_urgency_label("CRITICAL", 120)
        expected = f"{PRIORITY_EMOJI['CRITICAL']} CRITICAL | 2h overdue"
        assert result == expected

    def test_zero_overdue(self):
        """_sla_urgency_label('HIGH', 0) returns emoji + 'HIGH' (zero treated as no overdue)."""
        from apps.emails.services.chat_notifier import _sla_urgency_label, PRIORITY_EMOJI

        result = _sla_urgency_label("HIGH", 0)
        expected = f"{PRIORITY_EMOJI['HIGH']} HIGH"
        assert result == expected

    def test_none_overdue(self):
        """_sla_urgency_label('HIGH', None) returns emoji + 'HIGH'."""
        from apps.emails.services.chat_notifier import _sla_urgency_label, PRIORITY_EMOJI

        result = _sla_urgency_label("HIGH", None)
        expected = f"{PRIORITY_EMOJI['HIGH']} HIGH"
        assert result == expected


# ===========================================================================
# Open Button Tests (NEW -- Plan 04-01)
# ===========================================================================


@pytest.mark.django_db
class TestOpenButtonsAcrossCards:
    """Test inline Open buttons on breach, summary, and new-email cards."""

    TRACKER_URL = "https://triage.vidarbhainfotech.com"

    def _config_side_effect(self, key, default=None):
        mapping = {"tracker_url": self.TRACKER_URL}
        return mapping.get(key, default)

    def _make_email(self, **kwargs):
        defaults = {
            "pk": 42,
            "subject": "Test Email Subject",
            "from_address": "sender@example.com",
            "from_name": "Test Sender",
            "to_inbox": "info@vidarbhainfotech.com",
            "priority": "HIGH",
            "category": "Sales Lead",
            "ai_suggested_assignee": "Shreyas",
            "ai_summary": "A test summary",
        }
        defaults.update(kwargs)
        mock_email = MagicMock()
        for k, v in defaults.items():
            setattr(mock_email, k, v)
        return mock_email

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_personal_breach_has_open_button(self, mock_config_cls, mock_post):
        """notify_personal_breach card widgets have decoratedText.button with openLink URL."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        breached = [
            {"subject": "Overdue email", "priority": "HIGH", "overdue_minutes": 120, "pk": 42},
        ]
        notifier.notify_personal_breach("Alice", breached)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        # Find the decoratedText widget with a button
        found_button = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                btn = dt.get("button", {})
                url = btn.get("onClick", {}).get("openLink", {}).get("url", "")
                if "/emails/?selected=" in url:
                    found_button = True
        assert found_button, "Personal breach card should have inline Open button with /emails/?selected= URL"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_personal_breach_open_button_uses_pk(self, mock_config_cls, mock_post):
        """The Open button URL ends with the correct pk value."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        breached = [
            {"subject": "Overdue email", "priority": "HIGH", "overdue_minutes": 120, "pk": 99},
        ]
        notifier.notify_personal_breach("Alice", breached)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        found_pk = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                btn = dt.get("button", {})
                url = btn.get("onClick", {}).get("openLink", {}).get("url", "")
                if url.endswith("selected=99"):
                    found_pk = True
        assert found_pk, "Open button URL should end with correct pk (99)"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_breach_summary_top_offenders_have_open_button(self, mock_config_cls, mock_post):
        """notify_breach_summary top offender widgets have inline Open buttons."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        summary = {
            "total_respond_breached": 2,
            "total_ack_breached": 0,
            "top_offenders": [
                {"subject": "Urgent", "assignee_name": "Alice", "priority": "HIGH",
                 "overdue_str": "2h", "overdue_minutes": 120, "pk": 77},
            ],
            "per_assignee": {"Alice": [{"subject": "Urgent", "priority": "HIGH", "overdue_minutes": 120}]},
        }
        notifier.notify_breach_summary(summary)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        found_button = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                btn = dt.get("button", {})
                url = btn.get("onClick", {}).get("openLink", {}).get("url", "")
                if "/emails/?selected=77" in url:
                    found_button = True
        assert found_button, "Breach summary top offender should have inline Open button"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_new_emails_have_open_button(self, mock_config_cls, mock_post):
        """notify_new_emails per-email widgets have inline Open buttons using email.pk."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        notifier.notify_new_emails([self._make_email(pk=55)])

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        found_button = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                btn = dt.get("button", {})
                url = btn.get("onClick", {}).get("openLink", {}).get("url", "")
                if "/emails/?selected=55" in url:
                    found_button = True
        assert found_button, "New emails card should have inline Open button per email"

    @pytest.mark.skip(reason="manual validation helper")
    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_dump_card_payloads_for_validation(self, mock_config_cls, mock_post):
        """Print full JSON payloads for manual validation in Google Chat Card Builder.

        Run with: pytest apps/emails/tests/test_chat_notifier.py -k test_dump_card_payloads --no-header -rN -s
        """
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")

        # --- Personal breach card ---
        breached = [
            {"subject": "Invoice overdue - Acme Corp", "priority": "HIGH", "overdue_minutes": 150, "pk": 42},
            {"subject": "Support ticket #1234", "priority": "CRITICAL", "overdue_minutes": 300, "pk": 43},
        ]
        notifier.notify_personal_breach("Alice Dev", breached)
        personal_payload = mock_post.call_args.kwargs["json"]
        print("\n=== PERSONAL BREACH CARD ===")
        print(json.dumps(personal_payload, indent=2))
        mock_post.reset_mock()

        # --- Breach summary card ---
        summary = {
            "total_respond_breached": 3,
            "total_ack_breached": 1,
            "top_offenders": [
                {"subject": "Invoice overdue - Acme Corp", "assignee_name": "Alice Dev",
                 "priority": "HIGH", "overdue_str": "2h 30m", "overdue_minutes": 150, "pk": 42},
                {"subject": "Support ticket #1234", "assignee_name": "Bob Ops",
                 "priority": "CRITICAL", "overdue_str": "5h", "overdue_minutes": 300, "pk": 43},
            ],
            "per_assignee": {
                "Alice Dev": [{"subject": "Invoice overdue", "priority": "HIGH", "overdue_minutes": 150}],
                "Bob Ops": [{"subject": "Support ticket", "priority": "CRITICAL", "overdue_minutes": 300}],
            },
        }
        notifier.notify_breach_summary(summary)
        summary_payload = mock_post.call_args.kwargs["json"]
        print("\n=== BREACH SUMMARY CARD ===")
        print(json.dumps(summary_payload, indent=2))
        mock_post.reset_mock()

        # --- New emails card ---
        emails = [
            self._make_email(pk=55, subject="New vendor inquiry", priority="HIGH", category="Sales Lead"),
            self._make_email(pk=56, subject="Server alert notification", priority="CRITICAL", category="Technical"),
            self._make_email(pk=57, subject="Meeting request", priority="LOW", category="General Inquiry"),
        ]
        notifier.notify_new_emails(emails)
        new_payload = mock_post.call_args.kwargs["json"]
        print("\n=== NEW EMAILS CARD ===")
        print(json.dumps(new_payload, indent=2))


# ===========================================================================
# Urgency Label Consistency Tests (NEW -- Plan 04-01)
# ===========================================================================


@pytest.mark.django_db
class TestUrgencyLabelConsistency:
    """Test that urgency labels are consistent across card types."""

    TRACKER_URL = "https://triage.vidarbhainfotech.com"

    def _config_side_effect(self, key, default=None):
        mapping = {"tracker_url": self.TRACKER_URL}
        return mapping.get(key, default)

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_personal_breach_uses_urgency_label_format(self, mock_config_cls, mock_post):
        """topLabel in personal breach card matches _sla_urgency_label format."""
        from apps.emails.services.chat_notifier import _sla_urgency_label

        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        breached = [
            {"subject": "Overdue email", "priority": "HIGH", "overdue_minutes": 150, "pk": 42},
        ]
        notifier.notify_personal_breach("Alice", breached)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]

        expected_label = _sla_urgency_label("HIGH", 150)
        found = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                if dt.get("topLabel") == expected_label:
                    found = True
        assert found, f"Personal breach topLabel should match _sla_urgency_label format: {expected_label}"


# ===========================================================================
# Thread Update Notification Tests (NEW -- Plan 02-01)
# ===========================================================================


@pytest.mark.django_db
class TestNotifyThreadUpdate:
    """Test notify_thread_update for thread-update Chat notifications."""

    TRACKER_URL = "https://triage.vidarbhainfotech.com"

    def _config_side_effect(self, key, default=None):
        mapping = {"tracker_url": self.TRACKER_URL}
        return mapping.get(key, default)

    def _make_email_with_thread(self, **kwargs):
        """Create mock Email with attached Thread."""
        thread_defaults = {
            "subject": "Test Thread Subject",
            "assigned_to": None,
            "gmail_thread_id": "thread_test_001",
        }
        thread_overrides = kwargs.pop("thread_kwargs", {})
        thread_defaults.update(thread_overrides)
        mock_thread = MagicMock()
        for k, v in thread_defaults.items():
            setattr(mock_thread, k, v)

        email_defaults = {
            "pk": 42,
            "from_name": "Reply Sender",
            "from_address": "reply@example.com",
            "body": "This is a reply to the previous email in this thread.",
            "to_inbox": "info@vidarbhainfotech.com",
            "thread": mock_thread,
        }
        email_defaults.update(kwargs)
        mock_email = MagicMock()
        for k, v in email_defaults.items():
            setattr(mock_email, k, v)
        return mock_email

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_sends_thread_updated_card(self, mock_config_cls, mock_post):
        """notify_thread_update sends a card with 'Thread Updated' title containing thread subject."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread()
        result = notifier.notify_thread_update(email)

        assert result is True
        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        assert "Thread Updated" in card["header"]["title"]
        assert "Test Thread" in card["header"]["title"]

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_card_includes_sender(self, mock_config_cls, mock_post):
        """notify_thread_update card includes who replied (sender name/email)."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread(from_name="Alice Dev", from_address="alice@example.com")
        notifier.notify_thread_update(email)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        # Find From widget
        found_sender = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                if "Alice Dev" in dt.get("text", "") and "alice@example.com" in dt.get("text", ""):
                    found_sender = True
        assert found_sender, "Card should include sender name and email"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_card_includes_body_preview(self, mock_config_cls, mock_post):
        """notify_thread_update card includes first ~100 chars of new message body."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread(body="Short reply body")
        notifier.notify_thread_update(email)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        found_preview = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                if "Short reply body" in dt.get("text", ""):
                    found_preview = True
        assert found_preview, "Card should include body preview"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_card_has_dashboard_button(self, mock_config_cls, mock_post):
        """notify_thread_update card includes 'Open in Dashboard' button."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread(pk=99)
        notifier.notify_thread_update(email)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        found_button = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                bl = widget.get("buttonList", {})
                for btn in bl.get("buttons", []):
                    if "Open in Dashboard" in btn.get("text", ""):
                        url = btn.get("onClick", {}).get("openLink", {}).get("url", "")
                        if "selected=99" in url:
                            found_button = True
        assert found_button, "Card should have 'Open in Dashboard' button with email pk"

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_respects_quiet_hours(self, mock_config_cls, mock_post):
        """notify_thread_update respects quiet hours."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread()

        with patch.object(notifier, "_is_quiet_hours", return_value=True):
            result = notifier.notify_thread_update(email)

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_card_distinct_from_new_thread(self, mock_config_cls, mock_post):
        """notify_thread_update card is visually distinct from new-thread triage card."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread()
        notifier.notify_thread_update(email)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        card_id = payload["cardsV2"][0]["cardId"]
        # Card ID should identify it as thread-update
        assert "thread-update" in card_id
        # Title should say "Thread Updated" not "Poll Summary"
        assert "Thread Updated" in card["header"]["title"]

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_includes_assignee_if_assigned(self, mock_config_cls, mock_post):
        """notify_thread_update includes thread assignee name if assigned."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        mock_assignee = MagicMock()
        mock_assignee.get_full_name.return_value = "Shreyas Uge"
        mock_assignee.username = "shreyas"

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread(
            thread_kwargs={"assigned_to": mock_assignee}
        )
        notifier.notify_thread_update(email)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        subtitle = card["header"]["subtitle"]
        assert "Assigned to Shreyas Uge" in subtitle

    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_reopened_thread_shows_reopened_subtitle(self, mock_config_cls, mock_post):
        """notify_thread_update for a reopened thread includes 'Reopened' in the subtitle."""
        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        email = self._make_email_with_thread(from_name="Bob")
        notifier.notify_thread_update(email, reopened=True)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]
        subtitle = card["header"]["subtitle"]
        assert "Reopened" in subtitle


    @patch("apps.emails.services.chat_notifier.httpx.post")
    @patch("apps.emails.services.chat_notifier.SystemConfig")
    def test_breach_summary_uses_urgency_label_format(self, mock_config_cls, mock_post):
        """topLabel in breach summary offender widgets matches _sla_urgency_label format."""
        from apps.emails.services.chat_notifier import _sla_urgency_label

        mock_config_cls.get.side_effect = self._config_side_effect
        mock_post.return_value = MagicMock(status_code=200)

        notifier = ChatNotifier(webhook_url="https://chat.googleapis.com/test")
        summary = {
            "total_respond_breached": 1,
            "total_ack_breached": 0,
            "top_offenders": [
                {"subject": "Urgent", "assignee_name": "Alice", "priority": "CRITICAL",
                 "overdue_str": "3h", "overdue_minutes": 180, "pk": 10},
            ],
            "per_assignee": {"Alice": [{"subject": "Urgent", "priority": "CRITICAL", "overdue_minutes": 180}]},
        }
        notifier.notify_breach_summary(summary)

        payload = mock_post.call_args.kwargs["json"]
        card = payload["cardsV2"][0]["card"]

        expected_label = _sla_urgency_label("CRITICAL", 180)
        found = False
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                dt = widget.get("decoratedText", {})
                if dt.get("topLabel") == expected_label:
                    found = True
        assert found, f"Breach summary offender topLabel should match: {expected_label}"
