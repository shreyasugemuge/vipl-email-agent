# Phase 4: Assignment Engine + SLA - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

System auto-assigns emails based on category rules, provides AI fallback suggestions for unmatched emails, calculates SLA deadlines with breach detection, and sends alerts. Manager handles exceptions instead of every email. Team members can claim unassigned emails in their permitted categories. All configuration through the dashboard (no Django admin).

Requirements: ASGN-03, ASGN-04, SLA-02, SLA-03, SLA-04, INFR-09, INFR-10

</domain>

<decisions>
## Implementation Decisions

### Assignment Rules
- Priority list per category: "Sales Inquiry → Rahul, then Shreyas as backup"
- Always assigns to first person in the list (no workload balancing for rules)
- No availability/on-duty system — implicit from the priority list order
- If all people in a category's list are gone, email stays unassigned (manager picks up manually)
- Batch assignment: runs as a separate scheduled job after pipeline (not inline with triage) — gives a window for manual override before auto-assign kicks in
- Rules configured via a custom dashboard settings page (NOT Django admin — premium UI/UX)

### Self-Service Claiming
- Team members can claim unassigned emails in categories they're permitted to see
- Category visibility configured per person by admin (e.g., Rahul sees Sales + Vendor, Priya sees Complaints + General)
- "Claim" button on unassigned email cards within their visible categories
- Admin (manager) sees all categories and can assign anyone

### AI Fallback
- When no rule matches, AI suggests an assignee (ASGN-04)
- Suggest only — manager confirms or picks someone else (no auto-assign from AI)
- AI runs at triage time (enhances existing ai_suggested_assignee field with workload context)
- AI considers email content + category + each person's open email count
- Display: badge on email card ("AI: Rahul") + detailed suggestion bar in detail panel ("AI suggests Rahul based on [reason]") with Accept/Reject buttons

### SLA Deadline Model
- Two-tier SLA: acknowledge deadline + respond deadline (pulling SLA-10 forward from v2 requirements)
- Priority x Category matrix for deadline hours (e.g., CRITICAL Tender=1hr respond, CRITICAL Complaint=2hr respond)
- Business hours only clock: 8 AM – 8 PM IST (matches existing quiet hours config)
- Acknowledge deadline: configurable per priority (e.g., CRITICAL=15min, HIGH=30min, MEDIUM=1hr, LOW=2hr)
- SLA deadline field(s) needed on Email model

### SLA Display
- Color-coded time remaining on every card and detail panel
- Green (>50% time left), amber (25-50%), red (<25%), flashing red (breached)
- Shows both acknowledge and respond deadlines (e.g., "Ack: 12m | Respond: 3h 20m")

### Breach Alerts
- 3x daily summary at 9 AM, 1 PM, 5 PM IST (matches v1 SLA monitor pattern)
- Summary format: counts + top 3 worst offenders (subject, assignee, time overdue, priority)
- Recipients: manager gets full summary, each assignee gets personal alert (their breached emails only)
- Channel: Google Chat only (no email for breach alerts — less inbox noise)
- Auto-escalation: breach auto-bumps priority one level (MEDIUM→HIGH, HIGH→CRITICAL). CRITICAL stays CRITICAL.
- Priority bump logged in ActivityLog for audit trail

### Settings Page (new)
- Dashboard route for assignment rules + SLA config (admin only)
- Category-to-person mapping with drag-to-reorder priority list
- Category visibility per team member
- SLA matrix: acknowledge + respond hours per priority x category
- Premium UI consistent with Phase 3 dashboard design language

### Claude's Discretion
- Exact batch job interval for auto-assignment (suggestion: 2-5 minutes)
- Settings page layout and interaction patterns
- Rule test/preview feature (whether to include a dry-run preview after saving rules)
- ActivityLog action types for new events (auto_assigned, claimed, sla_breached, priority_bumped)
- SLA config model design (separate model vs JSON in SystemConfig)
- How to handle SLA for emails that arrive outside business hours

</decisions>

<specifics>
## Specific Ideas

- No Django admin UI anywhere — everything through the dashboard with gold-standard UX
- Claiming is key: each team member sees their category's unassigned emails and can grab them, reducing manager bottleneck
- AI suggestion is advisory, not authoritative — manager always has final say for unmatched emails
- Two-tier SLA pulled forward from v2 requirements because it adds real accountability (acknowledge ≠ respond)
- Business hours SLA is fairer — overnight emails shouldn't breach before anyone's at their desk

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/emails/services/assignment.py`: assign_email() and change_status() — extend with auto_assign_email() and claim_email()
- `apps/emails/models.py`: Email model has `ai_suggested_assignee` (string) — needs upgrade to store structured suggestion with reasoning
- `apps/emails/models.py`: ActivityLog model — add new action types for auto-assign, claim, SLA breach, priority bump
- `apps/core/models.py`: SystemConfig key-value store — can store SLA config or create dedicated model
- `apps/emails/services/chat_notifier.py`: ChatNotifier — add breach_summary() method alongside existing notify_assignment()
- `templates/base.html`: Premium dark sidebar layout — settings page follows same pattern
- `apps/emails/templatetags/email_tags.py`: Color system (priority_base, status_base) — extend with SLA color helpers

### Established Patterns
- Service layer: views call service functions, services handle ORM + notifications
- Fire-and-forget notifications: Chat never blocks or crashes the main flow
- HTMX partials: card + detail panel with OOB swaps for multi-target updates
- Management commands for background jobs (run_scheduler) — auto-assignment job fits here
- SystemConfig for runtime config with typed casting (str/int/bool/float/json)

### Integration Points
- Pipeline orchestrator (`apps/emails/services/pipeline.py`): auto-assignment runs after pipeline saves email
- APScheduler in `run_scheduler` command: add SLA check job (every 15 min) and assignment batch job
- Email card template (`_email_card.html`): add SLA countdown and AI suggestion badge
- Email detail template (`_email_detail.html`): add SLA bar and AI suggestion detail
- Dashboard views (`apps/emails/views.py`): add settings page views
- URL routes (`apps/emails/urls.py`): add /emails/settings/ routes

</code_context>

<deferred>
## Deferred Ideas

- AI feedback loop from manual corrections (ASGN-10) — v2 requirement, not Phase 4
- Gmail thread monitoring for auto-detecting replies (ASGN-11, ASGN-12) — v2 requirement
- Auto-reassignment on repeated breach (SLA-11) — v2 requirement
- Workload analytics dashboard (ANLY-02) — Phase 5 or later
- WhatsApp/SMS for CRITICAL escalations (NOTF-01) — v2 requirement

</deferred>

---

*Phase: 04-assignment-engine-sla*
*Context gathered: 2026-03-11*
