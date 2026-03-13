"""Google Sheets read-only sync mirror.

Syncs completed emails to a "v2 Mirror" tab in Google Sheets for quick
"who has what" lookups. Fire-and-forget: Sheets API errors are logged
but never block the pipeline or crash the scheduler.

Scheduled to run every 5 minutes via APScheduler.
"""

import logging
from datetime import datetime, timezone as dt_tz

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TAB_NAME = "v2 Mirror"

COLUMNS = [
    "Date",
    "From",
    "Subject",
    "Inbox",
    "Category",
    "Priority",
    "Assignee",
    "Status",
    "SLA Deadline",
    "Message ID",
]


class SheetsSyncService:
    """Syncs Email model rows to a Google Sheets 'v2 Mirror' tab.

    - Appends new emails as new rows
    - Updates existing rows when status/assignee changes
    - Auto-creates the tab with header row on first sync
    - Never raises -- all errors logged as warnings
    """

    def __init__(self, service_account_key_path: str, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self._initialized = False
        self._row_index: dict[str, int] = {}  # message_id -> row number

        credentials = service_account.Credentials.from_service_account_file(
            service_account_key_path,
            scopes=SCOPES,
        )
        self.service = build("sheets", "v4", credentials=credentials)

    def sync_changed_emails(self):
        """Main entry point: sync all emails changed since last sync.

        Reads sheets_last_synced from SystemConfig, queries changed emails,
        appends new rows, updates existing rows.
        """
        try:
            self._sync_changed_emails_inner()
        except Exception as e:
            logger.warning(f"Sheets sync failed (fire-and-forget): {e}")

    def _sync_changed_emails_inner(self):
        """Inner sync logic -- may raise on Sheets API errors."""
        from django.utils import timezone as tz

        from apps.core.models import SystemConfig
        from apps.emails.models import Email

        # Read last sync timestamp
        last_synced_str = SystemConfig.get("sheets_last_synced", "")
        if last_synced_str:
            try:
                last_synced = datetime.fromisoformat(last_synced_str)
            except (ValueError, TypeError):
                last_synced = datetime.min.replace(tzinfo=dt_tz.utc)
        else:
            last_synced = datetime.min.replace(tzinfo=dt_tz.utc)

        # Query changed emails since last sync
        changed_emails = list(
            Email.objects.filter(
                processing_status="completed",
                is_spam=False,
                updated_at__gt=last_synced,
            ).select_related("assigned_to")
        )

        if not changed_emails:
            return

        # Ensure tab exists on first sync
        if not self._initialized:
            self._ensure_tab_exists()

        # Build row index if empty
        if not self._row_index:
            self._build_row_index()

        # Separate into new and existing
        new_emails = []
        existing_updates = {}  # row_number -> row_data

        for email in changed_emails:
            row = self._email_to_row(email)
            if email.message_id in self._row_index:
                row_num = self._row_index[email.message_id]
                existing_updates[row_num] = row
            else:
                new_emails.append(row)

        # Append new rows
        if new_emails:
            self._append_rows(new_emails)
            # Update row index for newly appended rows
            # They start after the current last row
            current_max = max(self._row_index.values()) if self._row_index else 1  # 1 = header
            for i, row in enumerate(new_emails):
                message_id = row[9]  # Last column = Message ID
                self._row_index[message_id] = current_max + i + 1

        # Update existing rows
        if existing_updates:
            self._batch_update_rows(existing_updates)

        # Record sync timestamp
        now_iso = tz.now().isoformat()
        SystemConfig.objects.update_or_create(
            key="sheets_last_synced",
            defaults={
                "value": now_iso,
                "value_type": "str",
                "description": "Last successful Sheets sync timestamp",
                "category": "sync",
            },
        )

    def _ensure_tab_exists(self):
        """Create 'v2 Mirror' tab with header row if it doesn't exist."""
        spreadsheets = self.service.spreadsheets()

        # List existing tabs
        result = spreadsheets.get(
            spreadsheetId=self.spreadsheet_id,
            fields="sheets.properties.title",
        ).execute()

        existing_tabs = [
            s["properties"]["title"] for s in result.get("sheets", [])
        ]

        if TAB_NAME not in existing_tabs:
            # Create tab
            spreadsheets.batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {"title": TAB_NAME}
                            }
                        }
                    ]
                },
            ).execute()

            # Write header row
            spreadsheets.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{TAB_NAME}'!A1",
                valueInputOption="RAW",
                body={"values": [COLUMNS]},
            ).execute()

        self._initialized = True

    def _build_row_index(self):
        """Read Message ID column (J) and build {message_id: row_number} cache."""
        self._row_index = {}

        result = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{TAB_NAME}'!J2:J",  # Skip header row
            )
            .execute()
        )

        values = result.get("values", [])
        for i, row in enumerate(values):
            if row:  # non-empty row
                self._row_index[row[0]] = i + 2  # +2 because row 1 is header, 0-indexed

    def _email_to_row(self, email) -> list:
        """Format an Email model instance as a Sheets row (10 columns)."""
        # Format received_at
        date_str = ""
        if email.received_at:
            date_str = email.received_at.strftime("%Y-%m-%d %H:%M")

        # Format assignee
        assignee = ""
        if email.assigned_to:
            full_name = email.assigned_to.get_full_name()
            assignee = full_name if full_name.strip() else email.assigned_to.username

        # Format SLA deadline
        sla_str = ""
        if email.sla_respond_deadline:
            sla_str = email.sla_respond_deadline.strftime("%Y-%m-%d %H:%M")

        return [
            date_str,
            email.from_address,
            email.subject,
            email.to_inbox,
            email.category,
            email.priority,
            assignee,
            email.status,
            sla_str,
            email.message_id,
        ]

    def _append_rows(self, rows: list[list]):
        """Append rows to the Sheet via values().append()."""
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{TAB_NAME}'!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()

    def _batch_update_rows(self, updates: dict[int, list]):
        """Update existing rows via values().batchUpdate()."""
        data = []
        for row_num, row_data in updates.items():
            data.append(
                {
                    "range": f"'{TAB_NAME}'!A{row_num}:J{row_num}",
                    "values": [row_data],
                }
            )

        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={
                "valueInputOption": "RAW",
                "data": data,
            },
        ).execute()
