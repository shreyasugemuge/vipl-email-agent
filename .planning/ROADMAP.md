# Roadmap: VIPL Email Agent

## Milestones

- v2.1 VIPL Email Agent v2 -- Phases 1-6 (shipped 2026-03-14) -- [archive](milestones/v2.1-ROADMAP.md)
- v2.2 Polish & Hardening -- Phases 7-10 (shipped 2026-03-14) -- [archive](milestones/v2.2-ROADMAP.md)
- v2.3.6 UI/UX Polish & Bug Fixes -- Phases 11-13 (shipped 2026-03-15) -- [archive](milestones/v2.3.6-ROADMAP.md)
- v2.4.x Dashboard + Threads -- Phase 14 (shipped 2026-03-15)
- v2.5.0 Intelligence + UX -- Phases 1-7 (shipped 2026-03-15) -- [archive](milestones/v2.5.0-ROADMAP.md)

## Phases

<details>
<summary>v2.5.0 and earlier -- SHIPPED</summary>

- [x] Phases 1-6: v2.1 MVP (shipped 2026-03-14)
- [x] Phases 7-10: v2.2 Polish & Hardening (shipped 2026-03-14)
- [x] Phases 11-13: v2.3.6 UI/UX Polish (shipped 2026-03-15)
- [x] Phase 14: v2.4.x Dashboard UX + Threads (shipped 2026-03-15)
- [x] Phases 1-7: v2.5.0 Intelligence + UX (shipped 2026-03-15)

</details>

### v2.6.0 Gatekeeper Role + Irrelevant Emails

- [x] **Phase 1: Role + Permission Foundation** - Gatekeeper role on User model, centralized permission helpers replacing 25+ scattered is_admin checks (completed 2026-03-15)
- [x] **Phase 2: Assignment Enforcement** - Gatekeepers/admins control assignment; members self-claim or reassign with mandatory reason (completed 2026-03-15)
- [ ] **Phase 3: Mark Irrelevant** - Close-with-reason action for queue hygiene, excluded from unassigned counts
- [ ] **Phase 4: Alerts + Bulk Actions** - Unassigned count alerts via Chat, bulk assign, bulk mark-irrelevant, AI feedback summary

## Phase Details

### Phase 1: Role + Permission Foundation
**Goal**: Gatekeeper role exists in the system and all permission checks use centralized helpers instead of scattered inline checks
**Depends on**: Nothing (first phase)
**Requirements**: ROLE-01, ROLE-02, ROLE-06
**Success Criteria** (what must be TRUE):
  1. Admin can promote a user to gatekeeper from the team page and demote them back
  2. Gatekeeper sees threads filtered to their assigned categories in the triage queue
  3. Every permission check in the codebase uses `can_assign()` or `is_admin_only()` helpers -- zero inline `is_admin` checks remain
  4. Gatekeeper role appears correctly in welcome banner, sidebar, user badges, and context menu
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md -- Role model + permission properties + team page promote/demote + dev login + tests
- [ ] 01-02-PLAN.md -- Replace 28+ is_admin checks + category-scoped filtering + template updates + UI elements

### Phase 2: Assignment Enforcement
**Goal**: Assignment permissions are enforced so gatekeepers and admins control thread routing while members retain limited self-service
**Depends on**: Phase 1
**Requirements**: ROLE-03, ROLE-04, ROLE-05
**Success Criteria** (what must be TRUE):
  1. Gatekeeper and admin can assign any thread to any active user
  2. Member cannot see or use the "assign to others" action -- UI hides it and server rejects the request
  3. Member can self-claim an unassigned thread in their category without needing a reason
  4. Member reassigning a thread they own must provide a mandatory reason, which appears in the activity log
**Plans**: 2 plans

Plans:
- [ ] 02-01-PLAN.md — Backend: model migration, reassign_thread service, view endpoint, URL, 14 permission tests
- [ ] 02-02-PLAN.md — Frontend: role-conditional detail panel UI, context menu, visual checkpoint

### Phase 3: Mark Irrelevant
**Goal**: Gatekeepers and admins can dismiss irrelevant threads from the queue with an auditable reason
**Depends on**: Phase 1 (can run parallel with Phase 2)
**Requirements**: TRIAGE-01, TRIAGE-02, TRIAGE-03, TRIAGE-06
**Success Criteria** (what must be TRUE):
  1. Gatekeeper/admin can mark a thread as irrelevant with a mandatory free-text reason from the detail panel
  2. Gatekeeper/admin can mark a thread as irrelevant via the right-click context menu
  3. Irrelevant threads disappear from the triage queue and do not count toward unassigned totals
  4. The irrelevant reason and who marked it appear in the thread detail activity timeline
  5. Members cannot see or use the mark-irrelevant action
**Plans**: 2 plans

Plans:
- [ ] 03-01-PLAN.md — Backend: model migration, views, URLs, queryset filtering, 11 tests
- [ ] 03-02-PLAN.md — Frontend: detail panel modal, context menu, badge, stat card, activity timeline, visual checkpoint

### Phase 4: Alerts + Bulk Actions
**Goal**: Proactive unassigned count monitoring and batch operations for efficient queue management
**Depends on**: Phase 2 + Phase 3 (both must complete)
**Requirements**: ALERT-01, ALERT-02, ALERT-03, ALERT-04, TRIAGE-04, TRIAGE-05
**Success Criteria** (what must be TRUE):
  1. Dashboard shows a visible unassigned count badge to gatekeepers and admins (excluding irrelevant threads)
  2. Google Chat alert fires when unassigned count exceeds the configurable threshold in SystemConfig
  3. Chat alerts respect a configurable cooldown period -- no repeated alerts within the cooldown window
  4. Gatekeeper sees a recent AI corrections digest (feedback summary) on the triage queue page
  5. Gatekeeper/admin can select multiple threads via checkboxes and bulk-assign them to a user or bulk mark-irrelevant with a single reason
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md — Alert backend: rising-edge Chat alerts with cooldown, sidebar badge coloring, Settings config
- [ ] 04-02-PLAN.md — Bulk actions: checkbox selection UI, floating action bar, bulk assign/mark-irrelevant endpoints, undo toast
- [ ] 04-03-PLAN.md — AI corrections digest: collapsible card on triage queue with correction counts and top patterns

## Progress

**Execution Order:** 1 -> (2 ∥ 3) -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Role + Permission Foundation | 2/2 | Complete   | 2026-03-15 |
| 2. Assignment Enforcement | 2/2 | Complete   | 2026-03-15 |
| 3. Mark Irrelevant | 1/2 | In Progress|  |
| 4. Alerts + Bulk Actions | 1/3 | In Progress|  |
