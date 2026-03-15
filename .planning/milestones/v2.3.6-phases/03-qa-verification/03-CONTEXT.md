# Phase 3: QA & Verification - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify all interactive elements across the dashboard work correctly through Claude-in-Chrome browser automation on the live site. Find and fix bugs inline. Produce a QA report with screenshots and GIF recordings.

</domain>

<decisions>
## Implementation Decisions

### Testing approach
- Use Claude-in-Chrome MCP tools (not Playwright/Selenium) — no new dependencies
- Run against live site: triage.vidarbhainfotech.com (requires active Google OAuth session)
- Fully autonomous — Claude walks through all pages and interactions on its own, reports findings
- Phase 1+2 focused first (verify bug fixes and UX additions), then general sweep of all interactions

### Test coverage scope
- All pages: email list + detail panel, settings (all 6 tabs), activity log, login + team management
- Mobile viewport testing: resize to 375px (mobile) and 768px (tablet) for responsive checks
- HTMX interaction verification: click hx-get/hx-post elements, verify partial swaps work, no unexpected full-page reloads
- Console error checking: read_console_messages after each page interaction to catch silent JS errors, failed requests, 404s

### Regression handling
- Fix bugs inline during QA — find it, fix it, re-verify immediately
- Run pytest after each fix to catch cascading regressions
- Batch commits by page/section (e.g., "fix: email list QA issues"), not one per bug

### Test artifacts
- Markdown QA report in `.planning/milestones/v2.3.4-phases/03-qa-verification/03-QA-REPORT.md`
  - Pages tested, interactions verified, bugs found + fixed, remaining issues
- Screenshots of every page (desktop + mobile viewports)
- GIF recordings of key flows (login, email triage, mobile interactions)
- Store media in `.planning/qa/` — gitignored, deleted at milestone close
- QA report (markdown) committed; media files are ephemeral

### Claude's Discretion
- Order of pages to test (as long as Phase 1+2 changes are verified first)
- Which flows to record as GIFs vs just screenshot
- How to structure the QA report sections
- Whether to test edge cases (empty states, error states) or focus on happy paths

</decisions>

<specifics>
## Specific Ideas

- Delete all QA files (screenshots, GIFs) at milestone close via /gsd:cleanup or /gsd:complete-milestone
- The QA pass doubles as final acceptance — if it passes, the milestone is shippable

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- 78 HTMX interactions across 15 templates — these are the test targets
- pytest suite (381+ tests) — run after each fix as regression check
- `test_pipeline` management command — can verify pipeline still works after fixes

### Established Patterns
- HTMX partials: `_email_card.html`, `_email_detail.html`, `_email_list_body.html` — swapped via hx-target
- Filter state via URL params: `?status=new&priority=HIGH&view=unassigned`
- Settings tabs: each tab is an HTMX partial loaded into `#settings-content`
- Activity log: filter chips + date range + pagination

### Integration Points
- Claude-in-Chrome MCP tools: navigate, read_page, find, computer (click), form_input, screenshots, GIF recording, console messages, resize_window
- Live site requires Google OAuth login — need active session in Chrome
- Network requests can be monitored via read_network_requests for failed API calls

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-qa-verification*
*Context gathered: 2026-03-15*
