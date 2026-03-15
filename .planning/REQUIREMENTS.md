# Requirements: VIPL Email Agent v2.5.4

**Defined:** 2026-03-15
**Core Value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.

## v2.5.4 Requirements

### Bug Fixes

- [x] **BUG-01**: Welcome message no longer shows twice at login (#15)
- [x] **BUG-02**: Read/unread markers visible on thread cards (#16)
- [x] **BUG-03**: Reopened status tag and flow works end-to-end (#17)
- [x] **BUG-04**: Google avatar syncs on login (#27)
- [x] **BUG-05**: AI Assign button in detail card works (#28)

### Thread Cards & Detail

- [x] **CARD-01**: Thread cards have more height and spacing (#18)
- [x] **CARD-02**: Category/priority dropdowns are elegant inline pills (#19)
- [x] **CARD-03**: Context menu font is clearly visible (#20)
- [x] **CARD-04**: AI draft reply displayed in detail panel (#30)

### Workflow

- [ ] **FLOW-01**: Claim button available for unassigned threads (#22)
- [ ] **FLOW-02**: Undo spam feedback button in UI (#29)

### Pages

- [x] **PAGE-01**: Login page logo has no background (#21)
- [ ] **PAGE-02**: Settings page has better labeling and organization (#24)
- [ ] **PAGE-03**: Activity page redesigned with grouped sections (#25)
- [x] **PAGE-04**: Sidebar shows version instead of "Online" (#26)

### Dev Inspector

- [ ] **DEV-01**: Poll UX — live timer, force poll fix, history improvements (#23)
- [ ] **DEV-02**: Poll history table — human-readable times, interval column, empty vs fetched distinction

## Future Requirements

None — this is a polish milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reply from dashboard | Team replies from Gmail directly |
| Analytics dashboard | Separate feature branch (feature/analytics-dashboard) |
| New AI capabilities | Polish only, no new AI features |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 1 | Complete |
| BUG-02 | Phase 1 | Complete |
| BUG-03 | Phase 1 | Complete |
| BUG-04 | Phase 1 | Complete |
| BUG-05 | Phase 1 | Complete |
| CARD-01 | Phase 2 | Complete |
| CARD-02 | Phase 2 | Complete |
| CARD-03 | Phase 2 | Complete |
| CARD-04 | Phase 2 | Complete |
| FLOW-01 | Phase 3 | Pending |
| FLOW-02 | Phase 3 | Pending |
| PAGE-01 | Phase 4 | Complete |
| PAGE-02 | Phase 4 | Pending |
| PAGE-03 | Phase 4 | Pending |
| PAGE-04 | Phase 4 | Complete |
| DEV-01 | Phase 5 | Pending |
| DEV-02 | Phase 5 | Pending |

**Coverage:**
- v2.5.4 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after roadmap creation*
