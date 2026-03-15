# Phase 3: Spam Learning + Bug Fixes - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can correct spam verdicts from the thread detail panel, sender reputation auto-blocks repeat spammers, and known pipeline bugs are fixed. Models (SpamFeedback, SenderReputation) come from Phase 1. No ML — sender reputation is the spam learning mechanism.

</domain>

<decisions>
## Implementation Decisions

### Spam feedback UX
- Mark Spam / Not Spam buttons live in the **detail panel only** (header bar, near assign/status buttons)
- **Instant action + toast** — click triggers immediately, toast with 5s undo window (matches existing assignment/status change pattern)
- Marking "Not Spam" does **NOT** auto-whitelist — user must separately whitelist via Settings if desired (SPAM-05 becomes: marking "Not Spam" on a **blocked** sender auto-whitelists, but regular "Not Spam" is feedback-only)
- **All users** (admin and member) can mark spam/not-spam — SpamFeedback records who did it

### Auto-block behavior
- **Silent block** — pipeline skips blocked senders without notification or ActivityLog entry
- Block check runs **before spam filter** in pipeline: whitelist → block check → spam filter → AI triage (cheapest path, $0)
- Blocked sender management in **combined Whitelist/Block tab** in Settings (merge with existing SpamWhitelist management)
- Unblocking a sender affects **future emails only** — past emails stay as-is, admin can manually mark individual threads "Not Spam" if needed

### Sender reputation
- Reputation updates on **both** user feedback (explicit) and pipeline processing (passive — increments total_count for every email from a tracked sender)
- Only senders with spam_count > 0 or is_blocked = True shown in the combined Whitelist/Block tab
- Spam ratio and total count displayed as **columns** in the sender management table
- Auto-block threshold: spam ratio > 0.8 AND >= 3 total emails (from SPAM-04 requirement)

### Bug fixes
- **FIX-01** (Gmail avatar): _update_avatar() helper exists from Phase 8 with 6+ tests — researcher should investigate what's still broken (edge cases?)
- **FIX-02** (Cross-inbox dedup): _detect_cross_inbox_duplicate() exists with 5-min window — researcher should investigate remaining edge cases
- **FIX-03** (Force Poll in production): Remove dev/off mode restriction on Force Poll button — it should work in ALL modes including production
- **SPAM-06** (Spam badge): has_spam annotation exists — researcher should trace through templates to find where it breaks

### Claude's Discretion
- Button styling/placement details in detail panel header
- Toast notification wording and undo implementation
- Combined tab layout (how to merge whitelist + blocked senders visually)
- Pipeline block check implementation details
- How to increment SenderReputation.total_count during pipeline (get_or_create vs update_or_create)

</decisions>

<specifics>
## Specific Ideas

- Scheduler has stopped polling in production (inspector shows PRODUCTION mode, 0 polls in 7 days, "Due now") — investigate why during research
- Force Poll should work regardless of operating mode — it's a manual override for when scheduler is stuck
- Combined sender management tab should show: sender address, type (whitelisted/blocked), spam ratio, total emails, action button (unblock/remove)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SpamWhitelist` model (apps/emails/models.py): Already has entry_type (email/domain), entry, added_by, reason fields
- `_is_whitelisted()` (apps/emails/services/pipeline.py): Whitelist check pattern — block check will follow same pattern
- `spam_filter.py`: Pure Python, 13 regex patterns, returns TriageResult — no changes needed
- `has_spam` annotation (apps/emails/views.py:84): Exists subquery on Email.is_spam — may need fixing per SPAM-06
- Whitelist management views (apps/emails/views.py): add_whitelist, remove_whitelist, retroactive_unspam — pattern to follow for block management
- Toast notification pattern: Already used for assignment/status changes

### Established Patterns
- Pipeline order: whitelist → spam filter → AI → save → label (block check inserts after whitelist)
- `save_email_to_db()` uses update_or_create with message_id as key
- ActivityLog tracks all state changes with action TextChoices
- Settings tabs rendered with HTMX partials
- SoftDeleteModel + TimestampedModel base classes for all models

### Integration Points
- `pipeline.py:_process_single_email()`: Insert block check after whitelist, before spam filter
- `pipeline.py:run_poll_cycle()`: Increment SenderReputation.total_count for processed emails
- `views.py` thread detail: Add spam feedback buttons to header bar
- Settings whitelist tab template: Extend to show blocked senders
- `views.py` force_poll view: Remove mode restriction

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-spam-learning-bug-fixes*
*Context gathered: 2026-03-15*
