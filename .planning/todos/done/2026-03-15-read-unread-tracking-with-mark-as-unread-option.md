---
created: 2026-03-15T11:07:00.000Z
title: Read/unread tracking with mark as unread option
area: ui
files:
  - apps/emails/models.py
  - apps/emails/views.py
  - templates/emails/_thread_card.html
  - templates/emails/_thread_detail.html
  - templates/emails/thread_list.html
---

## Problem

Thread read/unread state is not working properly:

1. **No per-user read tracking**: Thread status `new` is a global state (visible to all users), not per-user. When any user opens a thread, it doesn't mark it as "read" for that specific user.
2. **Opening a thread doesn't mark it read**: Clicking a thread card loads the detail panel but doesn't change the visual state — the bold/blue-dot "new" indicator persists.
3. **No "mark as unread" option**: Users can't flag a thread to come back to later.
4. **Current "new" indicator**: `_thread_card.html` uses `thread.status == 'new'` for bold font + blue dot — this is the thread's workflow status, not read/unread state.

## Solution

1. **Per-user read state model**: Add `ThreadReadState` model:
   - `thread`, `user`, `read_at` (timestamp), `is_read` (bool)
   - Unique together on (thread, user)

2. **Auto-mark read on open**: In `thread_detail()` view, create/update `ThreadReadState(thread=thread, user=user, is_read=True, read_at=now)` when detail panel loads.

3. **Visual indicators**:
   - Unread: bold font-semibold + blue dot (current "new" style)
   - Read: normal font + no dot
   - Template: check `thread.is_read_by_user` (annotated in queryset) instead of `thread.status == 'new'`

4. **Mark as unread button**:
   - Small eye-slash icon in thread detail header or on card right-click/long-press
   - POST endpoint: `threads/<pk>/mark-unread/` → sets `is_read=False`
   - Re-renders card with unread styling

5. **Unread count in sidebar**: Show unread count badge next to "My Inbox" view — `ThreadReadState.objects.filter(user=user, is_read=False).count()`

6. **Queryset annotation**: In `thread_list()`, annotate `is_read_by_user=Exists(ThreadReadState.objects.filter(thread=OuterRef("pk"), user=user, is_read=True))`
