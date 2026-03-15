# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

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

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v2.1 | ~5 | 6 | Initial GSD workflow adoption |
| v2.2 | ~3 | 4 | Streamlined with settings/polish focus |
| v2.3.5 | 1 | 4 | Full milestone in single session, discuss-phase for all UI phases |

### Cumulative Quality

| Milestone | Tests | Key Metric |
|-----------|-------|------------|
| v2.1 | 349 | Foundation + pipeline + dashboard |
| v2.2 | 381 | OAuth SSO + branding |
| v2.3.5 | ~400+ | Threading + conversation UI + collaboration |

### Top Lessons (Verified Across Milestones)

1. discuss-phase for UI/UX phases prevents rework — visual decisions need user input before planning
2. Label-after-persist safety pattern holds across all pipeline extensions (threading, dedup)
3. Fire-and-forget notifications keep the pipeline resilient — never block on external calls
