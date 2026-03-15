---
phase: 04-collaboration
plan: 01
subsystem: ui
tags: [django, htmx, internal-notes, mentions, notifications, google-chat]

# Dependency graph
requires:
  - phase: 03-conversation-ui
    provides: Thread detail panel with timeline, HTMX partials
provides:
  - InternalNote model with soft delete and M2M mentioned_users
  - parse_mentions() utility for @username extraction
  - notify_mention() fire-and-forget Chat + email notifications
  - Note input form with @mention autocomplete in thread detail
  - Notes displayed inline in thread timeline with amber styling
  - NOTE_ADDED and MENTIONED ActivityLog actions
affects: [04-collaboration]

# Tech tracking
tech-stack:
  added: []
  patterns: [inline-note-timeline, mention-autocomplete-vanilla-js, fire-and-forget-notification]

key-files:
  created:
    - apps/emails/migrations/0010_alter_activitylog_action_internalnote.py
    - apps/emails/tests/test_notes.py
    - templates/emails/_thread_note.html
  modified:
    - apps/emails/models.py
    - apps/emails/services/assignment.py
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/_thread_detail.html

key-decisions:
  - "Notes use plain text with linebreaksbr, not rich text -- keeps it lightweight like Slack replies"
  - "Mention autocomplete is vanilla JS (no external library) -- keeps bundle zero-dependency"
  - "Notes appear inline in timeline (not separate tab) -- matches existing messages + activity pattern"
  - "notify_mention uses simple Chat text message (not Cards v2) -- lightweight for mentions"

patterns-established:
  - "Inline note in timeline: type='note' alongside type='message' and type='activity'"
  - "Amber visual distinction for internal notes (bg-amber-50, border-amber-400)"
  - "@mention autocomplete pattern: data attribute JSON + vanilla JS dropdown"

requirements-completed: [COLLAB-01, COLLAB-02, COLLAB-03]

# Metrics
duration: 5min
completed: 2026-03-15
---

# Phase 4 Plan 1: Internal Notes Summary

**InternalNote model with @mention parsing, Chat/email notifications, and inline timeline display with autocomplete**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-15T07:22:23Z
- **Completed:** 2026-03-15T07:27:40Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- InternalNote model with SoftDeleteModel base, thread FK, author FK, M2M mentioned_users
- parse_mentions() extracts @usernames from note body; notify_mention() sends Chat + email (fire-and-forget)
- Notes render inline in thread timeline with amber background and "Internal note" label
- @mention autocomplete dropdown in note textarea with keyboard navigation
- 20 new tests covering model CRUD, mention parsing, notification mocking

## Task Commits

Each task was committed atomically:

1. **Task 1: InternalNote model, @mention parsing, notification service, and tests** - `e5bfe8b` (feat)
2. **Task 2: Note input form, inline display, and @mention autocomplete** - `44fb9f4` (feat)

## Files Created/Modified
- `apps/emails/models.py` - Added InternalNote model and NOTE_ADDED/MENTIONED ActivityLog actions
- `apps/emails/services/assignment.py` - Added parse_mentions() and notify_mention() functions
- `apps/emails/tests/test_notes.py` - 20 tests for notes, mentions, notifications
- `apps/emails/migrations/0010_alter_activitylog_action_internalnote.py` - Migration for new model
- `apps/emails/views.py` - add_note_view endpoint, notes in timeline context
- `apps/emails/urls.py` - threads/<pk>/note/ URL pattern
- `templates/emails/_thread_detail.html` - Note form, note rendering in timeline, autocomplete JS
- `templates/emails/_thread_note.html` - Individual note card template with amber styling

## Decisions Made
- Notes use plain text (not rich text) -- lightweight, Slack-style replies
- Vanilla JS autocomplete (no external library) -- zero added dependencies
- Notes inline in timeline (not separate tab) -- consistent with existing pattern
- Chat notification for mentions uses simple text (not Cards v2) -- lightweight

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Notes infrastructure complete, ready for Phase 4 Plan 2 (collision detection)
- ActivityLog now has NOTE_ADDED and MENTIONED actions for audit trail

---
*Phase: 04-collaboration*
*Completed: 2026-03-15*
