---
phase: 04-collaboration
verified: 2026-03-15T08:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
human_verification:
  - test: "Open a thread, type a note with @mention, submit — confirm amber card appears inline with 'Internal note' label"
    expected: "Note appears in timeline with amber background and author name, separate from email messages"
    why_human: "Template rendering and visual styling cannot be verified programmatically"
  - test: "Open the same thread in two browser sessions — confirm viewer badge appears for the second session"
    expected: "Overlapping avatar circle(s) with 'viewing' pulse text appear in the sticky header within 15s"
    why_human: "Requires two live browser sessions; polling behavior is real-time and cannot be simulated by grep"
  - test: "Navigate away from a thread — confirm viewer badge disappears for other session within 30s"
    expected: "Badge disappears (sendBeacon fires clear-viewer, or 30s stale timeout expires)"
    why_human: "Requires live sessions and timing observation"
---

# Phase 4: Collaboration Verification Report

**Phase Goal:** Team members can discuss threads internally and see who else is viewing a thread
**Verified:** 2026-03-15T08:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can add an internal note on any thread — notes are never visible to the email sender | VERIFIED | `InternalNote` model exists with `thread` FK, no email/Gmail send path; `add_note_view` stores to DB only |
| 2 | Notes support @mentions that trigger a notification to the mentioned team member | VERIFIED | `parse_mentions()` in `assignment.py` + `notify_mention()` sends Chat text + Django email; wired in `add_note_view` |
| 3 | Notes appear inline in thread detail, visually distinct from email messages (amber background, "Internal note" label) | VERIFIED | `_thread_note.html` uses `bg-amber-50 border-l-4 border-amber-400`; timeline merges `type="note"` alongside `type="message"` |
| 4 | When another user has a thread open, a viewing indicator appears in the detail panel | VERIFIED | `ThreadViewer` model + `viewer_heartbeat` endpoint + `_viewer_badge.html` partial wired in `_thread_detail.html` with `setInterval` 15s |
| 5 | ActivityLog records NOTE_ADDED and MENTIONED actions | VERIFIED | Both choices exist in `ActivityLog.Action`; `add_note_view` creates both log entries |
| 6 | Viewer is removed after 30s inactivity or navigation | VERIFIED | `get_active_viewers` uses 30s cutoff; `sendBeacon` + idle detection (25s threshold) in template JS |
| 7 | Viewer badge shows overlapping avatars with count | VERIFIED | `_viewer_badge.html` renders up to 2 avatar circles + "+N" overflow with `title` tooltip |
| 8 | Note form targets thread-detail-panel via HTMX | VERIFIED | `hx-post="{% url 'emails:add_note' thread.pk %}"` `hx-target="#thread-detail-panel"` `hx-swap="innerHTML"` |
| 9 | @mention autocomplete shows team members | VERIFIED | `team_members_json` passed in context; vanilla JS dropdown wired to `#note-textarea` |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/emails/models.py` | InternalNote model + NOTE_ADDED/MENTIONED actions | VERIFIED | `class InternalNote` line 230; `NOTE_ADDED` line 191, `MENTIONED` line 192 |
| `apps/emails/models.py` | ThreadViewer model | VERIFIED | `class ThreadViewer` line 254 with `unique_together = [("thread", "user")]` |
| `templates/emails/_thread_note.html` | Note card with amber styling, "Internal note" label | VERIFIED | 35 lines; `bg-amber-50 border-l-4 border-amber-400`; label at line 9 |
| `templates/emails/_viewer_badge.html` | Viewer badge partial with overlapping avatars | VERIFIED | 21 lines; avatar loop with `-space-x-2` overlap, `+N` overflow, tooltip `title` |
| `apps/emails/views.py` | `add_note_view` endpoint | VERIFIED | Defined line 826; creates InternalNote, ActivityLog, parses @mentions, fires notifications |
| `apps/emails/views.py` | `viewer_heartbeat` and `get_active_viewers` | VERIFIED | `viewer_heartbeat` line 775; `get_active_viewers` line 764 |
| `apps/emails/views.py` | `clear_viewer` endpoint | VERIFIED | Defined line 791; returns 204 |
| `apps/emails/services/assignment.py` | `parse_mentions()` + `notify_mention()` | VERIFIED | `parse_mentions` line 29, `notify_mention` line 48; fire-and-forget with try/except |
| `apps/emails/tests/test_notes.py` | Tests for note creation, @mention parsing, permissions | VERIFIED | 204 lines, 20 tests; covers model CRUD, parse_mentions (9 cases), notify_mention (3 cases) |
| `apps/emails/tests/test_viewing.py` | Tests for viewing presence lifecycle | VERIFIED | 210 lines, 11 tests; covers model, get_active_viewers, heartbeat, clear_viewer |
| `apps/emails/migrations/0010_alter_activitylog_action_internalnote.py` | Migration for InternalNote | VERIFIED | File exists |
| `apps/emails/migrations/0011_threadviewer.py` | Migration for ThreadViewer | VERIFIED | File exists |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_thread_detail.html` note form | `views.add_note_view` | `hx-post="{% url 'emails:add_note' thread.pk %}"` | WIRED | Line 238 of template; URL registered in urls.py line 12 |
| `views.add_note_view` | `models.InternalNote` | `InternalNote.objects.create(...)` | WIRED | Line 844 of views.py |
| `views.add_note_view` | `assignment.notify_mention` | call with try/except after @mention lookup | WIRED | Lines 855-870 of views.py; imported as `_notify_mention` |
| `_thread_detail.html` JS | `views.viewer_heartbeat` | `setInterval` fetch POST every 15s | WIRED | Lines 275, 307 of template; URL at `viewer_heartbeat` named URL |
| `views.viewer_heartbeat` | `models.ThreadViewer` | `ThreadViewer.objects.update_or_create(...)` | WIRED | Lines 777-783 of views.py |
| `views.thread_detail` | `models.ThreadViewer` | `ThreadViewer.objects.update_or_create(...)` on load | WIRED | Lines 813-817 of views.py; `active_viewers` in context line 820 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| COLLAB-01 | 04-01-PLAN.md | User can add internal notes on a thread (team-only, not visible to customer) | SATISFIED | InternalNote model; `add_note_view`; no external email path for notes |
| COLLAB-02 | 04-01-PLAN.md | Notes support @mentions that notify the mentioned team member | SATISFIED | `parse_mentions()` + `notify_mention()` (Chat + Django email); wired in view |
| COLLAB-03 | 04-01-PLAN.md | Notes appear inline in thread detail, visually distinct from email messages | SATISFIED | `_thread_note.html` amber styling; timeline merged with `type="note"` entries |
| COLLAB-04 | 04-02-PLAN.md | Collision detection shows "X is viewing this thread" when another user has it open | SATISFIED | `ThreadViewer` + heartbeat endpoint + `_viewer_badge.html` + 15s polling JS |

All 4 COLLAB requirements satisfied. No orphaned requirements found — REQUIREMENTS.md maps exactly COLLAB-01 through COLLAB-04 to Phase 4.

### Anti-Patterns Found

None detected. No TODO/FIXME/PLACEHOLDER comments found in phase files. No stub implementations (empty returns, console.log only). All view functions contain real ORM operations and return rendered templates.

### Human Verification Required

#### 1. Note Submission and Inline Display

**Test:** Open a thread detail, type a note in the textarea at the bottom, submit
**Expected:** The note appears inline in the timeline with amber/yellow left border and "Internal note" label above the text, visually distinct from email message cards
**Why human:** Visual styling correctness and HTMX re-render behavior require a browser

#### 2. @Mention Autocomplete

**Test:** Type `@` in the note textarea — a dropdown of team members should appear; typing more letters filters the list; pressing Enter or clicking inserts the username
**Expected:** Dropdown appears, filters correctly, selection inserts `@username` into textarea
**Why human:** JS event-driven dropdown interaction cannot be verified by static analysis

#### 3. Viewer Badge Presence

**Test:** Open the same thread in two browser windows (or incognito); observe the first window
**Expected:** Within 15 seconds, the first window shows a small avatar circle in the sticky thread header with a pulsing "viewing" label
**Why human:** Requires two live sessions; polling behavior is time-dependent

#### 4. Viewer Badge Disappears on Navigation

**Test:** Navigate away from the thread in the second window; wait up to 30 seconds
**Expected:** The viewer badge disappears from the first window (sendBeacon fires immediately, or 30s stale timeout removes the record)
**Why human:** Requires live browser + timing observation

### Gaps Summary

No gaps. All automated checks passed:

- `pytest apps/emails/tests/test_notes.py apps/emails/tests/test_viewing.py` — 31 tests passed
- `python manage.py check` — 0 issues
- Migrations 0010 and 0011 exist
- All 4 key links verified via code inspection
- All 4 COLLAB requirements have clear implementation evidence

4 items flagged for human verification (visual/real-time behavior) — these are standard UI verification items, not blockers.

---

_Verified: 2026-03-15T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
