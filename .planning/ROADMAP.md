# Roadmap: VIPL Email Agent

## Milestones

- v2.1 VIPL Email Agent v2 -- Phases 1-6 (shipped 2026-03-14) -- [archive](milestones/v2.1-ROADMAP.md)
- v2.2 Polish & Hardening -- Phases 7-10 (shipped 2026-03-14) -- [archive](milestones/v2.2-ROADMAP.md)
- v2.3.6 UI/UX Polish & Bug Fixes -- Phases 11-13 (shipped 2026-03-15) -- [archive](milestones/v2.3.6-ROADMAP.md)
- v2.4.x Dashboard + Threads -- Phase 14 (shipped 2026-03-15)
- v2.5.0 Intelligence + UX -- Phases 1-7 (shipped 2026-03-15) -- [archive](milestones/v2.5.0-ROADMAP.md)
- v2.7.0 Gatekeeper Role + Irrelevant Emails -- Phases 1-4 (shipped 2026-03-16) -- [archive](milestones/v2.7.0-ROADMAP.md)
- **v2.7.1 QA + Bug Fixes -- Phases 1-3 (active)**

## Phases

<details>
<summary>v2.7.0 and earlier -- SHIPPED</summary>

- [x] Phases 1-6: v2.1 MVP (shipped 2026-03-14)
- [x] Phases 7-10: v2.2 Polish & Hardening (shipped 2026-03-14)
- [x] Phases 11-13: v2.3.6 UI/UX Polish (shipped 2026-03-15)
- [x] Phase 14: v2.4.x Dashboard UX + Threads (shipped 2026-03-15)
- [x] Phases 1-7: v2.5.0 Intelligence + UX (shipped 2026-03-15)
- [x] Phases 1-4: v2.7.0 Gatekeeper Role + Irrelevant Emails (shipped 2026-03-16)

</details>

### v2.7.1 QA + Bug Fixes

#### Phase 1: Backend Fixes

**Goal:** Fix irrelevant thread status handling and deactivate-teammate cascade logic.

**Requirements:** BUG-01, BUG-02

**Success Criteria:**
1. Irrelevant threads excluded from all open views, included in Closed tab and closed count
2. Deactivating a teammate unassigns all their open threads and shows pending count before confirmation
3. Deactivation cascades: AssignmentRules removed, ThreadViewers cleared
4. Activity log entries created for each unassignment

#### Phase 2: HTMX/UI Fixes

**Goal:** Fix stale UI after status changes, reassignment, and poll countdown.

**Requirements:** BUG-03, BUG-04, BUG-05, BUG-06

**Success Criteria:**
1. Closing/reopening a thread OOB-swaps sidebar counts and stat cards
2. Closed thread cards have visually muted styling
3. Reassigning a thread OOB-swaps sidebar counts, stat cards, and detail panel assignee
4. Poll countdown in dev inspector counts down correctly and resets after poll
5. Activity page thread links navigate to thread list with detail auto-open (done)

#### Phase 3: Documentation

**Goal:** Create user manual and link it from the application.

**Requirements:** DOCS-01, DOCS-02

**Success Criteria:**
1. GitHub Wiki has a user manual covering: getting started, daily workflows, roles (admin/gatekeeper/member), all features
2. App sidebar has a "Help" link that opens the Wiki user manual
3. Wiki is accessible to all team members
