---
phase: 03-dashboard
plan: 02
subsystem: ui
tags: [django, htmx, assignment, notifications, xss-sanitization, nh3]

# Dependency graph
requires:
  - phase: 03-dashboard
    plan: 01
    provides: Email list view, ActivityLog model, base layout, template tags
provides:
  - Assignment service (assign_email, change_status, notify_assignment_email)
  - ChatNotifier.notify_assignment method
  - Email detail panel with sanitized HTML rendering
  - Assignment and status change views with RBAC
  - Inline assign dropdown on email cards
affects: [03-dashboard-plan-03, 04-assignment-sla]

# Tech tracking
tech-stack:
  added: [nh3]
  patterns: [htmx-detail-panel, fire-and-forget-notifications, nh3-html-sanitization]

key-files:
  created:
    - apps/emails/services/assignment.py
    - templates/emails/_email_detail.html
    - templates/emails/_assign_dropdown.html
  modified:
    - apps/emails/services/chat_notifier.py
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/_email_card.html
    - templates/emails/email_list.html
    - requirements.txt
    - apps/emails/tests/test_assignment.py

key-decisions:
  - "nh3 for HTML sanitization (Rust-based, safe-by-default, strips scripts/iframes/event handlers)"
  - "Fire-and-forget notifications: Chat and email never block or crash assignment"
  - "List/detail split layout: 40% email list, 60% detail panel (per CONTEXT.md)"
  - "Inline assign dropdown on cards for fast triage without opening detail panel"

patterns-established:
  - "Service layer pattern: views call service functions, services handle ORM + notifications"
  - "RBAC: admin-only assignment, member own-email status changes"
  - "nh3.clean with explicit allowlist for safe HTML tags"

requirements-completed: [ASGN-01, ASGN-02, ASGN-05, SLA-01]

# Metrics
duration: 8min
completed: 2026-03-11
---

# Phase 3 Plan 02: Assignment Workflow + Detail Panel Summary

**Assignment dropdown on cards, slide-out detail panel with sanitized HTML, status changes with RBAC, Chat + email notifications on assignment**

## Performance

- **Duration:** 8 min
- **Tasks:** 2 (both TDD)
- **Files modified:** 10
- **Tests added:** 20 (12 service + 8 view)
- **Total test suite:** 129 tests passing

## Accomplishments
- Assignment service: assign_email sets assignee fields, creates ActivityLog, fires Chat + email notifications
- Reassignment support: detects existing assignee, creates REASSIGNED action with old/new values
- Status change service: change_status validates, updates, maps to ACKNOWLEDGED/CLOSED actions
- ChatNotifier.notify_assignment: Cards v2 payload with subject, priority, sender, dashboard link, quiet hours
- Email notification to assignee via Django send_mail (fire-and-forget)
- Detail panel: full email body (nh3-sanitized), AI draft reply, attachments, activity log, assign/status controls
- XSS prevention: nh3 strips scripts, iframes, event handlers; preserves safe formatting tags
- Inline assign dropdown on email cards (admin only, auto-submits on change)
- List/detail split layout (40/60) with HTMX-loaded detail panel
- RBAC: admin-only assignment, member can Acknowledge/Close own emails, 403 for unauthorized

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for assignment service** - `272d183` (test)
2. **Task 1 GREEN: Assignment service, Chat + email notifications** - `18aa5aa` (feat)
3. **Task 2 RED: Failing tests for views, detail, status** - `e8f4466` (test)
4. **Task 2 GREEN: Views, detail panel, templates, URL routes** - `da41518` (feat)

## Files Created/Modified
- `apps/emails/services/assignment.py` - assign_email, change_status, notify_assignment_email service functions
- `apps/emails/services/chat_notifier.py` - Added notify_assignment method (Cards v2 + quiet hours)
- `apps/emails/views.py` - Added email_detail, assign_email_view, change_status_view
- `apps/emails/urls.py` - Added detail, assign, status URL routes
- `templates/emails/_email_detail.html` - Slide-out detail panel partial
- `templates/emails/_assign_dropdown.html` - Inline assign dropdown for cards
- `templates/emails/_email_card.html` - Added hx-get for detail, inline assign dropdown
- `templates/emails/email_list.html` - Added 40/60 list-detail split with #detail-panel
- `requirements.txt` - Added nh3 for HTML sanitization
- `apps/emails/tests/test_assignment.py` - 20 tests (service + view)

## Decisions Made
- nh3 (Rust-based) for HTML sanitization -- safe-by-default, explicit tag allowlist
- Fire-and-forget notifications -- Chat and email never block or crash assignment flow
- 40/60 list-detail split layout as specified in CONTEXT.md
- Inline assign dropdown on cards for fast admin triage

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None -- no external service configuration required.

## Next Phase Readiness
- Assignment workflow fully functional for Plan 03 (search, keyboard shortcuts, batch actions)
- Detail panel ready for future enhancements (SLA display, attachment download)
- All 129 tests passing, no regressions

---
*Phase: 03-dashboard*
*Completed: 2026-03-11*
