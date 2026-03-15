# Phase 2: AI Confidence + Auto-Assign - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

AI triage returns confidence tiers (HIGH/MEDIUM/LOW), high-confidence threads auto-assign via pipeline, users can accept/reject AI suggestions, and past corrections feed back into future triages as distilled rules. Requirements: INTEL-01 through INTEL-08.

</domain>

<decisions>
## Implementation Decisions

### Confidence display
- Colored dot indicator: green (HIGH), amber (MEDIUM), red (LOW)
- Dot placement: after priority chip on thread cards
- Detail panel: confidence shown inside existing AI triage area, not a separate section
- All three tiers use the same dot pattern — only color changes (no special treatment for LOW)
- Tooltips on dots showing "AI Confidence: HIGH/MEDIUM/LOW" (consistent with existing chip tooltip pattern)

### Auto-assign behavior
- Inline in pipeline: assign immediately after triage when HIGH confidence + matching AssignmentRule (no 3-minute batch delay)
- Existing auto_assign_batch job remains as catch-up/fallback for edge cases
- Auto-assign threshold starts disabled (already decided: threshold=100 in project decisions), enabled after confidence calibration
- Chat notification: reuse existing assignment card format with "(auto-assigned)" label
- Dashboard badge: small muted "auto" pill next to assignee name; disappears when assignee explicitly accepts

### Reject flow
- Rejecting an auto-assignment returns thread to unassigned (back to Triage Queue)
- No prompt-for-reassign, no fall-to-next-rule — simple unassign

### Feedback UX
- Accept/reject buttons live in detail panel only (not on cards)
- Two inline buttons: checkmark (accept) and X (reject) next to AI suggested assignee
- Both auto-assigned and unassigned-with-suggestion threads show accept/reject controls
- After action: bar updates in place — "Assigned to [name]" in green (accept) or "Suggestion dismissed" in muted (reject)
- All feedback recorded in AssignmentFeedback model (accept/reject/reassign/auto-assign)

### Correction injection — running memory
- Corrections are distilled into compact rules (not raw history) injected into the AI prompt
- Distillation happens on each poll cycle — query AssignmentFeedback, generate updated rules
- Distillation done by Claude AI (Haiku call to summarize raw corrections into rules)
- Rules stored in SystemConfig as JSON blob — always fresh, bounded token cost (~100-200 tokens)
- Rules format: `<correction_rules>` block in system prompt with category/sender/outcome patterns

### Claude's Discretion
- Exact confidence dot size and color shades
- Spacing and typography of the AI suggestion bar
- AssignmentFeedback model field design (beyond what's specified in requirements)
- How to handle edge case: no AssignmentRule matches despite HIGH confidence (leave unassigned)
- Prompt engineering for the distillation call (Haiku system prompt)
- Whether to cache the distilled rules in SystemConfig or recompute each cycle

</decisions>

<specifics>
## Specific Ideas

- "Some kind of running memory should be maintained — history will always be relevant" — user wants corrections to accumulate and compound, not slide off a window
- Distilled rules should read like human-written assignment instructions (e.g., "Sales leads from acme.com: assign Rahul")
- Auto badge should feel subtle — muted color, not attention-grabbing

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AssignmentRule` model (apps/emails/models.py:288): category-to-person rules with priority_order — used for matching HIGH-confidence threads
- `auto_assign_batch()` (apps/emails/services/assignment.py:251): existing batch job, runs every 3 min — becomes fallback
- `TRIAGE_TOOL` schema (apps/emails/services/ai_processor.py:52): structured tool output — needs `confidence` field added
- `TriageResult` DTO (apps/emails/services/dtos.py:50): needs `confidence` field
- `ActivityLog.Action` choices: already has `auto_assigned` action type
- `ChatNotifier`: existing assignment card format to extend with "(auto)" label
- Status/priority chip tooltips pattern: already implemented in Phase 14 — reuse for confidence dot tooltips

### Established Patterns
- Two-tier AI: Haiku default, Sonnet for CRITICAL — distillation call should also use Haiku
- Prompt caching via `cache_control: {"type": "ephemeral"}` — correction rules should be in the cached system prompt block
- SystemConfig key-value store for runtime config — natural home for distilled rules JSON
- HTMX partials for dashboard updates — accept/reject should use hx-post with OOB swaps
- Existing chip/badge patterns (category, priority, spam, "(auto)") — confidence dot follows same visual system

### Integration Points
- `process_single_email()` in pipeline.py: where inline auto-assign would be added (after triage, before save)
- `ai_processor.py` system prompt: where correction rules get injected
- Thread detail template: where AI suggestion bar with accept/reject lives
- Thread card template: where confidence dot gets added after priority chip
- `run_scheduler`: where distillation call would happen (before poll job)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-ai-confidence-auto-assign*
*Context gathered: 2026-03-15*
