---
phase: 01-role-permission-foundation
plan: 02
subsystem: auth
tags: [django, permissions, is_admin-refactor, category-scoping, templates, context-processor]

requires:
  - phase: 01-role-permission-foundation/01
    provides: "5 permission properties on User model (can_assign, is_admin_only, can_triage, can_approve_users, is_triage_lead)"
provides:
  - "Zero inline is_admin checks in views or templates"
  - "Category-scoped thread filtering for Triage Lead via AssignmentRule"
  - "Sidebar category pills for Triage Lead"
  - "Settings read-only mode for non-admin triage users"
  - "user_permissions context processor for lead_categories"
  - "Welcome banner with assignment-focused copy for Triage Lead"
affects: [02-assignment-enforcement, 03-triage-queue, 04-intelligence-loop]

tech-stack:
  added: []
  patterns:
    - "user.can_assign / user.is_admin_only / user.can_triage in templates instead of is_admin context variable"
    - "Context processor for role-specific template data (apps.accounts.context_processors.user_permissions)"
    - "Category-scoped queryset filtering via AssignmentRule.objects.filter(assignee=user)"

key-files:
  created:
    - apps/accounts/context_processors.py
    - apps/emails/tests/test_triage_lead.py
  modified:
    - apps/emails/views.py
    - config/settings/base.py
    - templates/base.html
    - templates/emails/thread_list.html
    - templates/emails/_thread_detail.html
    - templates/emails/_context_menu.html
    - templates/emails/_email_card.html
    - templates/emails/_email_detail.html
    - templates/emails/_editable_status.html
    - templates/emails/email_list.html
    - templates/emails/settings.html

key-decisions:
  - "Templates use user.can_assign / user.is_admin_only directly via model properties (no context variable passing)"
  - "Context processor provides lead_categories globally so base.html sidebar pills work on all pages"
  - "Settings page is read-only (not hidden) for Triage Lead -- view-only access with blue info banner"
  - "Force poll stays admin-only (is_admin_only); inspector view accessible to can_triage users"

patterns-established:
  - "Zero is_admin context variable pattern: all permission checks via User model properties in templates"
  - "Category-scoped queryset: threads.filter(category__in=lead_categories) for Triage Lead"
  - "Read-only page pattern: readonly flag in context, disabled inputs, hidden save buttons"

requirements-completed: [ROLE-02, ROLE-06]

duration: 6min
completed: 2026-03-15
---

# Phase 1 Plan 02: Permission Refactor + Category Scoping Summary

**Replaced all 28+ is_admin checks with centralized User properties, added category-scoped thread filtering for Triage Lead, sidebar pills, settings read-only, and welcome banner**

## Performance

- **Duration:** 6 min (across two sessions with checkpoint)
- **Started:** 2026-03-15T19:00:00Z
- **Completed:** 2026-03-15T19:16:53Z
- **Tasks:** 3 (2 auto + 1 checkpoint)
- **Files modified:** 13

## Accomplishments
- Eliminated all 28+ scattered is_admin permission checks from views.py and 12 templates
- Category-scoped thread filtering: Triage Lead only sees threads matching their AssignmentRule categories
- Sidebar shows "Your Categories" pills for Triage Lead with assigned category names
- Settings page read-only for Triage Lead (blue info banner, disabled inputs, hidden save buttons)
- Welcome banner with "keep the queue empty" assignment-focused copy
- Context processor makes lead_categories available in all templates without per-view passing
- 10 new tests covering category scoping, permission enforcement, and zero-is_admin verification

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace all 28+ is_admin checks in views + add category-scoped filtering** - `3a9fabf` (feat)
2. **Task 2: Update all 12 templates + sidebar category pills + welcome banner + settings read-only** - `e1d0486` (feat)
3. **Task 3: Visual verification checkpoint** - approved (no commit)

## Files Created/Modified
- `apps/accounts/context_processors.py` - user_permissions context processor providing lead_categories globally
- `apps/emails/views.py` - All is_admin checks replaced with can_assign/is_admin_only/can_triage; category-scoped filtering added
- `apps/emails/tests/test_triage_lead.py` - Tests for category scoping, permissions, zero-is_admin verification
- `config/settings/base.py` - Registered user_permissions context processor
- `templates/base.html` - Per-link sidebar visibility, category pills section for Triage Lead
- `templates/emails/thread_list.html` - user.can_assign checks, Triage Lead welcome banner, no-categories empty state
- `templates/emails/_thread_detail.html` - user.can_assign replacing is_admin
- `templates/emails/_context_menu.html` - user.can_assign for assign actions, user.is_admin_only for whitelist
- `templates/emails/_email_card.html` - user.can_assign replacing is_admin
- `templates/emails/_email_detail.html` - user.can_assign replacing is_admin
- `templates/emails/_editable_status.html` - user.can_assign replacing is_admin
- `templates/emails/email_list.html` - user.can_assign replacing is_admin
- `templates/emails/settings.html` - Read-only banner, disabled inputs when readonly flag set

## Decisions Made
- Templates use User model properties directly (user.can_assign) rather than context variables -- cleaner, no risk of forgetting to pass
- Context processor for lead_categories ensures sidebar pills work on every page without modifying every view
- Settings page shown read-only (not hidden) so Triage Lead can see current configuration
- Force poll remains strictly admin-only; inspector view is view-only for triage leads

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 1 fully complete: role model + permission properties + permission refactor all done
- Ready for Phase 2 (Assignment Enforcement): all permission primitives in place
- No blockers

## Self-Check: PASSED

- FOUND: apps/accounts/context_processors.py
- FOUND: apps/emails/tests/test_triage_lead.py
- FOUND: 01-02-SUMMARY.md
- FOUND: commit 3a9fabf (Task 1)
- FOUND: commit e1d0486 (Task 2)

---
*Phase: 01-role-permission-foundation*
*Completed: 2026-03-15*
