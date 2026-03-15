# Feature Landscape

**Domain:** Gatekeeper/dispatcher role + irrelevant email handling for shared inbox triage system
**Researched:** 2026-03-15

## Table Stakes

Features users expect from a gatekeeper/assignment-control system. Missing = the role feels pointless.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Gatekeeper role on User model | Every helpdesk (Zendesk, Freshdesk) has a dispatcher/supervisor role distinct from admin and agent. Without it there is no permission boundary. | Low | `User.Role` choices field (exists) | Add `GATEKEEPER = "gatekeeper"` to `Role.choices`. Multiple users can hold the role. Gatekeeper sees all threads (like admin) but cannot manage system settings. |
| Exclusive assignment permissions | Freshdesk's dispatcher role exists specifically so agents cannot self-assign freely -- assignment is controlled. Core reason the role exists. | Medium | Gatekeeper role, `assign_thread()`, `claim_thread()`, all assignment views | Block members from assigning/reassigning. Gatekeepers + admins can assign. Members can only acknowledge/close threads assigned to them. Must update: `assign_thread`, `claim_thread`, context menu, assign button visibility. |
| Member reassign-with-mandatory-reason | Audit trail is table stakes in every helpdesk (Freshdesk, Zendesk, HelpDesk all log reassignment reasons). Members should not silently bounce work. | Low | `ActivityLog.detail` field (exists), assignment views | When a member reassigns (if allowed at all), require a non-empty reason string. Gatekeeper/admin reassigns optionally include reason. Store in `ActivityLog.detail`. |
| Mark irrelevant (close with reason) | Every triage system needs a way to dismiss non-actionable items without them clogging the queue. Zendesk has "Solved", Freshdesk has "Closed" with resolution notes. | Medium | `Thread.Status` choices, `change_thread_status()`, ActivityLog | Add `IRRELEVANT = "irrelevant"` status (or use existing `closed` with a `close_reason` field). Gatekeeper/admin only. Requires mandatory reason text. Removes thread from unassigned count. Feeds AI distillation pipeline. |
| Close reason stored and visible | Without the reason, marking irrelevant is just deleting -- loses institutional knowledge for AI training. | Low | Thread model or ActivityLog | Store as `ActivityLog.detail` on the close action. Display in thread detail activity timeline. |
| Gatekeeper dashboard badge for unassigned count | The whole point of the role is to notice unassigned work. A prominent count is expected -- Freshdesk shows this in the sidebar, Zendesk in views. | Low | Existing sidebar unassigned count (already shows for admin) | Ensure gatekeeper sees the same sidebar counts as admin. Already partially built -- just needs role check update. |

## Differentiators

Features that set the system apart from basic helpdesk assignment. Not expected, but valuable for a 3-5 person team.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| Bulk assign from triage queue | Speed: gatekeeper processes 10+ unassigned threads in one action instead of clicking each. Freshdesk Pro has this; most small tools do not. | Medium | Thread list view, HTMX, assignment service | Checkbox selection on thread cards + "Assign selected to..." dropdown. HTMX POST with thread IDs array. Single ActivityLog entry per thread. |
| Quick-dismiss (bulk mark irrelevant) | Same speed benefit as bulk assign but for clearing noise. Spam batch + vendor newsletters that slip through filters. | Low | Bulk selection UI (same as bulk assign), mark-irrelevant action | Reuse bulk selection UI. Single reason applies to all selected. |
| Configurable unassigned count alert via Google Chat | Proactive notification when queue grows -- gatekeeper does not need to watch dashboard. Threshold-based alerts (e.g., >5 unassigned for >15min). | Medium | Scheduler, `ChatNotifier`, `SystemConfig` | New SystemConfig keys: `unassigned_alert_threshold` (int), `unassigned_alert_cooldown_minutes` (int). Scheduler checks count each cycle. Sends Chat card with count + link to triage queue. Cooldown prevents spam. |
| AI feedback summary for gatekeeper | Show gatekeeper a digest of recent AI corrections (category changes, priority overrides) so they can spot patterns and adjust rules. | Medium | Existing `ActivityLog` with category/priority change actions, `AssignmentFeedback` | Aggregate last 7 days of corrections into a summary card on the triage queue view. No new models needed -- query existing ActivityLog. |
| Gatekeeper-specific triage queue view | Dedicated view optimized for rapid triage: compact cards, assignment dropdown inline, dismiss button visible without opening detail. | Medium | Thread list view, existing filter system | Not a new URL -- enhance existing `?view=unassigned` with gatekeeper-specific card layout. Show inline assign dropdown + dismiss button when user is gatekeeper/admin. |
| Reassignment notification to original assignee | When gatekeeper reassigns a thread, notify the original assignee so they know it moved. Prevents confusion. | Low | `assign_thread()`, `ChatNotifier` | Already partially built -- assignment Chat notification exists. Add "reassigned away from you" variant. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Separate gatekeeper dashboard/app | 3-5 users. A separate UI doubles maintenance for no benefit. Freshdesk and Zendesk use the same UI with role-conditional elements. | Conditionally show/hide UI elements based on `user.role`. Same views, different permissions. |
| Approval workflow for assignments | Over-engineered for a team of 4. Adds friction without value. No helpdesk at this scale uses approval chains. | Direct assignment by gatekeeper. Instant, no pending state. |
| Member self-assignment blocked entirely | Too restrictive. Members should still be able to claim unassigned threads in their category (existing `claim_thread` behavior). Only restrict reassigning others' work. | Keep `claim_thread` for members on unassigned threads. Block `assign_thread` (assigning to someone else) for members. |
| Complex permission matrix UI | Django admin for permission management is overkill for 4 users. | Role is a single field on User. Admin promotes/demotes via team page dropdown. |
| Irrelevant reason taxonomy/picklist | Predefined reason categories add rigidity. Free-text is sufficient at this scale and feeds AI better. | Free-text reason field. AI distillation pipeline extracts patterns. |
| Round-robin auto-assignment for gatekeeper | Already in PROJECT.md out-of-scope. Category rules are more accurate. | Keep existing `AssignmentRule` category-based assignment. |
| Gatekeeper-only visibility (hiding threads from members) | Members need context on the full queue to understand priorities. Hiding threads creates information silos. | Keep `can_see_all_emails` as the visibility control. Gatekeeper gets assignment power, not information hiding power. |

## Feature Dependencies

```
Gatekeeper role (User.Role.GATEKEEPER)
  --> Exclusive assignment permissions (permission checks in views + services)
  --> Gatekeeper sidebar badge (role check in template)
  --> Mark irrelevant action (role check in view)
      --> Close reason field/ActivityLog detail (model/service change)
      --> AI distillation of irrelevant patterns (feeds existing pipeline)
  --> Bulk assign UI (requires gatekeeper role check)
      --> Quick-dismiss (reuses bulk selection)
  --> Gatekeeper triage queue enhancements (conditional card layout)

Unassigned count alert (independent of gatekeeper role)
  --> SystemConfig keys (threshold + cooldown)
  --> Scheduler check (new job in run_scheduler)
  --> Chat notification card (new template in ChatNotifier)

Member reassign-with-reason (independent, can ship with role)
  --> Mandatory reason validation in assign_thread view
  --> ActivityLog.detail population (already supported)

AI feedback summary (independent, nice-to-have)
  --> ActivityLog query aggregation (no new models)
  --> Template partial on triage queue
```

## MVP Recommendation

**Phase 1 -- Core role + permissions (ship first):**
1. Gatekeeper role on User model (table stakes, lowest effort, unblocks everything)
2. Exclusive assignment permissions (core value of the role)
3. Mark irrelevant with mandatory reason (unblocks queue cleanup)
4. Gatekeeper badge/count visibility (already mostly built)

**Phase 2 -- Speed + alerts:**
5. Bulk assign from triage queue (gatekeeper efficiency)
6. Quick-dismiss (reuses bulk UI)
7. Unassigned count alert via Chat (proactive monitoring)
8. Member reassign-with-reason (audit trail)

**Defer:**
- AI feedback summary: Nice-to-have, not blocking any workflow. Can add in a polish phase.
- Gatekeeper-specific triage queue view: Optimize after the role is live and usage patterns are clear.
- Reassignment notification to original assignee: Low priority, existing Chat notifications partially cover this.

## Complexity Budget

| Feature | Model changes | Service changes | View changes | Template changes | Tests |
|---------|--------------|-----------------|--------------|-----------------|-------|
| Gatekeeper role | 1 field + migration | 0 | 0 | Role checks in templates | ~10 |
| Exclusive assignment | 0 | `assign_thread`, `claim_thread` guards | Assign/context-menu views | Button visibility | ~20 |
| Mark irrelevant | 1 status choice + migration | `change_thread_status` | New view endpoint | Detail panel + context menu | ~15 |
| Bulk assign | 0 | New `bulk_assign_threads` | New bulk endpoint | Card checkboxes + toolbar | ~15 |
| Quick-dismiss | 0 | New `bulk_mark_irrelevant` | New bulk endpoint | Reuses bulk UI | ~10 |
| Unassigned alert | 2 SystemConfig keys | New scheduler job + ChatNotifier method | 0 | Settings tab for threshold | ~10 |
| Reassign-with-reason | 0 | Validation in assign_thread | Reason textarea in assign modal | Modal update | ~8 |

**Total estimate:** ~88 new tests, 2 migrations, 7 view/service changes. Fits in one milestone with 2 phases.

## Sources

- [Freshdesk roles and permissions](https://www.eesel.ai/blog/freshdesk-roles-and-permissions) -- dispatcher/supervisor role patterns, custom role granularity
- [Freshdesk controlling agent access](https://support.freshdesk.com/support/solutions/articles/96909-controlling-agent-access-with-roles) -- role-based ticket access control
- [Zendesk roles and permissions 2026](https://www.eesel.ai/blog/zendesk-admin-center-roles-and-permissions) -- agent access scoping, custom roles
- [Zendesk standard user roles](https://support.zendesk.com/hc/en-us/articles/4408883763866-Understanding-standard-user-roles-for-Zendesk-Support) -- agent/admin/viewer role definitions
- [Helpdesk 365 dispatcher role](https://kb.hr365.us/sharepoint-helpdesk/modern/admin/settings/role/) -- Lite User Dispatcher cannot be assigned tickets
- [Shared mailbox best practices 2026](https://www.getinboxzero.com/blog/post/shared-mailbox-management-best-practices) -- triage queue patterns
- [HelpDesk audit log](https://www.helpdesk.com/help/track-actions-in-the-audit-log/) -- reassignment audit trail patterns
- [Freshdesk audit log](https://support.freshdesk.com/support/solutions/articles/235745-track-changes-using-audit-log) -- change tracking for ticket actions
- [SLA escalation workflows](https://unito.io/blog/sla-aware-ticket-escalation-workflows/) -- threshold alerts and notification escalation
- [Gatekeeper help desk](https://knowledge.gatekeeperhq.com/en/docs/helpdesk) -- incoming email routing and triage assignment
