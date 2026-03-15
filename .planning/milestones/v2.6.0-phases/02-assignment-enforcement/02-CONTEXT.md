# Phase 2: Assignment Enforcement - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Assignment permissions are enforced so gatekeepers and admins control thread routing while members retain limited self-service. Members can self-claim unassigned threads in their categories and reassign threads they own (with mandatory reason). Gatekeepers and admins can assign any thread to any active user.

</domain>

<decisions>
## Implementation Decisions

### Member reassign flow
- Inline textarea for mandatory reason appears in the detail panel when member clicks "Reassign" on a thread assigned to them
- Reason is required (non-empty, no minimum length) — server-side enforced
- Member can only reassign to users who share CategoryVisibility for that thread's category (not anyone active)
- Dedicated `REASSIGNED_BY_MEMBER` ActivityLog action type — distinct from regular `REASSIGNED` for easy filtering/reporting
- Admin/gatekeeper reassign does NOT require a reason (optional note field, same as today)

### Assignment UI gating
- Members: "Assign to" dropdown completely hidden in detail panel
- Members see "Claim" button on unassigned threads (in their categories) and "Reassign" button on threads assigned to them
- Gatekeepers/admins: full "Assign to" dropdown with all active users, optional note field
- Right-click context menu is role-conditional:
  - Admin/gatekeeper: full "Assign to" submenu
  - Member on unassigned thread in their category: "Claim" option
  - Member on own thread: "Reassign" option
  - Member on others' threads: no assignment options
- Member viewing thread assigned to someone else: read-only view (can see detail, activity log, add notes — but no assignment/status/priority actions)
- Server-side guard returns 403 with role-aware message: "Only gatekeepers and admins can assign threads to other users."

### Self-claim boundaries
- Members can only claim threads matching their CategoryVisibility entries (existing behavior preserved)
- If thread's category is outside member's visibility: claim button shown disabled with tooltip "This thread is outside your assigned categories"
- Members cannot claim threads already assigned to someone else — only unassigned threads (existing `claim_thread()` validation preserved)
- Gatekeepers bypass CategoryVisibility like admins — can claim and assign any thread regardless of category

### Claude's Discretion
- Exact placement and styling of the inline reassign reason textarea
- How the disabled claim button tooltip is implemented (title attr vs custom tooltip)
- Server-side validation error message wording details
- Whether to add a client-side character counter on the reason field

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — ROLE-03, ROLE-04, ROLE-05 define assignment permission rules

### Research
- `.planning/research/SUMMARY.md` — Architecture approach, pitfall catalog (especially Pitfall 5: member self-claim conflict, Pitfall 8: validation bypass)

### Existing code (Phase 1 will have modified these)
- `apps/emails/services/assignment.py` — `assign_thread()`, `claim_thread()` functions with CategoryVisibility pattern
- `apps/emails/views.py` — `assign_thread_view`, `claim_thread_view`, `change_thread_status_view`, `_build_thread_detail_context`
- `apps/emails/models.py` — `ActivityLog.Action` choices (add `REASSIGNED_BY_MEMBER`)
- `templates/emails/_thread_detail.html` — Detail panel assignment UI
- `templates/emails/_context_menu.html` — Right-click context menu

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `claim_thread()` in assignment.py: already validates assigned_to is None and checks CategoryVisibility — extend bypass to include gatekeeper role
- `assign_thread()` in assignment.py: handles assignment + ActivityLog + Chat notification — reuse for gatekeeper/admin flow
- `_build_thread_detail_context()` in views.py: builds template context with `is_admin` flag — replace with `can_assign` from Phase 1 helpers
- `_context_menu.html`: already role-conditional for some actions — extend pattern for claim/reassign

### Established Patterns
- Inline `is_admin` checks in views will be replaced by `can_assign()` / `is_admin_only()` helpers from Phase 1
- ActivityLog stores action type + old_value/new_value + detail text — use detail field for reassign reason
- HTMX partial swaps: assign/status views return detail_html + OOB card_html — same pattern for reassign

### Integration Points
- Phase 1 `can_assign()` helper: gatekeeper + admin return True, member returns False
- Phase 1 gatekeeper role: `User.Role.GATEKEEPER` exists in model
- `CategoryVisibility` model: controls which categories each user can see/claim
- Template `is_admin` context variable: Phase 1 likely renames to `can_assign` or adds both

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-assignment-enforcement*
*Context gathered: 2026-03-15*
