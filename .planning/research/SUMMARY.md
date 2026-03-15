# Project Research Summary

**Project:** VIPL Email Agent v2.6.0 — Gatekeeper Role + Irrelevant Emails
**Domain:** RBAC expansion + queue management for Django shared inbox triage system
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

v2.6.0 adds a third role (Gatekeeper) to a 4-5 person email triage system that already has Admin and Member. The Gatekeeper is a dispatcher/supervisor who can assign threads and dismiss irrelevant ones, but cannot manage users or system settings. Every feature required for this milestone is implementable using the existing stack with zero new dependencies — no new Python packages, no new JS libraries, no new Django apps. The entire feature set maps directly onto existing primitives: `User.Role` TextChoices, `Thread.Status`, `ActivityLog`, `SystemConfig`, and the APScheduler heartbeat job.

The recommended approach is a strict four-phase build ordered by dependency: (1) role + permission helpers, (2) assignment permission enforcement, (3) mark-irrelevant action, (4) unassigned count alerts and bulk actions. This ordering is non-negotiable — phases 2-4 all require the gatekeeper role to exist first, and phase 4 benefits from phase 3 excluding irrelevant threads from the unassigned count. The architecture analysis catalogued every one of the 25+ scattered `is_admin` checks in `views.py` and classified each into either "gatekeeper can do this" or "admin-only" — this audit is the backbone of the implementation.

The primary risk is the scattered permission pattern. The codebase has no centralized permission system; every view implements `is_admin = user.is_staff or user.role == User.Role.ADMIN` inline. Miss one location and you either lock the gatekeeper out of a feature or grant them unintended admin access. Prevention is a single complete pass replacing all 25+ checks with two helpers: `can_assign()` (admin or gatekeeper) and `is_admin_only()` (admin only). The alert storm risk on unassigned count notifications is secondary but real: a naive implementation fires on every scheduler heartbeat. The solution is a 30-minute cooldown stored in SystemConfig.

## Key Findings

### Recommended Stack

**Zero new dependencies.** Every v2.6.0 feature is implementable with the existing stack. The codebase already has all required primitives. Adding libraries would be over-engineering for a 4-5 user app. Requirements.txt does not change. No new CDN scripts. No new JS libraries (~20 lines vanilla JS for modal show/hide and client-side validation hints).

**Core technologies (existing, unchanged):**
- `User.Role` TextChoices — role storage; add `GATEKEEPER = "gatekeeper"` (exactly 10 chars — widen `max_length` to 20 in the same migration as a matter of hygiene)
- `Thread.Status` TextChoices — add `IRRELEVANT = "irrelevant"` as a terminal state distinct from "closed"
- `ActivityLog.Action` TextChoices — add `MARKED_IRRELEVANT` for audit trail
- `SystemConfig` key-value store — four new keys for unassigned alert threshold, cooldown, and last-alert timestamp
- APScheduler heartbeat job — piggyback the unassigned count check onto the existing 1-minute heartbeat with a 30-minute cooldown
- `ChatNotifier` — add one method for the unassigned count alert card

Django's built-in permissions framework (groups/permissions), django-guardian, django-rules, Celery, and any other external library were evaluated and rejected. See `STACK.md` for full rationale.

### Expected Features

**Must have (table stakes):**
- Gatekeeper role on User model — every helpdesk has a dispatcher role; without it the role is meaningless
- Exclusive assignment permissions — the core value of the role; block members from assigning to others
- Mark irrelevant with mandatory reason — queue hygiene; gatekeeper/admin only; feeds AI distillation
- Gatekeeper unassigned count visibility — the role exists to notice unassigned work; sidebar count must show

**Should have (differentiators for this team):**
- Bulk assign from triage queue — gatekeeper processes 10+ threads in one action
- Quick-dismiss (bulk mark irrelevant) — reuses bulk selection UI; clears noise batches
- Unassigned count alert via Google Chat — proactive notification when queue grows beyond threshold
- Member reassign-with-mandatory-reason — audit trail; members must explain when bouncing work

**Defer (post-v2.6.0):**
- AI feedback summary for gatekeeper — no workflow is blocked without it; add in a polish phase
- Gatekeeper-specific triage queue view — optimize after usage patterns emerge
- Reassignment notification to original assignee — existing Chat notifications partially cover this

### Architecture Approach

All changes touch existing files; no new files or apps are needed except two Django migrations (one for accounts, one for emails). The permission refactor is mechanical: catalogue the 25+ `is_admin` inline checks, classify each into "assignment-related" vs "admin-only", then replace with the appropriate helper. The mark-irrelevant flow adds `IRRELEVANT` as a distinct Thread status (keeping `CLOSED` semantically separate as "handled" vs "not worth handling") with a `close_reason` TextField denormalized onto Thread. The alert flow piggybacks on the existing heartbeat job with a 30-minute cooldown in SystemConfig.

**Major components and changes:**
1. `apps/accounts/models.py` — Add `GATEKEEPER` choice, widen `max_length` to 20, add `can_assign` / `can_manage_users` properties
2. `apps/emails/views.py` — Replace 25+ inline `is_admin` checks with `can_assign()` / `is_admin_only()` helpers; add `mark_irrelevant` view
3. `apps/emails/services/assignment.py` — Add `mark_irrelevant()` function; add mandatory-reason enforcement for member reassignment
4. `apps/emails/models.py` — Add `IRRELEVANT` status, `close_reason` field, `MARKED_IRRELEVANT` ActivityLog action
5. `apps/emails/management/commands/run_scheduler.py` — Add `_check_unassigned_alert()` to heartbeat
6. `apps/emails/services/chat_notifier.py` — Add `notify_unassigned_alert()` method
7. Templates (8 files) — Update role dropdowns, permission gates, welcome banner; remove hardcoded 'admin'/'member' strings

### Critical Pitfalls

1. **Scattered permission checks (25+ locations)** — Audit every `is_admin` check before writing any feature code. Classify each into `can_assign` or `is_admin_only`. Zero inline checks remaining when done. Missing one = privilege escalation or feature lockout.

2. **Alert storm from unassigned threshold** — Naive `if count > threshold: send_alert()` fires every heartbeat minute. Implement 30-minute cooldown stored in `SystemConfig.last_unassigned_alert_at`. Consider rising-edge detection (alert when crossing threshold, not on every poll while above it).

3. **Role field max_length tight fit** — "gatekeeper" is exactly 10 chars and `max_length=10`. Widen to 20 in the same migration as adding the choice. Use TextChoices enum values everywhere, never raw strings.

4. **Hardcoded role strings in templates** — `_user_row.html` hardcodes `<option>admin</option>` and `<option>member</option>`. Replace with a loop over `Role.choices`. Gatekeeper cannot be set from Team page until this is fixed.

5. **is_staff coupling** — Gatekeeper must have `is_staff=False`. They do not need Django admin access. When replacing permission checks, remove reliance on `is_staff` for application-level permissions entirely.

## Implications for Roadmap

Based on research, suggested phase structure (dependency-ordered):

### Phase 1: Role + Permission Foundation
**Rationale:** Everything else depends on the gatekeeper role existing. This is the unblocking step — build it first, build it completely. The permission helper audit happens here to prevent missed checks in later phases.
**Delivers:** Gatekeeper role in the database, `can_assign()` and `is_admin_only()` helper functions, dev login support for testing, team management UI updated, all 25+ `is_admin` checks audited and reclassified.
**Addresses:** Gatekeeper role model, template role dropdown fix, welcome banner gatekeeper text, gatekeeper badge/sidebar visibility (role check update)
**Avoids:** Pitfall 1 (scattered checks audited here), Pitfall 3 (max_length widened here), Pitfall 4 (hardcoded templates fixed here), Pitfall 9 (is_staff coupling clarified here)

### Phase 2: Assignment Permission Enforcement
**Rationale:** With the role existing, enforce who can assign. This is the core value delivered by the gatekeeper role. Member reassign-with-reason is a natural addition here since it touches the same assignment views.
**Delivers:** Gatekeepers and admins can assign freely; members cannot assign to others but can still self-claim; members must provide a reason when reassigning threads assigned to them.
**Addresses:** Exclusive assignment permissions, member reassign-with-mandatory-reason
**Avoids:** Pitfall 5 (member self-claim conflict — keep `claim_thread`, only block assigning to others), Pitfall 8 (validation bypass — server-side required check for member role)

### Phase 3: Mark Irrelevant
**Rationale:** The second core gatekeeper action. Depends on permission helpers from Phase 1. Creates the terminal state that Phase 4's alert count will exclude.
**Delivers:** Gatekeeper/admin can mark threads irrelevant with mandatory reason text stored on Thread. Irrelevant threads excluded from unassigned count and sidebar triage queue. ActivityLog captures decisions for AI distillation.
**Addresses:** Mark irrelevant action, close reason stored and visible in activity timeline
**Avoids:** Pitfall 7 (status collision — IRRELEVANT is a distinct status, not overloading CLOSED), Pitfall 11 (missing ActivityLog action — MARKED_IRRELEVANT added)

### Phase 4: Unassigned Count Alerts + Bulk Actions
**Rationale:** Operational efficiency features built on the role and queue mechanics from phases 1-3. Alert count is accurate because irrelevant threads are excluded. Bulk actions are independent but share the same selection UI.
**Delivers:** Google Chat alert when unassigned count exceeds configurable threshold; bulk assign (with confirmation + undo toast); bulk mark irrelevant reusing bulk selection; settings UI for alert threshold configuration.
**Addresses:** Unassigned count alert, bulk assign, quick-dismiss
**Avoids:** Pitfall 6 (alert storm — 30-minute cooldown + rising-edge detection), Pitfall 12 (bulk assign no undo — confirmation dialog + undo toast)

### Phase Ordering Rationale

- Phase 1 before everything: gatekeeper role must exist in the database before any permission check can reference it
- Phase 2 before 3: same views that control assignment also gate mark-irrelevant; cleaner to refactor the permission layer once then add the new action
- Phase 3 before 4: unassigned count alert threshold is more meaningful when irrelevant threads are excluded from the count; gatekeeper needs the tool to reduce the queue before alerts are tuned
- Bulk actions in Phase 4: reuse the same selection UI for both bulk assign and bulk dismiss — one implementation, two actions

### Research Flags

Phases with well-documented patterns (skip `/gsd:research-phase`):
- **Phase 1:** Standard Django TextChoices migration — zero ambiguity, all implementation points confirmed by direct source analysis
- **Phase 2:** Mechanical view refactor with every location catalogued in ARCHITECTURE.md — no unknowns
- **Phase 3:** Standard model field addition + service function — HIGH confidence, established pattern

Phase that may benefit from task-level design before coding:
- **Phase 4 (bulk actions):** The HTMX implementation for checkbox selection and bulk POST hasn't been detailed. Design the partial template and endpoint contract before writing code. Not a research blocker — just needs explicit design thought at the task level, not a full research phase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Direct codebase analysis; all implementation points confirmed by reading source files |
| Features | HIGH | Cross-referenced against Freshdesk/Zendesk dispatcher patterns; recommendations are grounded and opinionated |
| Architecture | HIGH | Every `is_admin` check location catalogued; build order derived from actual dependency graph, not guesswork |
| Pitfalls | HIGH | Most pitfalls identified from direct code reading (field widths, template hardcoding, scattered checks) — not speculative |

**Overall confidence: HIGH**

### Gaps to Address

- **Bulk action HTMX contract:** The research identified bulk assign as a differentiator and recommended reusing the selection UI for quick-dismiss. The exact HTMX partial structure (checkbox state management, toolbar show/hide, POST body format) needs to be designed before writing templates. Not blocking for phases 1-3.
- **Member claim policy:** Research flagged the tension between "gatekeeper controls assignment" and "members can self-claim." Current recommendation: keep `claim_thread` for members on unassigned threads, only block `assign_thread` (assigning to someone else). Confirm with product owner before Phase 2 implementation.
- **Alert threshold default:** Research recommends `10` as a default for `unassigned_alert_threshold`. Validate against actual queue volume after deployment; threshold will need tuning based on real usage.

## Sources

### Primary (HIGH confidence — direct codebase analysis)
- `apps/accounts/models.py` — User.Role TextChoices, max_length=10, is_staff coupling pattern
- `apps/emails/views.py` — 25+ `is_admin` check locations catalogued and classified by type
- `apps/emails/services/assignment.py` — assign_thread(), claim_thread() function signatures and patterns
- `apps/emails/models.py` — Thread.Status, ActivityLog.Action choices
- `apps/emails/management/commands/run_scheduler.py` — heartbeat job structure, APScheduler patterns
- `apps/core/models.py` — SystemConfig key-value store pattern
- `templates/emails/_context_menu.html`, `templates/accounts/_user_row.html` — hardcoded role string locations

### Secondary (MEDIUM confidence — industry helpdesk patterns)
- [Freshdesk roles and permissions](https://www.eesel.ai/blog/freshdesk-roles-and-permissions) — dispatcher/supervisor role design
- [Zendesk standard user roles](https://support.zendesk.com/hc/en-us/articles/4408883763866) — agent/admin/viewer role definitions
- [HelpDesk audit log](https://www.helpdesk.com/help/track-actions-in-the-audit-log/) — reassignment audit trail patterns
- [SLA escalation workflows](https://unito.io/blog/sla-aware-ticket-escalation-workflows/) — threshold alert and cooldown patterns

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
