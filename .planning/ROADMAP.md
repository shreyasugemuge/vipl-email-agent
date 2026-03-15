# Roadmap: VIPL Email Agent

## Milestones

- v2.1 VIPL Email Agent v2 -- Phases 1-6 (shipped 2026-03-14) -- [archive](milestones/v2.1-ROADMAP.md)
- v2.2 Polish & Hardening -- Phases 7-10 (shipped 2026-03-14) -- [archive](milestones/v2.2-ROADMAP.md)
- v2.3.6 UI/UX Polish & Bug Fixes -- Phases 11-13 (shipped 2026-03-15) -- [archive](milestones/v2.3.6-ROADMAP.md)
- v2.4.x Dashboard + Threads -- Phase 14 (shipped 2026-03-15)
- v2.5.0 Intelligence + UX -- Phases 1-7 (shipped 2026-03-15) -- [archive](milestones/v2.5.0-ROADMAP.md)
- v2.5.4 UI/UX Polish & Bug Fixes -- Phases 8-12 (in progress)

## Phases

<details>
<summary>v2.5.0 and earlier -- SHIPPED</summary>

- [x] Phases 1-6: v2.1 MVP (shipped 2026-03-14)
- [x] Phases 7-10: v2.2 Polish & Hardening (shipped 2026-03-14)
- [x] Phases 11-13: v2.3.6 UI/UX Polish (shipped 2026-03-15)
- [x] Phase 14: v2.4.x Dashboard UX + Threads (shipped 2026-03-15)
- [x] Phases 1-7: v2.5.0 Intelligence + UX (shipped 2026-03-15)

</details>

### v2.5.4 UI/UX Polish & Bug Fixes

- [ ] **Phase 8: Bug Fixes** - Fix 5 known bugs: welcome double-show, read/unread markers, reopened status, avatar sync, AI assign
- [ ] **Phase 9: Thread Card & Detail UX** - Polish thread cards and detail panel: spacing, pill dropdowns, context menu font, AI draft display
- [ ] **Phase 10: Workflow Actions** - Add claim button for unassigned threads and undo spam feedback
- [ ] **Phase 11: Page Polish** - Login logo, settings reorganization, activity redesign, sidebar version label
- [ ] **Phase 12: Dev Inspector** - Poll timer, force poll fix, history table improvements

## Phase Details

### Phase 8: Bug Fixes
**Goal**: All known bugs from v2.5.0 are resolved -- users no longer encounter broken behaviors
**Depends on**: Nothing (first phase of milestone)
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04, BUG-05
**Success Criteria** (what must be TRUE):
  1. Welcome banner shows once per session on login, never duplicates
  2. Thread cards display read/unread state with visible bold text and blue dot indicators
  3. User can reopen a closed thread and the "Reopened" status tag appears in card and detail
  4. Google avatar updates on each OAuth login and displays correctly in sidebar and team page
  5. AI Assign button in thread detail triggers assignment and updates the card without errors
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

### Phase 9: Thread Card & Detail UX
**Goal**: Thread cards and detail panel feel polished and information-dense without clutter
**Depends on**: Phase 8
**Requirements**: CARD-01, CARD-02, CARD-03, CARD-04
**Success Criteria** (what must be TRUE):
  1. Thread cards have comfortable spacing with more vertical height for content
  2. Category and priority dropdowns render as compact inline pills (not full-width selects)
  3. Right-click context menu text is clearly readable (appropriate font size and contrast)
  4. AI draft reply is visible in the thread detail panel when available
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

### Phase 10: Workflow Actions
**Goal**: Users can self-serve on common actions -- claim threads and undo spam mistakes
**Depends on**: Phase 8
**Requirements**: FLOW-01, FLOW-02
**Success Criteria** (what must be TRUE):
  1. Any team member can click "Claim" on an unassigned thread to assign it to themselves
  2. User who marked a thread as spam can undo that action from the same UI location
**Plans**: TBD

Plans:
- [ ] 10-01: TBD

### Phase 11: Page Polish
**Goal**: Login, settings, activity, and sidebar pages feel cohesive and well-organized
**Depends on**: Phase 8
**Requirements**: PAGE-01, PAGE-02, PAGE-03, PAGE-04
**Success Criteria** (what must be TRUE):
  1. Login page shows the VIPL logo without a colored background rectangle
  2. Settings page has clear section headers, grouped tabs, and descriptive labels
  3. Activity page displays events in grouped sections (by date or by thread) instead of flat list
  4. Sidebar footer shows current version number (e.g., "v2.5.4") instead of "Online"
**Plans**: TBD

Plans:
- [ ] 11-01: TBD
- [ ] 11-02: TBD

### Phase 12: Dev Inspector
**Goal**: Dev inspector provides accurate real-time poll status and readable history
**Depends on**: Phase 8
**Requirements**: DEV-01, DEV-02
**Success Criteria** (what must be TRUE):
  1. Poll countdown timer shows live seconds until next poll and resets after each cycle
  2. Force poll button triggers a poll cycle immediately and shows result feedback
  3. Poll history table shows human-readable timestamps, interval between polls, and distinguishes empty polls from polls that fetched emails
**Plans**: TBD

Plans:
- [ ] 12-01: TBD

## Progress

**Execution Order:** 8 -> 9 -> 10 -> 11 -> 12 (Phases 9, 10, 11 can run in parallel after 8)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 8. Bug Fixes | 0/TBD | Not started | - |
| 9. Thread Card & Detail UX | 0/TBD | Not started | - |
| 10. Workflow Actions | 0/TBD | Not started | - |
| 11. Page Polish | 0/TBD | Not started | - |
| 12. Dev Inspector | 0/TBD | Not started | - |
