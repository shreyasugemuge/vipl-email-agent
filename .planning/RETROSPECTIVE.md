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

## Cross-Milestone Trends

| Metric | v2.1 |
|--------|------|
| Phases | 7 |
| Plans | 18 |
| Days | 6 |
| Tests | 257 |
| LOC | 16,572 |
| Commits | 140 |
| Gaps found in audit | 11 (all closed) |

---
*Updated: 2026-03-14 after v2.1 milestone*
