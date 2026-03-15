# Requirements: VIPL Email Agent v2.3.4

**Defined:** 2026-03-15
**Core Value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.

## v2.3.4 Requirements

Requirements for UI/UX polish & bug fixes. Each maps to roadmap phases.

### Bug Fixes

- [ ] **BUG-01**: AI suggestion displays clean name text, not raw XML markup (`<parameter name="name">`)
- [ ] **BUG-02**: Mobile detail panel slides in reliably when tapping email card, with scroll lock and back button
- [ ] **BUG-03**: Mobile filter bar displays as stacked vertical layout with full-width touch-friendly selects
- [ ] **BUG-04**: Activity page filter chips don't truncate ("Priority Bump" fully visible)
- [ ] **BUG-05**: Email count updates accurately when switching between All/Unassigned/My Emails views
- [ ] **BUG-06**: All pages have consistent title pattern "VIPL Triage | {Page Name}"
- [ ] **BUG-07**: Toast notifications position below header on mobile, with touch-friendly close buttons

### Polish

- [ ] **UX-01**: First-login welcome banner shows role-specific guidance, dismissible, one-time per session
- [ ] **UX-02**: Active filter indicators show count badge and clear-all link when filters are applied
- [ ] **UX-03**: Mobile stat cards use scroll-snap for native swipe feel
- [ ] **UX-04**: Arrow key navigation between email cards, Escape closes detail panel
- [ ] **UX-05**: Loading skeleton shows in detail panel while HTMX fetches email content

### QA

- [ ] **QA-01**: All interactive elements tested via Chrome browser automation (clicks, forms, HTMX swaps)

## Future Requirements

None deferred — all scoped items included.

## Out of Scope

| Feature | Reason |
|---------|--------|
| PWA / service worker | 4-5 users, Chat notifications push alerts already |
| Dark mode | Doubles CSS, business hours only usage |
| Client-side filtering JS | Server-side HTMX search already works well |
| Drag-and-drop assignment | Overkill for 3-person team |
| Websocket real-time updates | 4-5 users, 5-min poll, Django Channels complexity |
| Inline reply composer | Out of scope per PROJECT.md |
| Multi-step onboarding wizard | Over-engineering for 4-5 person tool |
| Pull-to-refresh gesture | Marginal value given desktop-primary usage |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 8 | Pending |
| BUG-02 | Phase 8 | Pending |
| BUG-03 | Phase 8 | Pending |
| BUG-04 | Phase 8 | Pending |
| BUG-05 | Phase 8 | Pending |
| BUG-06 | Phase 8 | Pending |
| BUG-07 | Phase 8 | Pending |
| UX-01 | Phase 9 | Pending |
| UX-02 | Phase 9 | Pending |
| UX-03 | Phase 9 | Pending |
| UX-04 | Phase 9 | Pending |
| UX-05 | Phase 9 | Pending |
| QA-01 | Phase 10 | Pending |

**Coverage:**
- v2.3.4 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after roadmap creation*
