# Requirements: VIPL Email Agent v2.7.1

**Defined:** 2026-03-17
**Core Value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.

## v2.7.1 Requirements

### Bug Fixes

- [ ] **BUG-01**: Treat `irrelevant` as closed everywhere — exclude from open views/counts, include in Closed tab, fix sidebar/stat/unread counts (GH #48)
- [ ] **BUG-02**: Deactivating teammate unassigns their open threads, shows pending count warning, cascades cleanup of AssignmentRules and ThreadViewers (GH #47)
- [ ] **BUG-03**: Close/reopen status changes OOB-swap sidebar counts + stat cards, visually distinguish closed thread cards (GH #44)
- [ ] **BUG-04**: Reassign/assign OOB-swaps sidebar counts + stat cards + detail panel assignee without page refresh (GH #46)
- [ ] **BUG-05**: Fix inspector poll countdown stuck at "due now" — timer reset and interval calculation (GH #45)
- [x] **BUG-06**: Activity page click-through — non-HTMX redirect to thread list with auto-open (GH #43)

### Documentation

- [ ] **DOCS-01**: Create user manual on GitHub Wiki covering setup, daily workflows, roles, and features
- [ ] **DOCS-02**: Add "Help / User Manual" link in app sidebar pointing to the GitHub Wiki

## Out of Scope

| Feature | Reason |
|---------|--------|
| New features | This is a QA/bug-fix milestone only |
| Database migrations | All fixes are view/template/JS level |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUG-01 | Phase 1 | Pending |
| BUG-02 | Phase 1 | Pending |
| BUG-03 | Phase 2 | Pending |
| BUG-04 | Phase 2 | Pending |
| BUG-05 | Phase 2 | Pending |
| BUG-06 | Phase 2 | Complete |
| DOCS-01 | Phase 3 | Pending |
| DOCS-02 | Phase 3 | Pending |

**Coverage:**
- v2.7.1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-17*
