---
phase: 04-chat-notification-polish
plan: 01
subsystem: notifications
tags: [google-chat, cards-v2, sla, deep-links, webhook]

requires:
  - phase: 03-vipl-branding
    provides: branded card headers and VIPL footer
provides:
  - _sla_urgency_label() helper for consistent urgency formatting
  - pk field in breach summary dicts for deep linking
  - inline Open buttons on personal breach, breach summary, and new email cards
affects: []

tech-stack:
  added: []
  patterns: [decoratedText.button for inline actions, _sla_urgency_label for uniform urgency display]

key-files:
  created: []
  modified:
    - apps/emails/services/sla.py
    - apps/emails/services/chat_notifier.py
    - apps/emails/tests/test_sla.py
    - apps/emails/tests/test_chat_notifier.py

key-decisions:
  - "decoratedText.button (not buttonList) for inline per-row Open buttons -- Cards v2 union field constraint"
  - "pk passed through data dicts, not Django ORM import in chat_notifier -- keeps service layer clean"
  - "_sla_urgency_label as module-level function, not method, for reuse across all notify methods"

patterns-established:
  - "Inline Open button pattern: decoratedText.button with openLink URL using pk"
  - "Urgency label helper: single source of truth for emoji+priority+overdue formatting"

requirements-completed: [R4.1, R4.2, R4.3, R4.4]

duration: 4min
completed: 2026-03-14
---

# Phase 04 Plan 01: Chat Notification Polish Summary

**Inline Open buttons and consistent SLA urgency labels across all Google Chat notification cards via _sla_urgency_label helper**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-14T17:28:14Z
- **Completed:** 2026-03-14T17:32:57Z
- **Tasks:** 2 (1 auto + 1 checkpoint)
- **Files modified:** 4

## Accomplishments
- Added `pk` key to breach summary dicts (per_assignee entries and top_offenders) enabling deep links
- Created `_sla_urgency_label()` helper for consistent emoji+priority+overdue formatting across all card types
- Added inline "Open" buttons on personal breach, breach summary, and new email card rows
- Routed all 4 notify methods through the urgency helper for uniform display
- Full TDD: 12 new tests (all passing), 348 total suite green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Write failing tests** - `b968814` (test)
2. **Task 1 GREEN: Implement pk, urgency helper, Open buttons** - `c74c8f3` (feat)
3. **Task 2: Card payload dump helper for validation** - `d2fbf66` (test)

_TDD task with separate RED and GREEN commits._

## Files Created/Modified
- `apps/emails/services/sla.py` - Added "pk" key to breach entry and top_offenders dicts
- `apps/emails/services/chat_notifier.py` - Added _sla_urgency_label(), inline Open buttons on 3 card types, routed assignment subtitle through helper
- `apps/emails/tests/test_sla.py` - 2 new tests for pk presence in breach summary dicts
- `apps/emails/tests/test_chat_notifier.py` - 12 new tests: urgency label helper, Open buttons, consistency, dump helper

## Decisions Made
- Used `decoratedText.button` (not `buttonList`) for inline per-row Open buttons -- Cards v2 union field constraint prevents mixing endIcon and button
- pk flows through data dicts only, no Django ORM import in chat_notifier -- keeps the service layer clean
- `_sla_urgency_label` as module-level function (not a ChatNotifier method) for easy import and reuse

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All auto tasks complete; checkpoint:human-verify pending for visual card validation
- Card payload dump helper available via `pytest -k test_dump_card_payloads --no-header -rN -s`
- Phase 4 is the final phase -- no subsequent phases depend on this

---
*Phase: 04-chat-notification-polish*
*Completed: 2026-03-14*
