# Roadmap: VIPL Email Agent

## Milestones

- **v2.1 VIPL Email Agent v2** — Phases 1-6 (shipped 2026-03-14) — [archive](milestones/v2.1-ROADMAP.md)
- **v2.2 Polish & Hardening** — Phases 1-4 (shipped 2026-03-14) — [archive](milestones/v2.2-ROADMAP.md)
- **v2.3.4 UI/UX Polish & Bug Fixes** — Phases 1-3 (in progress)

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

### v2.3.4 UI/UX Polish & Bug Fixes

- [x] **Phase 1: Data & Bug Fixes** - Fix AI XML rendering, mobile layout bugs, count accuracy, title consistency, toast positioning (completed 2026-03-15)
- [ ] **Phase 2: Polish & UX** - Welcome banner, filter indicators, scroll snap, keyboard nav, loading skeleton
- [ ] **Phase 3: QA & Verification** - Chrome browser automation testing of all interactions

## Phase Details

### Phase 1: Data & Bug Fixes
**Goal**: Users see clean, accurate, consistent information across all pages and devices
**Depends on**: Nothing (first phase of v2.3.4)
**Requirements**: BUG-01, BUG-02, BUG-03, BUG-04, BUG-05, BUG-06, BUG-07
**Success Criteria** (what must be TRUE):
  1. AI suggestion text on email cards displays clean readable names, not XML tags like `<parameter name="name">`
  2. Tapping an email card on mobile opens the detail panel as a full-screen slide-in with a back button to dismiss
  3. Mobile filter bar displays as a stacked vertical layout where each select is full-width and easy to tap
  4. Activity page filter chips are fully visible ("Priority Bump" not truncated) on all screen sizes
  5. Email count label accurately reflects the current view and updates when switching between All/Unassigned/My Emails
  6. Every page title follows the pattern "VIPL Triage | {Page Name}"
  7. Toast notifications appear below the header on mobile with touch-friendly close buttons
**Plans**: 2 plans
Plans:
- [ ] 01-01-PLAN.md — AI XML cleanup + data migration, email count OOB update, page title consistency
- [ ] 01-02-PLAN.md — Mobile detail panel + history API, filter stacking, activity chips, toast positioning + swipe

### Phase 2: Polish & UX
**Goal**: Dashboard feels polished with guided onboarding, visible filter state, and responsive interactions
**Depends on**: Phase 1
**Requirements**: UX-01, UX-02, UX-03, UX-04, UX-05
**Success Criteria** (what must be TRUE):
  1. First-time users see a welcome banner with role-specific guidance that can be dismissed and does not reappear in the same session
  2. When filters are active, a count badge and "clear all" link are visible above the email list
  3. Stat cards on mobile scroll horizontally with snap points so each card lands cleanly in view
  4. User can navigate between email cards with arrow keys and close the detail panel with Escape
  5. Detail panel shows a loading skeleton (pulsing placeholder) while HTMX fetches email content
**Plans**: 2 plans
Plans:
- [ ] 02-01-PLAN.md — Welcome banner, filter indicators, scroll-snap stat cards
- [ ] 02-02-PLAN.md — Keyboard navigation, loading skeleton

### Phase 3: QA & Verification
**Goal**: All interactive elements verified working through automated browser testing
**Depends on**: Phase 2
**Requirements**: QA-01
**Success Criteria** (what must be TRUE):
  1. Chrome browser automation script exercises all clickable elements, form submissions, and HTMX swaps without errors
  2. Any regressions or remaining issues discovered during automation are documented and fixed
**Plans**: TBD

## Progress

**Execution Order:** Phase 1 → Phase 2 → Phase 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data & Bug Fixes | 2/2 | Complete   | 2026-03-15 |
| 2. Polish & UX | 0/2 | Planned | - |
| 3. QA & Verification | 0/? | Not started | - |
