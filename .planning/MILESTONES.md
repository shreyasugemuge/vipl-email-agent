# Milestones

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

