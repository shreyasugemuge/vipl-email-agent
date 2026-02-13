"""
Sheet Logger — Logs email tickets to Google Sheets and reads SLA/team config.

The Google Sheet is the single source of truth for ticket management.
This module handles all read/write operations to the Sheet.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

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
        self.agent_config_tab = config.get("agent_config_tab", "Agent Config")

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

        Uses RAW valueInputOption to prevent Sheets from mangling
        timestamps into serial numbers.
        """
        ticket_number = self._next_ticket_number(email.inbox)

        # Format timestamps as plain text strings (RAW prevents serial number conversion)
        ist_timestamp = email.timestamp.astimezone(IST) if email.timestamp.tzinfo else IST.localize(email.timestamp)
        timestamp_str = ist_timestamp.strftime("%d %b %Y, %I:%M %p")

        sla_deadline = ist_timestamp + timedelta(hours=sla_hours)
        sla_deadline_str = sla_deadline.strftime("%d %b %Y, %I:%M %p")

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
            # Append the row using RAW to keep timestamps as plain text
            body = {"values": [row]}
            result = self.sheets.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{self.email_log_tab}'!A:U",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()

            # Determine the row number that was just written
            updated_range = result.get("updates", {}).get("updatedRange", "")
            row_num = self._extract_row_number(updated_range)

            if row_num:
                # SLA Status + Resolution Time are set as initial static values.
                # The SLA monitor (server-side) handles breach detection every 15 min.
                # Formulas can't compare NOW() to text timestamps, so we use static defaults.
                self.sheets.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{self.email_log_tab}'!M{row_num}",
                    valueInputOption="RAW",
                    body={"values": [["OK"]]},
                ).execute()

            logger.info(f"Logged ticket {ticket_number}: {email.subject[:50]}")
            return ticket_number

        except Exception as e:
            logger.error(f"Failed to log email to Sheet: {e}")
            raise

    @staticmethod
    def _extract_row_number(updated_range: str) -> Optional[int]:
        """Extract row number from a Sheets API updatedRange string."""
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
                return []

            header = rows[0]
            tickets = []
            for row in rows[1:]:
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
            today_str = datetime.now(IST).strftime("%d %b %Y")
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
        """Read ALL tickets from the Email Log."""
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
            for row in rows[1:]:
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
            for row in rows[1:]:
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
        """Check if a Gmail thread ID already exists in the Sheet."""
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

    def _get_sheet_id(self, tab_name: str) -> Optional[int]:
        """Get the numeric sheet ID for a tab name."""
        try:
            spreadsheet = self.sheets.get(spreadsheetId=self.spreadsheet_id).execute()
            for sheet in spreadsheet.get("sheets", []):
                if sheet["properties"]["title"] == tab_name:
                    return sheet["properties"]["sheetId"]
        except Exception:
            pass
        return None

    def _create_tab_if_missing(self, tab_name: str) -> int:
        """Create a tab if it doesn't exist, return its sheet ID."""
        sheet_id = self._get_sheet_id(tab_name)
        if sheet_id is not None:
            return sheet_id

        result = self.sheets.batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={"requests": [{
                "addSheet": {"properties": {"title": tab_name}}
            }]}
        ).execute()
        new_sheet_id = result["replies"][0]["addSheet"]["properties"]["sheetId"]
        logger.info(f"Created tab: {tab_name} (sheetId={new_sheet_id})")
        return new_sheet_id

    # ----------------------------------------------------------------
    # Email Log Column Formatting — subtle header, no ugly blue
    # ----------------------------------------------------------------

    def format_email_log_columns(self):
        """Style the Email Log header row — dark text on light gray, bold, frozen."""
        try:
            sheet_id = self._get_sheet_id(self.email_log_tab)
            if sheet_id is None:
                return

            requests = [
                # Light gray header with bold dark text
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {"userEnteredFormat": {
                            "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93},
                            "textFormat": {"bold": True, "fontSize": 10,
                                           "foregroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2}},
                        }},
                        "fields": "userEnteredFormat(backgroundColor,textFormat)",
                    }
                },
                # Freeze header row
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                # Force timestamp columns (B and L) to plain text format
                # so Sheets never auto-converts them to date serials
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1000,
                                  "startColumnIndex": 1, "endColumnIndex": 2},
                        "cell": {"userEnteredFormat": {"numberFormat": {"type": "TEXT"}}},
                        "fields": "userEnteredFormat.numberFormat",
                    }
                },
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1000,
                                  "startColumnIndex": 11, "endColumnIndex": 12},
                        "cell": {"userEnteredFormat": {"numberFormat": {"type": "TEXT"}}},
                        "fields": "userEnteredFormat.numberFormat",
                    }
                },
            ]

            self.sheets.batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": requests},
            ).execute()
            logger.info("Formatted Email Log columns")
        except Exception as e:
            logger.warning(f"Could not format Email Log columns: {e}")

    # ----------------------------------------------------------------
    # Agent Config Tab — Google Sheet as Config UI
    # ----------------------------------------------------------------

    # Row layout:
    #  1  Title (merged)
    #  2  Subtitle (merged)
    #  3  blank
    #  4  Setting | Current Value | Instructions   (header)
    #  5  Poll Interval ...
    #  6  SLA Cooldown ...
    #  7  EOD Hour ...
    #  8  EOD Minute ...
    #  9  Admin Email ...
    # 10  EOD Recipients ...
    # 11  Monitored Inboxes ...
    # 12  Claude Model ...
    # 13  Last Updated ...
    # 14  blank
    # 15  Agent Status (merged, green)
    # 16  Label | Value   (header)
    # 17  Last Polled | <timestamp>
    # 18  Emails This Cycle | <count>
    # 19  blank
    # 20  Recent Errors / Highlights (merged, orange)
    # 21  Time | Message  (header)
    # 22-26  5 log rows

    CONFIG_FIELDS = [
        ("Poll Interval (seconds)", lambda c: str(c.get("gmail", {}).get("poll_interval_seconds", 300)),
         "How often to check for new emails. Minimum 60, maximum 3600."),
        ("SLA Alert Cooldown (hours)", lambda c: str(c.get("sla", {}).get("breach_alert_cooldown_hours", 4)),
         "Hours between repeated SLA breach alerts for same ticket. Range: 1-48."),
        ("EOD Report Hour (IST)", lambda c: str(c.get("eod", {}).get("send_hour", 19)),
         "Hour (0-23) in IST when the daily summary email is sent."),
        ("EOD Report Minute", lambda c: str(c.get("eod", {}).get("send_minute", 0)),
         "Minute (0-59) for the EOD report. Usually 0."),
        ("Admin Email", lambda c: c.get("admin", {}).get("email", ""),
         "Primary admin email. Receives escalations and fallback EOD reports."),
        ("EOD Recipients", lambda c: ", ".join(c.get("eod", {}).get("recipients", [])),
         "Comma-separated emails that receive the daily EOD summary."),
        ("Monitored Inboxes", lambda c: ", ".join(c.get("gmail", {}).get("inboxes", [])),
         "Comma-separated inbox addresses. Changes here need redeployment."),
        ("Claude Model", lambda c: c.get("claude", {}).get("model", "claude-sonnet-4-5-20250929"),
         "AI model for triage. Do not change unless instructed by admin."),
        ("Last Updated", lambda c: datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST"),
         "Auto-updated timestamp of last config write."),
    ]

    # 1-indexed row numbers for the status and log sections
    STATUS_HEADER_ROW = 15
    STATUS_DATA_ROW = 17     # Last Polled row
    LOG_HEADER_ROW = 20
    LOG_COL_HEADER_ROW = 21
    LOG_DATA_START_ROW = 22

    def ensure_agent_config_tab(self, config: dict):
        """Create or update the Agent Config tab with config, status, and error log."""
        tab_name = self.agent_config_tab
        sheet_id = self._create_tab_if_missing(tab_name)

        rows = [
            ["VIPL Email Agent — Configuration", "", ""],                    # 1
            ["Edit values in column B. Agent reads these on startup.", "", ""],  # 2
            ["", "", ""],                                                    # 3
            ["Setting", "Current Value", "Instructions"],                   # 4
        ]

        for field_name, default_fn, instruction in self.CONFIG_FIELDS:
            rows.append([field_name, default_fn(config), instruction])
        # rows now has 4 + 9 = 13 entries

        rows.append(["", "", ""])                                           # 14
        rows.append(["Agent Status", "", ""])                               # 15
        rows.append(["", "Value", ""])                                      # 16 header
        rows.append(["Last Polled", "Not yet", ""])                         # 17
        rows.append(["Emails This Cycle", "0", ""])                         # 18
        rows.append(["", "", ""])                                           # 19
        rows.append(["Recent Errors & Highlights", "", ""])                 # 20
        rows.append(["Time", "Message", ""])                                # 21
        for _ in range(5):
            rows.append(["—", "Waiting for first poll...", ""])             # 22-26

        self.sheets.values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"'{tab_name}'!A1:C{len(rows)}",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()

        self._format_agent_config_tab(sheet_id, len(self.CONFIG_FIELDS))
        logger.info("Agent Config tab ready")

    def _format_agent_config_tab(self, sheet_id: int, num_fields: int):
        """Apply colors, merges, column widths, and data validation."""
        BLUE = {"red": 0.10, "green": 0.27, "blue": 0.53}
        BLUE_LIGHT = {"red": 0.85, "green": 0.91, "blue": 0.97}
        WHITE = {"red": 1, "green": 1, "blue": 1}
        GRAY_LIGHT = {"red": 0.95, "green": 0.95, "blue": 0.95}
        GREEN_DARK = {"red": 0.06, "green": 0.40, "blue": 0.27}
        GREEN_LIGHT = {"red": 0.85, "green": 0.95, "blue": 0.88}
        ORANGE_DARK = {"red": 0.80, "green": 0.40, "blue": 0.0}
        ORANGE_LIGHT = {"red": 1.0, "green": 0.93, "blue": 0.80}

        requests = [
            # Column widths
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 240}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2}, "properties": {"pixelSize": 360}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 3}, "properties": {"pixelSize": 420}, "fields": "pixelSize"}},

            # Row 1: Title — dark blue, white bold, merged
            {"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 3}, "mergeType": "MERGE_ALL"}},
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": BLUE, "textFormat": {"bold": True, "fontSize": 14, "foregroundColor": WHITE}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"}},
            {"updateDimensionProperties": {"range": {"sheetId": sheet_id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 44}, "fields": "pixelSize"}},

            # Row 2: Subtitle — light blue, italic, merged
            {"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 0, "endColumnIndex": 3}, "mergeType": "MERGE_ALL"}},
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2}, "cell": {"userEnteredFormat": {"backgroundColor": BLUE_LIGHT, "textFormat": {"italic": True, "fontSize": 10, "foregroundColor": BLUE}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},

            # Row 4: Config header — dark blue, white bold
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 3, "endRowIndex": 4}, "cell": {"userEnteredFormat": {"backgroundColor": BLUE, "textFormat": {"bold": True, "foregroundColor": WHITE}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},

            # Config value cells (col B) — light blue bg with underline
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 4 + num_fields, "startColumnIndex": 1, "endColumnIndex": 2}, "cell": {"userEnteredFormat": {"backgroundColor": BLUE_LIGHT, "textFormat": {"bold": True}, "borders": {"bottom": {"style": "SOLID", "color": BLUE}}}}, "fields": "userEnteredFormat(backgroundColor,textFormat,borders)"}},

            # Config setting names (col A) — light gray, bold
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 4 + num_fields, "startColumnIndex": 0, "endColumnIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": GRAY_LIGHT, "textFormat": {"bold": True}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},

            # Instructions (col C) — italic gray, wrap
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 4 + num_fields, "startColumnIndex": 2, "endColumnIndex": 3}, "cell": {"userEnteredFormat": {"textFormat": {"italic": True, "foregroundColor": {"red": 0.37, "green": 0.39, "blue": 0.40}}, "wrapStrategy": "WRAP"}}, "fields": "userEnteredFormat(textFormat,wrapStrategy)"}},

            # Row 15: Agent Status header — green, merged
            {"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 14, "endRowIndex": 15, "startColumnIndex": 0, "endColumnIndex": 3}, "mergeType": "MERGE_ALL"}},
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 14, "endRowIndex": 15}, "cell": {"userEnteredFormat": {"backgroundColor": GREEN_DARK, "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": WHITE}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},

            # Row 16: Status column header — light green
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 15, "endRowIndex": 16}, "cell": {"userEnteredFormat": {"backgroundColor": GREEN_LIGHT, "textFormat": {"bold": True, "foregroundColor": GREEN_DARK}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},

            # Rows 17-18: Status data — light bg
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 16, "endRowIndex": 18, "startColumnIndex": 0, "endColumnIndex": 1}, "cell": {"userEnteredFormat": {"backgroundColor": GRAY_LIGHT, "textFormat": {"bold": True}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 16, "endRowIndex": 18, "startColumnIndex": 1, "endColumnIndex": 2}, "cell": {"userEnteredFormat": {"backgroundColor": GREEN_LIGHT, "textFormat": {"bold": True}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},

            # Row 20: Error log header — orange, merged
            {"mergeCells": {"range": {"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": 20, "startColumnIndex": 0, "endColumnIndex": 3}, "mergeType": "MERGE_ALL"}},
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 19, "endRowIndex": 20}, "cell": {"userEnteredFormat": {"backgroundColor": ORANGE_DARK, "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": WHITE}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},

            # Row 21: Error log column headers — light orange
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 20, "endRowIndex": 21}, "cell": {"userEnteredFormat": {"backgroundColor": ORANGE_LIGHT, "textFormat": {"bold": True, "foregroundColor": ORANGE_DARK}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},

            # Rows 22-26: Log data
            {"repeatCell": {"range": {"sheetId": sheet_id, "startRowIndex": 21, "endRowIndex": 26}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.99, "green": 0.97, "blue": 0.95}, "textFormat": {"fontSize": 10}, "wrapStrategy": "WRAP"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)"}},

            # Protect settings names + instructions
            {"addProtectedRange": {"protectedRange": {"range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 4 + num_fields, "startColumnIndex": 0, "endColumnIndex": 1}, "description": "Setting names", "warningOnly": True}}},
            {"addProtectedRange": {"protectedRange": {"range": {"sheetId": sheet_id, "startRowIndex": 4, "endRowIndex": 4 + num_fields, "startColumnIndex": 2, "endColumnIndex": 3}, "description": "Instructions", "warningOnly": True}}},
        ]

        # Data validation for numeric fields
        validations = [
            (4, {"condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "60"}, {"userEnteredValue": "3600"}]}, "strict": True, "showCustomUi": True, "inputMessage": "Enter 60-3600"}),
            (5, {"condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "1"}, {"userEnteredValue": "48"}]}, "strict": True, "showCustomUi": True, "inputMessage": "Enter 1-48"}),
            (6, {"condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0"}, {"userEnteredValue": "23"}]}, "strict": True, "showCustomUi": True, "inputMessage": "Enter 0-23"}),
            (7, {"condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0"}, {"userEnteredValue": "59"}]}, "strict": True, "showCustomUi": True, "inputMessage": "Enter 0-59"}),
        ]
        for row_idx, rule in validations:
            requests.append({"setDataValidation": {"range": {"sheetId": sheet_id, "startRowIndex": row_idx, "endRowIndex": row_idx + 1, "startColumnIndex": 1, "endColumnIndex": 2}, "rule": rule}})

        try:
            self.sheets.batchUpdate(spreadsheetId=self.spreadsheet_id, body={"requests": requests}).execute()
        except Exception as e:
            logger.warning(f"Could not fully format Agent Config tab: {e}")

    # ----------------------------------------------------------------
    # Write Agent Status + Logs to Sheet
    # ----------------------------------------------------------------

    def write_agent_status(self, last_polled: str, emails_this_cycle: int, error_logs: list[dict]):
        """Update the Agent Status section and error/highlight logs."""
        tab_name = self.agent_config_tab

        # Update status fields (rows 17-18)
        status_rows = [
            ["Last Polled", last_polled, ""],
            ["Emails This Cycle", str(emails_this_cycle), ""],
        ]

        # Update error log rows (rows 22-26)
        log_rows = []
        for log in error_logs:
            log_rows.append([log.get("time", "—"), log.get("message", "—"), ""])
        while len(log_rows) < 5:
            log_rows.insert(0, ["—", "No errors", ""])
        log_rows = log_rows[-5:]  # Keep only last 5

        try:
            # Batch both updates
            self.sheets.values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    "valueInputOption": "RAW",
                    "data": [
                        {"range": f"'{tab_name}'!A{self.STATUS_DATA_ROW}:C{self.STATUS_DATA_ROW + 1}", "values": status_rows},
                        {"range": f"'{tab_name}'!A{self.LOG_DATA_START_ROW}:C{self.LOG_DATA_START_ROW + 4}", "values": log_rows},
                    ]
                }
            ).execute()
        except Exception as e:
            logger.warning(f"Could not write agent status to sheet: {e}")
