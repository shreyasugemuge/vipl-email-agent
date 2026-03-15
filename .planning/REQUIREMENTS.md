# Requirements: VIPL Email Agent v2.3.5 — Email Threads & Inbox

**Defined:** 2026-03-15
**Core Value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.

## v2.3.5 Requirements

### Threading

- [x] **THRD-01**: Emails with the same `gmail_thread_id` are grouped into a single conversation/thread
- [x] **THRD-02**: Thread has its own status (New/Acknowledged/Closed) independent of individual messages
- [x] **THRD-03**: Thread has a single assignee — assigning the thread assigns ownership of all messages in it
- [x] **THRD-04**: New incoming email on an existing thread updates the thread (bumps to top, may reopen)
- [x] **THRD-05**: Thread displays message count and latest message preview in the conversation list

### Conversation UI

- [x] **UI-01**: Three-panel layout: left sidebar (views/filters), center (conversation list), right (detail panel)
- [x] **UI-02**: Conversation list shows threads (not individual messages) with inline metadata: assignee, status, priority, SLA, category
- [x] **UI-03**: Detail panel shows full message history in chronological order within a thread
- [x] **UI-04**: Thread detail panel shows all existing actions: assign, acknowledge, close, whitelist sender
- [x] **UI-05**: Left sidebar has quick-access views: Unassigned, Mine, All Open, Closed

### Collaboration

- [x] **COLLAB-01**: User can add internal notes on a thread (visible only to team, never to customer)
- [x] **COLLAB-02**: Notes support @mentions that notify the mentioned team member
- [x] **COLLAB-03**: Notes appear inline in the thread detail, visually distinct from email messages
- [ ] **COLLAB-04**: Collision detection shows "X is viewing this thread" when another user has it open

### Inbox Clarity

- [x] **INBOX-01**: Each email clearly shows which inbox it was received on (info@ vs sales@)
- [x] **INBOX-02**: When the same email arrives on multiple tracked inboxes, it is deduplicated into a single thread
- [x] **INBOX-03**: Deduplicated threads show all inboxes they were received on (e.g., "info@ + sales@")
- [x] **INBOX-04**: Inbox filter in sidebar allows filtering conversations by receiving inbox

## Future Requirements

### Productivity

- **PROD-01**: Response templates — canned replies for repetitive emails
- **PROD-02**: Batch operations — select multiple threads, assign/close in bulk
- **PROD-03**: Snooze/remind later — temporarily hide a thread, resurface at set time
- **PROD-04**: Keyboard shortcuts — j/k navigate, a assign, e close, n note

### Intelligence

- **INTEL-01**: Contact history sidebar — see all threads from same sender
- **INTEL-02**: Reply detection — auto-update thread status when assignee replies in Gmail

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reply from dashboard | Team replies from Gmail directly, compose UI is high effort low value |
| Kanban board view | Overkill for 3-person team |
| Analytics dashboards | Defer to future milestone |
| Shared drafts | Low value when team replies from Gmail |
| Real-time WebSocket updates | Polling sufficient for 3-5 users |
| Round-robin assignment | Category rules more accurate for small team |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| THRD-01 | Phase 1 | Complete |
| THRD-02 | Phase 1 | Complete |
| THRD-03 | Phase 1 | Complete |
| THRD-04 | Phase 2 | Complete |
| THRD-05 | Phase 1 | Complete |
| UI-01 | Phase 3 | Complete |
| UI-02 | Phase 3 | Complete |
| UI-03 | Phase 3 | Complete |
| UI-04 | Phase 3 | Complete |
| UI-05 | Phase 3 | Complete |
| COLLAB-01 | Phase 4 | Complete |
| COLLAB-02 | Phase 4 | Complete |
| COLLAB-03 | Phase 4 | Complete |
| COLLAB-04 | Phase 4 | Pending |
| INBOX-01 | Phase 2 | Complete |
| INBOX-02 | Phase 2 | Complete |
| INBOX-03 | Phase 2 | Complete |
| INBOX-04 | Phase 3 | Complete |

**Coverage:**
- v2.3.5 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after 01-01 execution*
