# Phase 4: Alerts + Bulk Actions - Research

**Researched:** 2026-03-16
**Domain:** Google Chat alerts, bulk HTMX operations, AI corrections digest for Django triage dashboard
**Confidence:** HIGH

## Summary

Phase 4 adds three distinct features to the gatekeeper's toolkit: (1) unassigned count alerts via Google Chat with rising-edge detection and cooldown, (2) bulk selection UI with floating action bar for batch assign/mark-irrelevant, and (3) an AI corrections digest card on the triage queue. All three build directly on existing primitives -- ChatNotifier, SystemConfig, ActivityLog, HTMX partials -- with zero new dependencies.

The highest-complexity item is the bulk selection UX. Thread cards currently have no checkbox, the list body template has no selection state management, and there is no floating bar pattern anywhere in the codebase. This requires vanilla JS for checkbox state tracking, a new floating bar partial, and two new POST endpoints that accept arrays of thread IDs. The alert system is lower complexity -- it piggybacks on the existing `_heartbeat_job` with a new `_check_unassigned_alert()` function and a new `notify_unassigned_alert()` method on ChatNotifier. The digest is the simplest -- a server-rendered collapsible card that queries ActivityLog on page load.

**Primary recommendation:** Build alerts first (scheduler + ChatNotifier), then bulk actions (JS + endpoints + templates), then digest (query + template). Alerts are backend-only with no UI coupling. Bulk actions are the most complex and benefit from being built after alerts (so the unassigned badge colors are already in place). Digest is independent and can slot in anywhere.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Floating bottom bar appears when >=1 thread checkbox is checked (Slack/Notion pattern)
- Checkboxes appear on hover over thread cards (not always visible)
- "Select all visible" checkbox in the list header selects all currently loaded thread cards
- Bar shows: selected count + "Assign to" dropdown + "Mark Irrelevant" button
- Bar has shadow, rounded corners, slides in from bottom
- After bulk action: undo toast (10-second window) -- no confirmation dialog before
- Bar disappears when selection is cleared or after action completes
- Rising-edge detection: alert fires once when unassigned count crosses threshold (e.g., 4->5), not on every poll while above
- Resets when count drops below threshold, so next crossing triggers again
- Default threshold: 5 unassigned threads
- Default cooldown: 30 minutes between alerts
- Piggyback on existing `_heartbeat_job` (1-minute interval) -- check count there with cooldown
- Threshold and cooldown configurable from Settings page (SLA/Config tab), not SystemConfig-admin-only
- Chat alert card shows count + top category breakdown with link to triage queue
- AI corrections digest: collapsible card above thread list on triage queue page
- Digest shows: correction counts (category changes, priority overrides, spam corrections) for last 7 days
- Digest shows: top 3-5 repeating patterns extracted from ActivityLog
- Gatekeeper + admin only -- members don't see it
- Digest refreshes on page load only -- no background polling
- Collapsible: expanded by default, remembers collapsed state
- Sidebar "Triage Queue" badge: extend existing role check to include gatekeepers
- Threshold-based coloring: green (0-2), yellow (3-4), red (5+, matches alert threshold)
- Count excludes irrelevant threads (Phase 3 delivers this status)

### Claude's Discretion
- Exact floating bar animation and styling
- HTMX contract for bulk POST (thread IDs array format)
- ActivityLog query structure for digest patterns
- SystemConfig key naming for alert threshold/cooldown
- Undo toast timing and implementation details

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ALERT-01 | Dashboard badge shows unassigned thread count, visible to gatekeeper and admin | Sidebar counts already computed in `thread_list` view (line 186). Role check needs widening from `is_admin` to include gatekeeper. Badge coloring (green/yellow/red) is new CSS logic on existing count. |
| ALERT-02 | Google Chat alert fires when unassigned count exceeds configurable threshold | `_heartbeat_job` in run_scheduler.py (line 36) runs every 1 min. Add `_check_unassigned_alert()` with rising-edge detection. New `notify_unassigned_alert()` on ChatNotifier follows existing Cards v2 pattern. |
| ALERT-03 | Chat alerts have cooldown period to prevent alert storms | Rising-edge detection + 30-min cooldown via two SystemConfig keys (`unassigned_alert_threshold`, `unassigned_alert_cooldown_minutes`). Store `last_unassigned_alert_at` and `_prev_below_threshold` flag in SystemConfig. |
| ALERT-04 | Gatekeeper sees AI feedback summary (recent corrections digest) on triage queue | Query ActivityLog for `CATEGORY_CHANGED`, `PRIORITY_CHANGED`, `SPAM_MARKED` actions in last 7 days. Aggregate counts + extract top patterns. Render collapsible card above thread list. |
| TRIAGE-04 | Gatekeeper/admin can select multiple threads via checkboxes and bulk-assign to a user | New `bulk_assign` view + URL. Checkbox JS on thread cards. Floating bar with assignee dropdown. HTMX POST with thread ID array. ActivityLog entry per thread. |
| TRIAGE-05 | Gatekeeper/admin can bulk mark-irrelevant with a single reason for all selected | Reuse bulk selection UI. New `bulk_mark_irrelevant` view + URL. Single reason text input. Shared floating bar with bulk assign. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Backend framework | Already in use, no change |
| HTMX | 2.0 (CDN) | Partial swaps for bulk action responses | Already in use, no change |
| Tailwind CSS | v4 (pre-built) | Floating bar, badge coloring, digest card styling | Already in use, no change |
| APScheduler | existing | Heartbeat job for alert check | Already in use, no change |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | existing | ChatNotifier webhook POST | Already used by ChatNotifier |
| vanilla JS | N/A | Checkbox state management, floating bar show/hide, select-all toggle | ~50 lines inline in thread_list.html |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla JS checkboxes | Alpine.js | Adds a dependency for ~50 lines of JS; not worth it for this codebase |
| SystemConfig for cooldown | In-memory variable | Would reset on scheduler restart; SystemConfig persists across deploys |

**Installation:**
```bash
# No new packages needed
```

## Architecture Patterns

### Recommended Project Structure
No new files except migrations. All changes modify existing files:
```
apps/emails/
  views.py              # +2 bulk views, +digest context in thread_list
  urls.py               # +2 bulk URL patterns
  services/
    assignment.py        # +bulk_assign_threads(), +bulk_mark_irrelevant()
    chat_notifier.py     # +notify_unassigned_alert()
  management/commands/
    run_scheduler.py     # +_check_unassigned_alert() in heartbeat
apps/core/
  migrations/            # Seed migration for alert SystemConfig keys
templates/emails/
  thread_list.html       # +floating bar, +select-all checkbox, +digest card
  _thread_card.html      # +checkbox (hover-visible)
  _thread_list_body.html # +selection count update script
  _bulk_action_bar.html  # NEW partial for floating bar (HTMX response swap)
  _corrections_digest.html  # NEW partial for digest card
```

### Pattern 1: Bulk Action POST with Thread ID Array
**What:** POST endpoint receives `thread_ids` as repeated form fields, processes each thread, returns updated thread list body.
**When to use:** Both bulk-assign and bulk-mark-irrelevant.
**Example:**
```python
# Source: existing assign_thread_view pattern in views.py
@login_required
@require_POST
def bulk_assign(request):
    """Bulk-assign selected threads to a user."""
    user = request.user
    if not can_assign(user):
        return HttpResponseForbidden("Permission denied.")

    thread_ids = request.POST.getlist("thread_ids")
    assignee_id = request.POST.get("assignee_id")
    if not thread_ids or not assignee_id:
        return _HttpResponse("Missing thread_ids or assignee_id", status=400)

    assignee = get_object_or_404(User, pk=assignee_id, is_active=True)
    threads = Thread.objects.filter(pk__in=thread_ids, status__in=["new", "acknowledged"])

    assigned_pks = []
    for thread in threads:
        _assign_thread(thread, assignee, assigned_by=user)
        assigned_pks.append(thread.pk)

    # Return updated thread list (HTMX swap)
    # Include undo data in HX-Trigger header for toast
    response = _render_thread_list_response(request)
    response["HX-Trigger"] = json.dumps({
        "bulkActionComplete": {
            "count": len(assigned_pks),
            "action": "assigned",
            "assignee": assignee.get_full_name() or assignee.username,
            "thread_ids": assigned_pks,
        }
    })
    return response
```

**HTMX form pattern (floating bar):**
```html
<form id="bulk-action-form"
      hx-post="{% url 'emails:bulk_assign' %}"
      hx-target="#thread-list-body"
      hx-swap="innerHTML">
    <!-- Hidden inputs populated by JS -->
    <div id="bulk-thread-ids"></div>
    <select name="assignee_id">
        {% for member in team_members %}
        <option value="{{ member.pk }}">{{ member.get_full_name }}</option>
        {% endfor %}
    </select>
    <button type="submit">Assign</button>
</form>
```

### Pattern 2: Rising-Edge Alert Detection
**What:** Alert fires only when count crosses threshold upward, not on every heartbeat while above.
**When to use:** Unassigned count alert in scheduler heartbeat.
**Example:**
```python
def _check_unassigned_alert():
    """Check unassigned count and fire Chat alert on rising edge."""
    close_old_connections()

    threshold = SystemConfig.get("unassigned_alert_threshold", 0)
    if not threshold:
        return  # alerts disabled

    try:
        threshold = int(threshold)
    except (ValueError, TypeError):
        return

    # Count unassigned threads (exclude irrelevant)
    count = Thread.objects.filter(
        assigned_to__isnull=True,
        status__in=["new", "acknowledged"],
    ).count()

    # Rising-edge: was below, now at/above
    was_below = SystemConfig.get("_unassigned_was_below_threshold", "true")

    if count >= threshold:
        if was_below != "true":
            return  # already above, don't re-alert

        # Cooldown check
        cooldown_minutes = int(SystemConfig.get("unassigned_alert_cooldown_minutes", 30))
        last_alert = SystemConfig.get("last_unassigned_alert_at", "")
        if last_alert:
            from datetime import datetime
            try:
                last = datetime.fromisoformat(last_alert)
                if (timezone.now() - last).total_seconds() < cooldown_minutes * 60:
                    return  # within cooldown
            except (ValueError, TypeError):
                pass

        # Fire alert
        webhook_url = (SystemConfig.get("chat_webhook_url", "")
                       or os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", ""))
        if webhook_url:
            # Build category breakdown
            from django.db.models import Count as DjCount
            breakdown = dict(
                Thread.objects.filter(
                    assigned_to__isnull=True,
                    status__in=["new", "acknowledged"],
                ).values_list("category").annotate(c=DjCount("pk")).values_list("category", "c")
            )
            notifier = ChatNotifier(webhook_url=webhook_url)
            notifier.notify_unassigned_alert(count, threshold, breakdown)
            SystemConfig.set("last_unassigned_alert_at", timezone.now().isoformat())

        SystemConfig.set("_unassigned_was_below_threshold", "false")
    else:
        # Count dropped below threshold -- reset for next rising edge
        if was_below != "true":
            SystemConfig.set("_unassigned_was_below_threshold", "true")
```

### Pattern 3: Corrections Digest Query
**What:** Aggregate ActivityLog for category/priority/spam corrections in last 7 days.
**When to use:** Triage queue page load for gatekeeper/admin.
**Example:**
```python
def get_corrections_digest():
    """Build corrections digest for last 7 days from ActivityLog."""
    from django.db.models import Count as DjCount
    cutoff = timezone.now() - timedelta(days=7)

    correction_actions = [
        ActivityLog.Action.CATEGORY_CHANGED,
        ActivityLog.Action.PRIORITY_CHANGED,
        ActivityLog.Action.SPAM_MARKED,
    ]

    # Counts by action type
    counts = dict(
        ActivityLog.objects.filter(
            action__in=correction_actions,
            created_at__gte=cutoff,
        ).values_list("action").annotate(c=DjCount("pk")).values_list("action", "c")
    )

    # Top patterns from detail text (e.g., "General -> Govt")
    # ActivityLog.detail stores change descriptions
    recent_logs = ActivityLog.objects.filter(
        action__in=[ActivityLog.Action.CATEGORY_CHANGED, ActivityLog.Action.PRIORITY_CHANGED],
        created_at__gte=cutoff,
    ).exclude(detail="").values_list("detail", flat=True)[:100]

    # Count repeating detail patterns
    from collections import Counter
    pattern_counts = Counter(recent_logs)
    top_patterns = pattern_counts.most_common(5)

    return {
        "category_changes": counts.get(ActivityLog.Action.CATEGORY_CHANGED, 0),
        "priority_overrides": counts.get(ActivityLog.Action.PRIORITY_CHANGED, 0),
        "spam_corrections": counts.get(ActivityLog.Action.SPAM_MARKED, 0),
        "total": sum(counts.values()),
        "top_patterns": top_patterns,  # list of (detail_text, count)
    }
```

### Pattern 4: Checkbox State Management (Vanilla JS)
**What:** Thread card checkboxes with floating bar, managed by ~50 lines of inline JS.
**When to use:** Thread list page for gatekeeper/admin users.
**Example:**
```javascript
// In thread_list.html <script> block
const bulkBar = document.getElementById('bulk-action-bar');
const bulkIdsContainer = document.getElementById('bulk-thread-ids');
const bulkCountEl = document.getElementById('bulk-count');

function updateBulkState() {
    const checked = document.querySelectorAll('.thread-checkbox:checked');
    const count = checked.length;

    // Show/hide floating bar
    if (count > 0) {
        bulkBar.classList.remove('translate-y-full', 'opacity-0');
        bulkBar.classList.add('translate-y-0', 'opacity-100');
    } else {
        bulkBar.classList.add('translate-y-full', 'opacity-0');
        bulkBar.classList.remove('translate-y-0', 'opacity-100');
    }

    // Update count label
    bulkCountEl.textContent = count + ' selected';

    // Update hidden inputs for HTMX form
    bulkIdsContainer.innerHTML = '';
    checked.forEach(cb => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'thread_ids';
        input.value = cb.value;
        bulkIdsContainer.appendChild(input);
    });
}

function toggleSelectAll(masterCb) {
    document.querySelectorAll('.thread-checkbox').forEach(cb => {
        cb.checked = masterCb.checked;
    });
    updateBulkState();
}
```

### Anti-Patterns to Avoid
- **HTMX form-per-card:** Do NOT put a form on each thread card for bulk selection. Use a single form wrapping the floating bar with dynamically populated hidden inputs.
- **Polling for alert state on frontend:** Alerts are backend (scheduler -> Chat). No JS polling on the dashboard for alert state.
- **Storing undo data server-side:** Undo is a simple re-POST with the previous state. Store the "what to undo" payload in the toast's JS closure, not in a server session.
- **Complex pattern extraction:** The digest patterns should use simple `Counter` on ActivityLog.detail strings, not AI/NLP. The detail field already contains human-readable change descriptions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Alert cooldown | Custom timer/thread | SystemConfig timestamp + comparison | Persists across restarts, trivial to implement |
| Bulk selection state | Custom state management lib | Vanilla JS + DOM queries | ~50 lines, no framework needed for 4-5 users |
| Category breakdown in alert | Custom aggregation | Django ORM `.values().annotate(Count)` | One-liner, already used throughout codebase |
| Toast with undo | Custom notification system | Existing toast system + JS closure for undo POST | Toast pattern already exists in base.html |

## Common Pitfalls

### Pitfall 1: Alert Storm Without Rising-Edge
**What goes wrong:** Alert fires every minute while unassigned count stays above threshold.
**Why it happens:** Naive `if count >= threshold: alert()` triggers on every heartbeat cycle.
**How to avoid:** Track `_unassigned_was_below_threshold` flag in SystemConfig. Alert only on false->true transition. Reset flag when count drops below.
**Warning signs:** Multiple identical Chat alerts within minutes.

### Pitfall 2: Bulk Action Losing Checkbox State After HTMX Swap
**What goes wrong:** When HTMX swaps the thread list body after a bulk action, all checkbox states are lost and the floating bar disappears.
**Why it happens:** HTMX replaces the DOM including checkboxes. The JS state is tied to DOM elements.
**How to avoid:** After bulk action, the response should swap the thread list body AND clear the floating bar. Use `HX-Trigger` header to fire a custom event that the JS listens for to reset state. The bar should slide out after action completes -- this is the expected behavior per user decision.
**Warning signs:** Floating bar stays visible with stale count after action.

### Pitfall 3: Undo Toast Race Condition
**What goes wrong:** User clicks undo after the 10-second window, but the toast already disappeared.
**Why it happens:** Undo endpoint processes regardless of toast state.
**How to avoid:** The undo endpoint should always work (idempotent). The toast is just the UI hint. If the user bookmarks the undo URL or the toast times out, the undo still works within a reasonable window (e.g., 5 minutes server-side). The 10-second window is just the toast visibility.
**Warning signs:** Undo fails silently after toast disappears.

### Pitfall 4: Checkbox Hover vs Mobile Touch
**What goes wrong:** Checkboxes set to `opacity-0 hover:opacity-100` are invisible on mobile (no hover).
**Why it happens:** Mobile has no hover state; touch-only.
**How to avoid:** On mobile (< sm breakpoint), show checkboxes always visible OR use long-press to enter selection mode (like Gmail app). Simplest approach: always-visible on mobile, hover-visible on desktop using Tailwind responsive: `opacity-0 sm:group-hover:opacity-100 max-sm:opacity-100`.
**Warning signs:** Mobile users cannot see or tap checkboxes.

### Pitfall 5: Digest Query Performance
**What goes wrong:** Corrections digest query on every page load slows dashboard.
**Why it happens:** Unindexed `created_at` + `action` combination on ActivityLog.
**How to avoid:** ActivityLog.created_at already has an index (from TimestampedModel's auto_now_add, Django creates index on datetime fields by default). The query filters on action + created_at, both indexed. For 7-day window on a 50-100 emails/day system, this is <1000 rows. No performance concern.
**Warning signs:** N/A -- not a real risk at this scale.

### Pitfall 6: SystemConfig.set Missing Method
**What goes wrong:** Code calls `SystemConfig.set(key, value)` but SystemConfig uses `update_or_create`.
**Why it happens:** The codebase uses `SystemConfig.objects.update_or_create()` pattern, not a `.set()` class method.
**How to avoid:** Use the established pattern: `SystemConfig.objects.update_or_create(key=..., defaults={"value": ..., "value_type": ...})`. Or check if a `.set()` convenience method already exists.
**Warning signs:** AttributeError on SystemConfig.set.

## Code Examples

### ChatNotifier.notify_unassigned_alert()
```python
# Source: follows existing notify_breach_summary pattern in chat_notifier.py
def notify_unassigned_alert(self, count, threshold, category_breakdown=None):
    """Post alert card when unassigned count exceeds threshold."""
    # No quiet hours check -- alerts should fire regardless
    breakdown_text = ""
    if category_breakdown:
        parts = [f"{count} {cat}" for cat, count in sorted(
            category_breakdown.items(), key=lambda x: -x[1]
        )]
        breakdown_text = ", ".join(parts)

    triage_url = f"{self._tracker_url}/emails/?view=unassigned"

    card = {
        "header": self._branded_header(
            title=f"\u26a0\ufe0f {count} unassigned threads (threshold: {threshold})",
            subtitle=breakdown_text or "Triage queue needs attention",
        ),
        "sections": [
            {"widgets": [
                {"decoratedText": {
                    "topLabel": "Category Breakdown",
                    "text": breakdown_text or "No category data",
                }},
            ]},
            {"widgets": [{"buttonList": {"buttons": [
                {"text": "Open Triage Queue", "onClick": {"openLink": {"url": triage_url}}},
            ]}}]},
            VIPL_FOOTER_SECTION,
        ],
    }

    payload = {"cardsV2": [{"cardId": "unassigned-alert", "card": card}]}
    return self._post(payload)
```

### Undo Toast Pattern
```python
# Source: extends existing toast system in base.html
# View returns HX-Trigger header with undo data:
response["HX-Trigger"] = json.dumps({
    "showUndoToast": {
        "message": f"Assigned {count} threads to {assignee_name}",
        "undo_url": reverse("emails:bulk_undo"),
        "undo_data": {"thread_ids": assigned_pks, "action": "assign",
                       "previous_states": previous_states},
    }
})
```

```javascript
// JS listener in thread_list.html
document.body.addEventListener('showUndoToast', function(e) {
    const data = e.detail;
    const toast = document.createElement('div');
    toast.className = 'toast-item flex items-center gap-3 px-4 py-3 bg-white rounded-xl shadow-lg border border-slate-200 max-w-sm';
    toast.style.animation = 'toast-in 0.3s ease-out';
    toast.innerHTML = `
        <span class="text-sm text-slate-700">${data.message}</span>
        <button class="undo-btn text-sm font-semibold text-blue-600 hover:text-blue-800" data-undo='${JSON.stringify(data)}'>Undo</button>
        <button onclick="this.closest('.toast-item').remove()" class="text-slate-300 hover:text-slate-500">&times;</button>
    `;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => { toast.style.animation = 'toast-out 0.3s ease-in forwards'; setTimeout(() => toast.remove(), 300); }, 10000);
});
```

### Sidebar Badge Coloring
```html
<!-- Source: extends existing sidebar count pattern in thread_list.html -->
{% with ucount=sidebar_counts.unassigned %}
<span class="inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-bold
    {% if ucount >= 5 %}bg-red-100 text-red-700
    {% elif ucount >= 3 %}bg-amber-100 text-amber-700
    {% elif ucount > 0 %}bg-green-100 text-green-700
    {% else %}bg-slate-100 text-slate-400
    {% endif %}">
    {{ ucount }}
</span>
{% endwith %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No bulk actions | Checkbox + floating bar (Slack/Notion pattern) | Current industry standard | Gatekeeper processes 10+ threads in one action |
| Naive threshold alerts | Rising-edge detection + cooldown | Standard in monitoring (Prometheus, PagerDuty) | Prevents alert fatigue |

## Open Questions

1. **Undo implementation complexity**
   - What we know: User wants 10-second undo toast, no confirmation dialog before action.
   - What's unclear: Should undo restore exact previous state (e.g., un-assign all threads) or just reverse the last assignment? For mark-irrelevant undo, should it restore status to "new" or the previous status?
   - Recommendation: Store previous `assigned_to_id` and `status` per thread in the undo payload. Undo reverses to exact previous state. Keep undo window to 5 minutes server-side (toast shows 10 seconds, but URL works for 5 min).

2. **Digest pattern extraction quality**
   - What we know: ActivityLog.detail contains change descriptions. Counter on these strings gives frequency.
   - What's unclear: How well-structured are the detail strings? If they vary (e.g., "Changed category from General to Govt" vs "category: General -> Govt"), simple counting won't group them.
   - Recommendation: Standardize the detail format in the edit_category/edit_priority views to ensure consistent strings like "General -> Govt". Then Counter works perfectly.

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
| ALERT-01 | Sidebar badge shows unassigned count with color tiers for gatekeeper | unit | `pytest apps/emails/tests/test_views.py -x -k "sidebar_badge_color or gatekeeper_sees_unassigned"` | Wave 0 |
| ALERT-02 | Chat alert fires when count exceeds threshold | unit | `pytest apps/emails/tests/test_scheduler_alert.py -x` | Wave 0 |
| ALERT-03 | Cooldown prevents repeated alerts; rising-edge detection | unit | `pytest apps/emails/tests/test_scheduler_alert.py -x -k "cooldown or rising_edge"` | Wave 0 |
| ALERT-04 | Corrections digest shows on triage queue for gatekeeper/admin | unit | `pytest apps/emails/tests/test_views.py -x -k "corrections_digest"` | Wave 0 |
| TRIAGE-04 | Bulk assign via checkbox selection | unit | `pytest apps/emails/tests/test_bulk_actions.py -x -k "bulk_assign"` | Wave 0 |
| TRIAGE-05 | Bulk mark-irrelevant with single reason | unit | `pytest apps/emails/tests/test_bulk_actions.py -x -k "bulk_mark_irrelevant"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/ -x -q`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_scheduler_alert.py` -- covers ALERT-02, ALERT-03
- [ ] `apps/emails/tests/test_bulk_actions.py` -- covers TRIAGE-04, TRIAGE-05
- [ ] Existing `apps/emails/tests/test_views.py` -- extend for ALERT-01, ALERT-04

## Sources

### Primary (HIGH confidence -- direct codebase analysis)
- `apps/emails/services/chat_notifier.py` -- 7 existing notify methods, Cards v2 pattern, `_post()` helper
- `apps/emails/management/commands/run_scheduler.py` -- `_heartbeat_job` structure, all scheduler jobs
- `apps/emails/views.py` -- `thread_list` view, sidebar counts computation (lines 178-208), `is_admin` check locations
- `apps/emails/models.py` -- `ActivityLog.Action` choices including `CATEGORY_CHANGED`, `PRIORITY_CHANGED`, `SPAM_MARKED`
- `apps/emails/services/distillation.py` -- existing correction query pattern on `AssignmentFeedback`
- `apps/core/models.py` -- `SystemConfig` key-value store, `update_or_create` pattern
- `templates/emails/_thread_card.html` -- current card structure, no checkbox yet
- `templates/emails/_thread_list_body.html` -- simple for-loop rendering
- `templates/base.html` -- existing toast system (lines 316-367), animation keyframes

### Secondary (MEDIUM confidence -- architecture research docs)
- `.planning/research/ARCHITECTURE.md` -- alert flow design, rising-edge pattern
- `.planning/research/FEATURES.md` -- bulk assign complexity budget, alert SystemConfig keys
- `.planning/research/SUMMARY.md` -- pitfall #6 (alert storm), pitfall #12 (bulk assign undo)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all existing primitives
- Architecture: HIGH -- every integration point verified by reading source
- Pitfalls: HIGH -- identified from direct code reading (checkbox hover, HTMX swap state loss, alert storm)
- Bulk action UX: MEDIUM -- floating bar pattern is new to this codebase, but well-understood industry pattern

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable -- no fast-moving dependencies)
