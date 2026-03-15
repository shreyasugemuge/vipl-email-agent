# Phase 4: Alerts + Bulk Actions - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Proactive unassigned count monitoring via Google Chat alerts and batch operations (bulk assign, bulk mark-irrelevant) for efficient queue management. Also includes an AI corrections digest for gatekeepers. Depends on Phase 2 (assignment enforcement) and Phase 3 (mark irrelevant) both being complete.

</domain>

<decisions>
## Implementation Decisions

### Bulk selection UX
- Floating bottom bar appears when ≥1 thread checkbox is checked (Slack/Notion pattern)
- Checkboxes appear on hover over thread cards (not always visible)
- "Select all visible" checkbox in the list header selects all currently loaded thread cards
- Bar shows: selected count + "Assign to" dropdown + "Mark Irrelevant" button
- Bar has shadow, rounded corners, slides in from bottom
- After bulk action: undo toast (10-second window) — no confirmation dialog before
- Bar disappears when selection is cleared or after action completes

### Alert behavior
- Rising-edge detection: alert fires once when unassigned count crosses threshold (e.g., 4→5), not on every poll while above
- Resets when count drops below threshold, so next crossing triggers again
- Default threshold: 5 unassigned threads
- Default cooldown: 30 minutes between alerts
- Piggyback on existing `_heartbeat_job` (1-minute interval) — check count there with cooldown
- Threshold and cooldown configurable from Settings page (SLA/Config tab), not SystemConfig-admin-only
- Chat alert card shows count + top category breakdown (e.g., "⚠️ 7 unassigned: 3 Sales, 2 Support, 2 General") with link to triage queue

### AI corrections digest
- Collapsible card above thread list on triage queue page
- Shows: correction counts (category changes, priority overrides, spam corrections) for last 7 days
- Shows: top 3-5 repeating patterns extracted from ActivityLog (e.g., "STPI tenders → Govt (was General)")
- Gatekeeper + admin only — members don't see it
- Refreshes on page load only (query ActivityLog) — no background polling
- Collapsible: expanded by default, remembers collapsed state

### Unassigned badge
- Sidebar "Triage Queue" pill already shows unassigned count for admins — extend role check to include gatekeepers
- No additional badge locations needed (sidebar only)
- Threshold-based coloring: green (0-2), yellow (3-4), red (5+, matches alert threshold)
- Count excludes irrelevant threads (Phase 3 delivers this status)

### Claude's Discretion
- Exact floating bar animation and styling
- HTMX contract for bulk POST (thread IDs array format)
- ActivityLog query structure for digest patterns
- SystemConfig key naming for alert threshold/cooldown
- Undo toast timing and implementation details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Role & permissions (Phase 1-3 foundation)
- `.planning/REQUIREMENTS.md` — ALERT-01 through ALERT-04, TRIAGE-04, TRIAGE-05 requirements
- `.planning/ROADMAP.md` §Phase 4 — Success criteria and dependency chain
- `.planning/research/SUMMARY.md` — Architecture approach, pitfall #6 (alert storm), pitfall #12 (bulk assign undo)
- `.planning/research/FEATURES.md` — Bulk assign complexity budget, alert SystemConfig keys

### Existing patterns
- `.planning/research/ARCHITECTURE.md` — Permission check locations, ChatNotifier patterns
- `.planning/codebase/CONVENTIONS.md` — Coding patterns, HTMX conventions
- `.planning/codebase/INTEGRATIONS.md` — ChatNotifier integration, SystemConfig usage

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatNotifier` (`apps/emails/services/chat_notifier.py`): 7 existing notify methods — add `notify_unassigned_alert()` following same Cards v2 pattern
- `_heartbeat_job` (`apps/emails/management/commands/run_scheduler.py:36`): 1-minute heartbeat — add unassigned count check here with cooldown
- `SystemConfig` (`apps/core/models.py`): Key-value store with typed casting — add threshold/cooldown keys
- `distillation.py` (`apps/emails/services/distillation.py`): Already queries AssignmentFeedback for corrections — digest can reuse similar queries
- Existing toast system in `base.html`: Stacked, auto-dismiss, close buttons — undo toast extends this
- Thread list templates (`templates/emails/thread_list.html`, `_thread_list_body.html`): Add checkbox + floating bar here
- Stat cards with clickable active states: Existing pattern for badge coloring

### Established Patterns
- HTMX partial swaps for inline updates (thread detail, assignment, status changes)
- `hx-post` + `hx-target` + `hx-swap` for form submissions
- ActivityLog for audit trail of all actions
- Settings page tab structure (SLA presets, config validation) — add alert config tab/section

### Integration Points
- Thread list view (`apps/emails/views.py`): Add bulk endpoints, digest context
- Sidebar template (`templates/base.html`): Badge color logic for unassigned count
- Settings template: Alert threshold/cooldown fields
- Scheduler heartbeat: Unassigned count check + ChatNotifier call

</code_context>

<specifics>
## Specific Ideas

- Floating bottom bar like Slack's bulk actions — shadow, rounded, slides in from bottom
- Chat alert card should include category breakdown, not just a raw count
- Digest patterns should show "was X → now Y" format for clarity (e.g., "STPI tenders → Govt (was General)")
- Badge colors tied to alert threshold: red at 5+ matches when the Chat alert would fire

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-alerts-bulk-actions*
*Context gathered: 2026-03-15*
