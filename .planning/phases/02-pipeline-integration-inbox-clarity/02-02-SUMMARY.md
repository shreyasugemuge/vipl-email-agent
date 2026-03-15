---
phase: 02-pipeline-integration-inbox-clarity
plan: 02
subsystem: pipeline, ui
tags: [deduplication, template-tags, chat-notification, inbox-tracking]

requires:
  - phase: 02-pipeline-integration-inbox-clarity/01
    provides: Thread-aware pipeline with create/update/reopen logic
provides:
  - Cross-inbox dedup detection with 5-minute window
  - Triage reuse for duplicate emails (zero AI cost)
  - Lightweight "also received on" Chat notification
  - inbox_badge and thread_inbox_badges template tags
affects: [03-conversation-ui]

tech-stack:
  added: []
  patterns:
    - "Cross-inbox dedup via gmail_thread_id + sender + time window"
    - "Transient attrs (_is_cross_inbox_duplicate) for notification routing"
    - "Template tags for colored pill badges with VIPL palette"

key-files:
  created:
    - apps/emails/templatetags/inbox_tags.py
    - apps/emails/tests/test_cross_inbox_dedup.py
    - apps/emails/tests/test_inbox_tags.py
  modified:
    - apps/emails/services/pipeline.py
    - apps/emails/services/chat_notifier.py

key-decisions:
  - "5-minute dedup window balances catching duplicates vs not blocking genuine replies"
  - "Duplicates skip both spam filter AND AI triage, reusing original's full triage result"
  - "Cross-inbox dups routed to separate notification path (not mixed with new/update)"

patterns-established:
  - "INBOX_COLORS dict for consistent inbox badge styling across templates"
  - "_is_cross_inbox_duplicate transient attr for pipeline routing decisions"

requirements-completed: [INBOX-01, INBOX-02, INBOX-03]

duration: 4min
completed: 2026-03-15
---

# Phase 2 Plan 2: Inbox Tracking, Deduplication, and Multi-Inbox Display Summary

**Cross-inbox email dedup with triage reuse, inbox pill badges (teal info@, amber sales@), and lightweight Chat notification for duplicates**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T06:51:46Z
- **Completed:** 2026-03-15T06:55:42Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Cross-inbox duplicates detected within 5-minute window (same gmail_thread_id + sender), skip AI/spam, reuse triage
- Colored inbox pill badges: info@ (teal), sales@ (amber), unknown (purple) -- complement VIPL plum palette
- Multi-inbox threads show all inbox badges via thread_inbox_badges template tag
- Lightweight "also received on" Chat notification for duplicates (not full triage card)

## Task Commits

Each task was committed atomically:

1. **Task 1: Cross-inbox dedup detection with triage reuse** - `1846ec6` (feat)
2. **Task 2: Inbox pill badge template tags** - `cff3761` (feat)

## Files Created/Modified
- `apps/emails/services/pipeline.py` - Added _detect_cross_inbox_duplicate, dedup step in process_single_email, cross-inbox routing in process_poll_cycle
- `apps/emails/services/chat_notifier.py` - Added notify_cross_inbox_duplicate method
- `apps/emails/templatetags/inbox_tags.py` - inbox_badge and thread_inbox_badges template tags
- `apps/emails/tests/test_cross_inbox_dedup.py` - 13 tests for dedup detection and notification
- `apps/emails/tests/test_inbox_tags.py` - 9 tests for badge rendering

## Decisions Made
- 5-minute dedup window chosen to catch typical mail server delivery delays without false-positive on genuine replies
- Duplicates skip both spam filter AND AI triage (zero cost), reusing original's full TriageResult
- Cross-inbox duplicates routed to separate notification path, not mixed with new-thread or thread-update notifications

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pipeline fully thread-aware with dedup -- ready for conversation UI (Phase 3)
- Template tags available for Phase 3's three-panel layout to show inbox badges inline
- All 462 tests passing, no regressions

---
*Phase: 02-pipeline-integration-inbox-clarity*
*Completed: 2026-03-15*
