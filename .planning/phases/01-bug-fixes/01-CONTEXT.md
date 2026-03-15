# Phase 1: Bug Fixes - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 5 known bugs from v2.5.0: welcome double-show, read/unread markers not working for new threads, reopened status missing, avatar sync broken, AI assign button not working.

</domain>

<decisions>
## Implementation Decisions

### BUG-01: Welcome double-show
- Welcome banner uses localStorage "don't show again" + sessionStorage per-session dismiss
- Bug: likely fires twice on login redirect flow (OAuth callback → dashboard)
- Fix: deduplicate by checking flag before rendering, or debounce the JS show logic

### BUG-02: Read/unread markers
- Root cause: pipeline creates Thread but NO ThreadReadState rows → "no row = read" → new emails appear read to everyone
- Fix: pipeline should create `ThreadReadState(is_read=False)` for all active users when:
  1. A new Thread is created
  2. An existing thread is reopened (new email on closed thread)
- This also fixes the edge case where users who never opened a thread don't see new emails as unread
- Keep "no row = read" as the default for backward compat (existing threads stay read)
- Active users = `User.objects.filter(is_active=True)` — only 4-5 users, cheap query

### BUG-03: Reopened status
- `Thread.Status.REOPENED` exists in model but pipeline logs `REOPENED` activity then sets status back to `NEW`
- Need: when a new email arrives on a closed thread, set status to `reopened` (not `new`)
- Need: status badge/color for "Reopened" in templates (currently falls through to default)
- Need: pipeline to also create `ThreadReadState(is_read=False)` on reopen (covered by BUG-02 fix)

### BUG-04: Avatar sync
- `_update_avatar()` in `adapters.py` fetches Google profile photo on OAuth login
- Bug: likely a URL construction or caching issue — avatar shows initial circle instead
- Check: does `avatar_url` field actually get populated? Is the Google People API call succeeding?
- Fix: verify the API call, ensure avatar_url is saved and propagated to templates

### BUG-05: AI Assign button
- `accept-suggestion` URL exists in `urls.py` but only one file references it
- Bug: likely the button's HTMX endpoint is broken or the view doesn't return proper response
- Fix: trace the HTMX POST flow, ensure view exists and returns card OOB swap

### Claude's Discretion
- Exact unread row creation strategy (bulk_create vs loop)
- Whether to add tests for each bug fix (recommended)
- Reopened badge color choice (suggest amber/yellow to distinguish from New/green)

</decisions>

<specifics>
## Specific Ideas

- Read/unread fix must not cause wall-of-bold for existing threads (backward compat)
- Reopened status should be visually distinct from New — different color badge
- QA confirmed blue dot (w-1.5 h-1.5 bg-blue-500) + font-semibold styling is correct in templates

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `annotate_unread()` in views.py — queryset annotation, works correctly given rows exist
- `_update_avatar()` in adapters.py — Google avatar fetch helper
- `update_thread_preview()` in assignment.py — denormalized field updater called by pipeline
- `ThreadReadState` model — user/thread/is_read/read_at fields

### Established Patterns
- OOB swap pattern: views return detail HTML + card OOB swap for real-time updates
- `update_or_create` for ThreadReadState (used in mark_read, mark_unread, assign)
- Status badge colors via `status_base` template filter
- Activity log for all state changes

### Integration Points
- `apps/emails/services/pipeline.py:_persist_email()` — where new thread/reopen detection happens
- `apps/emails/views.py:thread_detail()` — marks thread as read on open
- `apps/accounts/adapters.py:VIPLSocialAccountAdapter` — OAuth callback with avatar fetch
- `templates/emails/_thread_card.html` — unread styling (blue dot + bold)
- `templates/base.html` — welcome banner JS

### Key Files
- `apps/emails/services/pipeline.py` — BUG-02, BUG-03
- `apps/emails/views.py` — BUG-02, BUG-05
- `apps/accounts/adapters.py` — BUG-04
- `templates/base.html` — BUG-01
- `templates/emails/_thread_card.html` — BUG-02, BUG-03
- `apps/emails/models.py` — BUG-03 (status choices)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-bug-fixes*
*Context gathered: 2026-03-15*
