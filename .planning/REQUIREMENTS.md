# Requirements: VIPL Email Agent v2.5.0

**Defined:** 2026-03-15
**Core Value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.

## v2.5.0 Requirements

Requirements for v2.5.0 Intelligence + UX release. Each maps to roadmap phases.

### AI Intelligence

- [x] **INTEL-01**: AI triage returns confidence tier (HIGH/MEDIUM/LOW) alongside category, priority, and summary
- [x] **INTEL-02**: Confidence tier is displayed on thread cards and detail panels as a visual indicator
- [x] **INTEL-03**: Threads with HIGH confidence are auto-assigned when a matching AssignmentRule exists
- [x] **INTEL-04**: Auto-assign threshold is configurable via SystemConfig (default: HIGH only)
- [x] **INTEL-05**: Auto-assigned threads show "(auto)" badge and can be rejected by the assignee
- [x] **INTEL-06**: User can accept or reject AI assignment suggestion with one click
- [x] **INTEL-07**: Assignment feedback (accept/reject/reassign/auto-assign) is recorded in AssignmentFeedback model
- [x] **INTEL-08**: Recent correction history is injected into AI prompt to improve future triages
- [x] **INTEL-09**: User can inline-edit thread category from detail panel (dropdown with existing categories)
- [x] **INTEL-10**: User can inline-edit thread priority from detail panel (dropdown with CRITICAL/HIGH/MEDIUM/LOW)
- [ ] **INTEL-11**: Category/priority overrides are preserved when new emails arrive in the thread (override flags)

### Spam

- [x] **SPAM-01**: User can mark a thread as "Spam" or "Not Spam" from detail panel
- [x] **SPAM-02**: Spam/not-spam actions create SpamFeedback records with user, original verdict, and correction
- [x] **SPAM-03**: Sender reputation is tracked (total emails, spam count, spam ratio per sender address)
- [x] **SPAM-04**: Senders with spam ratio > 0.8 and >= 3 total emails are auto-blocked in future polls
- [x] **SPAM-05**: Marking "Not Spam" on a blocked sender auto-creates a SpamWhitelist entry
- [x] **SPAM-06**: Spam badge displays correctly on thread cards (fix has_spam annotation bug)

### Read/Unread

- [x] **READ-01**: Per-user read state is tracked for each thread (ThreadReadState model)
- [x] **READ-02**: Opening a thread detail panel marks it as read for the current user
- [x] **READ-03**: Unread threads display with bold text and blue indicator dot (visual distinction)
- [x] **READ-04**: User can mark a thread as unread from the detail panel or context menu
- [x] **READ-05**: Sidebar shows unread count badge next to "My Inbox" view

### Context Menu

- [x] **MENU-01**: Right-click on a thread/email card shows a context menu with quick actions
- [x] **MENU-02**: Context menu includes: Mark Read/Unread, Assign to, Claim, Acknowledge, Close, Mark Spam
- [x] **MENU-03**: Menu actions are role-aware (admin sees Assign, members see Claim if eligible)
- [x] **MENU-04**: Long-press on mobile triggers the same context menu
- [x] **MENU-05**: Every context menu action is also accessible via the primary UI (no menu-only actions)

### Reports

- [x] **RPT-01**: New "Reports" page accessible from sidebar navigation
- [x] **RPT-02**: Email volume chart showing daily/weekly incoming emails (bar chart)
- [x] **RPT-03**: Response time metrics (avg time to acknowledge, avg time to close) with trends
- [x] **RPT-04**: SLA compliance rate displayed as percentage with breach count
- [x] **RPT-05**: Team workload chart showing emails handled per team member (bar chart)
- [x] **RPT-06**: Date range picker to filter all report data
- [x] **RPT-07**: Charts rendered with Chart.js 4.x via CDN (no build step)

### Bug Fixes

- [x] **FIX-01**: Gmail profile picture imports correctly on OAuth login (avatar_url field)
- [x] **FIX-02**: Cross-inbox email deduplication handles same email arriving in info@ and sales@

## Future Requirements

Deferred beyond v2.5.0.

### Advanced Reporting
- **RPT-F01**: CSV export for any report
- **RPT-F02**: Scheduled email reports (daily/weekly digest)
- **RPT-F03**: Category breakdown analytics

### Advanced Intelligence
- **INTEL-F01**: AI confidence calibration dashboard (actual vs predicted accuracy)
- **INTEL-F02**: Custom category management (add/rename/disable categories)

## Out of Scope

| Feature | Reason |
|---------|--------|
| ML-based spam classifier | Volume too low (50-100 emails/day), sender reputation is more reliable |
| Float confidence scores | Claude's self-reported confidence is uncalibrated; discrete tiers are more honest |
| Custom report builder | Enterprise feature, 4 users don't need ad-hoc reports |
| Reply from dashboard | Team replies from Gmail directly |
| Activity page redesign | Captured as todo but not critical for v2.5.0 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTEL-01 | Phase 2 | Complete |
| INTEL-02 | Phase 2 | Complete |
| INTEL-03 | Phase 2 | Complete |
| INTEL-04 | Phase 2 | Complete |
| INTEL-05 | Phase 2 | Complete |
| INTEL-06 | Phase 2 | Complete |
| INTEL-07 | Phase 2 | Complete |
| INTEL-08 | Phase 2 | Complete |
| INTEL-09 | Phase 5 | Complete |
| INTEL-10 | Phase 5 | Complete |
| INTEL-11 | Phase 7 | Pending |
| SPAM-01 | Phase 3 | Complete |
| SPAM-02 | Phase 3 | Complete |
| SPAM-03 | Phase 3 | Complete |
| SPAM-04 | Phase 3 | Complete |
| SPAM-05 | Phase 3 | Complete |
| SPAM-06 | Phase 3 | Complete |
| READ-01 | Phase 4 | Complete |
| READ-02 | Phase 4 | Complete |
| READ-03 | Phase 4 | Complete |
| READ-04 | Phase 4 | Complete |
| READ-05 | Phase 4 | Complete |
| MENU-01 | Phase 5 | Complete |
| MENU-02 | Phase 5 | Complete |
| MENU-03 | Phase 5 | Complete |
| MENU-04 | Phase 5 | Complete |
| MENU-05 | Phase 5 | Complete |
| RPT-01 | Phase 6 | Complete |
| RPT-02 | Phase 6 | Complete |
| RPT-03 | Phase 6 | Complete |
| RPT-04 | Phase 6 | Complete |
| RPT-05 | Phase 6 | Complete |
| RPT-06 | Phase 6 | Complete |
| RPT-07 | Phase 6 | Complete |
| FIX-01 | Phase 3 | Complete |
| FIX-02 | Phase 3 | Complete |

**Coverage:**
- v2.5.0 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0

---
*Requirements defined: 2026-03-15*
*Last updated: 2026-03-15 -- traceability populated by roadmapper*
