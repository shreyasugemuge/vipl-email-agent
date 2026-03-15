# Retrospective

## Milestone: v2.1 — VIPL Email Agent v2

**Shipped:** 2026-03-14
**Phases:** 7 | **Plans:** 18

### What Was Built
- Django 4.2 application replacing Cloud Run + Google Sheets v1 system
- Gmail polling pipeline with Claude AI two-tier triage (Haiku/Sonnet)
- Dashboard with card list, HTMX filters, slide-out detail panel
- Assignment engine with category rules, AI fallback, SLA tracking
- Per-category Google Chat webhooks, EOD reports, Sheets sync mirror
- Docker Compose deployment with release-triggered CI/CD

### What Worked
- GSD phase-based workflow: 18 plans across 7 phases in 6 days
- Research → plan → execute → verify cycle caught integration gaps early (Phase 4.5 gap closure)
- HTMX + Tailwind CDN = zero build step, fast iteration on UI
- Service layer pattern kept views thin and business logic testable
- Fire-and-forget notifications prevented UX-blocking failures
- Milestone audit before shipping caught 4 post-deploy issues

### What Was Inefficient
- PROJECT.md not updated during development (still showed pre-build state at v2.1 completion)
- Django version mismatch discovered late: started with 5.2, had to downgrade to 4.2 for PG 12.3
- Deploy script needed 5 unplanned fixes during first production deploy (ALLOWED_HOSTS, Nginx SSL, root URL, etc.)
- Per-category webhooks designed 3 times: per-user → per-team-model → per-category (should have asked user's mental model first)

### Patterns Established
- SystemConfig key-value store for runtime configuration (replaces env vars for mutable config)
- Label-after-persist safety pattern (Gmail labels only after PostgreSQL commit)
- Seed migrations for default config values (dev-safe defaults)
- Per-category webhook routing via `chat_webhook_{category}` SystemConfig keys
- Release-triggered deploys (not tag push) for intentional deployments
- `{% if obj.field %}` guards in templates for nullable ForeignKeys

### Key Lessons
- Always verify the production database version before choosing Django version
- First deploy to a new environment will have unplanned fixes — budget time for it
- Ask the user's mental model before designing configuration structures
- Post-deploy QA pass is essential — template errors only surface with real data

### Cost Observations
- Model mix: ~80% Sonnet, ~20% Opus (GSD workflow used Sonnet for planning/execution)
- Claude API cost for email triage: ~$0.001/email (Haiku), ~$0.01/email (Sonnet escalation)
- Total dev time: ~6 days (mostly automated via GSD agents)

---

## Milestone: v2.2 — Polish & Hardening

**Shipped:** 2026-03-14
**Phases:** 4 | **Plans:** 6

### What Was Built
- Google OAuth SSO with domain lock, admin approval flow, avatar display, welcome toast
- Type-aware settings page with SpamWhitelist model and pipeline integration
- Whitelist Sender button in email detail + management tab with HTMX add/delete
- VIPL brand identity: logo assets, plum palette, favicon, page titles, copyright footer
- Google Chat card branding: header icon + footer across all 5 card types
- Inline Open buttons and consistent urgency labels in Chat notifications

### What Worked
- All 4 phases completed in a single day (research through verification)
- TDD discipline: 92 new tests across 4 phases, zero regressions
- Cross-phase integration was clean: phases touched separate domains (auth, settings, templates, services)
- Human checkpoint for Chat card validation caught the real-world quiet hours issue
- Audit found zero critical gaps (22/22 requirements, 6/6 E2E flows)

### What Was Inefficient
- ROADMAP.md phase checkboxes not auto-updated by execute-phase (some showed `[ ]` despite being complete)
- Nyquist validation files created but left in draft — never filled in during execution
- SUMMARY.md one_liner field was empty for all plans (summary-extract returned None)

### Patterns Established
- `_sla_urgency_label()` as module-level helper for cross-method formatting
- `decoratedText.button` for inline action buttons in Cards v2 (not buttonList — union field)
- pk passed through data dicts (not ORM import) to keep chat_notifier Django-free
- Signal-based welcome toast with `_welcome_shown` session flag for deduplication
- Settings-based allauth APP config (no SocialApp DB records)

### Key Lessons
- Always test Chat notifications with quiet hours disabled — or you won't see them
- HTMX partials inherit `@theme` from parent page — no need for inline styles
- Cards v2 `decoratedText` has a union field: `button` OR `endIcon`, never both

### Cost Observations
- Model mix: ~70% Sonnet, ~20% Opus, ~10% Haiku (executor agents on Sonnet, orchestrator on Opus)
- Single-day milestone: 4 phases in ~7 hours wall clock
- All 45 commits in one feature branch (no merge conflicts)

---

## Milestone: v2.3.4 — UI/UX Polish & Bug Fixes

**Shipped:** 2026-03-15
**Phases:** 3 | **Plans:** 6

### What Was Built
- AI suggested assignee XML tag cleanup at ingest + data migration for existing records
- Mobile detail panel with history API back-button, scroll lock, swipe-to-dismiss toasts
- Welcome banner with role-specific onboarding (admin vs member), auto-fade after 8s
- Active filter indicators with count badge and amber "Clear all" link
- Scroll-snap stat cards for mobile swiping
- Keyboard navigation (Arrow Up/Down, Escape) with form field guard
- Loading skeleton (animate-pulse) for detail panel HTMX fetches
- Full QA verification: 13/13 requirements PASS, 3 inline bugs found and fixed

### What Worked
- All 3 phases completed in a single day (executed on worktree branch fix/ui-ux)
- TDD discipline continued: 94 new tests across phases 1+2, 443 total
- QA phase caught 3 real bugs that would have shipped: urgent filter mismatch, JS null guards, desktop Escape behavior
- OOB swap pattern for email count updates — clean HTMX pattern, no page reload
- Research phase for QA created a thorough test matrix covering all 38 HTMX endpoints

### What Was Inefficient
- Phase directory split: Phase 1 in `.planning/phases/`, Phases 2+3 in `.planning/milestones/v2.3.4-phases/` — confused the CLI tools
- Plan 03-02 (general sweep) couldn't use Chrome MCP for live browser testing, fell back to code-level audit — still valuable but didn't match the stated success criteria
- Verifier flagged methodology gaps (no screenshots, code audit vs browser automation) — cosmetic, accepted by user

### Patterns Established
- `_clean_xml_tags`: reusable regex cleaner for Claude API response artifacts
- OOB swap: append hx-swap-oob elements to HTMX partial responses for out-of-band UI updates
- pushState/popstate pattern for mobile panel open/close with browser back button
- Touch swipe gesture pattern with threshold and visual feedback for dismissable elements
- sessionStorage/localStorage pattern for dismissible UI elements (session vs permanent)
- Form field guard: check activeElement.tagName before handling keyboard shortcuts
- Target-scoped htmx event handling: check e.detail.target.id before acting

### Key Lessons
- Always test virtual filter mappings end-to-end (URGENT = CRITICAL + HIGH, not just CRITICAL)
- Null guards needed for DOM elements that HTMX may swap out mid-interaction
- Code-level QA audits are surprisingly thorough for template/HTMX verification — covers patterns that browser clicks might miss

### Cost Observations
- Model mix: ~60% Sonnet (executors), ~30% Opus (orchestrator), ~10% Haiku
- Single-day milestone: 3 phases in ~2 hours wall clock
- Minimal code changes: only 2 source files changed (+28/-11 lines), all features via templates

---

## Cross-Milestone Trends

| Metric | v2.1 | v2.2 | v2.3.4 |
|--------|------|------|--------|
| Phases | 7 | 4 | 3 |
| Plans | 18 | 6 | 6 |
| Days | 6 | 1 | 1 |
| Tests | 257 | 349 | 443 |
| Commits | 140 | 45 | 8 |
| Gaps found in audit | 11 (all closed) | 0 | 2 (accepted) |

---
*Updated: 2026-03-15 after v2.3.4 milestone*
