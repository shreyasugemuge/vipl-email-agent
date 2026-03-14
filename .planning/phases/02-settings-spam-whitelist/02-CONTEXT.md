# Phase 2: Settings Page + Spam Whitelist - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the settings page type-aware with pre-filled values, add a SpamWhitelist model with management UI in settings, add a "Whitelist Sender" button in the email detail panel, normalize bool config values, and add consistent inline save feedback across all settings tabs.

</domain>

<decisions>
## Implementation Decisions

### Whitelist tab layout
- Simple table layout: rows with email/domain, type badge, added-by, date, and delete (×) button
- Inline add form always visible at top: text input + type dropdown (Email/Domain) + Add button
- Delete requires inline confirmation before removing
- Empty state message: "No whitelisted senders yet. Use 'Whitelist Sender' on any email to add one here."
- New tab added to settings page alongside existing 6 tabs

### Whitelist button in email detail
- Whitelists the exact sender email address (not domain)
- Button appears in the action bar (next to Assign/Acknowledge/Close)
- Visible on all emails, not just spam-categorized ones (preemptive whitelisting)
- Admin-only action (role check in view)
- Feedback: inline green success banner "john@acme.com added to whitelist" that fades after 3s via HTMX swap

### Settings save feedback
- All tabs get consistent inline save feedback (extend existing _config_editor.html pattern)
- Green banner at top of saved section: "Configuration saved successfully."
- Same style across Assignment Rules, Category Visibility, SLA, Webhooks, Inboxes, System, and new Whitelist tab

### Bool normalization
- Data migration to normalize existing bool SystemConfig values to lowercase ("True" → "true", "False" → "false")
- `typed_value` getter made case-insensitive: `self.value.lower() in ("true", "1", "yes")`
- Hidden input fallback before each checkbox in _config_editor.html (value="false") so unchecked checkboxes submit correctly

### Claude's Discretion
- Exact table column widths and responsive behavior
- Confirmation UI pattern for whitelist delete (inline "Sure?" text vs small popover)
- Whether save feedback auto-fades or stays until next action
- SpamWhitelist model field details beyond email/domain/type/added_by

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard approaches. Keep consistent with existing settings page style (slate/indigo color scheme, rounded-xl cards, text-xs font sizing).

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/emails/_config_editor.html`: Already has type-aware inputs (bool→checkbox, int→number, text) and inline save success banner. Pattern to replicate across other tabs.
- `templates/emails/settings.html`: 6-tab layout with JS `switchTab()` function. Adding 7th tab is straightforward.
- `apps/emails/services/spam_filter.py`: Pure regex module (`is_spam()`) — needs whitelist check added before regex patterns.
- Welcome toast CSS from Phase 1 (`base.html` lines 216-234): Can reference for fade animation patterns.

### Established Patterns
- HTMX: `hx-post` + `hx-target` + `hx-swap="innerHTML"` for all settings saves
- Admin-only actions: role check in views (`if not request.user.is_admin`)
- Settings tabs: each tab is a `_*.html` partial included in `settings.html`
- SoftDeleteModel base class for all models (nothing truly deleted)

### Integration Points
- `apps/emails/models.py`: New SpamWhitelist model alongside existing Email, AssignmentRule, etc.
- `apps/emails/views.py`: New view for whitelist CRUD + whitelist-sender action from detail panel
- `apps/emails/urls.py`: New URL patterns for whitelist endpoints
- `apps/emails/services/spam_filter.py`: `is_spam()` needs to check whitelist before regex
- `apps/core/models.py`: SystemConfig.typed_value getter needs case-insensitive normalization

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-settings-spam-whitelist*
*Context gathered: 2026-03-14*
