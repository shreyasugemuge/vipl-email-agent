# Roadmap: VIPL Email Agent

## Milestones

- **v2.1 VIPL Email Agent v2** — Phases 1-6 (shipped 2026-03-14) — [archive](milestones/v2.1-ROADMAP.md)
- **v2.2 Polish & Hardening** — Phases 1-4 (shipped 2026-03-14) — [archive](milestones/v2.2-ROADMAP.md)
- **v2.3.5 Email Threads & Inbox** — Phases 1-4 (in progress)

## Phases

<details>
<summary>v2.2 (Phases 1-4) — SHIPPED 2026-03-14</summary>

- [x] Phase 1: Google OAuth SSO (1/1 plans) — completed 2026-03-14
- [x] Phase 2: Settings + Spam Whitelist (2/2 plans) — completed 2026-03-14
- [x] Phase 3: VIPL Branding (2/2 plans) — completed 2026-03-14
- [x] Phase 4: Chat Notification Polish (1/1 plan) — completed 2026-03-14

</details>

<details>
<summary>v2.1 (Phases 1-6) — SHIPPED 2026-03-14</summary>

- [x] Phase 1: Foundation (2/2 plans) — completed 2026-03-09
- [x] Phase 2: Email Pipeline (3/3 plans) — completed 2026-03-11
- [x] Phase 3: Dashboard (3/3 plans) — completed 2026-03-11
- [x] Phase 4: Assignment Engine + SLA (3/3 plans) — completed 2026-03-11
- [x] Phase 4.5: Integration Fixes + Tech Debt (2/2 plans) — completed 2026-03-12
- [x] Phase 5: Reporting + Admin + Sheets Mirror (3/3 plans) — completed 2026-03-12
- [x] Phase 6: Migration + Cutover (2/2 plans) — completed 2026-03-14

</details>

### v2.3.5 Email Threads & Inbox (In Progress)

**Milestone Goal:** Transform the email triage experience from individual messages to threaded conversations, matching Gmelius/Hiver-level shared inbox UX.

- [x] **Phase 1: Thread Model + Data Migration** - Thread/conversation model with thread-level assignment, status, and migration of existing emails into threads
- [x] **Phase 2: Pipeline Integration + Inbox Clarity** - Poller creates/updates threads on new email, deduplication across inboxes, multi-inbox tracking
- [x] **Phase 3: Conversation UI** - Three-panel layout replacing card list, thread-based browsing with message history detail panel
- [x] **Phase 4: Collaboration** - Internal notes with @mentions and collision detection for team coordination (completed 2026-03-15)

## Phase Details

### Phase 1: Thread Model + Data Migration
**Goal**: Emails are grouped into threads with thread-level ownership and lifecycle
**Depends on**: Nothing (first phase)
**Requirements**: THRD-01, THRD-02, THRD-03, THRD-05
**Success Criteria** (what must be TRUE):
  1. All existing Email records are grouped into Thread objects by their `gmail_thread_id`
  2. Each thread has its own status (New/Acknowledged/Closed) that is independent of individual message statuses
  3. Assigning a thread sets ownership of all messages within it — there is one assignee per thread
  4. Thread displays a message count and the latest message preview (subject, sender, timestamp)
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Thread model, ActivityLog refactor, migrations, admin
- [x] 01-02-PLAN.md — Thread-level assignment, status, and preview logic

### Phase 2: Pipeline Integration + Inbox Clarity
**Goal**: New emails automatically land in the correct thread, and multi-inbox emails are deduplicated
**Depends on**: Phase 1
**Requirements**: THRD-04, INBOX-01, INBOX-02, INBOX-03
**Success Criteria** (what must be TRUE):
  1. When a new email arrives on an existing thread, the thread bumps to the top of the list and reopens if it was closed
  2. Each email clearly shows which inbox it was received on (info@ vs sales@)
  3. When the same email arrives on both info@ and sales@, it appears as a single thread (not duplicated)
  4. Deduplicated threads display all inboxes they were received on (e.g., "info@ + sales@")
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Pipeline thread creation/update and reopen logic
- [x] 02-02-PLAN.md — Inbox tracking, deduplication, and multi-inbox display

### Phase 3: Conversation UI
**Goal**: Users browse and manage threads in a three-panel layout with full message history
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, INBOX-04
**Success Criteria** (what must be TRUE):
  1. Dashboard shows a three-panel layout: left sidebar (views/filters), center (thread list), right (detail panel)
  2. Center panel shows threads (not individual emails) with assignee, status, priority, SLA, and category inline
  3. Clicking a thread opens a detail panel showing all messages in chronological order
  4. Thread detail panel includes all actions: assign, acknowledge, close, whitelist sender
  5. Left sidebar has quick-access views (Unassigned, Mine, All Open, Closed) and an inbox filter (info@, sales@, all)
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Three-panel layout with sidebar views, inbox filter, and thread list
- [x] 03-02-PLAN.md — Thread detail panel with message history and actions

### Phase 4: Collaboration
**Goal**: Team members can discuss threads internally and see who else is viewing a thread
**Depends on**: Phase 3
**Requirements**: COLLAB-01, COLLAB-02, COLLAB-03, COLLAB-04
**Success Criteria** (what must be TRUE):
  1. User can add an internal note on any thread — notes are never visible to the email sender
  2. Notes support @mentions that trigger a notification to the mentioned team member
  3. Notes appear inline in the thread detail, visually distinct from email messages (different background, "Internal note" label)
  4. When another user has a thread open, a "X is viewing this" indicator appears in the detail panel
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Internal notes model, @mention notifications, inline display
- [ ] 04-02-PLAN.md — Collision detection (polling-based "viewing" indicator)

## Progress

**Execution Order:** 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Thread Model + Data Migration | 2/2 | Complete | 2026-03-15 |
| 2. Pipeline Integration + Inbox Clarity | 2/2 | Complete | 2026-03-15 |
| 3. Conversation UI | 2/2 | Complete | 2026-03-15 |
| 4. Collaboration | 2/2 | Complete   | 2026-03-15 |
