---
phase: 04-read-unread-tracking
verified: 2026-03-15T14:30:00Z
status: human_needed
score: 10/10 must-haves verified
human_verification:
  - test: "Open a thread that has no ThreadReadState row — card should appear in normal weight, no blue dot"
    expected: "Thread card shows normal font weight and no blue indicator dot (no-row = read convention)"
    why_human: "Requires visual inspection of the rendered card in a browser"
  - test: "Create an unread state in shell, reload list — thread card should show bold text and blue dot"
    expected: "Card renders with font-semibold class and the blue dot indicator is visible"
    why_human: "Cannot programmatically verify CSS rendering and visual indicator appearance"
  - test: "Click an unread thread — card should immediately update to read styling without page reload"
    expected: "OOB card swap fires; blue dot disappears and bold weight drops on the card in the list"
    why_human: "Requires HTMX OOB swap to be observed live in a browser"
  - test: "Click the envelope 'Mark as Unread' button in the detail panel"
    expected: "Detail panel closes (shows 'Select a thread'), card reverts to bold+dot styling"
    why_human: "Requires HTMX response and DOM swap observation in browser"
  - test: "Press 'U' key while a thread detail panel is open"
    expected: "Same result as clicking the Mark as Unread button — panel closes, card goes unread"
    why_human: "Keyboard shortcut behavior requires live browser interaction"
  - test: "Assign a thread to a user — check that user sees it as unread in their inbox"
    expected: "After assignment, recipient's sidebar shows incremented unread count for My Inbox"
    why_human: "Requires two-user session or direct DB observation correlated with UI state"
  - test: "Sidebar badges — My Inbox should show a blue pill when user has unread assigned threads"
    expected: "Blue pill with count visible next to 'My Inbox'; muted count appears when all read"
    why_human: "Visual badge styling requires browser rendering to confirm blue vs muted display"
  - test: "Browser tab title shows '(N) VIPL Triage' when unread threads exist"
    expected: "Tab title prefix changes dynamically as threads are marked read/unread"
    why_human: "Tab title is set by OOB JS script; requires live browser observation"
---

# Phase 4: Read/Unread Tracking Verification Report

**Phase Goal:** Users can see which threads they have and have not read, with visual distinction and manual override
**Verified:** 2026-03-15T14:30:00Z
**Status:** human_needed (all automated checks passed; visual/interaction behaviors require browser)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Opening a thread detail creates/updates a ThreadReadState row with is_read=True and read_at=now | VERIFIED | `ThreadReadState.objects.update_or_create(thread=thread, user=user, defaults={"is_read": True, "read_at": timezone.now()})` in `thread_detail` (views.py:898). TestMarkAsRead passes 3/3. |
| 2 | POST to mark-unread endpoint sets ThreadReadState is_read=False and read_at=None | VERIFIED | `mark_thread_unread` view (views.py:921) calls `update_or_create` with `defaults={"is_read": False, "read_at": None}`. TestMarkAsUnread passes 3/3. |
| 3 | Assigning a thread to a user resets their ThreadReadState to unread | VERIFIED | `assign_thread_view` (views.py:1055) calls `ThreadReadState.objects.update_or_create(thread=thread, user=assignee, defaults={"is_read": False, "read_at": None})`. TestAssignmentResetsReadState passes 1/1. |
| 4 | Thread queryset is annotated with is_unread boolean based on ThreadReadState vs last_message_at | VERIFIED | `annotate_unread(qs, user)` helper (views.py:63) uses Exists subquery with `Q(is_read=False) \| Q(read_at__lt=OuterRef("last_message_at"))`. Called at views.py:116 in thread_list. TestUnreadAnnotation passes 4/4. |
| 5 | Unread threads show bold text and blue indicator dot; read threads show normal weight, no dot | VERIFIED (automated) / NEEDS HUMAN (visual) | `_thread_card.html` uses `{% if thread.is_unread %}` (4 occurrences) for font-semibold, blue dot div, font-bold, and subject weight. No `status == 'new'` remaining for styling. |
| 6 | Sidebar badges show unread count (blue pill) when unreads exist, muted total when all read | VERIFIED (automated) / NEEDS HUMAN (visual) | `thread_list.html` has conditional `{% if sidebar_counts.unread_mine > 0 %}` pattern for all 4 sidebar entries (unassigned, mine, all_open, closed). Blue pill markup confirmed. |
| 7 | Browser tab title shows unread count prefix like (3) VIPL Triage | VERIFIED (automated) / NEEDS HUMAN (visual) | `base.html:7` has `{% if unread_total %}({{ unread_total }}) {% endif %}`. OOB JS title updater in `_thread_list_body.html:3-5`. `unread_total` computed in views.py:204 and passed to context at line 256. |
| 8 | Mark as unread button appears in thread detail action bar | VERIFIED | `_thread_detail.html:219-228` has `<form hx-post="{% url 'emails:mark_thread_unread' thread.pk %}">` with envelope SVG button. |
| 9 | Marking unread closes detail panel and card shows unread styling | VERIFIED (automated) / NEEDS HUMAN (visual) | `mark_thread_unread` returns `close_html + card_html` where `close_html` is the "Select a thread" placeholder and card sets `thread.is_unread = True` before OOB render. |
| 10 | Opening a thread updates card to read styling via OOB swap | VERIFIED (automated) / NEEDS HUMAN (visual) | `thread_detail` sets `thread.is_unread = False` then renders OOB card and returns combined response via `_HttpResponse`. |

**Score:** 10/10 truths verified (automated), 8 require human confirmation for visual/interaction behavior

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/emails/tests/test_read_state.py` | Tests for all read state backend logic | VERIFIED | 12 tests, 5 test classes, 239 lines. All 12 pass. |
| `apps/emails/views.py` | mark_thread_unread view, unread annotation helper, read state upsert in thread_detail | VERIFIED | `annotate_unread()` at line 63, upsert at 898, `mark_thread_unread` at 921, assignment reset at 1055, sidebar unread counts at 188-201. |
| `apps/emails/urls.py` | URL pattern for mark_thread_unread | VERIFIED | `path("threads/<int:pk>/mark-unread/", views.mark_thread_unread, name="mark_thread_unread")` at line 19. Resolves to `/emails/threads/1/mark-unread/`. |
| `templates/emails/_thread_card.html` | Per-user unread visual indicators (bold + blue dot) | VERIFIED | 4 occurrences of `thread.is_unread` controlling font-semibold, blue dot div, font-bold (sender), font-bold (subject). |
| `templates/emails/thread_list.html` | Sidebar unread count badges with conditional styling | VERIFIED | Conditional badge pattern for all 4 sidebar views. `unread_mine`, `unread_unassigned`, `unread_open`, `unread_closed` all present. |
| `templates/emails/_thread_detail.html` | Mark as unread button in action bar | VERIFIED | `hx-post="{% url 'emails:mark_thread_unread' thread.pk %}"` at line 220. Keyboard shortcut at line 528. |
| `templates/base.html` | Tab title with unread count prefix | VERIFIED | `{% if unread_total %}({{ unread_total }}) {% endif %}` at line 7. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `views.py:thread_detail` | `ThreadReadState` | `update_or_create` on GET | WIRED | Pattern `ThreadReadState.objects.update_or_create` found at views.py:898 |
| `views.py:mark_thread_unread` | `ThreadReadState` | `update_or_create` with is_read=False | WIRED | `defaults={"is_read": False, "read_at": None}` at views.py:924-927 |
| `views.py:assign_thread_view` | `ThreadReadState` | reset read state for assignee | WIRED | `ThreadReadState.objects.update_or_create(thread=thread, user=assignee, ...)` at views.py:1055 |
| `_thread_card.html` | `views.py:annotate_unread` | `thread.is_unread` annotation | WIRED | `{% if thread.is_unread %}` in card template; `annotate_unread(qs, user)` called at thread_list views.py:116 |
| `thread_list.html` | `views.py:sidebar_counts` | `unread_mine`, `unread_open` context vars | WIRED | `sidebar_counts.unread_mine`, `sidebar_counts.unread_unassigned`, `sidebar_counts.unread_open`, `sidebar_counts.unread_closed` all present in template |
| `_thread_detail.html` | `urls.py:mark_thread_unread` | `hx-post` URL | WIRED | `{% url 'emails:mark_thread_unread' thread.pk %}` at _thread_detail.html:220 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| READ-01 | 04-01-PLAN | Per-user read state is tracked for each thread (ThreadReadState model) | SATISFIED | ThreadReadState imported and used via update_or_create in thread_detail, mark_thread_unread, assign_thread_view. Model pre-exists from Phase 1 migration. |
| READ-02 | 04-01-PLAN | Opening a thread detail panel marks it as read for the current user | SATISFIED | `thread_detail` view upserts ThreadReadState with is_read=True at views.py:898. TestMarkAsRead passes. |
| READ-03 | 04-02-PLAN | Unread threads display with bold text and blue indicator dot (visual distinction) | SATISFIED (automated) | `_thread_card.html` uses `thread.is_unread` for bold/dot (4 occurrences). Automated: no `status == 'new'` styling remnants. Human: visual confirmation needed. |
| READ-04 | 04-01-PLAN | User can mark a thread as unread from the detail panel | SATISFIED | `mark_thread_unread` endpoint (views.py:921), URL wired (urls.py:19), button in detail template (line 220), keyboard shortcut 'U' (line 528). |
| READ-05 | 04-02-PLAN | Sidebar shows unread count badge next to "My Inbox" view | SATISFIED (automated) | Conditional badges for all 4 sidebar views in thread_list.html. `unread_mine` key in sidebar_counts context verified by TestSidebarUnreadCounts. Human: visual badge rendering. |

No orphaned requirements. All 5 READ-* requirements are claimed by plans and have codebase evidence.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder code found in phase-modified files. No empty handler stubs or return-null implementations. The `placeholder` occurrences found in templates are HTML input field attributes, not code stubs.

### Human Verification Required

All automated checks pass. The following behaviors require browser observation:

#### 1. Unread thread visual appearance

**Test:** Create an unread ThreadReadState in the Django shell, then load `/emails/`. Confirm the thread card shows bold text and a blue dot indicator.
**Expected:** Card renders with visibly bolder font and a small blue circle to the left of the sender name.
**Why human:** CSS class application and visual rendering cannot be verified programmatically.

#### 2. Read-on-open OOB card swap

**Test:** Click an unread thread card. Without a page reload, the card in the list should immediately update to normal weight with no blue dot.
**Expected:** The HTMX OOB swap fires synchronously with the detail panel opening; card loses bold styling in-place.
**Why human:** Requires observing HTMX DOM mutation live in a browser.

#### 3. Mark as Unread button behavior

**Test:** With a thread detail panel open, click the envelope button in the action bar.
**Expected:** Detail panel closes (shows "Select a thread" placeholder), card in list reverts to bold+dot styling.
**Why human:** Requires HTMX swap result observation in browser.

#### 4. 'U' keyboard shortcut

**Test:** With a thread detail panel open, press the 'U' key (not inside an input field).
**Expected:** Same behavior as clicking Mark as Unread — panel closes, card goes unread.
**Why human:** Keyboard event handling and HTMX trigger behavior requires live browser testing.

#### 5. Sidebar badge conditional styling

**Test:** Ensure at least one unread thread exists for the logged-in user. Check the sidebar.
**Expected:** "My Inbox" (and any relevant views) show a blue pill badge with the count. When all are read, badge reverts to muted grey.
**Why human:** Color differentiation (blue pill vs muted grey) requires visual inspection.

#### 6. Browser tab title update

**Test:** Have unread threads, then open one. Observe tab title before and after.
**Expected:** Before: "(N) VIPL Triage". After opening and reading: count decrements or prefix disappears.
**Why human:** Tab title is updated via JavaScript; requires live browser observation and may depend on OOB partial swap timing.

#### 7. Assignment unread reset

**Test:** Log in as admin, assign a thread to a member user. Log in as that member. Check if the thread appears unread in their "My Inbox".
**Expected:** Assigned thread shows bold+dot for the newly-assigned member.
**Why human:** Requires two-user session or multi-step verification combining DB state and UI rendering.

### Test Suite Status

- `apps/emails/tests/test_read_state.py`: 12/12 passed
- Full suite: 677 passed, 1 skipped, 0 failed (no regressions)

---

_Verified: 2026-03-15T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
