---
created: 2026-03-15T10:56:10.330Z
title: Add spam feedback learning and user spam controls
area: ui
files:
  - apps/emails/services/spam_filter.py
  - apps/emails/views.py
  - apps/emails/models.py
  - templates/emails/_thread_detail.html
  - templates/emails/_email_detail.html
  - templates/emails/_thread_card.html
---

## Problem

The current spam filter uses 13 static regex patterns — no user feedback loop. Users cannot:
1. Mark an email as "spam" or "not spam" from the UI (no yes/no toggle)
2. Have the system learn from their corrections (misclassified emails stay misclassified)
3. See spam confidence or reasoning on cards/detail panels

The whitelist feature exists (whitelist sender from thread detail) but there's no inverse — no way to flag a non-spam email as spam, and no way for corrections to feed back into future filtering.

## Solution

1. **Spam toggle on detail panels**: Add "Mark as Spam" / "Not Spam" button on thread detail and email detail panels. POST endpoint updates `is_spam` field and creates ActivityLog entry.

2. **Spam learning model**: Create `SpamFeedback` model to store user corrections (email_id, original_verdict, user_verdict, user, timestamp). Use these corrections to:
   - Auto-whitelist senders marked "not spam" N times
   - Auto-add patterns from emails marked "spam" N times
   - Export corrections as training data for future AI-based spam filter

3. **Spam indicator on cards**: Already added spam badge on thread cards (v2.4.1). Ensure it shows on both thread and email cards with tooltip. Add spam confidence if available.

4. **Spam filter stats**: Add spam filter hit rates to the dev inspector MIS table — which patterns match most, false positive rate from user corrections.

5. **Spam review queue**: Optional view filter `?view=spam` to see all spam-flagged emails for batch review (mark all as not-spam, whitelist sender, etc).
