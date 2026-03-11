# Phase 3: Dashboard - Context

**Gathered:** 2026-03-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Manager can see every email, assign it to a team member, track status, and filter/sort the list. Team members see their assigned emails and can acknowledge/close them. Activity log tracks all changes. This is the core workflow that v1 completely lacks — the transition from "monitoring tool" to "inbox management system."

Requirements: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, SLA-01, ASGN-01, ASGN-02, ASGN-05

</domain>

<decisions>
## Implementation Decisions

### Email Card Layout
- Card-based layout (not table rows) — each email is a card like Linear/Trello
- Each card shows: priority badge (colored), category badge, sender, subject, AI summary (1-2 lines), assignee name, time-ago / SLA countdown
- Newest first, flat list as default sort
- Paginated at 25 per page (not infinite scroll)
- Click card opens a slide-out detail panel on the right (40% list / 60% detail)
- Detail panel shows: full email body, draft reply, attachment metadata, activity log, "Open in Gmail" link, assign/status controls

### Assignment Workflow
- Assignee dropdown directly on each card — one click to open, one click to assign
- Reassignment: pick new person from same dropdown, optional note field appears for context
- Assignment notification: Google Chat message only (subject, sender, priority, dashboard link)
- Team members can change status on their own assigned emails: Acknowledge and Close
- Only admins can assign/reassign

### Status & Filtering
- 4 statuses: New → Acknowledged → Replied → Closed (Replied auto-detection deferred to Phase 4)
- Default manager view: Unassigned queue only (emails with no assignee)
- Default team member view: My assigned emails only (respects `can_see_all_emails` User flag)
- Toolbar navigation: tab bar [All] [Unassigned] [My Emails] + per-assignee tabs
- Dropdown filters: Status, Priority, Category, Inbox
- Sort by any visible field (date, priority, status, assignee)
- URL-based filter state (shareable, bookmarkable)
- Filter counts shown (e.g., "12 emails matching")

### Visual Design
- Clean minimal style — white background, subtle borders, colored priority/status badges
- Tailwind CSS via CDN play script (zero build step, fine for 4-5 users)
- Left sidebar + top bar navigation
  - Sidebar: nav links (Emails, Activity), team member list (admin only), Settings link (admin)
  - Top bar: app name/logo, user info, logout
- Priority badge colors: CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=gray
- Font: Inter or system-ui
- Desktop-first, mobile-usable (responsive cards stack vertically on small screens)

### Dev/Test Mode
- Dashboard must work with fake data from `fake_data.py` (11 sample emails) without a running pipeline
- `test_pipeline` command should seed the database with fake emails for dashboard development
- No external API calls needed to develop or test the dashboard
- Dev inspector at `/emails/inspect/` already exists for pipeline output — dashboard views complement this

### Claude's Discretion
- Exact card spacing, typography, and shadow values
- Sidebar width and collapse behavior
- Detail panel animation (slide vs instant)
- Empty state illustrations/messages
- Mobile breakpoint behavior
- HTMX swap strategies (innerHTML vs outerHTML, push URL, etc.)
- Activity log model design (separate model or JSON field)
- How to structure Django templates (one big template vs partials)

</decisions>

<specifics>
## Specific Ideas

- Cards should feel like Linear's issue cards — clean, not cluttered, content-focused
- Slide-out detail panel like Linear's issue detail — list stays visible on the left
- "Open in Gmail" link is the primary action for actually responding (no reply from dashboard)
- Unassigned queue is THE core screen — manager should be able to triage 20 emails in 2 minutes with dropdown assigns
- Phase 2.5 established dev safety patterns (fake_data.py, test_pipeline, dev inspector) — Phase 3 should follow the same pattern so dashboard development doesn't require a running email pipeline

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/emails/models.py`: Email model has `status`, `assigned_to`, `priority`, `category`, `ai_summary`, `processing_status` — all fields the dashboard needs
- `apps/accounts/models.py`: User model has `role` (admin/member) and `can_see_all_emails` flag — ready for view permissions
- `apps/emails/services/fake_data.py`: 11 sample emails with matched triages — can seed the DB for dashboard dev
- `apps/emails/services/chat_notifier.py`: ChatNotifier already has Cards v2 webhook — reuse for assignment notifications
- `templates/base.html`: Exists but bare (no CSS, no nav) — needs full rebuild with Tailwind + sidebar + top bar
- `templates/emails/inspect.html`: Dev inspector template exists with dark theme — different from dashboard but shows template patterns

### Established Patterns
- Django templates + HTMX (server-rendered, no React/Node) — confirmed in Phase 1
- URL routing: `config/urls.py` includes `apps/emails/urls.py` at `/emails/`
- User auth: Django built-in, login required, role-based access
- Service modules: business logic in `apps/emails/services/`, views are thin
- Management commands for dev tooling (test_pipeline, run_scheduler)

### Integration Points
- `apps/emails/views.py`: Currently has dev inspector — dashboard views go here (or separate view modules)
- `apps/emails/urls.py`: Email URL routes — add dashboard routes
- `config/urls.py`: Root URL config — dashboard could be at `/` or `/emails/`
- `apps/emails/services/chat_notifier.py`: Reuse for assignment notification (needs new card format for "assigned to you")
- `templates/base.html`: Rebuild as dashboard layout (sidebar + top bar + content area)

</code_context>

<deferred>
## Deferred Ideas

- Auto-assignment (category → person rules) — Phase 4
- SLA deadline calculation and breach detection — Phase 4
- "Replied" status auto-detection from Gmail thread — Phase 4
- Dashboard settings/config page — Phase 5
- Analytics charts (response times, volume trends) — Phase 5
- Google Sheets sync mirror — Phase 5
- Dark mode toggle — future enhancement

</deferred>

---

*Phase: 03-dashboard*
*Context gathered: 2026-03-11*
