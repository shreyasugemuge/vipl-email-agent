"""
Gmail Poller — Polls shared inboxes for new emails via Gmail API.

Uses a Google Workspace service account with domain-wide delegation
to impersonate the shared inbox users and read their mail.
"""

import base64
import html as html_module
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parseaddr
from typing import Optional

import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify",
]


@dataclass
class EmailMessage:
    """Parsed email data ready for AI processing."""
    thread_id: str
    message_id: str
    inbox: str                          # info@ or sales@
    sender_name: str
    sender_email: str
    subject: str
    body: str                           # Plain text body (truncated to ~4000 chars)
    timestamp: datetime
    attachment_count: int = 0
    attachment_names: list = field(default_factory=list)
    attachment_details: list = field(default_factory=list)  # [{filename, attachment_id, size, mime_type}]
    gmail_link: str = ""


class GmailPoller:
    """Polls Gmail inboxes for new unprocessed emails."""

    def __init__(self, service_account_key_path: str, processed_label: str = "Agent/Processed"):
        self.sa_key_path = service_account_key_path
        self.processed_label = processed_label
        self._services = {}  # Cache per-inbox Gmail service instances
        self._label_ids = {}  # Cache per-inbox label IDs
        self._first_poll_done = False  # Track if first poll has completed
        # Record start time — subsequent polls only look at emails after this
        self._start_epoch = int(datetime.now().timestamp())
        logger.info("Gmail poller initialized (first poll will fetch latest 5 per inbox)")

    def _get_service(self, inbox_email: str):
        """Get or create a Gmail API service impersonating the given inbox."""
        if inbox_email not in self._services:
            credentials = service_account.Credentials.from_service_account_file(
                self.sa_key_path,
                scopes=SCOPES,
                subject=inbox_email,
            )
            self._services[inbox_email] = build("gmail", "v1", credentials=credentials)
            logger.info(f"Created Gmail service for {inbox_email}")
        return self._services[inbox_email]

    def _ensure_label(self, service, inbox_email: str) -> Optional[str]:
        """Ensure the 'Agent/Processed' label exists; return its ID."""
        try:
            results = service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            for label in labels:
                if label["name"] == self.processed_label:
                    return label["id"]

            # Create the label if it doesn't exist
            label_body = {
                "name": self.processed_label,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }
            created = service.users().labels().create(userId="me", body=label_body).execute()
            logger.info(f"Created label '{self.processed_label}' for {inbox_email}")
            return created["id"]
        except Exception as e:
            logger.error(f"Failed to ensure label for {inbox_email}: {e}")
            return None

    def _mark_as_processed(self, service, message_id: str, label_id: str):
        """Apply the processed label to a message."""
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id]},
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to label message {message_id}: {e}")

    def _parse_message(self, service, msg_data: dict, inbox_email: str) -> Optional[EmailMessage]:
        """Parse a Gmail API message response into an EmailMessage."""
        try:
            headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}

            # Parse sender
            from_raw = headers.get("from", "")
            sender_name, sender_email = parseaddr(from_raw)
            if not sender_name:
                sender_name = sender_email.split("@")[0] if sender_email else "Unknown"

            # Parse subject
            subject = headers.get("subject", "(no subject)")

            # Parse timestamp (timezone-aware UTC — converted to IST in sheet_logger)
            internal_date_ms = int(msg_data.get("internalDate", 0))
            timestamp = datetime.fromtimestamp(internal_date_ms / 1000, tz=pytz.UTC)

            # Extract plain text body (truncate early — AI processor truncates further to 1500)
            body = self._extract_body(msg_data.get("payload", {}))
            if len(body) > 2000:
                body = body[:2000] + "\n[...truncated...]"

            # Count attachments
            attachments = []
            attachment_details = []
            self._find_attachments(msg_data.get("payload", {}), attachments, attachment_details)

            # Build Gmail deep link
            thread_id = msg_data.get("threadId", "")
            gmail_link = f"https://mail.google.com/mail/u/?authuser={inbox_email}#inbox/{thread_id}"

            return EmailMessage(
                thread_id=thread_id,
                message_id=msg_data["id"],
                inbox=inbox_email,
                sender_name=sender_name,
                sender_email=sender_email,
                subject=subject,
                body=body,
                timestamp=timestamp,
                attachment_count=len(attachments),
                attachment_names=attachments,
                attachment_details=attachment_details,
                gmail_link=gmail_link,
            )
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None

    def _extract_body(self, payload: dict) -> str:
        """Recursively extract plain text body from a Gmail message payload."""
        mime_type = payload.get("mimeType", "")

        if mime_type == "text/plain" and "body" in payload:
            data = payload["body"].get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                result = self._extract_body(part)
                if result:
                    return result

        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    return self._strip_html(html)

        for part in parts:
            if part.get("mimeType", "").startswith("multipart/"):
                result = self._extract_body(part)
                if result:
                    return result

        return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        """Strip HTML tags, scripts, styles, and decode entities."""
        text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html_module.unescape(text)  # Decode &nbsp; &amp; etc.
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _find_attachments(self, payload: dict, names: list, details: list):
        """Recursively find attachment filenames and metadata."""
        filename = payload.get("filename", "")
        if filename:
            names.append(filename)
            body = payload.get("body", {})
            details.append({
                "filename": filename,
                "attachment_id": body.get("attachmentId", ""),
                "size": body.get("size", 0),
                "mime_type": payload.get("mimeType", ""),
            })
        for part in payload.get("parts", []):
            self._find_attachments(part, names, details)

    def download_attachment(self, inbox_email: str, message_id: str, attachment_id: str) -> Optional[bytes]:
        """Download an attachment by its ID. Returns raw bytes or None on failure."""
        try:
            service = self._get_service(inbox_email)
            result = service.users().messages().attachments().get(
                userId="me", messageId=message_id, id=attachment_id,
            ).execute()
            data = result.get("data", "")
            if data:
                return base64.urlsafe_b64decode(data)
        except Exception as e:
            logger.error(f"Failed to download attachment {attachment_id}: {e}")
        return None

    def fetch_thread_message(self, inbox_email: str, thread_id: str) -> Optional[EmailMessage]:
        """Fetch the first message from a Gmail thread by thread ID.
        Used for dead letter retry — reconstructing an EmailMessage from a thread ID."""
        try:
            service = self._get_service(inbox_email)
            thread = service.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()
            messages = thread.get("messages", [])
            if messages:
                return self._parse_message(service, messages[0], inbox_email)
        except Exception as e:
            logger.error(f"Could not fetch thread {thread_id}: {e}")
        return None

    def poll(self, inbox_email: str) -> list[EmailMessage]:
        """
        Poll a single inbox for new unprocessed emails.

        First poll: fetches the latest 5 emails (regardless of label).
        Subsequent polls: only picks up new emails since agent started + unlabeled.

        Dedup is NOT done here — main.py checks the Sheet thread cache.
        This method just fetches and labels.
        """
        emails = []
        try:
            service = self._get_service(inbox_email)
            label_id = self._ensure_label(service, inbox_email)
            if label_id:
                self._label_ids[inbox_email] = label_id

            if not self._first_poll_done:
                query = "in:inbox"
                max_results = 5
                logger.info(f"First poll for {inbox_email}: fetching latest {max_results} emails")
            else:
                query = f"in:inbox after:{self._start_epoch} -label:{self.processed_label}"
                max_results = 10
                logger.info(f"Incremental poll for {inbox_email}: new emails after epoch {self._start_epoch}")

            results = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results,
            ).execute()

            messages = results.get("messages", [])
            if not messages:
                logger.debug(f"No new emails in {inbox_email}")
                return emails

            logger.info(f"Found {len(messages)} email(s) in {inbox_email}")

            for msg_ref in messages:
                # Fetch full message
                msg_data = service.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="full",
                ).execute()

                email_msg = self._parse_message(service, msg_data, inbox_email)
                if email_msg:
                    emails.append(email_msg)

        except Exception as e:
            logger.error(f"Gmail poll failed for {inbox_email}: {e}")
            raise

        return emails

    def poll_all(self, inboxes: list[str]) -> list[EmailMessage]:
        """Poll all configured inboxes and return combined results."""
        all_emails = []
        for inbox in inboxes:
            try:
                emails = self.poll(inbox)
                all_emails.extend(emails)
            except Exception as e:
                logger.error(f"Failed to poll {inbox}: {e}")
                continue

        # After first successful poll of all inboxes, switch to ongoing mode
        if not self._first_poll_done:
            self._first_poll_done = True
            logger.info("First poll complete — switching to incremental mode")

        return all_emails

    def mark_processed(self, email_msg):
        """Apply the 'Agent/Processed' label to an email AFTER successful Sheet log.
        Called by main.py to prevent email loss — label is only applied once
        the email is safely persisted to Google Sheets."""
        label_id = self._label_ids.get(email_msg.inbox)
        if not label_id:
            logger.warning(f"No label ID cached for {email_msg.inbox}, cannot mark processed")
            return
        service = self._get_service(email_msg.inbox)
        self._mark_as_processed(service, email_msg.message_id, label_id)
