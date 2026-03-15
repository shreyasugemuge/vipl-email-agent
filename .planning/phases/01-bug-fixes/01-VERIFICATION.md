---
phase: 01-bug-fixes
verified: 2026-03-15T17:30:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Login via Google OAuth and observe welcome banner"
    expected: "Banner appears once. Navigating away and back within the same session does not show it again."
    why_human: "sessionStorage behavior across redirect chain cannot be verified by static grep"
  - test: "Receive a new email into a closed thread and navigate to thread list"
    expected: "Thread card shows amber 'Reopened' badge. Thread appears bold (unread) for all logged-in users."
    why_human: "Requires live pipeline + active Gmail poll to trigger the code path end-to-end"
  - test: "Log out and log back in via Google OAuth"
    expected: "Avatar updates in sidebar and team page within the same session"
    why_human: "Requires live Google OAuth flow and actual Google profile picture URL"
---

# Phase 1: Bug Fixes — Verification Report

**Phase Goal:** All known bugs from v2.5.0 are resolved — users no longer encounter broken behaviors
**Verified:** 2026-03-15T17:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Welcome banner shows once per session on login, never duplicates | VERIFIED | `email_list.html` lines 264-273: three-check IIFE sets `vipl_welcome_shown` before removing `hidden`; subsequent page loads within the session see the flag and skip display |
| 2 | Thread cards display read/unread state with visible bold text and blue dot indicators | VERIFIED | `pipeline.py` lines 142-167: `_create_unread_states_for_all_users` bulk-creates `ThreadReadState(is_read=False)` for all active users on new/reopened threads. `_thread_card.html` lines 6, 21-24, 48: `is_unread` annotation drives `font-semibold` on card, blue dot `bg-blue-500`, and `font-bold text-slate-900` on sender/subject |
| 3 | User can reopen a closed thread and the "Reopened" status tag appears in card and detail | VERIFIED | `models.py` line 16: `REOPENED = "reopened", "Reopened"` added to `Thread.Status`. `pipeline.py` line 263: `thread.status = Thread.Status.REOPENED`. `email_tags.py` line 24: `"reopened": "amber"` in `STATUS_BASE`, line 72: `"reopened": "amber-500"` in `status_color`, line 182: tooltip. `_thread_card.html` line 56: uses `status_base` filter. `_editable_status.html`: `Thread.Status.choices` includes REOPENED in dropdown. Views: all `status__in` filter lists include `"reopened"` |
| 4 | Google avatar updates on each OAuth login and displays correctly | VERIFIED | `adapters.py` line 79: `_update_avatar(user, extra_data)` called on every repeat login. Line 64: same call on auto-link path. Lines 107, 122: `avatar_url` set in `save_user` for both superadmin and new users. Guard `if picture and getattr(user, "avatar_url", None) != picture` prevents no-op saves |
| 5 | AI Assign button in thread detail triggers assignment and updates the card without errors | VERIFIED | `views.py` line 737: `accept_thread_suggestion` returns `_render_thread_detail_with_oob_card(thread, request, user)`. Line 789: `reject_thread_suggestion` does the same. Helper at line 1117 renders `_thread_card.html` with `{"thread": thread, "oob": True}`, which sets `hx-swap-oob="outerHTML"` on the card div |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/emails/services/pipeline.py` | ThreadReadState creation + REOPENED status | VERIFIED | `_create_unread_states_for_all_users` helper at line 142; called at line 254 (new thread) and 275 (reopen). `Thread.Status.REOPENED` set at line 263. Pattern `ThreadReadState.*bulk_create` confirmed at line 167 |
| `apps/emails/models.py` | REOPENED status choice on Thread.Status | VERIFIED | Line 16: `REOPENED = "reopened", "Reopened"` in `Thread.Status(TextChoices)`. CharField max_length=20 accommodates "reopened" — no migration needed |
| `apps/emails/templatetags/email_tags.py` | Status color and tooltip for reopened | VERIFIED | Line 24: `"reopened": "amber"` in `STATUS_BASE`. Line 72: `"reopened": "amber-500"` in `status_color`. Line 182: `"reopened": "Thread reopened by new message"` in `STATUS_TOOLTIPS` |
| `apps/accounts/adapters.py` | Reliable avatar sync on OAuth login | VERIFIED | `_update_avatar` called on all three login paths (new user, auto-link, repeat login). Saves only when `picture != current avatar_url`. No code changes were needed — existing implementation was correct |
| `templates/emails/email_list.html` | Deduplicated welcome banner JS | VERIFIED | Lines 263-273: IIFE checks `vipl_welcome_dismissed` (session dismiss), `vipl_welcome_permanent` (localStorage), and `vipl_welcome_shown` (shown this session). Sets `vipl_welcome_shown` before revealing banner |
| `apps/emails/views.py` | accept/reject suggestion returns OOB card swap | VERIFIED | Lines 737, 789: both views call `_render_thread_detail_with_oob_card`. All `status__in` filter lists include `"reopened"` at lines 130, 134, 184, 203, 206 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pipeline.py` | `models.py` | `ThreadReadState.objects.bulk_create` on new thread | WIRED | Line 167: `ThreadReadState.objects.bulk_create(new_states, ignore_conflicts=True)`. Called at line 254 for new threads, line 275 for reopened threads |
| `pipeline.py` | `models.py` | `Thread.Status.REOPENED` on reopen | WIRED | Line 263: `thread.status = Thread.Status.REOPENED`. Guard: `thread.status not in (Thread.Status.NEW, Thread.Status.REOPENED)` prevents double-reopen |
| `email_tags.py` | `_thread_card.html` | `status_base` filter returning amber for reopened | WIRED | `email_tags.py` line 24 maps `"reopened"` → `"amber"`. `_thread_card.html` line 56: `bg-{{ thread.status|status_base }}-50 text-{{ thread.status|status_base }}-600` |
| `views.py:accept_thread_suggestion` | `_thread_card.html` | OOB swap after accepting AI suggestion | WIRED | Line 737: `_render_thread_detail_with_oob_card`. Helper line 1117: `render_to_string("emails/_thread_card.html", {"thread": thread, "oob": True})`. Card line 4: `hx-swap-oob="outerHTML"` |
| `email_list.html` | `sessionStorage` | Welcome banner dedup flag | WIRED | Line 264: `sessionStorage.getItem('vipl_welcome_shown')`. Line 266: `sessionStorage.setItem('vipl_welcome_shown', '1')` set before revealing banner |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| BUG-01 | 01-02-PLAN.md | Welcome message no longer shows twice at login | SATISFIED | `email_list.html` IIFE with `vipl_welcome_shown` shown-flag. SUMMARY commit `43ac117` |
| BUG-02 | 01-01-PLAN.md | Read/unread markers visible on thread cards | SATISFIED | `_create_unread_states_for_all_users` in pipeline; `is_unread` annotation in views; bold + blue dot in `_thread_card.html` |
| BUG-03 | 01-01-PLAN.md | Reopened status tag and flow works end-to-end | SATISFIED | `REOPENED` in `Thread.Status`; pipeline sets it on reopen; amber badge via `status_base` filter; "reopened" in all filter lists |
| BUG-04 | 01-01-PLAN.md | Google avatar syncs on login | SATISFIED | `_update_avatar` called on all three OAuth paths; no code changes needed — existing implementation verified correct by 8 existing tests |
| BUG-05 | 01-02-PLAN.md | AI Assign button in detail card works | SATISFIED | `accept_thread_suggestion` and `reject_thread_suggestion` both return `_render_thread_detail_with_oob_card`. SUMMARY commit `bd7d33f` + 4 new tests |

No orphaned requirements. All 5 BUG-* requirements for Phase 1 appear in plan frontmatter and are verified in code.

### Anti-Patterns Found

None. All modified files scanned:
- `apps/emails/services/pipeline.py` — no TODO/FIXME/placeholders, no empty returns, no console.log
- `apps/emails/models.py` — no stubs; REOPENED is a real TextChoices entry
- `apps/emails/templatetags/email_tags.py` — both dicts fully populated for "reopened"
- `apps/accounts/adapters.py` — no changes, no stubs
- `templates/emails/email_list.html` — functional JS IIFE, no placeholder logic
- `apps/emails/views.py` — both accept/reject views call real helper, no stub returns

### Human Verification Required

#### 1. Welcome Banner — OAuth Redirect Flow

**Test:** Log out (or use a fresh incognito window), log in via Google OAuth, observe the welcome banner on the dashboard.
**Expected:** Banner appears exactly once. Navigate away with browser back/forward or HTMX navigation and return — banner does not reappear in the same session. Open a new tab (same session) — banner does not show again.
**Why human:** sessionStorage behavior across an OAuth redirect chain (login → Google → callback → dashboard) cannot be verified by static code analysis. The three-check guard is correct, but real-world redirect timing must be confirmed.

#### 2. Reopened Thread — Card and Detail Badge

**Test:** With the scheduler running in `dev` mode, send an email to a thread that was previously closed. Check the thread list.
**Expected:** Thread card shows amber "Reopened" badge. Card text is bold. Blue unread dot appears. Detail panel shows amber "Reopened" status chip.
**Why human:** Requires a live poll cycle to trigger the `REOPENED` code path in `save_email_to_db`. Static analysis confirms the logic but the full flow needs runtime validation.

#### 3. Avatar Sync

**Test:** Log out and log in via Google OAuth. Check the avatar in the sidebar and on the `/accounts/team/` page.
**Expected:** Avatar URL saved from Google's `picture` field is displayed. If the Google account's profile picture changed since the last login, the new picture appears.
**Why human:** Requires a live Google OAuth flow. The `_update_avatar` implementation is correct but end-to-end rendering (including `referrerpolicy="no-referrer"` behavior) needs visual confirmation.

### Gaps Summary

No gaps found. All 5 success criteria are verified in the actual codebase.

The SUMMARY claims match what was found in code:
- `_create_unread_states_for_all_users` exists and is wired at both call sites (new thread, reopen)
- `Thread.Status.REOPENED` is present in models.py and referenced in pipeline.py
- Amber color and tooltip for "reopened" are in both STATUS_BASE and STATUS_TOOLTIPS
- `vipl_welcome_shown` sessionStorage flag is set before banner display
- Both accept/reject suggestion views use `_render_thread_detail_with_oob_card`
- All `status__in` filter lists in views.py include `"reopened"`

---

_Verified: 2026-03-15T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
