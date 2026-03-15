# Roadmap: VIPL Email Agent

## Milestones

- v2.1 VIPL Email Agent v2 -- Phases 1-6 (shipped 2026-03-14) -- [archive](milestones/v2.1-ROADMAP.md)
- v2.2 Polish & Hardening -- Phases 7-10 (shipped 2026-03-14) -- [archive](milestones/v2.2-ROADMAP.md)
- v2.3.6 UI/UX Polish & Bug Fixes -- Phases 11-13 (shipped 2026-03-15) -- [archive](milestones/v2.3.6-ROADMAP.md)
- v2.4.x Dashboard + Threads -- Phase 14 (shipped 2026-03-15)
- **v2.5.0 Intelligence + UX** -- Phases 1-6 (in progress)

## Phases

<details>
<summary>v2.4.x and earlier -- SHIPPED</summary>

- [x] Phases 1-6: v2.1 MVP (shipped 2026-03-14)
- [x] Phases 7-10: v2.2 Polish & Hardening (shipped 2026-03-14)
- [x] Phases 11-13: v2.3.6 UI/UX Polish (shipped 2026-03-15)
- [x] Phase 14: v2.4.x Dashboard UX + Threads (shipped 2026-03-15)

</details>

### v2.5.0 Intelligence + UX

- [ ] **Phase 1: Models + Migrations** - All new models and fields in one migration batch
- [ ] **Phase 2: AI Confidence + Auto-Assign** - Confidence tiers, auto-assignment, and feedback loop
- [x] **Phase 3: Spam Learning + Bug Fixes** - Spam feedback, sender reputation, and pipeline fixes (completed 2026-03-15)
- [ ] **Phase 4: Read/Unread Tracking** - Per-user read state with visual indicators
- [ ] **Phase 5: Editable Attributes + Context Menu** - Inline edit and right-click quick actions
- [ ] **Phase 6: Reports Module** - Analytics dashboard with Chart.js charts

## Phase Details

### Phase 1: Models + Migrations
**Goal**: All new database models and fields exist in one migration batch, ready for feature phases
**Depends on**: Nothing (first phase of v2.5.0)
**Requirements**: INTEL-11
**Success Criteria** (what must be TRUE):
  1. ThreadReadState model exists with user, thread, and read_at fields
  2. SpamFeedback model exists with user, thread, original_verdict, correction, and timestamp
  3. SenderReputation model exists with sender_address, total_count, spam_count, and is_blocked flag
  4. Thread model has category_overridden and priority_overridden boolean fields (default False)
  5. `python manage.py migrate` runs cleanly on fresh SQLite and production PostgreSQL
**Plans:** 1 plan
Plans:
- [ ] 01-01-PLAN.md -- Add v2.5.0 models, fields, migration, and tests

### Phase 2: AI Confidence + Auto-Assign
**Goal**: AI triage includes confidence tiers, high-confidence threads auto-assign, and user feedback improves future triages
**Depends on**: Phase 1
**Requirements**: INTEL-01, INTEL-02, INTEL-03, INTEL-04, INTEL-05, INTEL-06, INTEL-07, INTEL-08
**Success Criteria** (what must be TRUE):
  1. Every triaged thread shows a confidence indicator (HIGH/MEDIUM/LOW) on its card and detail panel
  2. HIGH-confidence threads with a matching AssignmentRule are auto-assigned without manual intervention
  3. Auto-assigned threads display "(auto)" badge and assignee can reject with one click
  4. User can accept or reject an AI suggestion, and the action is recorded in AssignmentFeedback
  5. Recent corrections appear in AI prompt context, influencing subsequent triage decisions
**Plans:** 1/4 plans executed
Plans:
- [ ] 02-01-PLAN.md -- Confidence in AI triage: DTO, schema, pipeline save, template filters
- [ ] 02-02-PLAN.md -- Inline auto-assign in pipeline with threshold config
- [ ] 02-03-PLAN.md -- Accept/reject suggestion UI, feedback recording, confidence dots
- [ ] 02-04-PLAN.md -- Distillation service: correction rules into AI prompt

### Phase 3: Spam Learning + Bug Fixes
**Goal**: Users can correct spam verdicts, sender reputation auto-blocks repeat spammers, and known bugs are fixed
**Depends on**: Phase 1
**Requirements**: SPAM-01, SPAM-02, SPAM-03, SPAM-04, SPAM-05, SPAM-06, FIX-01, FIX-02
**Success Criteria** (what must be TRUE):
  1. User can mark any thread as "Spam" or "Not Spam" from the detail panel
  2. Senders with spam ratio above 0.8 (and 3+ emails) are automatically blocked on future polls
  3. Marking "Not Spam" on a blocked sender auto-whitelists them
  4. Spam badge displays correctly on thread cards (has_spam annotation fix)
  5. Gmail avatar imports correctly on OAuth login, and cross-inbox dedup works for the same email in info@ and sales@
**Plans:** 2/2 plans complete
Plans:
- [ ] 03-01-PLAN.md -- Spam feedback views, pipeline block check, sender reputation, combined settings tab
- [ ] 03-02-PLAN.md -- Bug fixes: force poll, spam badge, avatar/dedup edge cases

### Phase 4: Read/Unread Tracking
**Goal**: Users can see which threads they have and have not read, with visual distinction and manual override
**Depends on**: Phase 1
**Requirements**: READ-01, READ-02, READ-03, READ-04, READ-05
**Success Criteria** (what must be TRUE):
  1. Unread threads appear with bold text and a blue indicator dot; read threads appear normal
  2. Opening a thread detail panel automatically marks it as read for the current user
  3. User can mark a thread as unread from the detail panel
  4. Sidebar "My Inbox" view shows an unread count badge that updates in real time
**Plans:** 1/2 plans executed
Plans:
- [ ] 04-01-PLAN.md -- Backend: read state views, queryset annotation, mark-unread endpoint, assignment reset, tests
- [ ] 04-02-PLAN.md -- Frontend: card unread styling, sidebar badges, mark-unread button, tab title

### Phase 5: Editable Attributes + Context Menu
**Goal**: Users can quickly edit thread metadata and perform common actions via right-click menu
**Depends on**: Phase 2, Phase 4
**Requirements**: INTEL-09, INTEL-10, MENU-01, MENU-02, MENU-03, MENU-04, MENU-05
**Success Criteria** (what must be TRUE):
  1. User can change thread category and priority from inline dropdowns in the detail panel
  2. Right-click on a thread card shows a context menu with Mark Read/Unread, Assign, Claim, Acknowledge, Close, and Mark Spam
  3. Context menu is role-aware (admin sees Assign, members see Claim)
  4. Long-press on mobile triggers the same context menu
  5. Every context menu action is also available via the primary UI (no menu-only actions)
**Plans:** 2 plans
Plans:
- [ ] 05-01-PLAN.md -- Inline edit endpoints, dropdown partials, detail panel integration
- [ ] 05-02-PLAN.md -- Context menu component, JS handler, mobile long-press, role-aware rendering

### Phase 6: Reports Module
**Goal**: Manager can view email volume, response times, SLA compliance, and team workload from a dedicated reports page
**Depends on**: Phase 3, Phase 4
**Requirements**: RPT-01, RPT-02, RPT-03, RPT-04, RPT-05, RPT-06, RPT-07
**Success Criteria** (what must be TRUE):
  1. "Reports" link in sidebar navigates to a dedicated analytics page
  2. Email volume bar chart shows daily or weekly incoming email counts
  3. Response time metrics display average time to acknowledge and close, with trend indicators
  4. SLA compliance percentage and breach count are visible
  5. Team workload bar chart shows emails handled per team member, filterable by date range
**Plans:** 2 plans
Plans:
- [ ] 06-01-PLAN.md -- Reports skeleton: aggregation service, view, template with tabs, date picker, filters, sidebar nav
- [ ] 06-02-PLAN.md -- Chart.js charts for all tabs, tests, visual verification

## Progress

**Execution Order:** 1 -> 2/3/4 (parallel after 1) -> 5 (after 2+4) -> 6 (after 3+4)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Models + Migrations | 0/1 | Planning complete | - |
| 2. AI Confidence + Auto-Assign | 1/4 | In Progress|  |
| 3. Spam Learning + Bug Fixes | 2/2 | Complete   | 2026-03-15 |
| 4. Read/Unread Tracking | 1/2 | In Progress|  |
| 5. Editable Attributes + Context Menu | 0/2 | Planning complete | - |
| 6. Reports Module | 0/2 | Planning complete | - |
