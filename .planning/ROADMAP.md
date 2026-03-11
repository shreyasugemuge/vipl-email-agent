# Roadmap: VIPL Email Agent v2

## Overview

Rebuild the VIPL email triage system from a Cloud Run + Google Sheets monitoring tool into a Django-based inbox management application with PostgreSQL, assignment workflow, SLA tracking, and a dashboard. Deployed on the existing VM via Docker Compose. Five phases: lay the foundation (Django project, DB, auth, deployment), port the proven v1 email pipeline, build the dashboard for visibility and manual assignment, add automated assignment and SLA enforcement, then finish with reporting, admin config, and the Sheets sync mirror.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Django project, PostgreSQL schema, auth, Docker Compose deployment, health endpoint
- [x] **Phase 2: Email Pipeline** - Port v1 agent modules to Django with ORM, background scheduler, Chat notifications
- [x] **Phase 3: Dashboard** - Email card view, manual assignment, status tracking, filtering, activity log
- [x] **Phase 4: Assignment Engine + SLA** - Auto-assignment rules, AI fallback, SLA deadlines, breach alerts, escalation (completed 2026-03-11)
- [ ] **Phase 5: Reporting + Admin + Sheets Mirror** - EOD reports, inbox/config management UI, Google Sheets read-only sync
- [ ] **Phase 6: Migration + Cutover** - Production data migration, v1-to-v2 inbox rollover, Cloud Run decommission, CI/CD overhaul

## Phase Details

### Phase 1: Foundation
**Goal**: A running Django application deployed on the VM with PostgreSQL, user authentication, and team management -- the skeleton everything else builds on
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, INFR-01, INFR-02, INFR-03, INFR-06, INFR-12
**Success Criteria** (what must be TRUE):
  1. User can log in to the dashboard with a username and password (simple auth, not OAuth)
  2. Admin user can add/remove team members and set their roles (admin vs team member) via Django admin
  3. Application is running on the VM via Docker Compose, accessible at the configured subdomain
  4. Health endpoint returns system status (uptime, version) and is reachable
  5. CI/CD pipeline deploys a new version to the VM when a version tag is pushed
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md -- Django project skeleton, PostgreSQL models, custom User with roles, auth views, health endpoint, test infrastructure
- [x] 01-02-PLAN.md -- Dockerfile, Docker Compose, Nginx reverse proxy, CI/CD pipeline (GitHub Actions SSH deploy)

### Phase 2: Email Pipeline
**Goal**: Emails flow from Gmail into PostgreSQL -- polled, triaged by AI, spam-filtered, with dead letter retry and Chat notifications -- reaching functional parity with v1
**Depends on**: Phase 1
**Requirements**: PROC-01, PROC-02, PROC-03, PROC-04, PROC-05, PROC-06, INFR-08, INFR-11
**Success Criteria** (what must be TRUE):
  1. New emails from monitored inboxes appear in PostgreSQL within 5 minutes of arrival
  2. Each email has an AI-generated category, priority, summary, and draft reply stored in the database
  3. Spam emails are filtered out before hitting the AI (zero cost for junk)
  4. Failed triages appear in the dead letter queue and are retried automatically
  5. Admin can toggle feature flags (AI triage on/off, Chat notifications on/off) without redeploying
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md -- Email model migration, SystemConfig model, DTOs, spam filter, PDF extractor, state manager, dependencies
- [x] 02-02-PLAN.md -- GmailPoller + AIProcessor service ports, pipeline orchestrator (poll-filter-triage-save-label)
- [x] 02-03-PLAN.md -- ChatNotifier, APScheduler management command, health endpoint update, Docker Compose scheduler service

### Phase 3: Dashboard
**Goal**: Manager can see every email, assign it to a team member, and track status -- the core workflow that v1 lacks
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, SLA-01, ASGN-01, ASGN-02, ASGN-05
**Success Criteria** (what must be TRUE):
  1. Manager sees a table of all emails with date, from, subject, assignee, priority, status, and SLA remaining
  2. Manager can assign an unassigned email to a team member with one click, and that person gets notified (Chat + email)
  3. Manager can reassign an email to a different person, and the new assignee gets notified
  4. Manager can filter the table by status, assignee, priority, and inbox -- and sort by any column
  5. Activity log shows who assigned/reassigned/changed status on each email
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md -- Base layout, email card list with HTMX filters/sorting/pagination, ActivityLog model, unassigned queue
- [x] 03-02-PLAN.md -- Assignment service, status changes, detail panel, Chat notifications
- [x] 03-03-PLAN.md -- Activity log page, mobile-responsive layout, visual verification

### Phase 4: Assignment Engine + SLA
**Goal**: System auto-assigns emails and enforces SLA deadlines -- the manager only handles exceptions instead of every email
**Depends on**: Phase 3
**Requirements**: ASGN-03, ASGN-04, SLA-02, SLA-03, SLA-04, INFR-09, INFR-10
**Success Criteria** (what must be TRUE):
  1. New emails matching a category rule are auto-assigned to the configured team member without manager intervention
  2. Emails that don't match any rule get an AI-suggested assignee that the manager can confirm or override
  3. Each email shows its SLA deadline based on priority and category, with a visible countdown
  4. SLA breach summary posts to Chat and emails the manager 3x daily (9 AM, 1 PM, 5 PM)
  5. Admin can configure assignment rules and SLA deadlines per category/priority from the admin interface
**Plans**: 3 plans

Plans:
- [ ] 04-01-PLAN.md -- New models (AssignmentRule, SLAConfig, CategoryVisibility), SLA calculator with business hours, auto-assign batch job, claim service, pipeline SLA integration
- [ ] 04-02-PLAN.md -- SLA countdown display on cards/detail, claim/AI-suggestion endpoints, admin settings page (rules, visibility, SLA config with tabs)
- [ ] 04-03-PLAN.md -- Breach detection with auto-escalation, Chat breach summary (3x daily), scheduler jobs (auto-assign 3min, SLA summary 9/13/17), visual verification

### Phase 5: Reporting + Admin + Sheets Mirror
**Goal**: Daily reporting from real database, admin self-service for inbox and config management, and Sheets mirror for legacy access
**Depends on**: Phase 4
**Requirements**: INFR-04, INFR-05, INFR-07
**Success Criteria** (what must be TRUE):
  1. Daily EOD report (email + Chat) includes stats pulled from PostgreSQL (volume, response times, open items)
  2. Admin can add or remove monitored inboxes from the dashboard without touching code
  3. Google Sheet receives a read-only sync of emails (date, from, subject, assignee, status) for quick lookups
**Plans**: TBD

Plans:
- [ ] 05-01: EOD report from database, inbox management UI, Sheets sync mirror

### Phase 6: Migration + Cutover
**Goal**: Migrate production data from Sheets to PostgreSQL, cut inboxes over from v1 to v2, decommission Cloud Run, and finalize CI/CD for VM-only deployment
**Depends on**: Phase 5
**Requirements**: CUTV-01, CUTV-02, CUTV-03, CUTV-04
**Success Criteria** (what must be TRUE):
  1. All historical email data from production Google Sheet is migrated to PostgreSQL with zero data loss
  2. Both inboxes (info@, sales@) are being processed by v2, with v1 fully stopped
  3. Cloud Run service is decommissioned (no cost, no running instances)
  4. CI/CD pipeline (deploy.yml) targets VM only -- no Cloud Run references remain
  5. Rollback plan tested: can revert to v1 within 15 minutes if critical issues found
**Plans**: TBD

Plans:
- [ ] 06-01: Data migration script, v1/v2 cutover plan, Cloud Run decommission, CI/CD overhaul

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-03-09 |
| 2. Email Pipeline | 3/3 | Complete | 2026-03-11 |
| 3. Dashboard | 3/3 | Complete | 2026-03-11 |
| 4. Assignment Engine + SLA | 3/3 | Complete   | 2026-03-11 |
| 5. Reporting + Admin + Sheets Mirror | 0/1 | Not started | - |
| 6. Migration + Cutover | 0/1 | Not started | - |
