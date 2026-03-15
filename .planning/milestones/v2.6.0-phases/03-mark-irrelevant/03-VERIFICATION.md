---
phase: 03-mark-irrelevant
verified: 2026-03-16T08:00:00Z
status: passed
score: 20/20 must-haves verified
re_verification: false
---

# Phase 3: Mark Irrelevant Verification Report

**Phase Goal:** Gatekeeper can mark threads as irrelevant with a reason, hiding them from the default triage queue and providing activity-log audit trail.
**Verified:** 2026-03-16T08:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Gatekeeper/admin can POST to mark_irrelevant with a reason and thread status becomes IRRELEVANT | VERIFIED | `mark_irrelevant` view at views.py:1729; test `test_gatekeeper_can_mark_irrelevant` PASSES |
| 2 | Empty reason is rejected with 403 | VERIFIED | `HttpResponseForbidden("Reason is required.")` at views.py:1743; test `test_empty_reason_rejected` PASSES |
| 3 | Member user gets 403 when trying to mark irrelevant | VERIFIED | `user.can_triage` gate at views.py:1734; test `test_member_forbidden` PASSES |
| 4 | Irrelevant threads do not appear in Triage Queue, My Inbox, or All Open views | VERIFIED | `open_q = Q(status__in=["new", "acknowledged"])` excludes irrelevant; `has_explicit_status` logic at views.py:145-157; test `test_irrelevant_excluded_from_default_views` PASSES |
| 5 | Irrelevant threads appear only when ?status=irrelevant filter is used | VERIFIED | `has_explicit_status` flag at views.py:145 bypasses view-level constraints; test `test_status_filter_shows_irrelevant` PASSES |
| 6 | Sidebar counts exclude irrelevant from unassigned, all_open, urgent, new | VERIFIED | `irrelevant=Count("pk", filter=Q(status="irrelevant"))` at views.py:220; `open_q` naturally excludes irrelevant from all active-status aggregates |
| 7 | ActivityLog entry with action=MARKED_IRRELEVANT and full reason text is created | VERIFIED | `ActivityLog.objects.create(action=ActivityLog.Action.MARKED_IRRELEVANT, detail=reason, ...)` at views.py:1753; test `test_activity_log_created` PASSES |
| 8 | Revert sets status back to NEW, clears assignment, creates REVERTED_IRRELEVANT ActivityLog | VERIFIED | `revert_irrelevant` view clears assigned_to/assigned_by/assigned_at, creates ActivityLog with REVERTED_IRRELEVANT; tests `test_revert_resets_status` and `test_revert_activity_log` PASS |
| 9 | Non-irrelevant thread cannot be reverted (403) | VERIFIED | Guard at views.py:1781; test `test_revert_non_irrelevant_rejected` PASSES |
| 10 | Detail panel shows amber Mark Irrelevant button for gatekeeper/admin, hidden for members | VERIFIED | `{% if request.user.can_triage and thread.status != "irrelevant" %}` gate at _thread_detail.html:418; amber `bg-amber-500` button present |
| 11 | Clicking Mark Irrelevant opens a modal with textarea for reason | VERIFIED | `id="irrelevant-modal"` at _thread_detail.html:431; `openIrrelevantModal()` JS function at :737; textarea `id="irrelevant-reason-input"` at :442 |
| 12 | Modal submits via HTMX POST, swaps detail panel on success, shows toast | VERIFIED | `hx-post="{% url 'emails:mark_irrelevant' thread.pk %}" hx-target="#thread-detail-panel" hx-swap="innerHTML"` at _thread_detail.html:436 |
| 13 | Irrelevant thread shows Revert to New button instead of Mark Irrelevant | VERIFIED | `{% if request.user.can_triage and thread.status == "irrelevant" %}` gate at _thread_detail.html:465; hx-post to `revert_irrelevant` at :468 |
| 14 | Context menu has Mark Irrelevant entry in Status group for gatekeeper/admin | VERIFIED | `Mark Irrelevant` entry at _context_menu.html:125 with permission gate and `I` kbd shortcut |
| 15 | Context menu click opens detail panel and auto-opens reason modal | VERIFIED | `hx-get="{% url 'emails:thread_detail' thread.pk %}?open_modal=irrelevant"` at _context_menu.html:117; JS auto-open via `htmx:afterSettle` listener at _thread_detail.html:769 |
| 16 | Keyboard shortcut I opens the modal when detail panel is visible | VERIFIED | `keydown` listener for `key === 'I'` / `key === 'i'` at _thread_detail.html:759 (skips input/textarea elements) |
| 17 | Irrelevant badge appears on thread cards when viewing via status filter | VERIFIED | `{% if thread.status == "irrelevant" %}` badge with `bg-amber-100 text-amber-700` at _thread_card.html:85-86 |
| 18 | Irrelevant stat card visible to gatekeepers/admins only | VERIFIED | `{% if request.user.can_triage and sidebar_counts.irrelevant > 0 %}` gate at thread_list.html:303; `data-stat="irrelevant"` at :307 |
| 19 | Activity timeline shows amber-styled entry for marked_irrelevant with full reason | VERIFIED | `bg-amber-50 border-l-2 border-amber-400` block at _thread_detail.html:491, renders `item.obj.detail` |
| 20 | Activity timeline shows blue-styled entry for reverted_irrelevant | VERIFIED | `bg-blue-50 border-l-2 border-blue-400` block at _thread_detail.html:502 |

**Score:** 20/20 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/emails/models.py` | Thread.Status.IRRELEVANT + 2 ActivityLog actions | VERIFIED | `IRRELEVANT = "irrelevant"` at line 16; `MARKED_IRRELEVANT` at line 212; `REVERTED_IRRELEVANT` at line 213 |
| `apps/emails/migrations/0017_add_irrelevant_status.py` | Schema migration for new choices | VERIFIED | File exists |
| `apps/emails/views.py` | mark_irrelevant + revert_irrelevant view functions | VERIFIED | Substantive implementations at lines 1729 and 1769; `irrelevant=Count` at line 220 |
| `apps/emails/urls.py` | URL patterns for mark-irrelevant and revert-irrelevant | VERIFIED | Both patterns at lines 30-31 |
| `apps/emails/tests/test_mark_irrelevant.py` | 11 tests covering permissions, filtering, activity log, revert | VERIFIED | 191 lines, 11 `def test_` methods, all 11 PASS |
| `templates/emails/_thread_detail.html` | Mark Irrelevant button, reason modal, revert button, activity timeline styling | VERIFIED | All elements present; `irrelevant-modal`, `mark_irrelevant`, `revert_irrelevant`, `marked_irrelevant`, `reverted_irrelevant`, `openIrrelevantModal` all found |
| `templates/emails/_context_menu.html` | Mark Irrelevant context menu entry | VERIFIED | Entry at line 113-128 with `open_modal=irrelevant` and `I` kbd hint |
| `templates/emails/_thread_card.html` | Irrelevant badge on thread cards | VERIFIED | Badge at lines 85-86 with `bg-amber-100 text-amber-700` |
| `templates/emails/thread_list.html` | Irrelevant stat card, status filter option | VERIFIED | Stat card at lines 303-315 with `data-stat="irrelevant"` and `sidebar_counts.irrelevant` |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `views.py::mark_irrelevant` | `Thread.Status.IRRELEVANT` | `thread.status = Thread.Status.IRRELEVANT` | WIRED | views.py:1747 |
| `views.py::mark_irrelevant` | `ActivityLog.Action.MARKED_IRRELEVANT` | `ActivityLog.objects.create(...)` | WIRED | views.py:1753 |
| `views.py::thread_list` | `sidebar_counts.irrelevant` | `irrelevant=Count(...)` aggregate | WIRED | views.py:220 |
| `_thread_detail.html` | `/threads/<pk>/mark-irrelevant/` | `hx-post` form in modal | WIRED | `hx-post="{% url 'emails:mark_irrelevant' thread.pk %}"` at line 436 |
| `_thread_detail.html` | `/threads/<pk>/revert-irrelevant/` | `hx-post` on revert button | WIRED | `hx-post="{% url 'emails:revert_irrelevant' thread.pk %}"` at line 468 |
| `_context_menu.html` | thread detail + modal auto-open | `hx-get` with `?open_modal=irrelevant` | WIRED | `_context_menu.html:117`; JS listener at `_thread_detail.html:769` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TRIAGE-01 | 03-01, 03-02 | Gatekeeper/admin can mark a thread as irrelevant with mandatory free-text reason | SATISFIED | `mark_irrelevant` view with non-empty reason validation; amber button in detail panel |
| TRIAGE-02 | 03-01, 03-02 | Irrelevant threads are closed immediately and excluded from unassigned count | SATISFIED | `open_q` excludes irrelevant; `has_explicit_status` override for ?status=irrelevant filter; sidebar counts correct |
| TRIAGE-03 | 03-02 | Mark-irrelevant available via button in detail panel and right-click context menu | SATISFIED | Button in `_thread_detail.html:418`; context menu entry in `_context_menu.html:113` |
| TRIAGE-06 | 03-01, 03-02 | Irrelevant reason stored in ActivityLog and visible in thread detail activity timeline | SATISFIED | `ActivityLog.objects.create(detail=reason, ...)` at views.py:1753; amber timeline entry renders `item.obj.detail` |

All 4 requirement IDs declared across plans for this phase are satisfied. No orphaned requirements — TRIAGE-04 and TRIAGE-05 are correctly mapped to Phase 4 (Pending) and not claimed here.

---

## Anti-Patterns Found

No blockers or warnings found. No TODO/FIXME/placeholder comments in phase-modified files. No stub implementations. All views have substantive bodies with proper error handling and DB operations.

---

## Human Verification Required

### 1. Visual modal UX

**Test:** Open any thread as admin, click "Mark Irrelevant"
**Expected:** Modal overlays correctly, backdrop blur visible, confirm button disabled until text typed, Escape closes it, I key reopens it
**Why human:** CSS animation, overlay z-index stacking, and interactive state transitions cannot be verified programmatically

### 2. Context menu auto-modal bridge

**Test:** Right-click a thread card, click "Mark Irrelevant" from context menu
**Expected:** Thread detail panel loads and reason modal auto-opens without additional clicks
**Why human:** Requires verifying the HTMX afterSettle + URL param timing sequence in a real browser

### 3. Member visibility exclusion

**Test:** Log in as a user with `role=MEMBER`, open any thread detail panel and right-click thread cards
**Expected:** "Mark Irrelevant" button, modal, context menu entry, and stat card are all absent
**Why human:** Template rendering under a specific session role requires browser verification

---

## Test Results

- `pytest apps/emails/tests/test_mark_irrelevant.py -v` — **11/11 PASSED**
- `pytest -x -q --tb=short` — **795 passed, 1 skipped** (no regressions)

---

## Summary

Phase 3 goal is fully achieved. The mark-irrelevant feature is complete end-to-end:

- Model layer: `Thread.Status.IRRELEVANT` + two ActivityLog actions with a clean migration
- Backend: `mark_irrelevant` and `revert_irrelevant` POST endpoints with `can_triage` permission gating, mandatory reason validation, transactional state changes, ActivityLog creation, and detail panel re-render
- Queryset: irrelevant excluded from all active-status views via `open_q`; accessible via `?status=irrelevant` through the `has_explicit_status` override; sidebar irrelevant count available in template context
- Frontend: amber button + reason modal (disabled-until-input confirm) in detail panel; revert button with browser confirm; amber/blue activity timeline entries; context menu entry with I keyboard hint; amber badge on thread cards; gatekeeper-only stat card
- Tests: 11 dedicated tests covering all permission scenarios, filtering, activity log content, and revert behavior — all passing
- All four requirement IDs (TRIAGE-01, TRIAGE-02, TRIAGE-03, TRIAGE-06) are satisfied

---

_Verified: 2026-03-16T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
