---
phase: M6-P2-thread-card-detail-ux
plan: 01
subsystem: ui
tags: [tailwind, django-templates, htmx, thread-cards, context-menu]

requires:
  - phase: M6-P1-bug-fixes
    provides: bug fixes and baseline thread card template
provides:
  - Redesigned 3-row thread card with larger text and reorganized badge layout
  - Readable context menu with text-sm and high-contrast text
affects: [M6-P2-02, thread-detail-ux]

tech-stack:
  added: []
  patterns:
    - "line-clamp-2 for multi-line text truncation (CSS-only, no Django filter)"
    - "Badges cluster in row 3 alongside AI summary for cleaner card layout"

key-files:
  created: []
  modified:
    - templates/emails/_thread_card.html
    - templates/emails/_context_menu.html

key-decisions:
  - "Used line-clamp-2 CSS instead of truncatechars Django filter for AI summary"
  - "Moved all badges (priority, confidence, status, SLA, spam, AI assignee) to row 3"
  - "Unread dot sized to w-2.5 h-2.5 for better visibility"

patterns-established:
  - "Card row layout: Row 1 sender/meta, Row 2 subject only, Row 3 summary + badges"

requirements-completed: [CARD-01, CARD-03]

duration: 4min
completed: 2026-03-15
---

# Phase M6-P2 Plan 01: Thread Card & Context Menu UX Summary

**Redesigned thread cards with larger text (+1-2px all sizes), clean subject row, 2-line AI summary, and readable 14px context menu**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T17:22:38Z
- **Completed:** 2026-03-15T17:26:38Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Thread cards have visibly larger text across all elements (sender 13px, subject 13px, summary 12px, badges 9px)
- Subject line is clean on its own row -- badges moved to row 3 alongside AI summary
- AI summary wraps to 2 lines via CSS line-clamp-2 instead of Django truncatechars:80
- Context menu items readable at 14px (text-sm) with bright text-slate-100 contrast

## Task Commits

Each task was committed atomically:

1. **Task 1: Redesign thread card layout and sizing** - `00b1b70` (feat)
2. **Task 2: Fix context menu readability** - `40d76ae` (feat)

## Files Created/Modified
- `templates/emails/_thread_card.html` - Redesigned 3-row card with larger text, more padding, badge reorganization, line-clamp-2 summary
- `templates/emails/_context_menu.html` - Bumped text to text-sm (14px), brightened to text-slate-100

## Decisions Made
- Used CSS line-clamp-2 instead of Django truncatechars filter for AI summary -- lets content wrap naturally to 2 lines
- Moved all badges from subject row to row 3 for a clean subject line
- Sized unread dot at w-2.5 h-2.5 (biggest option) for clear visibility
- Increased card gap to my-1.5 and padding to py-3 for comfortable spacing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Card template ready for visual verification
- Context menu ready for visual verification
- Plan 02 (thread detail panel UX) can proceed independently

---
*Phase: M6-P2-thread-card-detail-ux*
*Completed: 2026-03-15*
