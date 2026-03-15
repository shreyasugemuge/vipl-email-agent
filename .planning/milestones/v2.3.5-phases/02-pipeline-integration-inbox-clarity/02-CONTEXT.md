# Phase 2: Pipeline Integration + Inbox Clarity - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the email pipeline thread-aware: new emails create or update Thread objects, cross-inbox duplicates are detected and deduplicated, and each email/thread clearly shows which inbox(es) it was received on. Chat notifications adapt to thread updates vs new threads.

Requirements: THRD-04, INBOX-01, INBOX-02, INBOX-03

</domain>

<decisions>
## Implementation Decisions

### Thread reopen behavior
- Any new message on a non-New thread reopens it to New status (both Closed and Acknowledged → New)
- Reopened threads get a visible "Reopened" badge/indicator so the assignee knows it was previously handled
- Keep the previous assignee on reopened threads AND send them a Chat notification about the reopen
- Fresh SLA deadlines on reopen — new ack/respond timers start from the reopen moment

### Deduplication strategy
- Store both Email records when same email arrives on info@ and sales@ — both link to the same Thread via gmail_thread_id
- Dedup detection key: same gmail_thread_id + same sender_email (within recent window)
- Skip AI triage on detected duplicates — reuse the first copy's triage result
- Skip spam filter on duplicates too — if the first copy passed, the duplicate is safe
- Send a lighter "also received on [inbox]" Chat notification for cross-inbox duplicates (not the full triage card)

### Inbox badge display
- Small colored pill badges showing "info@" / "sales@" next to thread subjects
- Multi-inbox threads show both badges: [info@] [sales@]
- Badges appear on both thread list items AND individual messages in the detail panel
- Badge labels: short "info@" / "sales@" format (not full email addresses)

### Chat notifications for thread updates
- New message on existing thread sends a "thread updated" card (different format from new thread triage card)
- Update card includes: thread subject, who replied, timestamp, first ~100 chars of new message, and a link to the thread
- Notification goes to both the thread's assignee AND the category webhook channel
- No rate limiting on update notifications — volume is low enough for the 3-person team

### Claude's Discretion
- Inbox badge color scheme (pick colors that complement the VIPL plum palette #a83362)
- Exact dedup detection time window (e.g., 1 minute, 5 minutes)
- "Reopened" badge styling and placement
- "Thread updated" Chat card layout within Cards v2 format
- How to handle edge case: email arrives on inbox that was later removed from monitored_inboxes

</decisions>

<specifics>
## Specific Ideas

- Cross-inbox duplicate notification should be lightweight: "Thread [subject] also received on sales@" — not a full triage card
- Reopened threads need to be visually obvious so assignees don't miss them in the thread list
- Thread update notifications should drive people to the dashboard with enough preview to decide urgency

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EmailMessage.thread_id` (DTO) and `Email.gmail_thread_id` (model) — already populated on every email, ready for thread grouping
- `EmailMessage.inbox` — already tracks receiving inbox in the DTO
- `Email.to_inbox` — stored on every Email record
- `save_email_to_db()` uses `update_or_create(message_id=...)` — can be extended with thread lookup
- `chat_notifier.py` — existing Cards v2 implementation with branding, can add new card type for thread updates
- `_sla_urgency_label()` — reusable for thread-level SLA display

### Established Patterns
- Label-after-persist safety: Gmail labeled AFTER DB save succeeds — must maintain this for thread updates
- `SystemConfig` for runtime config — inbox colors could be stored here if needed
- Circuit breaker pattern in pipeline — thread operations should respect it
- Fire-and-forget notifications — Chat/email never block the pipeline

### Integration Points
- `pipeline.process_single_email()` — main entry point, needs thread create/update logic before save
- `pipeline.process_poll_cycle()` — Chat notification loop needs thread-aware notification routing
- `gmail_poller.poll_all()` — polls each inbox separately, so duplicates arrive in separate poll calls
- `assignment.py` — thread-level assignment needs to propagate to the Thread model (Phase 1 delivers this)
- `Email` model — `to_inbox` field already exists, Thread model (Phase 1) will aggregate inboxes

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-pipeline-integration-inbox-clarity*
*Context gathered: 2026-03-15*
