/**
 * VIPL Email Agent — Google Sheets Change Log Script
 *
 * Install this as a Google Apps Script in the Email Tracker spreadsheet.
 * It auto-logs changes to Category, Priority, Assigned To, and Status
 * columns to the Change Log tab.
 *
 * Setup:
 *   1. Open the Google Sheet
 *   2. Extensions → Apps Script
 *   3. Paste this code and save
 *   4. It will auto-run on every edit via the onEdit trigger
 */

// Columns to track (0-indexed)
const TRACKED_COLUMNS = {
  7: "Category",      // Column H
  8: "Priority",      // Column I
  9: "Assigned To",   // Column J
  10: "Status",       // Column K
};

// Tab names
const EMAIL_LOG_TAB = "Email Log";
const CHANGE_LOG_TAB = "Change Log";

/**
 * Trigger: runs on every edit to the spreadsheet.
 */
function onEdit(e) {
  const sheet = e.source.getActiveSheet();

  // Only track edits on the Email Log tab
  if (sheet.getName() !== EMAIL_LOG_TAB) return;

  const range = e.range;
  const col = range.getColumn() - 1; // Convert to 0-indexed
  const row = range.getRow();

  // Skip header row
  if (row <= 1) return;

  // Only track changes to monitored columns
  if (!(col in TRACKED_COLUMNS)) return;

  const fieldName = TRACKED_COLUMNS[col];
  const oldValue = e.oldValue || "(empty)";
  const newValue = e.value || "(empty)";

  // Don't log if value didn't actually change
  if (oldValue === newValue) return;

  // Get the ticket number from column A
  const ticketNumber = sheet.getRange(row, 1).getValue();
  if (!ticketNumber) return;

  // Get the user who made the change
  const userEmail = Session.getActiveUser().getEmail() || "Unknown";

  // Log to Change Log tab
  logChange(ticketNumber, fieldName, oldValue, newValue, userEmail);

  // Special handling: if Status changed FROM "New", record First Response timestamp
  if (fieldName === "Status" && oldValue === "New") {
    const timestamp = new Date();
    sheet.getRange(row, 15).setValue(timestamp); // Column O: First Response At
  }

  // Special handling: if Status changed TO "Closed", record Resolved At timestamp
  if (fieldName === "Status" && newValue === "Closed") {
    const timestamp = new Date();
    sheet.getRange(row, 16).setValue(timestamp); // Column P: Resolved At
  }
}

/**
 * Append a row to the Change Log tab.
 */
function logChange(ticketNumber, field, oldValue, newValue, userEmail) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let logSheet = ss.getSheetByName(CHANGE_LOG_TAB);

  // Create Change Log tab if it doesn't exist
  if (!logSheet) {
    logSheet = ss.insertSheet(CHANGE_LOG_TAB);
    logSheet.appendRow(["Timestamp", "Ticket #", "Field", "Old Value", "New Value", "Changed By"]);

    // Format header row
    const headerRange = logSheet.getRange(1, 1, 1, 6);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#f3f3f3");
  }

  const timestamp = new Date();
  logSheet.appendRow([timestamp, ticketNumber, field, oldValue, newValue, userEmail]);
}

/**
 * One-time setup: create the Change Log tab with headers.
 * Run this manually from the Apps Script editor if needed.
 */
function setupChangeLog() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let logSheet = ss.getSheetByName(CHANGE_LOG_TAB);

  if (!logSheet) {
    logSheet = ss.insertSheet(CHANGE_LOG_TAB);
  }

  // Set headers
  logSheet.getRange(1, 1, 1, 6).setValues([
    ["Timestamp", "Ticket #", "Field", "Old Value", "New Value", "Changed By"]
  ]);

  // Format
  logSheet.getRange(1, 1, 1, 6).setFontWeight("bold").setBackground("#f3f3f3");
  logSheet.setColumnWidth(1, 180);
  logSheet.setColumnWidth(2, 100);
  logSheet.setColumnWidth(3, 120);
  logSheet.setColumnWidth(4, 200);
  logSheet.setColumnWidth(5, 200);
  logSheet.setColumnWidth(6, 200);

  Logger.log("Change Log tab created successfully.");
}
