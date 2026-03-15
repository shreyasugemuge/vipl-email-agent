---
phase: M6-P2-thread-card-detail-ux
plan: 02
subsystem: ui
tags: [tailwind, htmx, select, clipboard, pill-dropdown]

requires:
  - phase: M6-P2-01
    provides: Thread card and detail panel templates
provides:
  - Pill-styled priority and category selects (no badge-to-edit toggle)
  - Copy-to-clipboard button on AI draft reply
affects: [thread-detail, editable-dropdowns]

tech-stack:
  added: []
  patterns: [pill-select-with-hover-caret, clipboard-api-copy-feedback]

key-files:
  created: []
  modified:
    - templates/emails/_editable_priority.html
    - templates/emails/_editable_category.html
    - templates/emails/_thread_detail.html

key-decisions:
  - "Native select with appearance-none + pill styling (no custom popover)"
  - "Hover caret via group-hover SVG overlay instead of CSS background-image"
  - "Copy button in summary bar with stopPropagation to avoid toggle"

patterns-established:
  - "Pill select: appearance-none + rounded-full + colored bg + hover caret SVG"

requirements-completed: [CARD-02, CARD-04]

duration: 2min
completed: 2026-03-15
---

# Phase M6-P2 Plan 02: Pill Dropdowns & Draft Copy Summary

**Pill-styled priority/category selects replacing badge-to-edit toggles, plus clipboard copy button on AI draft reply**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-15T17:22:39Z
- **Completed:** 2026-03-15T17:24:21Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Priority and category dropdowns now render as always-interactive colored pill selects
- Removed the click-badge-to-reveal-dropdown pattern entirely
- AI draft reply section has a one-click copy-to-clipboard button with "Copied!" feedback

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert priority and category to pill-style selects** - `6a3e106` (feat)
2. **Task 2: Add copy-to-clipboard button on AI draft reply** - `e40e39d` (feat)

## Files Created/Modified
- `templates/emails/_editable_priority.html` - Pill-styled priority select with hover caret
- `templates/emails/_editable_category.html` - Pill-styled category select with hover caret, custom option preserved
- `templates/emails/_thread_detail.html` - AI draft reply section with copy-to-clipboard button

## Decisions Made
- Used native `<select>` with `appearance-none` rather than a custom popover for maximum compatibility
- Hover caret implemented as SVG with `group-hover` opacity transition, positioned with negative margin overlap
- Copy button placed in the `<summary>` bar so it's visible even when details collapsed
- Custom category input styled with `rounded-full` to match the pill select aesthetic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pill dropdowns and copy button ready for visual verification
- No blockers for remaining M6-P2 plans

---
*Phase: M6-P2-thread-card-detail-ux*
*Completed: 2026-03-15*
