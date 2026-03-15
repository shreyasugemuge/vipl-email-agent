---
created: 2026-03-15T10:36:55.087Z
title: Fix cross-inbox email deduplication
area: api
files:
  - apps/emails/services/pipeline.py
  - apps/emails/services/gmail_poller.py
  - apps/emails/models.py
---

## Problem

When the same email is delivered to multiple monitored inboxes (e.g., info@ and sales@), it still appears as duplicate entries in the dashboard. Phase 10 introduced cross-inbox dedup logic, but it's not working correctly in production. Users see the same email multiple times, cluttering the inbox view and potentially causing duplicate triage/assignment work.

## Solution

- Audit the existing dedup logic in the pipeline — check how `message_id` (RFC 822 Message-ID header) is being used for uniqueness
- Ensure the pipeline checks for existing emails by Message-ID before creating new records, regardless of which inbox it was polled from
- Handle edge cases: same thread across inboxes, CC'd emails, forwarded copies
- Add a unique constraint or dedup check at the model level (not just pipeline logic)
- Consider showing which inboxes received the email rather than creating separate entries
- Add tests covering multi-inbox scenarios
