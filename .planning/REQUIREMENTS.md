# Requirements: VIPL Email Agent v2

**Defined:** 2026-03-09
**Core Value:** Every email that lands in a shared inbox gets assigned to a person, tracked to response, and never falls through the cracks.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Email Processing

- [x] **PROC-01**: System polls configured Gmail inboxes for new emails every 5 minutes
- [x] **PROC-02**: System triages emails with Claude AI (category, priority, summary, draft reply)
- [x] **PROC-03**: System pre-filters spam via regex patterns before AI processing (zero cost)
- [x] **PROC-04**: System extracts PDF attachment text for triage context
- [x] **PROC-05**: System detects email language (Hindi, Marathi, English) and writes summary in English
- [x] **PROC-06**: System logs failed triages to dead letter queue and retries up to 3 times

### Assignment

- [x] **ASGN-01**: Manager can manually assign an email to a team member from the dashboard
- [x] **ASGN-02**: Manager can reassign an email to a different team member
- [x] **ASGN-03**: System auto-assigns emails based on category-to-person mapping rules
- [x] **ASGN-04**: System uses AI fallback for emails that don't match any assignment rule
- [x] **ASGN-05**: Assignment triggers notification to assignee via Google Chat + email

### Status & SLA

- [x] **SLA-01**: Each email has a status: New, Acknowledged, Replied, Closed
- [x] **SLA-02**: System calculates SLA deadline per email based on priority and category
- [x] **SLA-03**: System detects SLA breaches and posts summary alerts (3x daily)
- [x] **SLA-04**: SLA breach alerts manager (Shreyas) via Chat + email

### Dashboard

- [x] **DASH-01**: Dashboard shows all emails in a table with columns: date, from, subject, assignee, priority, status, SLA remaining
- [x] **DASH-02**: Dashboard supports filtering by status, assignee, priority, inbox
- [x] **DASH-03**: Dashboard supports sorting by any column
- [x] **DASH-04**: Dashboard shows unassigned queue as default manager view
- [x] **DASH-05**: Dashboard has activity log showing who did what (assignments, status changes)
- [x] **DASH-06**: Dashboard is desktop-first, usable on mobile

### Auth

- [x] **AUTH-01**: Dashboard requires login (simple password auth for v1)
- [x] **AUTH-02**: Admin role (manager) can assign, reassign, configure
- [x] **AUTH-03**: User role (team member) sees their assignments and can acknowledge

### Infrastructure

- [x] **INFR-01**: PostgreSQL is the source of truth for all email and assignment data
- [x] **INFR-02**: System deployed via Docker Compose on existing VM
- [x] **INFR-03**: CI/CD via GitHub Actions triggered by version tags
- [ ] **INFR-04**: Google Sheets receives read-only sync (simplified: date, from, subject, assignee, status)
- [x] **INFR-05**: Daily EOD report sent via email + Chat card with stats from database
- [x] **INFR-06**: Health endpoint reports system status (uptime, failure count, last poll)
- [x] **INFR-07**: Admin can configure monitored inboxes without code changes
- [x] **INFR-08**: Admin can configure polling frequency, quiet hours, and business hours
- [x] **INFR-09**: Admin can configure SLA deadlines per category/priority
- [x] **INFR-10**: Admin can configure assignment rules (category-to-person mapping)
- [x] **INFR-11**: Admin can toggle feature flags (AI triage, Chat notifications, EOD email) without redeploy
- [x] **INFR-12**: Admin can manage team members (add/remove, set roles)

### Migration + Cutover

- [ ] **CUTV-01**: All historical email data migrated from production Sheet to PostgreSQL with zero data loss
- [ ] **CUTV-02**: Both inboxes cut over from v1 to v2 with v1 fully stopped
- [ ] **CUTV-03**: Cloud Run service decommissioned (no cost, no running instances)
- [ ] **CUTV-04**: CI/CD pipeline targets VM only — no Cloud Run references remain

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Auth

- **AUTH-10**: Google OAuth SSO restricted to @vidarbhainfotech.com
- **AUTH-11**: Session management with proper token expiry

### Advanced Assignment

- **ASGN-10**: AI feedback loop — corrections logged and used to improve future assignments
- **ASGN-11**: Gmail thread monitoring to auto-detect when assignee replies
- **ASGN-12**: Auto-update status to "Replied" when reply detected in Gmail thread

### Advanced SLA

- **SLA-10**: Two-tier SLA — separate acknowledgement deadline + response deadline
- **SLA-11**: Escalation chain with auto-reassignment on repeated breach

### Analytics

- **ANLY-01**: Response time analytics with charts and trends
- **ANLY-02**: Workload view showing open items per team member
- **ANLY-03**: Volume trends by day, hour, category

### Notifications

- **NOTF-01**: WhatsApp/SMS for CRITICAL priority escalations
- **NOTF-02**: Configurable notification preferences per user

### Admin

- **ADMN-01**: Assignment rule configuration from dashboard (moved to v1 as INFR-10)
- **ADMN-02**: Inbox management from dashboard (moved to v1 as INFR-07)

### Tender Intelligence

- **TNDR-01**: MahaTender email parsing (8 notification types)
- **TNDR-02**: Tender document scraping via Playwright
- **TNDR-03**: CAPTCHA handling (human-in-the-loop or automated)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Reply from dashboard | Team replies from Gmail directly — building compose UI is high effort, low value |
| Round-robin assignment | Team is 3 people — category rules are more accurate than mechanical rotation |
| CSAT surveys | Internal tool, not customer support platform |
| Canned response templates | Gmail already has Templates feature |
| Real-time collaboration | 3 users — collision is rare, "assigned to X" is sufficient |
| Complex workflow states | 4 statuses max — no enterprise help desk bloat |
| Multi-tenant / team hierarchy | Single company, single team |
| Mobile native app | Responsive web + notifications via Chat/WhatsApp is sufficient |
| Email conversation view in dashboard | Not rebuilding Gmail — show summary + "Open in Gmail" link |
| Ticket numbering system | Nobody references ticket numbers in conversation — use email subject as identifier |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROC-01 | Phase 2 | Complete |
| PROC-02 | Phase 2 | Complete |
| PROC-03 | Phase 2 | Complete (02-01) |
| PROC-04 | Phase 2 | Complete (02-01) |
| PROC-05 | Phase 2 | Complete |
| PROC-06 | Phase 2 | Complete (02-03) |
| ASGN-01 | Phase 3 | Complete (03-02) |
| ASGN-02 | Phase 3 | Complete (03-02) |
| ASGN-03 | Phase 4 | Complete |
| ASGN-04 | Phase 4 | Complete |
| ASGN-05 | Phase 3 | Complete (03-02) |
| SLA-01 | Phase 3 | Complete (03-02) |
| SLA-02 | Phase 4 | Complete |
| SLA-03 | Phase 4 | Complete |
| SLA-04 | Phase 4 | Complete |
| DASH-01 | Phase 3 | Complete (03-01) |
| DASH-02 | Phase 3 | Complete (03-01) |
| DASH-03 | Phase 3 | Complete (03-01) |
| DASH-04 | Phase 3 | Complete (03-01) |
| DASH-05 | Phase 3 | Complete |
| DASH-06 | Phase 3 | Complete |
| AUTH-01 | Phase 1 | Complete (01-01) |
| AUTH-02 | Phase 1 | Complete (01-01) |
| AUTH-03 | Phase 1 | Complete (01-01) |
| INFR-01 | Phase 1 | Complete (01-01) |
| INFR-02 | Phase 1 | Complete |
| INFR-03 | Phase 1 | Complete |
| INFR-04 | Phase 5 | Pending |
| INFR-05 | Phase 5 | Complete |
| INFR-06 | Phase 1 | Complete (01-01) |
| INFR-07 | Phase 5 | Complete (05-01) |
| INFR-08 | Phase 2 | Complete (02-01) |
| INFR-09 | Phase 4 | Complete |
| INFR-10 | Phase 4 | Complete |
| INFR-11 | Phase 2 | Complete (02-01) |
| INFR-12 | Phase 1 | Complete (01-01) |
| CUTV-01 | Phase 6 | Pending |
| CUTV-02 | Phase 6 | Pending |
| CUTV-03 | Phase 6 | Pending |
| CUTV-04 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-11 after plan 03-02 execution (assignment workflow + detail panel)*
