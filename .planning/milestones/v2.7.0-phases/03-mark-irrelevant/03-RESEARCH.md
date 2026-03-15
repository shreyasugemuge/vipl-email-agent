# Phase 3: Mark Irrelevant - Research

**Researched:** 2026-03-16
**Domain:** Django thread status extension + HTMX modal + queryset filtering
**Confidence:** HIGH

## Summary

Phase 3 adds a "Mark Irrelevant" action that lets gatekeepers/admins dismiss threads with a mandatory reason. The implementation touches: Thread.Status choices (add IRRELEVANT), ActivityLog.Action choices (add MARKED_IRRELEVANT and REVERTED_IRRELEVANT), two new views (mark_irrelevant, revert_irrelevant), queryset filtering changes in thread_list to exclude irrelevant threads from default views, a new stat card for gatekeepers, a modal dialog in the detail panel, and context menu integration.

This is entirely within existing patterns. The mark_spam flow is the closest analog: a POST view that changes state, creates an ActivityLog entry, and re-renders the detail panel. The main new element is the reason modal (HTMX-driven textarea dialog), which has no existing equivalent but is straightforward with HTMX's `hx-post` + form pattern. The context menu integration follows the exact same `{% if is_admin %}` gating pattern (which Phase 1 will have converted to `{% if user.can_triage %}`).

**Primary recommendation:** Follow the mark_spam view pattern exactly -- `@login_required`, `@require_POST`, permission check, `transaction.atomic()`, status change + ActivityLog creation, re-render detail panel. The modal is a client-side HTML/JS overlay that submits via HTMX POST.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Modal with textarea for mandatory reason (click button -> modal overlay with reason textarea + confirm/cancel)
- Button in a standalone section in the detail panel (below AI triage area, separate from mark-spam)
- Amber/warning button styling (not red like spam, not gray)
- Keyboard shortcut: I key opens the modal
- Modal submitted via HTMX POST, swaps detail panel on success
- Irrelevant threads hidden from Triage Queue, My Inbox, All Open views by default
- Accessible via status filter dropdown ("Irrelevant" option alongside New/Acknowledged/Closed)
- Excluded from Unassigned, Urgent, New stat cards
- New "Irrelevant" stat card visible to gatekeepers/admins only
- Muted "Irrelevant" badge on thread cards when filtered in
- Undo supported: "Revert to New" button on irrelevant thread detail
- Prominent styled activity entry with amber background, full reason text inline
- Badge only on cards; full reason visible only in activity timeline
- On revert: both original and reversal entries stay in timeline
- Context menu: Mark Irrelevant in Status group (after Acknowledge and Close)
- Context menu click opens detail panel + auto-opens reason modal
- Completely hidden from members (not grayed out)
- Gated by gatekeeper/admin permission check (uses `can_triage` helper from Phase 1)

### Claude's Discretion
- Modal design details (exact dimensions, animation, z-index)
- Irrelevant badge color shade and sizing
- Stat card positioning among existing stat cards
- "Revert to New" button placement within detail panel

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRIAGE-01 | Gatekeeper/admin can mark a thread as irrelevant with mandatory free-text reason | mark_irrelevant view + modal textarea + `Thread.Status.IRRELEVANT` + permission gate via `user.can_triage` |
| TRIAGE-02 | Irrelevant threads are closed immediately and excluded from unassigned count | Status set to IRRELEVANT + thread_list queryset excludes IRRELEVANT from `open_q` and sidebar counts |
| TRIAGE-03 | Mark-irrelevant available via button in detail panel and right-click context menu | Detail panel standalone section + context menu Status group entry with `{% if user.can_triage %}` |
| TRIAGE-06 | Irrelevant reason stored in ActivityLog and visible in thread detail activity timeline | ActivityLog with action=MARKED_IRRELEVANT, detail=reason text, styled amber in timeline template |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Web framework | Already in use |
| HTMX | 2.0 (CDN) | Modal form submission + detail panel swap | Already in use |

### Supporting
No new dependencies. Zero changes to requirements.txt.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTMX modal | Alpine.js modal | Adds new dependency, HTMX already handles the POST pattern |
| Inline textarea (no modal) | Simpler but worse UX | Modal provides focused input + confirm/cancel, matches user decision |

## Architecture Patterns

### Changes Map

```
apps/emails/models.py           # Thread.Status.IRRELEVANT + ActivityLog.Action additions
apps/emails/migrations/0017_*   # Add IRRELEVANT status choice + new action choices
apps/emails/views.py            # mark_irrelevant + revert_irrelevant views + thread_list filtering
apps/emails/urls.py             # 2 new URL patterns
templates/emails/_thread_detail.html    # Mark irrelevant section + modal + revert button
templates/emails/_context_menu.html     # Mark Irrelevant entry in Status group
templates/emails/thread_list.html       # Irrelevant stat card + status filter option + badge
templates/emails/_thread_detail.html    # Amber-styled activity timeline entry for irrelevant
```

### Pattern 1: Mark Irrelevant View (follows mark_spam pattern)

**What:** POST endpoint that validates permission, requires reason, sets status, creates ActivityLog, re-renders detail.
**When to use:** This is the core action endpoint.
**Example:**
```python
# Source: existing mark_spam pattern in apps/emails/views.py:1516
@login_required
@require_POST
def mark_irrelevant(request, pk):
    """Mark a thread as irrelevant. Gatekeeper/admin only."""
    user = request.user
    if not user.can_triage:  # Phase 1 helper
        return HttpResponseForbidden("Permission denied.")

    reason = request.POST.get("reason", "").strip()
    if not reason:
        return HttpResponseForbidden("Reason is required.")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"), pk=pk
    )

    with transaction.atomic():
        old_status = thread.status
        thread.status = Thread.Status.IRRELEVANT
        thread.save(update_fields=["status", "updated_at"])

        ActivityLog.objects.create(
            thread=thread,
            user=user,
            action=ActivityLog.Action.MARKED_IRRELEVANT,
            detail=reason,
            old_value=old_status,
            new_value=Thread.Status.IRRELEVANT,
        )

    # Re-render detail panel
    # ... (same pattern as mark_spam: _build_thread_detail_context + render_to_string)
```

### Pattern 2: Revert to New View

**What:** POST endpoint that resets status to NEW, clears assignment, creates reversal ActivityLog.
**Example:**
```python
@login_required
@require_POST
def revert_irrelevant(request, pk):
    """Revert an irrelevant thread to New status. Gatekeeper/admin only."""
    user = request.user
    if not user.can_triage:
        return HttpResponseForbidden("Permission denied.")

    thread = get_object_or_404(
        Thread.objects.select_related("assigned_to", "assigned_by"), pk=pk
    )

    if thread.status != Thread.Status.IRRELEVANT:
        return HttpResponseForbidden("Thread is not marked irrelevant.")

    with transaction.atomic():
        thread.status = Thread.Status.NEW
        thread.assigned_to = None
        thread.assigned_by = None
        thread.assigned_at = None
        thread.save(update_fields=["status", "assigned_to", "assigned_by", "assigned_at", "updated_at"])

        ActivityLog.objects.create(
            thread=thread,
            user=user,
            action=ActivityLog.Action.REVERTED_IRRELEVANT,
            detail=f"Reverted from irrelevant to new by {user.get_full_name() or user.username}",
            old_value=Thread.Status.IRRELEVANT,
            new_value=Thread.Status.NEW,
        )
```

### Pattern 3: Modal Dialog (HTMX + inline HTML)

**What:** Modal overlay with textarea + confirm/cancel, triggered by button click or keyboard shortcut I.
**Example:**
```html
<!-- Modal trigger button in detail panel -->
<button type="button" onclick="openIrrelevantModal()"
        class="inline-flex items-center gap-1 px-3 py-1.5 text-[10px] font-bold
               text-amber-600 bg-amber-50 rounded-md hover:bg-amber-100
               transition-colors cursor-pointer border border-amber-200/60">
    Mark Irrelevant
</button>

<!-- Modal overlay (hidden by default) -->
<div id="irrelevant-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/50">
    <div class="bg-white rounded-lg shadow-xl p-5 w-full max-w-md">
        <h3 class="text-sm font-bold text-slate-800 mb-3">Mark as Irrelevant</h3>
        <form hx-post="{% url 'emails:mark_irrelevant' thread.pk %}"
              hx-target="#thread-detail-panel" hx-swap="innerHTML">
            {% csrf_token %}
            <textarea name="reason" required rows="3" placeholder="Why is this thread irrelevant?"
                      class="w-full border border-slate-300 rounded-md p-2 text-sm"></textarea>
            <div class="flex justify-end gap-2 mt-3">
                <button type="button" onclick="closeIrrelevantModal()"
                        class="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded">Cancel</button>
                <button type="submit" hx-disabled-elt="this"
                        class="px-3 py-1.5 text-xs font-bold text-white bg-amber-500 hover:bg-amber-600 rounded">
                    Confirm
                </button>
            </div>
        </form>
    </div>
</div>

<script>
function openIrrelevantModal() {
    document.getElementById('irrelevant-modal').classList.remove('hidden');
    document.querySelector('#irrelevant-modal textarea').focus();
}
function closeIrrelevantModal() {
    document.getElementById('irrelevant-modal').classList.add('hidden');
}
// Keyboard shortcut: I key
document.addEventListener('keydown', function(e) {
    if (e.key === 'I' || e.key === 'i') {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        const modal = document.getElementById('irrelevant-modal');
        if (modal) openIrrelevantModal();
    }
});
</script>
```

### Pattern 4: Queryset Filtering Changes

**What:** Exclude IRRELEVANT from default views, include only via explicit status filter.
**Key change in thread_list view:**
```python
# Current open_q (line 184 in views.py):
open_q = Q(status__in=["new", "acknowledged"])
# This already excludes "closed" and will naturally exclude "irrelevant" -- no change needed.

# The "closed" view also won't show irrelevant -- correct behavior.
# Irrelevant threads visible ONLY when ?status=irrelevant is set explicitly.
```

**Sidebar counts -- current aggregation (line 185-192) already uses explicit status values,
so IRRELEVANT is automatically excluded from unassigned/mine/all_open/closed/urgent/new counts.**

Only addition needed: an `irrelevant` count for the new stat card:
```python
sidebar_counts = base_threads.aggregate(
    # ... existing counts ...
    irrelevant=Count("pk", filter=Q(status="irrelevant")),
)
```

### Pattern 5: Activity Timeline Styling

**What:** Amber-highlighted activity entry for irrelevant actions, with full reason text.
**Key change in _thread_detail.html timeline:**
```html
{% elif item.type == "activity" %}
    {% if item.obj.action == "marked_irrelevant" %}
    <div class="flex items-start gap-2 px-5 py-2 text-[11px] bg-amber-50 border-l-2 border-amber-400 rounded-r">
        <div class="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0 mt-1"></div>
        <div>
            <span class="font-semibold text-amber-700">Marked Irrelevant</span>
            <span class="text-slate-500"> by {{ item.obj.user.get_full_name }}</span>
            <p class="text-slate-600 mt-0.5">{{ item.obj.detail }}</p>
        </div>
        <span class="text-slate-300 tabular-nums shrink-0 ml-auto">{{ item.obj.created_at|time_ago }}</span>
    </div>
    {% elif item.obj.action == "reverted_irrelevant" %}
    <div class="flex items-start gap-2 px-5 py-2 text-[11px] bg-emerald-50 border-l-2 border-emerald-400 rounded-r">
        <!-- Similar structure with green styling for revert -->
    </div>
    {% else %}
    <!-- existing default activity rendering -->
    {% endif %}
{% endif %}
```

### Anti-Patterns to Avoid
- **Overloading Thread.Status.CLOSED for irrelevant:** User explicitly decided IRRELEVANT is a distinct status. Do not reuse CLOSED with a flag.
- **Separate reason model/table:** The reason fits naturally in ActivityLog.detail field (TextField, unlimited length). No new model needed.
- **Graying out for members:** Context menu entry must be completely hidden (not grayed out) from non-can_triage users. Same pattern as "Assign to..." which is hidden for members.
- **Inline textarea (no modal):** User decided modal overlay. Do not use `hx-confirm` (that's a browser dialog, not a styled modal with textarea).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Permission checks | Custom decorators | `user.can_triage` property (Phase 1) | Centralized, template-accessible |
| Activity logging | Custom log table | Existing `ActivityLog` model | Already has all needed fields (action, detail, old_value, new_value) |
| Status filtering | Custom queryset manager | URL query params + existing filter pattern | Already works with `?status=irrelevant` |
| Modal dialog | Third-party modal library | Inline HTML + JS + HTMX POST | Zero dependencies, matches existing patterns |

## Common Pitfalls

### Pitfall 1: Forgetting to exclude IRRELEVANT from sidebar counts
**What goes wrong:** Irrelevant threads counted in "All Open" or "Unassigned" totals.
**Why it happens:** The `open_q` filter already uses `status__in=["new", "acknowledged"]` which naturally excludes irrelevant. But if anyone changes this to exclude only "closed", irrelevant threads leak through.
**How to avoid:** Verify all sidebar_counts aggregation queries explicitly do NOT include "irrelevant" in any "open" filter. The current pattern is safe.
**Warning signs:** Sidebar counts don't decrease after marking threads irrelevant.

### Pitfall 2: Modal not closing after HTMX swap
**What goes wrong:** After successful mark_irrelevant POST, HTMX swaps the detail panel but the modal overlay stays visible.
**Why it happens:** The modal is in the detail panel HTML that gets swapped, so it actually goes away. But if the modal is placed outside the swap target, it persists.
**How to avoid:** Keep the modal HTML inside `#thread-detail-panel` so it gets replaced on swap. Or use `htmx:afterSwap` event to explicitly close it.
**Warning signs:** Stale modal visible after successful action.

### Pitfall 3: Empty reason submission
**What goes wrong:** Thread marked irrelevant without explanation, defeating audit purpose.
**Why it happens:** Client-side `required` attribute bypassed or JS form submission skips validation.
**How to avoid:** Server-side validation in the view (check `reason.strip()` is not empty, return 403 if so). Client-side `required` on textarea is defense-in-depth only.

### Pitfall 4: Context menu auto-open modal race condition
**What goes wrong:** Context menu click should open detail panel AND auto-open the modal, but modal opens before panel loads.
**Why it happens:** The detail panel loads via HTMX GET, and the modal trigger fires before the response arrives.
**How to avoid:** Use URL param like `?open_modal=irrelevant` on the detail panel GET, and check in template JS: `if (new URLSearchParams(location.search).get('open_modal') === 'irrelevant') openIrrelevantModal()`. Or use `htmx:afterSettle` event.
**Warning signs:** Modal flash or modal not appearing after context menu click.

### Pitfall 5: Migration ordering
**What goes wrong:** New migration conflicts with Phase 1 migration if both touch Thread model.
**Why it happens:** Phase 3 depends on Phase 1 (for `can_triage`), so Phase 1 migration must come first.
**How to avoid:** Phase 3 migration depends on Phase 1's migration that adds TRIAGE_LEAD role. Number accordingly (0017 or later, after Phase 1's migrations).

## Code Examples

### URL Patterns
```python
# In apps/emails/urls.py -- add to thread-level endpoints
path("threads/<int:pk>/mark-irrelevant/", views.mark_irrelevant, name="mark_irrelevant"),
path("threads/<int:pk>/revert-irrelevant/", views.revert_irrelevant, name="revert_irrelevant"),
```

### Model Changes
```python
# Thread.Status -- add IRRELEVANT
class Status(models.TextChoices):
    NEW = "new", "New"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    CLOSED = "closed", "Closed"
    IRRELEVANT = "irrelevant", "Irrelevant"

# ActivityLog.Action -- add two new actions
MARKED_IRRELEVANT = "marked_irrelevant", "Marked Irrelevant"
REVERTED_IRRELEVANT = "reverted_irrelevant", "Reverted to New"
```

### Context Menu Entry (after Close, before Spam group)
```html
{% if user.can_triage and thread.status != "irrelevant" %}
<button role="menuitem" tabindex="-1"
        class="ctx-item flex items-center justify-between w-full px-3 py-1.5 text-[12px] hover:bg-slate-700/60 transition-colors"
        hx-get="{% url 'emails:thread_detail' thread.pk %}?open_modal=irrelevant"
        hx-target="#thread-detail-panel"
        onclick="closeContextMenu()">
    <span class="flex items-center gap-2">
        <svg class="w-3.5 h-3.5 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"/>
        </svg>
        Mark Irrelevant
    </span>
    <kbd class="text-slate-500 text-[10px] font-mono ml-4">I</kbd>
</button>
{% endif %}
```

### Thread Card Badge
```html
{% if thread.status == "irrelevant" %}
<span class="text-[9px] font-bold text-amber-500 bg-amber-50 px-1.5 py-0.5 rounded-full border border-amber-200/40">
    Irrelevant
</span>
{% endif %}
```

### Stat Card (gatekeepers/admins only)
```html
{% if user.can_triage and sidebar_counts.irrelevant > 0 %}
<a href="{% url 'emails:thread_list' %}?status=irrelevant"
   hx-get="{% url 'emails:thread_list' %}?status=irrelevant"
   hx-target="#thread-list-body" hx-push-url="true"
   data-stat="irrelevant"
   class="stat-card flex flex-col items-center gap-0.5 px-3 py-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] transition-colors cursor-pointer">
    <span class="text-[12px] font-extrabold text-amber-600 tabular-nums">{{ sidebar_counts.irrelevant }}</span>
    <span class="text-[9px] font-bold text-amber-500/70 uppercase">Irrelevant</span>
</a>
{% endif %}
```

## State of the Art

No technology changes. This phase uses the same Django 4.2 + HTMX 2.0 + Tailwind v4 stack already in the project. The HTMX modal pattern is well-established and documented.

## Open Questions

1. **Modal auto-open from context menu**
   - What we know: Context menu click should open detail panel + auto-open the reason modal (two-step flow per CONTEXT.md)
   - What's unclear: Best mechanism to trigger modal after HTMX detail panel load
   - Recommendation: Use query param `?open_modal=irrelevant` on the detail GET, check in template `<script>` on page/swap init. This is simpler and more reliable than event-based approaches.

2. **Keyboard shortcut I scope**
   - What we know: I key opens the modal, should not fire in text inputs
   - What's unclear: Should it work when no thread is selected (detail panel empty)?
   - Recommendation: Only attach the listener when detail panel contains the modal element. Guard with `if (document.getElementById('irrelevant-modal'))`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails/tests/test_mark_irrelevant.py -x` |
| Full suite command | `pytest -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TRIAGE-01 | Gatekeeper/admin can mark thread irrelevant with reason | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestMarkIrrelevantView -x` | Wave 0 |
| TRIAGE-01 | Reason is mandatory (empty reason rejected) | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestMarkIrrelevantView::test_empty_reason_rejected -x` | Wave 0 |
| TRIAGE-01 | Members cannot mark irrelevant (403) | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestMarkIrrelevantView::test_member_forbidden -x` | Wave 0 |
| TRIAGE-02 | Irrelevant threads excluded from default views | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestIrrelevantFiltering -x` | Wave 0 |
| TRIAGE-02 | Irrelevant threads excluded from sidebar counts | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestIrrelevantFiltering::test_sidebar_counts_exclude_irrelevant -x` | Wave 0 |
| TRIAGE-03 | Context menu shows Mark Irrelevant for gatekeepers | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestContextMenuIntegration -x` | Wave 0 |
| TRIAGE-03 | Context menu hides Mark Irrelevant from members | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestContextMenuIntegration::test_member_no_irrelevant -x` | Wave 0 |
| TRIAGE-06 | ActivityLog created with reason on mark | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestMarkIrrelevantView::test_activity_log_created -x` | Wave 0 |
| TRIAGE-06 | ActivityLog created on revert | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestRevertIrrelevantView -x` | Wave 0 |
| -- | Revert resets status to NEW and clears assignment | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestRevertIrrelevantView::test_revert_resets_status -x` | Wave 0 |
| -- | Irrelevant threads accessible via ?status=irrelevant | unit | `pytest apps/emails/tests/test_mark_irrelevant.py::TestIrrelevantFiltering::test_status_filter_shows_irrelevant -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_mark_irrelevant.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_mark_irrelevant.py` -- covers TRIAGE-01, TRIAGE-02, TRIAGE-03, TRIAGE-06
- [ ] Conftest fixture: `triage_lead_user` (depends on Phase 1 Role.TRIAGE_LEAD) -- if not already added by Phase 1

## Sources

### Primary (HIGH confidence)
- `apps/emails/views.py` -- mark_spam view pattern (lines 1516-1556), thread_list queryset filtering (lines 98-237), context menu view (lines 1213-1237)
- `apps/emails/models.py` -- Thread.Status choices (line 12-15), ActivityLog model + Action choices (lines 188-245)
- `apps/emails/urls.py` -- existing URL pattern structure
- `templates/emails/_context_menu.html` -- role gating pattern (`{% if is_admin %}`)
- `templates/emails/_thread_detail.html` -- mark spam button pattern, activity timeline rendering
- `templates/emails/thread_list.html` -- stat cards, sidebar counts, status filter
- `conftest.py` -- test fixtures (admin_user, member_user, create_thread, create_email)
- `.planning/phases/01-role-permission-foundation/01-RESEARCH.md` -- Phase 1 helper properties (can_triage, can_assign)

### Secondary (MEDIUM confidence)
- HTMX modal pattern -- well-established, no external docs needed; project already uses HTMX POST forms extensively

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all existing libraries
- Architecture: HIGH -- directly follows mark_spam pattern with minor additions
- Pitfalls: HIGH -- identified from code inspection of existing patterns
- Modal UX: MEDIUM -- auto-open from context menu needs implementation testing

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable stack, no version changes expected)
