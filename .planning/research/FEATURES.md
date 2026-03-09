# Feature Landscape

**Domain:** Shared inbox management — assignment, SLA tracking, escalation, team oversight
**Researched:** 2026-03-09
**Competitors analyzed:** Front, Hiver, Help Scout, Missive, Gmelius, Drag

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Manual assignment** — assign email to team member | Every competitor has this. Without clear ownership, emails fall through cracks. Core value prop of the product. | Low | Click-to-assign from dashboard. Must update status immediately. |
| **Assignment visibility** — see who owns what | Front, Hiver, Help Scout all show assignee prominently. Prevents duplicate work. | Low | Assignee column in email table view. |
| **Status tracking** — New / Acknowledged / Replied / Closed | Every tool tracks conversation lifecycle. Manager needs to see what's stuck. | Low | 4-5 statuses max. Auto-detect "Replied" from Gmail thread monitoring (already in PROJECT.md scope). |
| **SLA deadlines per priority** — response time targets | Hiver, Front, Missive all offer SLA configuration. v1 already has this — must carry forward. | Low | Already built in v1. Migrate SLA config to PostgreSQL. |
| **SLA breach alerts** — notify when deadline missed | Every tool alerts on breach. Without this, SLA tracking is just decoration. | Low | Already built in v1 (3x daily summary). Enhance with per-ticket escalation. |
| **Basic dashboard** — table view with filters | Every competitor has a conversation list view. Manager needs to see all emails, filter by status/assignee/priority. | Med | Table with columns: date, from, subject, assignee, priority, status, SLA remaining. Filters + sort. |
| **Google OAuth SSO** — login with company Google account | Standard for any internal tool in a Google Workspace org. No excuse for password-based auth. | Med | Restrict to @vidarbhainfotech.com via `hd` claim validation. Use Google Identity Services library. |
| **Notification on assignment** — tell someone they got assigned | Hiver, Help Scout, Front all notify on assignment. If nobody tells the assignee, assignment is pointless. | Low | Google Chat message (existing webhook) + email notification. |
| **Unassigned queue** — see emails nobody owns | Every tool highlights unassigned conversations. This is the "things falling through cracks" view. | Low | Filter: assignee = null. Should be the default view for managers. |
| **Activity log / audit trail** — who did what when | Help Scout, Front track assignment changes. Needed for accountability. | Low | Log: assigned, reassigned, status changed, with timestamp + actor. Simple append-only table. |

## Differentiators

Features that set this product apart. Not expected in every tool, but high value for VIPL's specific context.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **AI auto-assignment** — assign based on email content + category rules | Hiver offers round-robin and keyword-based. VIPL can do better: Claude already classifies category/priority, so assignment rules map category->person with AI fallback for ambiguous cases. This is the "smart" part of the system. | Med | Phase 1: rules-based (category->person mapping). Phase 2: AI content analysis for edge cases. Don't try to do ML workload balancing — team is 3 people, round-robin is overkill. |
| **AI feedback loop** — corrections improve future assignments | No competitor does this well. When manager reassigns, log the correction. Over time, build a pattern library. Even simple frequency-based corrections ("last 10 emails about X went to person Y") beat static rules. | Med | Store corrections in PostgreSQL. Query correction history when assigning. No ML needed — frequency counting is sufficient for a 3-person team. |
| **Two-tier SLA** — acknowledgement deadline + response deadline | Most tools track one SLA (first response). VIPL wants to know: did the assignee SEE the email (acknowledge) AND did they REPLY (respond). Two separate deadlines, two separate alerts. | Med | Ack deadline: 30 min (configurable). Response deadline: per-category (existing SLA config). Gmail thread monitoring detects reply auto-completion. |
| **Gmail thread auto-detection** — auto-close when replied | Most tools are the reply platform. Since VIPL replies from Gmail directly, the system needs to detect replies by monitoring the Gmail thread. This is unique to VIPL's "triage only, reply from Gmail" model. | Med | Poll Gmail threads for assignee's reply. When detected, auto-update status to "Replied". Already in PROJECT.md scope. |
| **Escalation chain** — alert manager when assignee misses deadline | Front and Hiver have this in enterprise tiers. For VIPL, escalation is simple: notify Shreyas (the manager) via Chat + email when SLA breaches. No complex chains needed. | Low | One-level escalation: assignee misses -> alert manager. Maybe add WhatsApp for CRITICAL. |
| **WhatsApp/SMS for urgent escalations** — multi-channel alerts beyond Chat | Most competitors offer multi-channel. For VIPL, Google Chat is the daily driver, but CRITICAL SLA breaches should hit WhatsApp (everyone checks WhatsApp). | Med | Use Twilio or WhatsApp Business API for CRITICAL-only alerts. Don't over-notify — only SLA breaches on CRITICAL emails. |
| **Workload view** — see how many open items each person has | Hiver and Help Scout show workload distribution. For a 3-person team this is a simple count, but it helps the manager balance assignments. | Low | Card or sidebar showing: Person A (5 open), Person B (3 open), Person C (7 open). Simple query. |
| **Response time analytics** — average response times per person, per category | Hiver, Front, Help Scout all offer this in paid tiers. VIPL can build it into the dashboard since they own the data in PostgreSQL. | Med | Charts: avg response time trend, volume by day/hour, response time by assignee. Use a charting library (Recharts or similar). |
| **Configurable inbox management** — add/remove monitored inboxes without code changes | Currently hardcoded. Admin UI to add a new inbox and its polling config. | Low | Admin settings page. Store inbox config in PostgreSQL. Backend picks up changes on next poll cycle. |

## Anti-Features

Features to explicitly NOT build. These are traps that add complexity without proportional value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Reply from dashboard** | Already decided (PROJECT.md out-of-scope). Building a compose/reply UI is enormous effort: rich text editor, attachment handling, Gmail send-as, threading. The team already knows Gmail. | Show a "Open in Gmail" link that deep-links to the thread. One click to reply. |
| **Round-robin auto-assignment** | Team is 3 people. Round-robin is for 20+ agent support teams. With 3 people, category-based rules ("tender emails -> Amit, sales inquiries -> Raj") are more accurate and predictable than mechanical rotation. | Category-to-person mapping rules with AI fallback for uncategorized. |
| **CSAT / customer satisfaction surveys** | This is an internal tool for a small team, not a customer support platform. Nobody is sending satisfaction surveys to people emailing info@. | Track internal metrics: response time, SLA compliance, volume. |
| **Canned responses / templates** | Team replies from Gmail directly. Building a template system in the dashboard adds complexity for something Gmail already does (Templates feature, Smart Compose). | If needed later, use Gmail's built-in Templates feature. |
| **Real-time collaboration** (co-viewing, typing indicators) | Front's killer feature, but requires WebSocket infrastructure and complex state management. With 3 users, collision is rare. | Show "Currently assigned to X" — that's enough to prevent duplicate replies. |
| **Ticket numbering / ticketing system** | v1 has ticket numbers but they serve no real purpose for internal use. Nobody references "ticket #247" in conversation. It adds complexity to assignment and tracking. | Use email subject + sender as the natural identifier. Keep a database ID for internal references. |
| **Complex workflow states** (In Review, Pending Customer, On Hold, etc.) | 3-person team doesn't need 8-state workflows. That's enterprise help desk bloat. | 4 states: New, Acknowledged, Replied, Closed. Maybe add "Escalated" if needed. |
| **Multi-tenant / team hierarchy** | Single company, single team. No need for departments, teams, roles beyond admin/user. | Two roles: Admin (Shreyas — can reassign, configure) and User (team members — see their assignments, acknowledge). |
| **Mobile native app** | Already decided out-of-scope. Responsive web covers the "check on phone" use case. Notifications go via Chat/WhatsApp anyway. | Make dashboard responsive. Use existing notification channels for alerts. |
| **Email threading / conversation view** | Building a threaded email viewer is reimplementing Gmail. The dashboard just needs to show the triage summary, not the full conversation. | Show: AI summary, sender, subject, priority, draft reply. Link to Gmail for the full thread. |

## Feature Dependencies

```
Google OAuth SSO
  --> Dashboard (can't show dashboard without auth)
    --> Email table view (core dashboard component)
      --> Manual assignment (assign from table)
        --> Notification on assignment (notify after assign)
        --> Status tracking (status changes after assign)
          --> Gmail thread auto-detection (auto-update status)
      --> Filters (filter table by status/assignee/priority)
      --> Unassigned queue (filtered view)

SLA deadlines (migrated from v1)
  --> SLA breach detection (migrated from v1)
    --> Escalation alerts (notify manager)
      --> WhatsApp/SMS for CRITICAL (multi-channel escalation)
  --> Two-tier SLA (ack + response deadlines)

AI triage (migrated from v1)
  --> AI auto-assignment (use triage output for rules)
    --> AI feedback loop (log corrections to improve)

Activity log (independent — start logging from day 1)

Response time analytics (requires: status tracking data accumulated over time)

Workload view (requires: assignment data)

Configurable inbox management (independent — admin feature)
```

## MVP Recommendation

**Prioritize (Phase 1 — "emails get owners"):**

1. Google OAuth SSO (gate everything behind auth)
2. Email table view with filters (the dashboard core)
3. Manual assignment + notification on assignment
4. Unassigned queue as default manager view
5. Status tracking (New / Acknowledged / Replied / Closed)
6. SLA deadlines + breach alerts (migrate from v1)
7. Activity log (start logging from day 1, even if no UI yet)

**Phase 2 — "smart assignment + accountability":**

1. AI auto-assignment (category-to-person rules + AI fallback)
2. Gmail thread auto-detection (auto-update status on reply)
3. Two-tier SLA (ack + response deadlines)
4. Escalation to manager on breach
5. Workload view

**Defer (Phase 3+ — "analytics + polish"):**

1. AI feedback loop from corrections
2. Response time analytics / charts
3. WhatsApp/SMS for CRITICAL escalations
4. Configurable inbox management UI

**Rationale:** Phase 1 solves the core problem ("emails have no owner") with the simplest possible implementation. Phase 2 makes assignment smarter and tracking automatic. Phase 3 adds intelligence and polish that only matter once the workflow is running.

## Sources

- [Hiver features page](https://hiverhq.com/features) — assignment, SLA, analytics
- [Hiver best shared inbox software comparison](https://hiverhq.com/blog/best-shared-inbox-software) — 12 tools compared
- [Help Scout shared inbox guide](https://www.helpscout.com/blog/shared-inbox/) — 7 tools compared
- [Help Scout automatic workflows](https://docs.helpscout.com/article/1399-automatic-workflows) — assignment rules
- [Missive SLA blog post](https://missiveapp.com/blog/reduce-response-time-sla) — SLA implementation
- [Front assignment: round robin vs load balancing](https://help.front.com/en/articles/1315904) — assignment methods
- [Gmelius round-robin and load balancing](https://help.gmelius.com/workflow-rules-slas/round-robin) — assignment methods
- [Front review on Tidio](https://www.tidio.com/blog/front-review/) — features and pricing
- [Google OAuth web server guide](https://developers.google.com/identity/protocols/oauth2/web-server) — domain restriction via `hd` claim
