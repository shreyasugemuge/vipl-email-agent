# Phase 1: Thread Model + Data Migration - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Group emails into threads by `gmail_thread_id` with thread-level status, assignment, and SLA. Thread model wraps existing Email model. No data migration of existing records — clean slate deployment.

</domain>

<decisions>
## Implementation Decisions

### Thread owns everything
- Thread model is the single source of truth for status, assignment, and SLA
- Thread has: status, assigned_to, assigned_by, assigned_at, sla_ack_deadline, sla_respond_deadline
- Thread stores latest triage fields: category, priority, ai_summary, ai_draft_reply (copied from most recent email's triage)
- Email keeps its existing fields (status, assigned_to, etc.) frozen — no code reads/writes them after migration, but columns stay on the model

### Clean slate — no data migration
- Wipe all existing Email, ActivityLog, and AttachmentMetadata records on deploy
- Thread model starts empty — first poll cycle creates the first threads
- No backfill migration needed — simplifies deployment significantly

### Thread status choices
- Claude's Discretion: Pick status choices based on requirements and future scope (likely New/Acknowledged/Closed, dropping Replied since reply detection is out of scope)

### Empty gmail_thread_id handling
- Claude's Discretion: Decide how to handle emails with empty/missing gmail_thread_id (likely create single-message thread per email — no orphans)

### Thread lifecycle
- Acknowledge = "I've seen this, I'll handle it" — lightweight, stops SLA ack timer (matches current Email behavior)
- SLA deadlines set at thread level, not per-email — when a new email reopens a thread, SLA resets
- Auto-reopen behavior: Claude's Discretion (likely reopen to New when closed thread gets new email — matches Gmelius/Hiver)

### ActivityLog refactored to thread level
- ActivityLog gets thread FK (required), email FK becomes optional (for per-message events)
- Old activity logs wiped along with emails — clean slate
- New action types added: NEW_EMAIL_RECEIVED, REOPENED, THREAD_CREATED
- Existing actions (assigned, acknowledged, closed, etc.) now apply to threads

</decisions>

<specifics>
## Specific Ideas

- User wants Gmelius/Hiver-level shared inbox UX as the target experience
- "Delete those shits" — no sentimentality about existing data, clean break preferred
- Thread displays message count and latest message preview (subject, sender, timestamp) per THRD-05

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SoftDeleteModel` + `TimestampedModel` base classes: Thread should extend both
- `Email.gmail_thread_id` field: Already captured, used as the grouping key
- `Email.Status` TextChoices: Reference for Thread status choices
- `ActivityLog.Action` TextChoices: Extend with thread-specific actions
- `AssignmentRule` model: Thread assignment can reuse same category-based rules

### Established Patterns
- ForeignKey with `on_delete=models.SET_NULL` for user references (assigned_to, assigned_by)
- `related_name` convention: descriptive like `assigned_emails`, `activity_logs`
- `JSONField(default=list/dict)` for flexible metadata
- `class Meta: ordering = ["-received_at"]` for default sort
- `TextChoices` for enum fields

### Integration Points
- `apps/emails/models.py`: Thread model goes here alongside Email
- `apps/emails/services/pipeline.py`: Will need to create/update Thread on email processing (Phase 2)
- `apps/emails/services/assignment.py`: Will shift from Email to Thread assignment (Phase 2)
- `apps/emails/views.py`: Dashboard queries will shift from Email to Thread (Phase 3)
- `apps/emails/admin.py`: Thread admin registration

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-thread-model-data-migration*
*Context gathered: 2026-03-15*
