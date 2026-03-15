# Requirements: VIPL Email Agent v2.6.0

**Defined:** 2026-03-15
**Core Value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.

## v2.6.0 Requirements

### Role & Permissions

- [ ] **ROLE-01**: Admin can promote/demote user to gatekeeper role from team page
- [ ] **ROLE-02**: Gatekeeper sees all threads in their assigned categories (category-scoped visibility)
- [ ] **ROLE-03**: Only gatekeeper and admin can assign threads to other users
- [ ] **ROLE-04**: Members can self-claim unassigned threads in their category
- [ ] **ROLE-05**: Members can reassign threads only with a mandatory reason (logged in ActivityLog)
- [ ] **ROLE-06**: Permission checks centralized into `can_assign`/`is_admin_only` helpers replacing 25+ scattered `is_admin` checks

### Triage Actions

- [ ] **TRIAGE-01**: Gatekeeper/admin can mark a thread as irrelevant with mandatory free-text reason
- [ ] **TRIAGE-02**: Irrelevant threads are closed immediately and excluded from unassigned count
- [ ] **TRIAGE-03**: Mark-irrelevant available via button in detail panel and right-click context menu
- [ ] **TRIAGE-04**: Gatekeeper/admin can select multiple threads via checkboxes and bulk-assign to a user
- [ ] **TRIAGE-05**: Gatekeeper/admin can bulk mark-irrelevant with a single reason for all selected
- [ ] **TRIAGE-06**: Irrelevant reason stored in ActivityLog and visible in thread detail activity timeline

### Alerts & Monitoring

- [ ] **ALERT-01**: Dashboard badge shows unassigned thread count, visible to gatekeeper and admin
- [ ] **ALERT-02**: Google Chat alert fires when unassigned count exceeds configurable threshold (SystemConfig)
- [ ] **ALERT-03**: Chat alerts have cooldown period (configurable) to prevent alert storms
- [ ] **ALERT-04**: Gatekeeper sees AI feedback summary (recent corrections digest) on triage queue

## Future Requirements

None deferred — all scoped features included in this milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Separate gatekeeper dashboard | Same UI with role-conditional elements (research: Freshdesk/Zendesk pattern) |
| Approval workflow for assignments | Over-engineered for 4-person team |
| Irrelevant reason taxonomy/picklist | Free-text feeds AI distillation better at this scale |
| Gatekeeper-only thread visibility | Members need context on full queue to understand priorities |
| Reassignment notification to original assignee | Low priority, existing Chat notifications partially cover |
| Round-robin auto-assignment | Already out of scope — category rules more accurate |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROLE-01 | — | Pending |
| ROLE-02 | — | Pending |
| ROLE-03 | — | Pending |
| ROLE-04 | — | Pending |
| ROLE-05 | — | Pending |
| ROLE-06 | — | Pending |
| TRIAGE-01 | — | Pending |
| TRIAGE-02 | — | Pending |
| TRIAGE-03 | — | Pending |
| TRIAGE-04 | — | Pending |
| TRIAGE-05 | — | Pending |
| TRIAGE-06 | — | Pending |
| ALERT-01 | — | Pending |
| ALERT-02 | — | Pending |
| ALERT-03 | — | Pending |
| ALERT-04 | — | Pending |

**Coverage:**
- v2.6.0 requirements: 16 total
- Mapped to phases: 0
- Unmapped: 16 ⚠️

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 after initial definition*
