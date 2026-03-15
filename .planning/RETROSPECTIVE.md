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

## Milestone: v2.3.5 — Email Threads & Inbox

**Shipped:** 2026-03-15
**Phases:** 4 | **Plans:** 8 | **Sessions:** 1

### What Was Built
- Thread model grouping emails by gmail_thread_id with thread-level assignment, status, and SLA
- Thread-aware pipeline: auto-create/update threads, reopen closed threads, cross-inbox deduplication
- Three-panel conversation UI (sidebar + thread list + detail panel) replacing card-based email list
- Internal notes with @mentions and Chat/email notifications
- Collision detection with "X is viewing this" polling-based presence
- Inbox pill badges and inbox filter for multi-inbox tracking

### What Worked
- discuss-phase workflow captured precise decisions that eliminated ambiguity during planning and execution
- Consolidating 3 planned plans to 2 in Phase 3 (sidebar integral to layout) reduced overhead without losing scope
- All 18 requirements mapped and completed in a single session
- Existing gmail_thread_id field meant Phase 1 was a data migration, not a pipeline rewrite

### What Was Inefficient
- gsd-tools init phase-op matched archived milestone phases instead of current — required manual workarounds
- Phase numbering collision between archived milestones (v2.2 Phase 3) and current milestone (v2.3.5 Phase 3)

### Patterns Established
- Thread model wraps Email model (FK relationship) — don't replace, extend
- "Store both copies, link to one thread" for cross-inbox dedup — simple and auditable
- Compact 2-line cards with SLA-only-when-urgent for dense thread lists
- Polling-based presence (15s heartbeat) sufficient for <5 users, avoids WebSocket infra

### Key Lessons
1. When extending a model hierarchy (Email → Thread), phase 1 should deliver the model + migration, phase 2 should wire the pipeline — clean separation
2. UI phases benefit from discuss-phase more than backend phases — visual decisions (layout proportions, card density, badge placement) can't be inferred from requirements alone

### Cost Observations
- Model mix: 100% opus (quality profile)
- Sessions: 1 (full milestone in single conversation)
- Notable: discuss-phase + plan-phase + execute-phase pipeline efficient — no rework cycles needed

---

## Cross-Milestone Trends

| Metric | v2.1 | v2.2 | v2.3.5 |
|--------|------|------|--------|
| Phases | 7 | 4 | 4 |
| Plans | 18 | 6 | 8 |
| Days | 6 | 1 | 1 |
| Tests | 257 | 349 | ~400+ |
| LOC | 16,572 | 18,763 | ~22,000 |
| Commits | 140 | 45 | 51 |
| Gaps found in audit | 11 (all closed) | 0 | — (skipped) |

### Top Lessons (Verified Across Milestones)

1. discuss-phase for UI/UX phases prevents rework — visual decisions need user input before planning
2. Label-after-persist safety pattern holds across all pipeline extensions (threading, dedup)
3. Fire-and-forget notifications keep the pipeline resilient — never block on external calls
4. Ask the user's mental model before designing config structures — saves redesign cycles

---
*Updated: 2026-03-15 after v2.3.5 milestone*
