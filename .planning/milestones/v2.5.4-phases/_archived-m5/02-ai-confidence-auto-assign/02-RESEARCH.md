# Phase 2: AI Confidence + Auto-Assign - Research

**Researched:** 2026-03-15
**Domain:** AI triage confidence tiers, pipeline auto-assignment, user feedback loop, prompt injection of correction rules
**Confidence:** HIGH

## Summary

This phase extends the existing AI triage pipeline to return confidence tiers (HIGH/MEDIUM/LOW), auto-assign high-confidence threads via matching AssignmentRules, expose accept/reject UX for AI suggestions, and feed correction history back into future triages as distilled rules. All required models (`AssignmentFeedback`, `ai_confidence` fields on Email/Thread) already exist from Phase 1. The work is entirely within established Django/HTMX patterns with no new dependencies.

The implementation touches four layers: (1) AI processor -- add `confidence` to tool schema + TriageResult DTO, (2) pipeline -- inline auto-assign after triage when confidence=HIGH + matching rule, (3) templates -- confidence dot on cards, accept/reject buttons in detail panel, auto badge, (4) distillation -- Haiku call to summarize AssignmentFeedback into compact rules stored in SystemConfig, injected into system prompt.

**Primary recommendation:** Implement in 3 plans: backend (AI schema + pipeline + distillation service), frontend (confidence dot + suggestion bar + accept/reject), integration (wire distillation into scheduler + end-to-end tests).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Colored dot indicator: green (HIGH), amber (MEDIUM), red (LOW)
- Dot placement: after priority chip on thread cards
- Detail panel: confidence shown inside existing AI triage area, not a separate section
- All three tiers use the same dot pattern -- only color changes
- Tooltips on dots showing "AI Confidence: HIGH/MEDIUM/LOW"
- Inline in pipeline: assign immediately after triage when HIGH confidence + matching AssignmentRule (no 3-minute batch delay)
- Existing auto_assign_batch job remains as catch-up/fallback
- Auto-assign threshold starts disabled (threshold=100 in project decisions), enabled after confidence calibration
- Chat notification: reuse existing assignment card format with "(auto-assigned)" label
- Dashboard badge: small muted "auto" pill next to assignee name; disappears when assignee explicitly accepts
- Rejecting an auto-assignment returns thread to unassigned (back to Triage Queue) -- no prompt-for-reassign, no fall-to-next-rule
- Accept/reject buttons live in detail panel only (not on cards)
- Two inline buttons: checkmark (accept) and X (reject) next to AI suggested assignee
- Both auto-assigned and unassigned-with-suggestion threads show accept/reject controls
- After action: bar updates in place via HTMX
- All feedback recorded in AssignmentFeedback model
- Corrections distilled into compact rules (not raw history) injected into AI prompt
- Distillation happens on each poll cycle -- query AssignmentFeedback, generate updated rules
- Distillation done by Claude AI (Haiku call to summarize raw corrections into rules)
- Rules stored in SystemConfig as JSON blob -- bounded token cost (~100-200 tokens)
- Rules format: `<correction_rules>` block in system prompt

### Claude's Discretion
- Exact confidence dot size and color shades
- Spacing and typography of the AI suggestion bar
- AssignmentFeedback model field design (beyond what's specified in requirements)
- How to handle edge case: no AssignmentRule matches despite HIGH confidence (leave unassigned)
- Prompt engineering for the distillation call (Haiku system prompt)
- Whether to cache the distilled rules in SystemConfig or recompute each cycle

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INTEL-01 | AI triage returns confidence tier (HIGH/MEDIUM/LOW) alongside category, priority, and summary | Add `confidence` field to TRIAGE_TOOL schema + TriageResult DTO; Claude returns tier as enum |
| INTEL-02 | Confidence tier displayed on thread cards and detail panels as visual indicator | Template filter `confidence_base` for color mapping; dot after priority chip on cards, inside AI area on detail |
| INTEL-03 | Threads with HIGH confidence auto-assigned when matching AssignmentRule exists | Inline in `process_single_email()` after triage + save; reuse `AssignmentRule` lookup pattern from `auto_assign_batch()` |
| INTEL-04 | Auto-assign threshold configurable via SystemConfig (default: HIGH only) | SystemConfig key `auto_assign_confidence_threshold` = "HIGH"; threshold=100 initially (disabled) |
| INTEL-05 | Auto-assigned threads show "(auto)" badge, can be rejected by assignee | Template badge next to assignee; reject endpoint unassigns thread and records AssignmentFeedback |
| INTEL-06 | User can accept or reject AI assignment suggestion with one click | Two HTMX POST buttons in detail panel suggestion bar; both update UI in place |
| INTEL-07 | Assignment feedback recorded in AssignmentFeedback model | Model exists from Phase 1; record on accept/reject/reassign/auto-assign actions |
| INTEL-08 | Recent correction history injected into AI prompt to improve future triages | Distillation service queries AssignmentFeedback, calls Haiku to summarize, stores rules in SystemConfig, injects into system prompt |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Web framework | Already in use, no change |
| Anthropic SDK | existing | Claude API calls (triage + distillation) | Already in use for two-tier AI |
| HTMX | 2.0 (CDN) | Dynamic UI updates for accept/reject | Already in use for all dashboard interactions |
| Tailwind CSS | v4 (pre-built) | Styling for confidence dots, badges | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | existing | Retry logic for distillation Haiku call | Same retry pattern as existing `_call_claude` |
| pytz | existing | Timezone handling in distillation timestamps | Already imported in ai_processor |

### Alternatives Considered
None. Zero new dependencies per project decision.

## Architecture Patterns

### Recommended Changes by File

```
apps/emails/
├── services/
│   ├── dtos.py              # Add confidence field to TriageResult
│   ├── ai_processor.py      # Add confidence to TRIAGE_TOOL schema + parsing
│   │                        # Add correction rules injection into system prompt
│   ├── pipeline.py          # Add inline auto-assign after triage
│   ├── assignment.py        # Add accept/reject/auto-assign feedback functions
│   └── distillation.py      # NEW: distill AssignmentFeedback into rules
├── views.py                 # Add accept_suggestion, reject_suggestion views
├── urls.py                  # Add accept/reject URL patterns
├── templatetags/
│   └── email_tags.py        # Add confidence_base, confidence_tooltip filters
├── tests/
│   ├── test_ai_confidence.py  # NEW: confidence in triage
│   ├── test_auto_assign_inline.py  # NEW: inline auto-assign in pipeline
│   ├── test_feedback.py       # NEW: accept/reject/feedback recording
│   └── test_distillation.py   # NEW: distillation service
templates/emails/
├── _thread_card.html         # Add confidence dot after priority chip
├── _thread_detail.html       # Add confidence in AI area, accept/reject bar, auto badge
```

### Pattern 1: Confidence in TRIAGE_TOOL Schema
**What:** Add `confidence` as an enum field to the tool_use schema so Claude returns it as structured output.
**When to use:** Every triage call.
**Example:**
```python
# In TRIAGE_TOOL["input_schema"]["properties"]:
"confidence": {
    "type": "string",
    "enum": ["HIGH", "MEDIUM", "LOW"],
    "description": (
        "Your confidence in the category and assignee suggestion. "
        "HIGH = very clear match to a known pattern. "
        "MEDIUM = reasonable guess but ambiguous. "
        "LOW = uncertain, multiple categories could apply."
    ),
}
# Add to "required" list
```

### Pattern 2: Inline Auto-Assign in Pipeline
**What:** After `save_email_to_db()` succeeds, check if thread qualifies for auto-assignment.
**When to use:** Inside `process_single_email()`, after Step 3 (save to DB), before Step 4 (label Gmail).
**Example:**
```python
# In process_single_email(), after save_email_to_db():
if (
    not email_obj.is_spam
    and triage.confidence == "HIGH"
    and _auto_assign_enabled()
    and email_obj.thread
    and email_obj.thread.assigned_to is None
):
    _try_inline_auto_assign(email_obj.thread, triage)
```

### Pattern 3: Feedback Recording
**What:** Record every accept/reject/auto-assign action in AssignmentFeedback.
**When to use:** On accept_suggestion, reject_suggestion views, and in inline auto-assign.
**Example:**
```python
from apps.emails.models import AssignmentFeedback

AssignmentFeedback.objects.create(
    thread=thread,
    suggested_user=suggested_user,
    actual_user=actual_user,  # None if rejected
    action=AssignmentFeedback.FeedbackAction.ACCEPTED,
    confidence_at_time=thread.ai_confidence,
    user_who_acted=request.user,
)
```

### Pattern 4: Distillation Service
**What:** Query recent AssignmentFeedback, call Haiku to summarize corrections into compact rules, store in SystemConfig.
**When to use:** At the start of each poll cycle, before triage calls.
**Example:**
```python
# distillation.py
def distill_correction_rules():
    """Distill AssignmentFeedback into compact rules for prompt injection."""
    feedbacks = AssignmentFeedback.objects.filter(
        action__in=["rejected", "reassigned"],
    ).select_related("thread", "suggested_user", "actual_user").order_by("-created_at")[:50]

    if not feedbacks:
        return  # No corrections to distill

    # Format corrections for Haiku
    corrections_text = _format_corrections(feedbacks)

    # Call Haiku to distill
    rules_json = _call_haiku_distill(corrections_text)

    # Store in SystemConfig
    SystemConfig.objects.update_or_create(
        key="correction_rules",
        defaults={
            "value": rules_json,
            "value_type": SystemConfig.ValueType.JSON,
            "description": "AI-distilled assignment correction rules",
            "category": "ai",
        },
    )
```

### Pattern 5: Prompt Injection of Correction Rules
**What:** Load distilled rules from SystemConfig and inject into the system prompt as a `<correction_rules>` block.
**When to use:** In `AIProcessor.__init__()` or before each triage call.
**Example:**
```python
# In ai_processor.py, when building system prompt:
correction_rules = SystemConfig.get("correction_rules", "")
if correction_rules:
    rules_block = f"\n\n<correction_rules>\n{correction_rules}\n</correction_rules>"
    # Append to raw_prompt before wrapping in cache_control
```

### Anti-Patterns to Avoid
- **Re-computing distillation on every triage call:** Distill once per poll cycle, not per email. Store result in SystemConfig.
- **Raw feedback in prompt:** Never inject raw AssignmentFeedback rows into the prompt. Always distill to compact rules (~100-200 tokens).
- **Blocking pipeline on distillation failure:** Distillation is non-critical. If Haiku call fails, use stale rules or no rules. Never crash the poll cycle.
- **Auto-assigning spam:** Always check `is_spam` before auto-assign.
- **Auto-assigning when threshold disabled:** Respect `auto_assign_confidence_threshold` SystemConfig. When threshold=100 (default), no confidence tier matches.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Assignment logic | Custom assign function | Existing `assign_thread()` from assignment.py | Already handles ActivityLog, Chat notifications, email notifications |
| Rule matching | New matching logic | Existing `AssignmentRule` query pattern from `auto_assign_batch()` | Same category-to-person lookup with priority ordering |
| Template color mapping | Inline conditionals | Template filter `confidence_base` (like existing `priority_base`) | Consistent with project pattern, DRY |
| HTMX partial updates | Custom JS | HTMX `hx-post` + `hx-target` + `hx-swap` | Established project pattern for all form submissions |

## Common Pitfalls

### Pitfall 1: Confidence Dot Not Updating on Thread Preview
**What goes wrong:** Thread.ai_confidence is set on save but `update_thread_preview()` doesn't copy it from the latest email.
**Why it happens:** `update_thread_preview()` in assignment.py currently copies category, priority, ai_summary, ai_draft_reply but NOT ai_confidence.
**How to avoid:** Add `ai_confidence` to the fields copied in `update_thread_preview()` and to the `save(update_fields=[...])` call.
**Warning signs:** Confidence dot shows on detail (from email) but not on cards (from thread).

### Pitfall 2: Auto-Assign Race Condition
**What goes wrong:** Two poll cycles or batch + inline both try to assign the same thread.
**Why it happens:** `auto_assign_batch()` runs every 3 minutes; inline auto-assign runs in pipeline.
**How to avoid:** Use optimistic locking (same pattern as existing `auto_assign_batch`): `Thread.objects.filter(pk=pk, assigned_to__isnull=True).update(...)`. If update returns 0, someone else assigned first -- skip silently.
**Warning signs:** Duplicate ActivityLog entries for the same thread.

### Pitfall 3: System Prompt Cache Invalidation
**What goes wrong:** Correction rules change but prompt caching means Claude uses the old rules.
**Why it happens:** Anthropic prompt caching caches the system prompt block. If rules change, the cache key changes and costs increase.
**How to avoid:** Put correction rules in the user message (after the email content) instead of the system prompt, OR accept the cache miss cost (small, since rules change at most once per poll cycle). The user decision says "correction rules should be in the cached system prompt block" -- so accept the cache miss. Rules change infrequently (only when new feedback exists), so cache miss rate is low.
**Warning signs:** Higher prompt caching costs after enabling corrections.

### Pitfall 4: Distillation Call Crashing Pipeline
**What goes wrong:** Haiku API call fails during distillation, which runs at poll cycle start.
**Why it happens:** API transient errors, rate limits, key issues.
**How to avoid:** Wrap distillation in try/except. On failure, log warning and continue with stale rules. Never let distillation failure prevent email processing.
**Warning signs:** Poll cycles failing with Anthropic API errors when they previously worked.

### Pitfall 5: TriageResult.confidence Missing for Spam-Filtered Emails
**What goes wrong:** Spam-filtered emails bypass AI and get a TriageResult without confidence.
**Why it happens:** `spam_filter.py` creates TriageResult directly without confidence field.
**How to avoid:** Default confidence to empty string in TriageResult dataclass (already done -- field has `default=""`). Spam emails simply have no confidence dot, which is correct.
**Warning signs:** Template errors on spam-flagged threads.

### Pitfall 6: Accept/Reject Requires Resolving Suggested User
**What goes wrong:** Accept button needs to know which User to assign, but `ai_suggested_assignee` is a JSON dict with a name string, not a user ID.
**Why it happens:** AI returns name strings; the pipeline tries to resolve `user_id` but it's optional.
**How to avoid:** In the accept flow, resolve the suggested user from the JSON dict's `user_id` field (if present) or by name lookup (same pattern as `_map_suggested_assignee` in pipeline.py). If no match found, show an error message.
**Warning signs:** Accept button silently fails or assigns to wrong user.

## Code Examples

### Confidence Dot on Thread Card (after priority chip)
```html
<!-- In _thread_card.html, after priority dot span -->
{% if thread.ai_confidence %}
<span class="w-2 h-2 rounded-full bg-{{ thread.ai_confidence|confidence_base }}-500 shrink-0"
      title="AI Confidence: {{ thread.ai_confidence }}"></span>
{% endif %}
```

### Template Filter for Confidence Colors
```python
# In email_tags.py
CONFIDENCE_BASE = {
    "HIGH": "emerald",
    "MEDIUM": "amber",
    "LOW": "red",
}

@register.filter
def confidence_base(value):
    """Return base color family for confidence tier."""
    return CONFIDENCE_BASE.get(value, "slate")

CONFIDENCE_TOOLTIPS = {
    "HIGH": "AI is highly confident in this categorization",
    "MEDIUM": "AI has moderate confidence -- review recommended",
    "LOW": "AI is uncertain -- manual review needed",
}

@register.filter
def confidence_tooltip(value):
    """Return tooltip text for confidence tier."""
    return CONFIDENCE_TOOLTIPS.get(value, "")
```

### Accept/Reject Suggestion Bar in Detail Panel
```html
<!-- In _thread_detail.html, modify AI suggested assignee section -->
{% if ai_suggested_assignee %}
<div class="px-5 py-2 border-t border-blue-200/60 bg-blue-50/50">
    <div class="flex items-center gap-2 text-[11px]">
        <svg class="w-3.5 h-3.5 text-blue-500 shrink-0" ...>...</svg>
        <span class="font-semibold text-blue-700">AI suggests</span>
        <span class="font-bold text-blue-900">{{ ai_suggested_assignee.name }}</span>
        {% if thread.ai_confidence %}
        <span class="w-1.5 h-1.5 rounded-full bg-{{ thread.ai_confidence|confidence_base }}-500"></span>
        {% endif %}
        <!-- Accept/Reject buttons -->
        <div class="ml-auto flex items-center gap-1.5">
            <button hx-post="{% url 'emails:accept_suggestion' thread.pk %}"
                    hx-target="#thread-detail-panel" hx-swap="innerHTML"
                    hx-disabled-elt="this"
                    class="p-1 rounded hover:bg-emerald-100 text-emerald-600 transition-colors"
                    title="Accept suggestion">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
            </button>
            <button hx-post="{% url 'emails:reject_suggestion' thread.pk %}"
                    hx-target="#thread-detail-panel" hx-swap="innerHTML"
                    hx-disabled-elt="this"
                    class="p-1 rounded hover:bg-red-100 text-red-400 transition-colors"
                    title="Dismiss suggestion">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
    </div>
</div>
{% endif %}
```

### Auto Badge Next to Assignee
```html
<!-- In _thread_detail.html, in the assignment display section -->
{% if thread.assigned_to %}
<div class="flex items-center gap-2 px-2.5 py-1 bg-slate-50 rounded-md">
    <div class="w-5 h-5 rounded-full bg-gradient-to-br from-primary-400 to-primary-500 ...">
        {{ thread.assigned_to.first_name.0|default:thread.assigned_to.username.0|upper }}
    </div>
    <span class="text-[11px] font-semibold text-slate-600">{{ thread.assigned_to.get_full_name }}</span>
    {% if thread.is_auto_assigned %}
    <span class="text-[8px] font-medium text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">auto</span>
    {% endif %}
</div>
{% endif %}
```

### Distillation Haiku System Prompt
```python
DISTILLATION_PROMPT = """You are an assignment rule summarizer for an email triage system.

Given a list of corrections (where AI suggested one person but the team assigned someone else),
distill them into compact assignment rules.

Output format: One rule per line, like:
- Sales leads from acme.com domains: assign to Rahul
- Government/Tender emails about STPI: assign to Shreyas
- Support requests in Marathi: assign to Priya

Rules should be specific, actionable, and based on patterns in the corrections.
Maximum 10 rules. Merge similar corrections. Drop one-off corrections that don't form patterns.
If no clear patterns exist, output "No correction rules yet."
"""
```

### Inline Auto-Assign in Pipeline
```python
def _try_inline_auto_assign(thread, triage):
    """Attempt inline auto-assign for HIGH confidence threads.

    Uses optimistic locking to prevent race conditions with batch auto-assign.
    Non-critical -- failures are logged and swallowed.
    """
    try:
        threshold = SystemConfig.get("auto_assign_confidence_threshold", "HIGH")
        # threshold=100 means disabled (no confidence tier matches "100")
        if triage.confidence != threshold:
            return

        rule = (
            AssignmentRule.objects.filter(
                category=triage.category,
                is_active=True,
                assignee__is_active=True,
            )
            .order_by("priority_order")
            .first()
        )
        if not rule:
            return

        # Optimistic locking
        updated = Thread.objects.filter(
            pk=thread.pk,
            assigned_to__isnull=True,
        ).update(
            assigned_to=rule.assignee,
            assigned_by=None,
            assigned_at=timezone.now(),
        )

        if updated:
            # Record auto-assign feedback
            AssignmentFeedback.objects.create(
                thread=thread,
                suggested_user=rule.assignee,
                actual_user=rule.assignee,
                action=AssignmentFeedback.FeedbackAction.AUTO_ASSIGNED,
                confidence_at_time=triage.confidence,
                user_who_acted=None,
            )

            ActivityLog.objects.create(
                thread=thread,
                action=ActivityLog.Action.AUTO_ASSIGNED,
                detail=f"Auto-assigned (HIGH confidence, rule: {triage.category})",
                new_value=rule.assignee.get_full_name() or rule.assignee.username,
            )

            logger.info("Inline auto-assigned thread %s to %s", thread.pk, rule.assignee)

    except Exception:
        logger.exception("Inline auto-assign failed for thread %s", thread.pk)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No confidence tiers | Discrete HIGH/MEDIUM/LOW tiers | Phase 2 (this phase) | Enables auto-assign gating |
| Batch-only auto-assign (3min delay) | Inline + batch fallback | Phase 2 (this phase) | Instant assignment for HIGH confidence |
| No feedback loop | Distilled correction rules in prompt | Phase 2 (this phase) | AI improves over time |

**Deprecated/outdated:**
- Float confidence scores: Explicitly out of scope (Claude's self-reported confidence is uncalibrated; discrete tiers are more honest)

## Open Questions

1. **Whether to inject correction rules in system prompt vs user message**
   - What we know: User decision says "correction rules should be in the cached system prompt block". System prompt uses `cache_control: {"type": "ephemeral"}`.
   - What's unclear: When rules change, the entire system prompt cache is invalidated. This is a cache write cost (~$0.01) per rule change, which happens at most once per poll cycle.
   - Recommendation: Follow the user decision -- put rules in system prompt. The cache miss cost is negligible since rules change infrequently (only when new feedback accumulates). The benefit is that rules are cached for all subsequent triage calls in the same poll cycle.

2. **How to track "is_auto_assigned" for the auto badge**
   - What we know: The badge should disappear when assignee explicitly accepts. Thread model doesn't have an `is_auto_assigned` field.
   - What's unclear: Whether to add a model field or derive from ActivityLog.
   - Recommendation: Add a boolean field `is_auto_assigned` to Thread model (small migration). Set to True on auto-assign, set to False on accept. Simpler than querying ActivityLog on every detail panel render. This is within Claude's discretion per CONTEXT.md.

3. **Distillation frequency and caching**
   - What we know: Distillation should happen each poll cycle per user decision. Poll cycles run every 5 minutes.
   - What's unclear: Whether to always call Haiku or only when new feedback exists.
   - Recommendation: Only distill when new AssignmentFeedback exists since last distillation. Track last distillation timestamp in SystemConfig (`last_distillation_epoch`). Skip distillation call when no new feedback -- saves API costs.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails/tests/ -x -q` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTEL-01 | AI triage returns confidence tier | unit | `pytest apps/emails/tests/test_ai_confidence.py::test_confidence_in_triage_result -x` | Wave 0 |
| INTEL-02 | Confidence displayed on cards and detail | unit | `pytest apps/emails/tests/test_ai_confidence.py::test_confidence_template_filter -x` | Wave 0 |
| INTEL-03 | HIGH confidence auto-assigned with rule | unit | `pytest apps/emails/tests/test_auto_assign_inline.py::test_inline_auto_assign_high_confidence -x` | Wave 0 |
| INTEL-04 | Threshold configurable via SystemConfig | unit | `pytest apps/emails/tests/test_auto_assign_inline.py::test_auto_assign_threshold_disabled -x` | Wave 0 |
| INTEL-05 | Auto badge + reject flow | unit | `pytest apps/emails/tests/test_feedback.py::test_reject_auto_assignment -x` | Wave 0 |
| INTEL-06 | Accept/reject one-click | unit | `pytest apps/emails/tests/test_feedback.py::test_accept_suggestion -x` | Wave 0 |
| INTEL-07 | Feedback recorded in AssignmentFeedback | unit | `pytest apps/emails/tests/test_feedback.py::test_feedback_recorded -x` | Wave 0 |
| INTEL-08 | Correction history injected into prompt | unit | `pytest apps/emails/tests/test_distillation.py::test_distill_corrections -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_ai_confidence.py apps/emails/tests/test_auto_assign_inline.py apps/emails/tests/test_feedback.py apps/emails/tests/test_distillation.py -x -q`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_ai_confidence.py` -- covers INTEL-01, INTEL-02
- [ ] `apps/emails/tests/test_auto_assign_inline.py` -- covers INTEL-03, INTEL-04
- [ ] `apps/emails/tests/test_feedback.py` -- covers INTEL-05, INTEL-06, INTEL-07
- [ ] `apps/emails/tests/test_distillation.py` -- covers INTEL-08

## Sources

### Primary (HIGH confidence)
- `/apps/emails/services/ai_processor.py` -- existing TRIAGE_TOOL schema, two-tier AI, prompt caching pattern
- `/apps/emails/services/pipeline.py` -- existing `process_single_email()` flow, `save_email_to_db()`
- `/apps/emails/services/assignment.py` -- existing `auto_assign_batch()`, `assign_thread()`, optimistic locking pattern
- `/apps/emails/models.py` -- AssignmentFeedback model (Phase 1), AssignmentRule, Thread.ai_confidence field
- `/apps/emails/services/dtos.py` -- TriageResult dataclass
- `/apps/emails/templatetags/email_tags.py` -- existing filter patterns (priority_base, status_base, tooltips)
- `/templates/emails/_thread_card.html` -- existing card layout with priority dot, AI summary, badges
- `/templates/emails/_thread_detail.html` -- existing AI suggestion bar, action bar, HTMX patterns

### Secondary (MEDIUM confidence)
- Anthropic prompt caching documentation -- ephemeral cache_control behavior, cache invalidation on prompt change

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new deps, all existing libraries
- Architecture: HIGH -- all patterns directly extend existing code with clear integration points
- Pitfalls: HIGH -- identified from direct code reading of existing pipeline, assignment, and template code

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable codebase, no external dependency changes)
