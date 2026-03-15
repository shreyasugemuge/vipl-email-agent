---
created: 2026-03-15T11:05:00.000Z
title: Fix spam label not showing on cards
area: ui
files:
  - templates/emails/_thread_card.html:75
  - templates/emails/_email_card.html:54-56
  - templates/emails/_thread_detail.html:41-43
  - apps/emails/views.py:79-83
---

## Problem

Spam badge/label is not displaying on thread cards despite being added in v2.4.1. Likely causes:

1. **Thread card**: Uses `thread.has_spam` (line 75) which requires an `Exists` annotation added in views.py. The annotation may not be reaching the template correctly, or the `has_spam` attribute name may not match what the template expects.

2. **Email card**: Has spam badge at line 54-56 (`{% if email.is_spam %}`) — should work since `is_spam` is a direct model field. Verify it renders.

3. **Thread detail**: Uses `has_spam` context variable (line 41-43) — verify `_build_thread_detail_context` passes it.

4. **Prefetch issue**: The `has_spam` annotation uses `Exists(Email.objects.filter(thread=OuterRef("pk"), is_spam=True))` — verify the subquery is correct and not filtered out by SoftDeleteManager.

## Solution

1. Debug by checking `thread.has_spam` value in dev inspector or test_pipeline output
2. Verify the `Exists` annotation in `thread_list()` view is using correct field reference
3. Ensure `_build_thread_detail_context` computes `has_spam` from prefetched emails
4. Test with `test_pipeline --count 5` — some fake emails should be spam-flagged
