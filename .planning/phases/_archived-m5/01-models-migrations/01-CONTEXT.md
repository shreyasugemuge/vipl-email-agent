# Phase 1: Models + Migrations - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

All new database models and fields needed by v2.5.0 features, delivered in one migration batch. No UI, no business logic, no views — just schema.

</domain>

<decisions>
## Implementation Decisions

### New models
- **ThreadReadState**: user (FK), thread (FK), is_read (bool, default False), read_at (DateTimeField, null). Unique together (user, thread).
- **SpamFeedback**: user (FK), thread (FK, null), email (FK, null), original_verdict (bool), user_verdict (bool), created_at. Records each spam/not-spam correction.
- **SenderReputation**: sender_address (EmailField, unique, db_index), total_count (int, default 0), spam_count (int, default 0), is_blocked (bool, default False), updated_at. Tracks per-sender spam ratio.
- **AssignmentFeedback**: thread (FK), email (FK, null), suggested_user (FK, null), actual_user (FK, null), action (choices: accepted/rejected/reassigned/auto_assigned), confidence_at_time (CharField, null), user_who_acted (FK), created_at.

### New fields on existing models
- **Thread**: `category_overridden` (BooleanField, default False), `priority_overridden` (BooleanField, default False) — prevents pipeline from overwriting user edits
- **Thread**: `ai_confidence` (CharField, max_length=10, blank, default "") — stores HIGH/MEDIUM/LOW tier
- **Email**: `ai_confidence` (CharField, max_length=10, blank, default "") — raw confidence from triage

### New ActivityLog actions
- `SPAM_MARKED = "spam_marked"` — user marked thread as spam
- `SPAM_UNMARKED = "spam_unmarked"` — user marked thread as not-spam
- `PRIORITY_CHANGED = "priority_changed"` — user changed priority
- `CATEGORY_CHANGED = "category_changed"` — user changed category
- `AUTO_ASSIGNED = "auto_assigned"` — system auto-assigned based on confidence

### Migration strategy
- Single migration file for all new models and fields
- All new fields have defaults (no data migration needed)
- Must run cleanly on SQLite (dev) and PostgreSQL 12.3 (prod)

### Claude's Discretion
- Exact field ordering in models
- Whether to add Meta.indexes vs db_index=True on individual fields
- Model __str__ implementations

</decisions>

<specifics>
## Specific Ideas

No specific requirements — schema follows directly from research ARCHITECTURE.md and FEATURES.md specifications.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SoftDeleteModel` (apps/core/models.py): Base class for all models with soft delete
- `TimestampedModel` (apps/core/models.py): created_at/updated_at auto fields
- `ActivityLog.Action` (apps/emails/models.py): TextChoices enum to extend with new actions

### Established Patterns
- All models inherit SoftDeleteModel + TimestampedModel
- FK to User uses `settings.AUTH_USER_MODEL`
- Related names follow pattern: `{related_thing}_{model}s` (e.g., `assigned_threads`)
- Boolean fields use `models.BooleanField(default=False)`

### Integration Points
- Thread model (apps/emails/models.py ~line 9): add override flags + ai_confidence
- Email model (apps/emails/models.py ~line 72): add ai_confidence
- ActivityLog.Action (apps/emails/models.py ~line 185): extend TextChoices

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-models-migrations*
*Context gathered: 2026-03-15*
