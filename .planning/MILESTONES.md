# Milestones

## v2.6.0 Gatekeeper Role + Irrelevant Emails (Shipped: 2026-03-16)

**Phases completed:** 4 phases, 9 plans
**Stats:** 78 commits, 91 files changed, +13,815 lines, 824 tests
**Timeline:** ~3 hours (2026-03-16)

**Key accomplishments:**
- Triage Lead (gatekeeper) role with 5 permission properties, team page promote/demote, category-scoped visibility
- Centralized permission refactor: replaced 28+ scattered is_admin checks with User model properties
- Assignment enforcement: gatekeepers/admins control routing, members self-claim or reassign with mandatory reason
- Mark irrelevant: close-with-reason for queue hygiene, amber UI (button + modal + context menu + badge), activity audit trail
- Rising-edge unassigned alert system: Chat notification on threshold crossing with cooldown, sidebar badge coloring
- Bulk actions: checkbox selection → floating action bar → bulk assign + bulk mark-irrelevant with 10s undo toast
- AI corrections digest: collapsible card on triage queue showing 7-day correction patterns

**Archives:**
- `milestones/v2.6.0-ROADMAP.md`
- `milestones/v2.6.0-REQUIREMENTS.md`
- `milestones/v2.6.0-MILESTONE-AUDIT.md`

---

## v2.5.0 Intelligence + UX (Shipped: 2026-03-15)

**Phases completed:** 7 phases, 14 plans
**Stats:** 90 commits, 101 files changed, +15,456 lines, 626 tests

**Key accomplishments:**
- AI confidence scoring (HIGH/MEDIUM/LOW) on every triage with visual dots on cards and detail
- Auto-assign pipeline: HIGH confidence + matching AssignmentRule → automatic assignment with "(auto)" badge
- Feedback distillation: user corrections → Haiku-generated rules → injected into AI prompt for learning
- Spam learning: mark spam/not-spam buttons, SenderReputation auto-block (ratio > 0.8), whitelist on unblock
- Per-user read/unread tracking: bold + blue dot indicators, sidebar badges, mark-as-unread, keyboard shortcut (U)
- Right-click context menu on thread cards with role-aware quick actions (mobile long-press support)
- Inline editable category/priority/status with override flags preserved across new emails
- Reports module: 4-tab analytics dashboard (Overview, Volume, Team, SLA) with Chart.js charts and date filtering

**Archives:**
- `milestones/v2.5.0-ROADMAP.md`
- `milestones/v2.5.0-REQUIREMENTS.md`
- `milestones/v2.5.0-MILESTONE-AUDIT.md`

---

## v2.3.6 UI/UX Polish & Bug Fixes (Shipped: 2026-03-15)

**Phases completed:** 3 phases, 6 plans, 14 tasks
**Timeline:** 1 day (2026-03-15)
**Stats:** 8 commits ahead of main, 2 code files changed (+28/-11), 443 tests

**Key accomplishments:**
- AI suggested assignee XML tag cleanup at ingest + data migration for existing records
- Mobile detail panel with history API back-button, scroll lock, swipe-to-dismiss toasts
- Welcome banner with role-specific onboarding (admin vs member), session/permanent dismiss
- Keyboard navigation (Arrow Up/Down between cards, Escape closes detail) with form field guard
- Loading skeleton (animate-pulse) for detail panel HTMX fetches, scoped to target
- Full QA verification: 13/13 requirements PASS, 3 inline bug fixes discovered and fixed

**Archives:**
- `milestones/v2.3.6-ROADMAP.md`
- `milestones/v2.3.6-REQUIREMENTS.md`

---

## v2.2 Polish & Hardening (Shipped: 2026-03-14)

**Phases completed:** 4 phases, 6 plans
**Timeline:** 1 day (2026-03-14)
**Stats:** 45 commits, 82 files changed, +7,672 lines, 349 tests

**Key accomplishments:**
- Google OAuth SSO with @vidarbhainfotech.com domain lock, admin approval, avatar + welcome toast
- Type-aware settings page with SpamWhitelist model and pipeline-level whitelist integration
- Whitelist Sender button in email detail + management tab (HTMX add/delete/OOB swap)
- VIPL brand identity: logo assets, plum palette (#a83362), favicon, page titles, copyright footer
- Google Chat card branding: VIPL header icon + "Sent by VIPL Email Triage" footer on all 5 card types
- Inline Open buttons and consistent `_sla_urgency_label()` across all Chat notification cards

**Archives:**
- `milestones/v2.2-ROADMAP.md`
- `milestones/v2.2-MILESTONE-AUDIT.md`

---

## v2.1 VIPL Email Agent (Shipped: 2026-03-14)

**Phases completed:** 7 phases, 18 plans
**Timeline:** 6 days (2026-03-09 → 2026-03-14)
**Stats:** 140 commits, 204 files changed, 16,572 LOC Python, 257 tests

**Key accomplishments:**
- Django 4.2 LTS application with PostgreSQL, Docker Compose deployment on existing VM
- Gmail polling pipeline with Claude AI two-tier triage (Haiku default, Sonnet for CRITICAL)
- Dashboard with email card list, HTMX filters, slide-out detail panel, activity log
- Assignment engine with category-based auto-assign rules, AI fallback suggestions, SLA tracking
- Per-category Google Chat webhook routing with quiet hours
- EOD reports (email + Chat), SystemConfig admin, Google Sheets read-only mirror
- Live at triage.vidarbhainfotech.com with release-triggered CI/CD

**Deferred:**
- Artifact Registry cleanup (gcloud auth needed)
- Go-live Chat announcement

**Archives:**
- `milestones/v2.1-ROADMAP.md`
- `milestones/v2.1-REQUIREMENTS.md`
- `milestones/v2.1-MILESTONE-AUDIT.md`

---

