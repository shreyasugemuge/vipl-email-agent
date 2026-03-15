# Phase 4: Collaboration - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Add internal notes on threads with @mentions and collision detection ("X is viewing this"). Notes are team-internal only (never visible to email senders). @mentions trigger notifications. Viewing indicator shows when another user has the same thread open.

Requirements: COLLAB-01, COLLAB-02, COLLAB-03, COLLAB-04

</domain>

<decisions>
## Implementation Decisions

### Viewing indicator placement
- Floating badge in the top-right area of the thread detail panel sticky header
- Shows overlapping small avatars + count (e.g., two avatar circles + "2")
- Hover reveals full names of viewers
- Only appears in detail panel — NOT on thread list cards (keeps list clean)

### Viewing presence lifecycle
- User is "viewing" while the thread detail panel is open and they are active
- 30-second idle timeout: if no scrolling, clicking, or interaction for 30s, user is removed from viewers
- Cleared immediately when user navigates to another thread or closes the detail panel

### Viewing backend approach
- Claude's Discretion: Choose between DB model (ThreadViewer with polling) or Django cache backend — pick what's simplest given current VM stack (no Redis/memcached currently deployed)

### Internal notes design
- Claude's Discretion: Note input placement in thread detail, formatting (plain text vs rich), visual distinction from email messages (different background, "Internal note" label per COLLAB-03)

### @mention behavior
- Claude's Discretion: Autocomplete UI for @mentions, notification delivery channel (Chat, email, or both), mention notification content

### Note visibility and permissions
- Claude's Discretion: All team members can add notes (no admin-only restriction), note editing/deletion policy, note permanence

</decisions>

<specifics>
## Specific Ideas

- Viewing indicator should be lightweight — a 3-person team doesn't need real-time WebSocket presence, polling is fine
- Notes should feel like Slack thread replies — quick, lightweight, not like composing an email
- Activity events from notes (added, @mentioned) should appear inline in the thread timeline alongside email messages and status changes (established pattern from Phase 3)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ActivityLog` model with `Action` TextChoices — extend with NOTE_ADDED, MENTIONED action types
- `ActivityLog.detail` TextField — can store note content or mention context
- `chat_notifier.py` — existing notification patterns (notify_assignment, notify_thread_update) for @mention notifications
- `notify_assignment_email()` in `assignment.py` — email notification pattern reusable for @mention emails
- `User` model with `first_name`, `last_name`, `get_full_name()` — for @mention autocomplete
- HTMX OOB swaps — can update viewer badge without full page reload

### Established Patterns
- `SoftDeleteModel` + `TimestampedModel` base classes for new models
- `ForeignKey(on_delete=models.SET_NULL)` for user references
- HTMX `hx-post` for form submissions (note creation)
- `nh3` HTML sanitization — apply to note content if rich text supported
- Fire-and-forget notifications — never block the main action

### Integration Points
- Thread detail panel (Phase 3) — note input form goes here, notes render inline with messages
- Thread detail sticky header (Phase 3) — viewing badge integrates here
- `_build_detail_context()` helper — extend to include notes and viewers
- Thread model `activity_logs` related manager — notes can be ActivityLog entries or a separate model

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-collaboration*
*Context gathered: 2026-03-15*
