# Phase 4: Page Polish - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Login, settings, activity, and sidebar pages feel cohesive and well-organized. Four specific requirements: logo fix (PAGE-01), settings reorg (PAGE-02), activity redesign (PAGE-03), sidebar version (PAGE-04). No new features — polish only.

</domain>

<decisions>
## Implementation Decisions

### Login Page Branding (PAGE-01)
- Replace vipl-logo-full.jpg background rectangle using CSS techniques (mix-blend-mode, clip-path, or border-radius) — no new PNG needed
- Keep the glass-morphism card (backdrop-blur + white glass effect)
- Retheme the entire login page as **retro modern** — still VIPL branded
- Keep animated gradient background but adjust to fit retro-modern aesthetic
- Decorative elements (blur circles, title, subtitle) should be updated to match the retro-modern theme

### Settings Reorganization (PAGE-02)
- Group 7 tabs into 3 sections with visible group headers:
  - **Assignment**: Assignment Rules, Team Visibility, SLA Targets
  - **Integrations**: Chat Webhooks, Email Inboxes
  - **System**: System Config, Spam Whitelist
- Render as horizontal tab bar with visual group separators (dividers between groups)
- Section labels above each group of tabs
- Rename tabs to descriptive names: Assignment Rules, Team Visibility, SLA Targets, Chat Webhooks, Email Inboxes, System Config, Spam Whitelist
- Each tab content panel gets a bold title + 1-line description header at the top

### Activity Page Redesign (PAGE-03)
- Switch from date-grouped flat list to **thread-grouped** activity
- Each thread shown as a card/section with all its events listed inside
- Clicking a thread group header navigates to thread detail (/emails/threads/<pk>/detail/)
- Keep stat cards (Total, Today, Assignments, Status Changes)
- Improve filter chips — organize/group better, make smarter (not replace, enhance)
- Sorting/date headers: Claude's discretion — pick what works best with thread grouping

### Sidebar Version Display (PAGE-04)
- Replace "Online" text with version number (e.g., "v2.5.4")
- Add environment badge next to version: [PROD], [DEV], [OFF]
- Badge colors: green = production, amber = dev, red = off (maps to SystemConfig operating_mode)
- Keep green pulsing dot as health indicator
- Version sourced from git tag at Docker build time (injected into settings)
- Fallback for local dev: read from settings constant or git describe

### Claude's Discretion
- Retro-modern design specifics for login (color palette, typography choices, decorative elements)
- Activity page: whether to keep date headers within thread grouping or sort purely by recency
- Activity filter chip organization approach
- Login CSS technique for hiding logo background (mix-blend-mode vs clip-path vs other)
- Settings tab bar responsive behavior on mobile

</decisions>

<specifics>
## Specific Ideas

- Login: "retro modern, branded for VIPL still" — user wants a distinctive aesthetic, not generic corporate
- Settings: horizontal tabs with dividers felt right — user liked the grouped preview layout
- Activity: thread-grouped view selected specifically over timeline and date-grouped alternatives
- Activity filters: "good but need to be organized or grouped better, also make smarter"
- Sidebar: version + env badge preferred over plain version — useful for dev/prod distinction

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `static/img/vipl-logo-full.jpg`: Current login logo (220px, has background rectangle)
- `static/img/vipl-icon.jpg`: Small square icon (used in sidebar, could be used on login)
- Login glass card: `backdrop-filter: blur(24px)` pattern at `templates/registration/login.html`
- Tab switcher: `switchTab()` JS function in `templates/emails/settings.html`
- Stat card pattern: Clickable cards with colored icons, active ring state
- Activity date grouping: `groupby()` in views.py line 2285
- ActivityLog model with Action enum for all event types

### Established Patterns
- Tailwind v4 with Plus Jakarta Sans font (weights 300-800)
- Primary color: `rgb(168,51,98)` / Tailwind `primary-*` scale
- Dark sidebar: `bg-[#0f1117]`, 220px fixed width
- Cards: `bg-white rounded-xl border border-slate-200/60`
- HTMX for all dynamic content loading with `hx-push-url` for browser history
- Tab descriptions stored in JS object, updated on tab switch

### Integration Points
- `templates/base.html` lines 197-200: "Online" status → version display
- `templates/emails/settings.html` lines 11-45: tab bar → grouped tabs
- `templates/emails/activity_log.html`: stat cards + filter chips + activity feed
- `templates/emails/_activity_feed.html`: date-grouped entries → thread-grouped entries
- `apps/emails/views.py` line 2285: `grouped_entries` groupby logic → thread groupby
- `config/settings/base.py`: add VERSION constant or git-tag injection
- `Dockerfile`: inject git tag into build args
- Context processor needed to expose version + operating_mode to all templates

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-page-polish*
*Context gathered: 2026-03-15*
