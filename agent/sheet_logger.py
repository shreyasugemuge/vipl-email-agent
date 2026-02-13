"""
Sheet Logger — Logs email tickets to Google Sheets and reads SLA/team config.

The Google Sheet is the single source of truth for ticket management.
This module handles all read/write operations to the Sheet.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetLogger:
    """Manages all Google Sheets interactions for the email agent."""

    def __init__(self, service_account_key_path: str, spreadsheet_id: str, config: dict):
        self.spreadsheet_id = spreadsheet_id
        self.config = config

        # Tab names from config
        self.email_log_tab = config.get("email_log_tab", "Email Log")
        self.sla_config_tab = config.get("sla_config_tab", "SLA Config")
        self.team_tab = config.get("team_tab", "Team")
        self.change_log_tab = config.get("change_log_tab", "Change Log")

        credentials = service_account.Credentials.from_service_account_file(
            service_account_key_path,
            scopes=SCOPES,
        )
        self.service = build("sheets", "v4", credentials=credentials)
        self.sheets = self.service.spreadsheets()

        # Cache for ticket counter
        self._ticket_counts = {"INF": 0, "SAL": 0, "SUP": 0}
        self._load_ticket_counts()

    # ----------------------------------------------------------------
    # Ticket Number Generation
    # ----------------------------------------------------------------

    def _load_ticket_counts(self):
        """Load current ticket counts from the Sheet to continue numbering."""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!A:A",
            ).execute()
            values = result.get("values", [])

            for row in values:
                if row and len(row) > 0:
                    ticket = row[0]
                    if ticket.startswith("INF-"):
                        num = int(ticket.split("-")[1])
                        self._ticket_counts["INF"] = max(self._ticket_counts["INF"], num)
                    elif ticket.startswith("SAL-"):
                        num = int(ticket.split("-")[1])
                        self._ticket_counts["SAL"] = max(self._ticket_counts["SAL"], num)
                    elif ticket.startswith("SUP-"):
                        num = int(ticket.split("-")[1])
                        self._ticket_counts["SUP"] = max(self._ticket_counts["SUP"], num)

            logger.info(f"Ticket counters: INF={self._ticket_counts['INF']}, SAL={self._ticket_counts['SAL']}, SUP={self._ticket_counts['SUP']}")
        except Exception as e:
            logger.warning(f"Could not load ticket counts (new sheet?): {e}")

    def _next_ticket_number(self, inbox: str) -> str:
        """Generate the next ticket number based on inbox."""
        if "sales@" in inbox:
            prefix = "SAL"
        elif "support@" in inbox:
            prefix = "SUP"
        else:
            prefix = "INF"
        self._ticket_counts[prefix] += 1
        return f"{prefix}-{self._ticket_counts[prefix]:04d}"

    # ----------------------------------------------------------------
    # Email Logging
    # ----------------------------------------------------------------

    def log_email(self, email, triage_result, sla_hours: float) -> str:
        """
        Log a processed email as a new row in the Email Log tab.

        Returns the generated ticket number.
        """
        ticket_number = self._next_ticket_number(email.inbox)
        timestamp_str = email.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        sla_deadline = email.timestamp + timedelta(hours=sla_hours)
        sla_deadline_str = sla_deadline.strftime("%Y-%m-%d %H:%M:%S")

        # SLA Status formula (column M, row is dynamic)
        # We'll insert the formula after appending to get the correct row number

        attachments_str = f"{email.attachment_count} file(s)"
        if email.attachment_names:
            attachments_str += ": " + ", ".join(email.attachment_names[:5])

        tags_str = ", ".join(triage_result.tags) if triage_result.tags else ""

        row = [
            ticket_number,                      # A: Ticket #
            timestamp_str,                      # B: Timestamp
            email.inbox,                        # C: Inbox
            email.sender_name,                  # D: From (Name)
            email.sender_email,                 # E: From (Email)
            email.subject,                      # F: Subject
            triage_result.summary,              # G: AI Summary
            triage_result.category,             # H: Category
            triage_result.priority,             # I: Priority
            triage_result.suggested_assignee,   # J: Assigned To
            "New",                              # K: Status
            sla_deadline_str,                   # L: SLA Deadline
            "",                                 # M: SLA Status (formula added separately)
            triage_result.draft_reply,          # N: Draft Reply
            "",                                 # O: First Response At
            "",                                 # P: Resolved At
            "",                                 # Q: Resolution Time (formula)
            "",                                 # R: Notes
            tags_str,                           # S: Tags
            email.thread_id,                    # T: Gmail Thread ID
            attachments_str,                    # U: Attachments
        ]

        try:
            # Append the row
            body = {"values": [row]}
            result = self.sheets.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!A:U",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()

            # Determine the row number that was just written
            updated_range = result.get("updates", {}).get("updatedRange", "")
            row_num = self._extract_row_number(updated_range)

            if row_num:
                # Add SLA Status formula (column M)
                sla_formula = (
                    f'=IF(K{row_num}="Closed","OK",'
                    f'IF(K{row_num}="Spam","N/A",'
                    f'IF(NOW()>L{row_num},"BREACHED","OK")))'
                )
                # Add Resolution Time formula (column Q)
                res_formula = (
                    f'=IF(P{row_num}<>"",ROUND((P{row_num}-B{row_num})*24,1),"")'
                )
                self.sheets.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{self.email_log_tab}'!M{row_num}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[sla_formula]]},
                ).execute()
                self.sheets.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{self.email_log_tab}'!Q{row_num}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[res_formula]]},
                ).execute()

            logger.info(f"Logged ticket {ticket_number}: {email.subject[:50]}")
            return ticket_number

        except Exception as e:
            logger.error(f"Failed to log email to Sheet: {e}")
            raise

    @staticmethod
    def _extract_row_number(updated_range: str) -> Optional[int]:
        """Extract row number from a Sheets API updatedRange string."""
        # Format: 'Email Log'!A42:U42
        import re
        match = re.search(r"!A(\d+)", updated_range)
        if match:
            return int(match.group(1))
        return None

    # ----------------------------------------------------------------
    # Reading Data
    # ----------------------------------------------------------------

    def get_open_tickets(self) -> list[dict]:
        """Read all open (non-closed, non-spam) tickets from the Email Log."""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!A:U",
            ).execute()
            rows = result.get("values", [])
            if len(rows) < 2:
                return []  # Only header row or empty

            header = rows[0]
            tickets = []
            for row in rows[1:]:
                # Pad row to header length
                padded = row + [""] * (len(header) - len(row))
                ticket = dict(zip(header, padded))

                status = ticket.get("Status", "").strip()
                if status not in ("Closed", "Spam", ""):
                    tickets.append(ticket)

            return tickets
        except Exception as e:
            logger.error(f"Failed to read open tickets: {e}")
            return []

    def get_all_tickets_today(self) -> list[dict]:
        """Read all tickets from today for EOD reporting."""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!A:U",
            ).execute()
            rows = result.get("values", [])
            if len(rows) < 2:
                return []

            header = rows[0]
            today_str = datetime.now().strftime("%Y-%m-%d")
            tickets = []
            for row in rows[1:]:
                padded = row + [""] * (len(header) - len(row))
                ticket = dict(zip(header, padded))
                timestamp = ticket.get("Timestamp", "")
                if timestamp.startswith(today_str):
                    tickets.append(ticket)

            return tickets
        except Exception as e:
            logger.error(f"Failed to read today's tickets: {e}")
            return []

    def get_all_tickets(self) -> list[dict]:
        """Read ALL tickets from the Email Log (for dashboard stats)."""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!A:U",
            ).execute()
            rows = result.get("values", [])
            if len(rows) < 2:
                return []

            header = rows[0]
            tickets = []
            for row in rows[1:]:
                padded = row + [""] * (len(header) - len(row))
                tickets.append(dict(zip(header, padded)))
            return tickets
        except Exception as e:
            logger.error(f"Failed to read all tickets: {e}")
            return []

    def get_sla_config(self) -> dict:
        """Read SLA configuration from the SLA Config tab."""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.sla_config_tab}'!A:C",
            ).execute()
            rows = result.get("values", [])
            config = {}
            for row in rows[1:]:  # Skip header
                if len(row) >= 2:
                    category = row[0].strip()
                    try:
                        hours = float(row[1])
                    except ValueError:
                        hours = 24
                    escalation_email = row[2].strip() if len(row) > 2 else ""
                    config[category] = {"hours": hours, "escalation_email": escalation_email}
            return config
        except Exception as e:
            logger.warning(f"Could not read SLA config from Sheet: {e}")
            return {}

    def get_team_members(self) -> list[dict]:
        """Read team members from the Team tab."""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.team_tab}'!A:D",
            ).execute()
            rows = result.get("values", [])
            members = []
            for row in rows[1:]:  # Skip header
                if len(row) >= 2:
                    members.append({
                        "name": row[0].strip(),
                        "email": row[1].strip() if len(row) > 1 else "",
                        "role": row[2].strip() if len(row) > 2 else "",
                        "active": row[3].strip().upper() == "YES" if len(row) > 3 else True,
                    })
            return members
        except Exception as e:
            logger.warning(f"Could not read team members: {e}")
            return []

    def is_thread_logged(self, thread_id: str) -> bool:
        """Check if a Gmail thread ID already exists in the Sheet (deduplication)."""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!T:T",
            ).execute()
            values = result.get("values", [])
            for row in values:
                if row and row[0] == thread_id:
                    return True
            return False
        except Exception as e:
            logger.warning(f"Could not check thread dedup: {e}")
            return False

    # ----------------------------------------------------------------
    # Sheet Initialization
    # ----------------------------------------------------------------

    def ensure_headers(self):
        """Ensure the Email Log tab has the correct header row."""
        headers = [
            "Ticket #", "Timestamp", "Inbox", "From (Name)", "From (Email)",
            "Subject", "AI Summary", "Category", "Priority", "Assigned To",
            "Status", "SLA Deadline", "SLA Status", "Draft Reply",
            "First Response At", "Resolved At", "Resolution Time", "Notes",
            "Tags", "Gmail Thread ID", "Attachments",
        ]
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!A1:A1",
            ).execute()
            existing = result.get("values", [[]])
            first_cell = existing[0][0] if existing and existing[0] else ""

            if first_cell != "Ticket #":
                if first_cell:
                    # Row 1 has data but it's NOT the header — insert a row above
                    # by shifting everything down first
                    logger.warning(f"Row 1 contains '{first_cell}' instead of headers. Inserting header row.")
                    # Use batchUpdate to insert a row at the top
                    sheet_id = self._get_sheet_id(self.email_log_tab)
                    if sheet_id is not None:
                        self.sheets.batchUpdate(
                            spreadsheetId=self.spreadsheet_id,
                            body={"requests": [{
                                "insertDimension": {
                                    "range": {
                                        "sheetId": sheet_id,
                                        "dimension": "ROWS",
                                        "startIndex": 0,
                                        "endIndex": 1,
                                    },
                                    "inheritFromBefore": False,
                                }
                            }]},
                        ).execute()

                # Write headers to row 1
                self.sheets.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{self.email_log_tab}'!A1:U1",
                    valueInputOption="RAW",
                    body={"values": [headers]},
                ).execute()
                logger.info("Wrote header row to Email Log tab")
            else:
                logger.info("Email Log headers already present")
        except Exception as e:
            logger.error(f"Failed to ensure headers: {e}")

    def _get_sheet_id(self, tab_name: str):
        """Get the numeric sheet ID for a tab name."""
        try:
            spreadsheet = self.sheets.get(spreadsheetId=self.spreadsheet_id).execute()
            for sheet in spreadsheet.get("sheets", []):
                if sheet["properties"]["title"] == tab_name:
                    return sheet["properties"]["sheetId"]
        except Exception:
            pass
        return None
