# Phase 4: Read/Unread Tracking - Research

**Researched:** 2026-03-15
**Domain:** Django per-user read state, HTMX OOB swaps, sidebar badge updates
**Confidence:** HIGH

## Summary

This phase adds per-user read/unread tracking to the thread dashboard. The `ThreadReadState` model already exists (created in Phase 1, migration `0015_v250_models`), with `thread`, `user`, `is_read`, and `read_at` fields plus a `unique_together` constraint. The work is purely view/template layer: upsert read state on detail open, annotate thread querysets with per-user unread status, swap the card's bold/dot condition from `status == 'new'` to per-user unread, add a "Mark as Unread" button, and inject unread counts into sidebar badges.

The existing OOB swap pattern (used by assign/status actions) provides a proven mechanism for updating individual thread cards after read state changes. The sidebar counts aggregate query (`sidebar_counts` in `thread_list` view) needs extension with per-user unread subqueries. No new dependencies are required -- this is pure Django ORM + template + HTMX work.

**Primary recommendation:** Use `update_or_create` on ThreadReadState in the detail view, annotate the thread queryset with `Exists(ThreadReadState)` subquery for unread detection, and use OOB swaps for instant card updates after read/unread actions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Blue dot + bold text = "unread by you" (per-user), replacing the current `status == 'new'` logic on thread cards
- Blue-500 dot color (same as current, familiar)
- Read threads: normal weight text, no dot -- regardless of thread status
- New emails arriving in an already-read thread flip it back to unread (compare `read_at` vs `last_message_at`)
- Initial deploy state: no ThreadReadState row = treated as read (avoids wall of bold on first login)
- Opening thread detail panel marks it as read immediately (no delay timer)
- View upserts ThreadReadState on the detail panel GET request
- Card updates to read styling via OOB swap in the detail response (optimistic feel)
- Assignment to a user resets their read state for that thread (thread becomes unread for assignee)
- Sidebar count badges show unread count (not total) when there are unreads; show muted total when all read
- Unread badges on: My Inbox (required by READ-05), All Open, Closed views, plus Claude's discretion on Triage Queue
- Browser tab title shows unread count: "(3) VIPL Triage | Inbox" -- standard pattern
- Counts update on HTMX navigation (OOB swaps), no background polling
- "Mark as unread" icon button in thread detail header actions bar (alongside assign, status, close)
- Marking unread closes the detail panel and returns focus to thread list
- Card immediately shows as unread (bold + dot) via OOB swap or list refresh
- No confirmation needed -- instant, low-risk action
- No bulk "Mark all read" initially (Phase 5 context menu may add it)

### Claude's Discretion
- Keyboard shortcut for mark unread (e.g., 'U' key) -- decide based on effort and existing keyboard nav
- Bulk "Mark all as read" -- decide based on implementation effort vs UX value
- Whether Triage Queue gets unread badges or just My Inbox + Views
- Exact icon choice for mark unread button
- Loading/transition states during OOB swaps

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| READ-01 | Per-user read state is tracked for each thread (ThreadReadState model) | Model exists from Phase 1. Needs `update_or_create` logic in views + unread annotation on querysets |
| READ-02 | Opening a thread detail panel marks it as read for the current user | Upsert in `thread_detail` view + OOB card swap in response |
| READ-03 | Unread threads display with bold text and blue indicator dot (visual distinction) | Replace `thread.status == 'new'` condition in `_thread_card.html` with `thread.is_unread` annotation |
| READ-04 | User can mark a thread as unread from the detail panel or context menu | New POST endpoint + icon button in action bar + OOB swap + panel close |
| READ-05 | Sidebar shows unread count badge next to "My Inbox" view | Extend `sidebar_counts` aggregate with per-user unread subqueries |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | ORM, views, templates | Already in use |
| HTMX | 2.0.8 | OOB swaps for instant card updates | Already in use via CDN |
| Tailwind CSS | v4 | Styling for bold/dot/badge changes | Already in use (pre-built CSS) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| django-htmx | (existing) | `request.htmx` detection for partial vs full renders | Already integrated |

### Alternatives Considered
None -- zero new dependencies. All work uses existing stack.

## Architecture Patterns

### Pattern 1: Unread Detection via Queryset Annotation

**What:** Annotate the thread queryset with a boolean `is_unread` based on comparing `ThreadReadState.read_at` against `Thread.last_message_at`. No row = read (per locked decision for initial deploy).

**When to use:** Every thread list query.

**Example:**
```python
from django.db.models import Exists, OuterRef, Q, Subquery

# A thread is unread if:
# 1. A ThreadReadState row exists AND is_read=False, OR
# 2. A ThreadReadState row exists AND read_at < thread.last_message_at
# No row = treated as read (initial deploy safety)

read_state_sq = ThreadReadState.objects.filter(
    thread=OuterRef("pk"),
    user=user,
)

is_unread = Exists(
    read_state_sq.filter(
        Q(is_read=False) | Q(read_at__lt=OuterRef("last_message_at"))
    )
)

qs = qs.annotate(is_unread=is_unread)
```

**Key insight:** The "no row = read" decision means we only need `Exists` with a positive match on unread conditions. Threads without any `ThreadReadState` row will have `is_unread=False` by default, avoiding the wall-of-bold problem on first deploy.

### Pattern 2: Mark as Read via Upsert in Detail View

**What:** In `thread_detail`, upsert the ThreadReadState with `is_read=True, read_at=now`. Return the detail HTML plus an OOB-swapped thread card.

**Example:**
```python
from django.utils import timezone

# In thread_detail view, after loading thread:
ThreadReadState.objects.update_or_create(
    thread=thread, user=request.user,
    defaults={"is_read": True, "read_at": timezone.now()},
)

# Build detail HTML + OOB card swap
detail_html = render(request, "emails/_thread_detail.html", context)

# OOB swap: re-render the card with is_unread=False
card_html = render_to_string(
    "emails/_thread_card.html",
    {"thread": thread, "oob": True, "is_unread": False},
    request=request,
)
return _HttpResponse(detail_html.content + card_html.encode())
```

### Pattern 3: Mark as Unread via POST Endpoint

**What:** New POST endpoint that sets `is_read=False` and `read_at=None`, returns an OOB card swap plus a signal to close the detail panel.

**Example:**
```python
@login_required
@require_POST
def mark_thread_unread(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    ThreadReadState.objects.update_or_create(
        thread=thread, user=request.user,
        defaults={"is_read": False, "read_at": None},
    )
    # OOB swap the card back to unread styling
    card_html = render_to_string(
        "emails/_thread_card.html",
        {"thread": thread, "oob": True, "is_unread": True},
        request=request,
    )
    # Return empty detail + OOB card (HTMX will swap both)
    close_html = '<div id="thread-detail-panel" class="flex items-center justify-center h-full"><span class="text-sm text-slate-400">Select a thread</span></div>'
    return _HttpResponse(close_html + card_html)
```

### Pattern 4: Sidebar Unread Counts

**What:** Extend the existing `sidebar_counts` aggregate query with per-user unread counts. Use conditional Count with Exists subquery.

**Implementation approach:**
```python
# In thread_list view, alongside existing sidebar_counts:
from django.db.models import Exists, OuterRef, Q

unread_sq = ThreadReadState.objects.filter(
    thread=OuterRef("pk"),
    user=user,
).filter(
    Q(is_read=False) | Q(read_at__lt=OuterRef("last_message_at"))
)

# Separate query for unread counts per view
unread_counts = {
    "unread_mine": base_threads.filter(
        assigned_to=user
    ).filter(Exists(unread_sq)).count(),
    "unread_open": base_threads.filter(
        status__in=["new", "acknowledged"]
    ).filter(Exists(unread_sq)).count(),
    # ... etc
}
```

**Template badge display:**
```html
<!-- Show unread count if > 0, otherwise show muted total -->
{% if sidebar_counts.unread_mine > 0 %}
<span class="text-[10px] font-bold text-white bg-blue-500 px-1.5 py-0.5 rounded-full">
    {{ sidebar_counts.unread_mine }}
</span>
{% else %}
<span class="view-count text-[10px] font-bold text-slate-500 bg-white/[0.06] px-1.5 py-0.5 rounded-full">
    {{ sidebar_counts.mine }}
</span>
{% endif %}
```

### Pattern 5: Assignment Resets Read State

**What:** When a thread is assigned to someone, reset their ThreadReadState so the thread appears unread in their inbox.

**Where:** In `assign_thread_view` (or in the `_assign_thread` service function), after assignment:
```python
# Reset read state for new assignee so thread appears unread for them
ThreadReadState.objects.update_or_create(
    thread=thread, user=assignee,
    defaults={"is_read": False, "read_at": None},
)
```

### Pattern 6: Browser Tab Title with Unread Count

**What:** Update the `<title>` tag to include unread count prefix.

**Where:** `base.html` title block or a context processor.

**Example:**
```html
<title>{% if unread_total > 0 %}({{ unread_total }}) {% endif %}{% block title %}VIPL Triage{% endblock %}</title>
```

The unread total should be computed once in a template context processor or passed in `thread_list` context. For HTMX partial swaps, the title needs updating via an OOB `<title>` tag or JS snippet.

### Anti-Patterns to Avoid
- **N+1 queries for read state:** Never check `ThreadReadState.objects.filter(thread=t, user=u)` per-card in a loop. Always annotate the queryset.
- **Background polling for badge counts:** The decision explicitly says "no background polling" -- counts update on HTMX navigation only.
- **Using SoftDeleteModel for ThreadReadState:** CONTEXT.md says ThreadReadState should NOT use soft delete. However, the Phase 1 migration created it WITH SoftDeleteModel. This is a known discrepancy -- the model currently extends SoftDeleteModel (see `models.py:283`). Pragmatic approach: leave as-is for now since `update_or_create` works fine with soft-deleted manager, but note it for cleanup.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-card unread check | Loop + filter per thread | `Exists()` subquery annotation | Avoids N+1, single query |
| Read state upsert | Manual get/create/save | `update_or_create()` | Atomic, handles race conditions |
| OOB card update | JS DOM manipulation | HTMX `hx-swap-oob="outerHTML"` | Already proven pattern in codebase |
| Sidebar count refresh | AJAX polling endpoint | OOB swap sidebar counts in response | Matches existing navigation pattern |

**Key insight:** Every pattern needed is already in use in the codebase. This phase composes existing building blocks -- no new techniques required.

## Common Pitfalls

### Pitfall 1: N+1 on Unread Annotation
**What goes wrong:** Checking read state per-thread in a loop instead of annotating the queryset.
**Why it happens:** Tempting to add a method to Thread model that checks read state for "current user" -- but there's no current user in model context.
**How to avoid:** Always annotate in the view with `Exists()` subquery before passing to template.
**Warning signs:** Multiple `ThreadReadState` queries in Django Debug Toolbar per page load.

### Pitfall 2: OOB Swap Card Missing Annotations
**What goes wrong:** When rendering an OOB card swap (e.g., after mark-as-read), the thread object lacks annotations like `email_count`, `has_spam`, `ai_suggested_assignee_name` that the card template expects.
**Why it happens:** The OOB card is rendered with a plain `Thread.objects.get()` instead of the annotated queryset.
**How to avoid:** Create a helper function that returns an annotated single-thread queryset for OOB renders, or pass the `is_unread` value directly as template context rather than relying on annotation.
**Warning signs:** Template errors or missing data in OOB-swapped cards.

### Pitfall 3: Race Condition on Concurrent Read/Unread
**What goes wrong:** Two concurrent requests (e.g., mark read + new email arriving) could conflict on ThreadReadState.
**Why it happens:** `update_or_create` with `unique_together` is safe in PostgreSQL but edge cases exist with SoftDeleteModel's custom manager.
**How to avoid:** Use `update_or_create` (Django handles `IntegrityError` retry internally). Verify the soft-delete manager's `update_or_create` works correctly.
**Warning signs:** Sporadic IntegrityError in logs.

### Pitfall 4: "No Row = Read" vs Future Features
**What goes wrong:** Future features (like "Mark all as read") need to understand the "no row" convention.
**Why it happens:** The convention is an optimization for initial deploy but creates an implicit state.
**How to avoid:** Document the convention clearly. When creating "mark all read" in Phase 5, consider creating explicit rows rather than deleting them.
**Warning signs:** Inconsistent behavior between users who've never opened a thread and users who marked it read.

### Pitfall 5: Title Tag Update on HTMX Navigation
**What goes wrong:** Browser tab title doesn't update on HTMX partial swaps (HTMX only updates the target element).
**Why it happens:** The `<title>` tag is in `<head>`, outside HTMX's typical swap targets.
**How to avoid:** Use `hx-swap-oob` on a `<title>` element, or use HTMX's `htmx:afterSettle` event to update `document.title` via a small JS snippet embedded in the response.
**Warning signs:** Tab title stays stale after navigating between views.

### Pitfall 6: SoftDeleteModel on ThreadReadState
**What goes wrong:** The `objects` manager on SoftDeleteModel filters out soft-deleted rows. An `update_or_create` through `objects` won't find a soft-deleted row, creating a duplicate and hitting `IntegrityError` on the DB unique constraint.
**Why it happens:** ThreadReadState currently extends SoftDeleteModel (Phase 1 created it that way), but CONTEXT.md says it shouldn't.
**How to avoid:** Either (a) change the model to not extend SoftDeleteModel (requires a migration), or (b) use `all_objects` manager for `update_or_create` calls, or (c) never call `.delete()` on ThreadReadState -- always flip `is_read` flag instead. Option (c) is simplest and avoids migration changes.
**Warning signs:** `IntegrityError` on ThreadReadState create after a previous soft-delete.

## Code Examples

### Thread Card Template Change (replacing status == 'new' with per-user unread)

Current code in `_thread_card.html`:
```html
<!-- Current: status-based -->
{% if thread.status == 'new' %}font-semibold{% endif %}
{% if thread.status == 'new' %}
<span class="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0"></span>
{% endif %}
```

New code:
```html
<!-- New: per-user unread-based -->
{% if thread.is_unread %}font-semibold{% endif %}
{% if thread.is_unread %}
<span class="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0"></span>
{% endif %}
```

The `is_unread` value comes from the queryset annotation in the view, or from a template context variable for OOB swaps.

### Mark Unread Button (in action bar)

```html
<!-- Mark as Unread button (envelope-open icon) -->
<form hx-post="{% url 'emails:mark_thread_unread' thread.pk %}"
      hx-target="#thread-detail-panel" hx-swap="innerHTML" class="inline">
    {% csrf_token %}
    <button type="submit" hx-disabled-elt="this"
            class="inline-flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-bold text-slate-500 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors cursor-pointer"
            title="Mark as unread">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
        </svg>
    </button>
</form>
```

Icon recommendation: Envelope (mail) icon -- universally recognized for "mark as unread" in email clients.

## Discretion Recommendations

### Keyboard Shortcut for Mark Unread
**Recommendation:** Add 'U' key shortcut. Low effort -- the codebase already has keyboard nav (`onkeydown` handlers on cards, arrow key navigation). Add a single event listener in `_thread_detail.html` that triggers the mark-unread form submit when 'U' is pressed and the detail panel is open.

### Bulk "Mark All as Read"
**Recommendation:** Skip for now. Phase 5 context menu (MENU-02) explicitly lists "Mark Read/Unread" as a context menu action. Adding bulk operations now would duplicate effort. The underlying mechanism (UPDATE ThreadReadState SET is_read=True WHERE user=X) is trivial to add later.

### Triage Queue Unread Badges
**Recommendation:** Yes, add to Triage Queue too. The unread count is already being computed for all views. Showing it on Triage Queue helps admins see new arrivals. Cost: one extra count in the sidebar aggregate query. The badge styling (blue pill when unreads, muted when all read) applies uniformly.

### Loading/Transition States
**Recommendation:** Rely on existing HTMX request states (`.htmx-request { opacity: 0.7 }` in base.html). The mark-as-read is instant (single DB upsert), so no skeleton needed. Mark-as-unread uses `hx-disabled-elt` on the button (existing pattern).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | `pytest.ini` |
| Quick run command | `pytest apps/emails/tests/test_read_state.py -x` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| READ-01 | ThreadReadState upsert on detail open | unit | `pytest apps/emails/tests/test_read_state.py::TestMarkAsRead -x` | No -- Wave 0 |
| READ-02 | Detail view marks thread as read | integration | `pytest apps/emails/tests/test_read_state.py::TestDetailMarksRead -x` | No -- Wave 0 |
| READ-03 | Unread threads show bold + dot | unit | `pytest apps/emails/tests/test_read_state.py::TestUnreadAnnotation -x` | No -- Wave 0 |
| READ-04 | Mark as unread endpoint works | integration | `pytest apps/emails/tests/test_read_state.py::TestMarkAsUnread -x` | No -- Wave 0 |
| READ-05 | Sidebar unread count badge | integration | `pytest apps/emails/tests/test_read_state.py::TestSidebarUnreadCounts -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_read_state.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_read_state.py` -- all READ-XX tests (new file)
- [ ] Test fixtures: thread + user + ThreadReadState setup (can reuse existing conftest patterns from `test_v250_models.py`)

## Open Questions

1. **SoftDeleteModel on ThreadReadState**
   - What we know: Model currently extends SoftDeleteModel (Phase 1 migration). CONTEXT.md says it should NOT.
   - What's unclear: Whether to change the model (requires migration) or work around it.
   - Recommendation: Work around it -- never call `.delete()` on ThreadReadState, always flip `is_read` flag. Add a comment in the model noting the SoftDelete inheritance is vestigial. Avoids migration risk.

2. **OOB Sidebar Count Refresh**
   - What we know: Sidebar counts currently come from `thread_list` view context. Detail panel views don't return sidebar HTML.
   - What's unclear: Best mechanism to refresh sidebar counts when marking read/unread from detail panel.
   - Recommendation: Include OOB sidebar count elements in the detail response (same pattern as OOB card swap). Wrap sidebar count spans in identifiable elements for OOB targeting.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `apps/emails/models.py` -- ThreadReadState model (lines 283-298)
- Codebase inspection: `apps/emails/views.py` -- thread_list sidebar_counts (lines 148-162), thread_detail (lines 835-857), assign_thread_view OOB pattern (lines 953-989)
- Codebase inspection: `templates/emails/_thread_card.html` -- existing blue dot + bold logic (lines 6, 17-19, 20, 44)
- Codebase inspection: `templates/emails/_thread_detail.html` -- action bar structure (lines 86-175)
- Codebase inspection: `apps/emails/tests/test_v250_models.py` -- existing ThreadReadState tests (5 tests)

### Secondary (MEDIUM confidence)
- Django docs: `update_or_create()` atomic behavior with unique constraints
- HTMX docs: `hx-swap-oob` for out-of-band swaps

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- zero new dependencies, all patterns proven in codebase
- Architecture: HIGH -- all patterns are variations of existing assign/status OOB swap flow
- Pitfalls: HIGH -- identified from direct codebase inspection (SoftDelete, N+1, OOB annotation gaps)

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- Django 4.2 LTS, no moving parts)
