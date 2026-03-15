# Roadmap: VIPL Email Agent

## Milestones

- M1 v2.1 VIPL Email Agent v2 -- Phases 1-6 (shipped 2026-03-14) -- [archive](milestones/v2.1-ROADMAP.md)
- M2 v2.2 Polish & Hardening -- Phases 7-10 (shipped 2026-03-14) -- [archive](milestones/v2.2-ROADMAP.md)
- M3 v2.3.6 UI/UX Polish & Bug Fixes -- Phases 11-13 (shipped 2026-03-15) -- [archive](milestones/v2.3.6-ROADMAP.md)
- M4 v2.4.x Dashboard + Threads -- Phase 14 (shipped 2026-03-15)
- M5 v2.5.0 Intelligence + UX -- Phases 1-7 (shipped 2026-03-15) -- [archive](milestones/v2.5.0-ROADMAP.md)
- **M6 v2.5.4 UI/UX Polish & Bug Fixes -- Phases 1-5 (in progress)**

## Phases

<details>
<summary>M1–M5 (v2.5.0 and earlier) -- SHIPPED</summary>

- [x] M1 Phases 1-6: v2.1 MVP (shipped 2026-03-14)
- [x] M2 Phases 7-10: v2.2 Polish & Hardening (shipped 2026-03-14)
- [x] M3 Phases 11-13: v2.3.6 UI/UX Polish (shipped 2026-03-15)
- [x] M4 Phase 14: v2.4.x Dashboard UX + Threads (shipped 2026-03-15)
- [x] M5 Phases 1-7: v2.5.0 Intelligence + UX (shipped 2026-03-15)

Old phase dirs archived to `.planning/phases/_archived-m5/`

</details>

### M6 v2.5.4 UI/UX Polish & Bug Fixes

```
Execution Order:

  P1 (Bug Fixes)
      │
      ├──→ P2 (Thread Card & Detail UX)  ─┐
      ├──→ P3 (Workflow Actions)          ─┼──→ Done
      ├──→ P4 (Page Polish)              ─┘
      │
      └──→ P5 (Dev Inspector) ← independent, can run anytime
```

**Wave 1 (parallel):** P1 + P5 (no dependencies between them)
**Wave 2 (parallel after P1):** P2 + P3 + P4

- [x] **Phase 1: Bug Fixes** — Fix 5 known bugs: welcome double-show, read/unread markers, reopened status, avatar sync, AI assign (completed 2026-03-15)
- [x] **Phase 2: Thread Card & Detail UX** — Polish cards and detail: spacing, pill dropdowns, context menu font, AI draft display (completed 2026-03-15)
- [ ] **Phase 3: Workflow Actions** — Claim button for unassigned threads, undo spam feedback *(after P1)*
- [ ] **Phase 4: Page Polish** — Login logo, settings reorganization, activity redesign, sidebar version *(after P1)*
- [ ] **Phase 5: Dev Inspector** — Poll timer, force poll fix, history table improvements *(independent)*

## Phase Details

### Phase 1: Bug Fixes (M6-P1)
**Goal**: All known bugs from v2.5.0 are resolved — users no longer encounter broken behaviors
**Depends on**: Nothing (first phase, all others wait on this)
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04, BUG-05
**Plans:** 2/2 plans complete
**Success Criteria** (what must be TRUE):
  1. Welcome banner shows once per session on login, never duplicates
  2. Thread cards display read/unread state with visible bold text and blue dot indicators
  3. User can reopen a closed thread and the "Reopened" status tag appears in card and detail
  4. Google avatar updates on each OAuth login and displays correctly in sidebar and team page
  5. AI Assign button in thread detail triggers assignment and updates the card without errors

Plans:
- [ ] 01-01-PLAN.md — Backend fixes: unread state creation, REOPENED status, avatar sync
- [x] 01-02-PLAN.md — Frontend fixes: welcome banner dedup, AI Assign OOB card swap

### Phase 2: Thread Card & Detail UX (M6-P2)
**Goal**: Thread cards and detail panel feel polished and information-dense without clutter
**Depends on**: Phase 1
**Parallel with**: Phase 3, Phase 4
**Requirements**: CARD-01, CARD-02, CARD-03, CARD-04
**Plans:** 2 plans
**Success Criteria** (what must be TRUE):
  1. Thread cards have comfortable spacing with more vertical height for content
  2. Category and priority dropdowns render as compact inline pills (not full-width selects)
  3. Right-click context menu text is clearly readable (appropriate font size and contrast)
  4. AI draft reply is visible in the thread detail panel when available

Plans:
- [ ] M6-P2-01-PLAN.md — Card spacing redesign + context menu readability
- [x] M6-P2-02-PLAN.md — Pill-style dropdowns + AI draft copy button

### Phase 3: Workflow Actions (M6-P3)
**Goal**: Users can self-serve on common actions — claim threads and undo spam mistakes
**Depends on**: Phase 1
**Parallel with**: Phase 2, Phase 4
**Requirements**: FLOW-01, FLOW-02
**Plans:** 1 plan
**Success Criteria** (what must be TRUE):
  1. Any team member can click "Claim" on an unassigned thread to assign it to themselves
  2. User who marked a thread as spam can undo that action from the same UI location

Plans:
- [ ] 03-01-PLAN.md — Fix Claim button bugs, add toast, verify spam toggle

### Phase 4: Page Polish (M6-P4)
**Goal**: Login, settings, activity, and sidebar pages feel cohesive and well-organized
**Depends on**: Phase 1
**Parallel with**: Phase 2, Phase 3
**Requirements**: PAGE-01, PAGE-02, PAGE-03, PAGE-04
**Plans:** 1/2 plans executed
**Success Criteria** (what must be TRUE):
  1. Login page shows the VIPL logo without a colored background rectangle
  2. Settings page has clear section headers, grouped tabs, and descriptive labels
  3. Activity page displays events in grouped sections (by date or by thread) instead of flat list
  4. Sidebar footer shows current version number (e.g., "v2.5.4") instead of "Online"

Plans:
- [ ] 04-01-PLAN.md — Version/env badge in sidebar + login page retro-modern retheme
- [ ] 04-02-PLAN.md — Settings grouped tabs + activity thread-grouped redesign

### Phase 5: Dev Inspector (M6-P5)
**Goal**: Dev inspector provides accurate real-time poll status and readable history
**Depends on**: Nothing (independent — can run anytime, even parallel with P1)
**Requirements**: DEV-01, DEV-02
**Plans:** 1 plan
**Success Criteria** (what must be TRUE):
  1. Poll countdown timer shows live seconds until next poll and resets after each cycle
  2. Force poll button triggers a poll cycle immediately and shows result feedback
  3. Poll history table shows human-readable timestamps, interval between polls, and distinguishes empty polls from polls that fetched emails

Plans:
- [ ] 05-01-PLAN.md — Force poll inline results + poll history table enhancements

## Progress

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 (M6-P1) | 2/2 | Complete   | 2026-03-15 | - |
| 2 (M6-P2) | Thread Card & Detail UX | 2/2 | Complete | 2026-03-15 |
| 3 (M6-P3) | Workflow Actions | 0/1 | Planning complete | - |
| 4 (M6-P4) | 1/2 | In Progress|  | - |
| 5 (M6-P5) | Dev Inspector | 0/1 | Planning complete | - |
