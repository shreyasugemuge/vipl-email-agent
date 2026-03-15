# Phase 3: QA & Verification - Research

**Researched:** 2026-03-15
**Domain:** Browser automation QA via Claude-in-Chrome MCP tools
**Confidence:** HIGH

## Summary

Phase 3 uses Claude-in-Chrome MCP browser tools to exercise all interactive elements on the live site (triage.vidarbhainfotech.com). The approach is zero-dependency -- no Playwright, Selenium, or test frameworks to install. Claude navigates the real browser, clicks elements, fills forms, reads console errors, takes screenshots, and records GIFs. The site has 38 HTMX endpoint references across 17 templates and 27 URL routes to verify.

The key challenge is systematic coverage: ensuring every interactive element is tested without missing pages or flows. The research below catalogs all testable surfaces, the MCP tools available, and a structured approach to walk through them.

**Primary recommendation:** Organize QA by page/section, verify Phase 1+2 fixes first, then sweep all interactions. Use `read_console_messages` after every navigation and interaction to catch silent failures.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use Claude-in-Chrome MCP tools (not Playwright/Selenium) -- no new dependencies
- Run against live site: triage.vidarbhainfotech.com (requires active Google OAuth session)
- Fully autonomous -- Claude walks through all pages and interactions, reports findings
- Phase 1+2 changes verified first, then general sweep
- Fix bugs inline during QA -- find it, fix it, re-verify immediately
- Run pytest after each fix to catch cascading regressions
- Batch commits by page/section
- QA report in `.planning/milestones/v2.3.4-phases/03-qa-verification/03-QA-REPORT.md`
- Screenshots/GIFs stored in `.planning/qa/` (gitignored, ephemeral)
- QA report (markdown) committed; media files are ephemeral

### Claude's Discretion
- Order of pages to test (as long as Phase 1+2 changes are verified first)
- Which flows to record as GIFs vs just screenshot
- How to structure the QA report sections
- Whether to test edge cases (empty states, error states) or focus on happy paths

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QA-01 | All interactive elements tested via Chrome browser automation (clicks, forms, HTMX swaps) | Full MCP tool catalog below; 38 HTMX endpoints and 27 URL routes mapped as test targets |
</phase_requirements>

## Standard Stack

### Core
| Tool | Purpose | Why Standard |
|------|---------|--------------|
| Claude-in-Chrome MCP | Browser automation, screenshots, GIF recording | Zero-dependency, uses existing Chrome session with OAuth |
| pytest | Regression checking after fixes | Already in project (381+ tests) |

### MCP Tools Reference (21 tools available)

**Navigation & Interaction:**
| Tool | Parameters | Use For |
|------|-----------|---------|
| `navigate` | `url`, `tabId` | Go to pages, forward/back |
| `computer` | `action` (click/type/scroll/key/screenshot), `coordinate`, `tabId` | Click elements, type text, scroll, take screenshots |
| `find` | `query` (natural language), `tabId` | Find elements by description |
| `read_page` | `filter` (interactive/all), `tabId` | Get accessibility tree of page elements |
| `form_input` | `ref`, `value`, `tabId` | Set form values using element refs |

**Debugging:**
| Tool | Parameters | Use For |
|------|-----------|---------|
| `read_console_messages` | `tabId`, `onlyErrors`, `pattern`, `clear` | Check for JS errors, failed requests |
| `read_network_requests` | `tabId`, `urlPattern`, `clear` | Monitor HTMX requests, 404s, 500s |
| `javascript_tool` | `text`, `tabId` | Execute JS to check DOM state |

**Media & Recording:**
| Tool | Parameters | Use For |
|------|-----------|---------|
| `gif_creator` | `action` (start_recording/stop_recording/export), `tabId` | Record interaction flows |
| `resize_window` | `width`, `height`, `tabId` | Switch between desktop/mobile/tablet viewports |

**Tab Management:**
| Tool | Parameters | Use For |
|------|-----------|---------|
| `tabs_context_mcp` | `createIfEmpty` | Get tab info |
| `tabs_create_mcp` | none | Create new tab for testing |

### No Installation Required
This phase adds zero dependencies. All tools are built into the Claude-in-Chrome extension.

## Architecture Patterns

### Test Surface Inventory

**Email App Routes (17 endpoints):**
| Route | Method | HTMX? | Test Action |
|-------|--------|-------|-------------|
| `/emails/` | GET | Yes | List view, filters, pagination, view switching |
| `/emails/<pk>/detail/` | GET | Yes | Slide-out detail panel |
| `/emails/<pk>/assign/` | POST | Yes | Assignment dropdown |
| `/emails/<pk>/status/` | POST | Yes | Acknowledge/Close buttons |
| `/emails/<pk>/claim/` | POST | Yes | Claim button |
| `/emails/<pk>/accept-ai/` | POST | Yes | Accept AI suggestion |
| `/emails/<pk>/reject-ai/` | POST | Yes | Reject AI suggestion |
| `/emails/<pk>/whitelist-sender/` | POST | Yes | Whitelist from detail |
| `/emails/settings/` | GET | Yes | 6 tab settings page |
| `/emails/settings/rules/` | POST | Yes | Save assignment rules |
| `/emails/settings/visibility/` | POST | Yes | Save category visibility |
| `/emails/settings/sla/` | POST | Yes | Save SLA config |
| `/emails/settings/inboxes/` | POST | Yes | Save inbox config |
| `/emails/settings/config/` | POST | Yes | Save system config |
| `/emails/settings/webhooks/` | POST | Yes | Save webhook config |
| `/emails/settings/whitelist/add/` | POST | Yes | Add whitelist entry |
| `/emails/activity/` | GET | Yes | Activity log with filters |
| `/emails/inspect/` | GET | No | Dev inspector (read-only) |

**Account Routes (6 endpoints):**
| Route | Method | HTMX? | Test Action |
|-------|--------|-------|-------------|
| `/accounts/login/` | GET | No | Login page render |
| `/accounts/google/login/` | GET | No | Google OAuth redirect |
| `/accounts/team/` | GET | Yes | Team management |
| `/accounts/team/<pk>/toggle-active/` | POST | Yes | Activate/deactivate user |
| `/accounts/team/<pk>/change-role/` | POST | Yes | Change role dropdown |
| `/accounts/team/<pk>/toggle-visibility/` | POST | Yes | Toggle user visibility |

**Other:**
| Route | Purpose |
|-------|---------|
| `/health/` | Health endpoint (JSON) |
| `/admin/` | Django admin |

### HTMX Templates (17 files with hx- attributes)
| Template | hx- count | Key Interactions |
|----------|-----------|-----------------|
| `_email_detail.html` | 22 | Assign, status change, AI accept/reject, whitelist |
| `email_list.html` | 17 | Filter selects, view tabs, pagination, card clicks |
| `_user_row.html` | 12 | Toggle active, change role, categories |
| `_email_card.html` | 8 | Card click opens detail panel |
| `_email_list_body.html` | 4 | Pagination, list refresh |
| `activity_log.html` | 4 | Filter chips, date range, pagination |
| `_assignment_rules.html` | 4 | Rule form save |
| `_inboxes_tab.html` | 4 | Inbox config save |
| `_sla_config.html` | 4 | SLA config save |
| `_activity_feed.html` | 3 | Activity pagination |
| `_assign_dropdown.html` | 3 | User selection |
| `_webhooks_tab.html` | 3 | Webhook save |
| `_whitelist_tab.html` | 4 | Add/delete whitelist entries |
| `_config_editor.html` | 2 | Config key-value save |
| `_category_visibility.html` | 2 | Toggle visibility save |
| `base.html` | 1 | Navigation links |

### Recommended QA Order

**Wave 1: Phase 1+2 Verification (Priority)**
1. Email list -- verify BUG-01 (no XML in AI suggestions), BUG-05 (count updates on view switch)
2. Mobile email list -- verify BUG-03 (stacked filters), BUG-07 (toast positioning)
3. Mobile detail panel -- verify BUG-02 (slide-in, scroll lock, back button)
4. Activity page -- verify BUG-04 (chip truncation)
5. Page titles -- verify BUG-06 across all pages
6. Phase 2 UX features -- UX-01 through UX-05 (welcome banner, filter indicators, scroll-snap, keyboard nav, loading skeleton)

**Wave 2: General Sweep**
7. Email detail panel -- all interactions (assign, status, AI actions, whitelist)
8. Settings page -- all 6 tabs with form submissions
9. Team management -- toggle active, change role, categories
10. Activity log -- filters, date range, pagination

**Wave 3: Viewport Testing**
11. Resize to 375px -- mobile sweep of all pages
12. Resize to 768px -- tablet sweep of all pages

### QA Workflow Per Page
```
1. navigate to page
2. read_console_messages (clear: true) -- baseline
3. computer(action: screenshot) -- capture initial state
4. read_page(filter: interactive) -- catalog all interactive elements
5. For each interactive element:
   a. Click/interact with element
   b. read_console_messages(onlyErrors: true) -- check for errors
   c. read_network_requests -- verify HTMX responses (200, no 404/500)
   d. Verify expected DOM change occurred
6. computer(action: screenshot) -- capture final state
7. Log results to QA report
```

### Viewport Sizes
| Device | Width | Height | Use |
|--------|-------|--------|-----|
| Desktop | 1440 | 900 | Default testing |
| Tablet | 768 | 1024 | Responsive check |
| Mobile | 375 | 812 | Mobile layout check |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser automation | Playwright/Selenium scripts | Claude-in-Chrome MCP tools | Zero deps, uses real OAuth session |
| Screenshot comparison | Visual diff tooling | Human review of screenshots | 4-5 user app, not worth automation overhead |
| Test reporting | Custom HTML report | Markdown QA report | Simple, committable, readable |
| Console error parsing | Custom log analyzer | `read_console_messages(onlyErrors: true)` | Built into MCP tools |

## Common Pitfalls

### Pitfall 1: OAuth Session Expiry
**What goes wrong:** Google OAuth session expires mid-QA, all subsequent requests redirect to login
**Why it happens:** Long QA sessions exceed OAuth token lifetime
**How to avoid:** Check for login redirects after each navigation. If detected, pause and re-authenticate manually.
**Warning signs:** `read_network_requests` shows 302 redirects to `/accounts/login/`

### Pitfall 2: HTMX Partial vs Full Page Confusion
**What goes wrong:** Clicking an HTMX element triggers a full page reload instead of a partial swap
**Why it happens:** Missing `HX-Request` header, broken hx-target, or JS error preventing HTMX
**How to avoid:** After every HTMX interaction, check `read_network_requests` for the response and verify it was a partial (not full HTML document)
**Warning signs:** Page flash/reload, URL changes unexpectedly, scroll position resets

### Pitfall 3: Console Errors Swallowed Silently
**What goes wrong:** JavaScript errors or failed network requests don't show visual symptoms
**Why it happens:** HTMX and Tailwind degrade gracefully -- broken interactions just do nothing
**How to avoid:** `read_console_messages(onlyErrors: true)` after EVERY interaction, not just when something looks broken
**Warning signs:** Element click produces no visible change

### Pitfall 4: Mobile Viewport Not Actually Testing Mobile CSS
**What goes wrong:** `resize_window` changes viewport but page doesn't re-render mobile layout
**Why it happens:** Tailwind breakpoints need actual viewport change, not just window resize without reload
**How to avoid:** After `resize_window`, do a page reload to ensure CSS media queries re-evaluate
**Warning signs:** Desktop layout still showing at 375px width

### Pitfall 5: Fixing Bugs Without Running Tests
**What goes wrong:** Fix one bug, break three others
**Why it happens:** HTMX partials share templates; CSS changes cascade
**How to avoid:** `pytest -x` after every fix, before moving to next page
**Warning signs:** Template name appears in multiple URL handlers

### Pitfall 6: Testing Against Empty Database
**What goes wrong:** All pages show empty states, can't test real interactions
**Why it happens:** Live site might have no recent emails, or test against wrong environment
**How to avoid:** Verify data exists on live site before starting QA. If empty, run `test_pipeline` to seed data.
**Warning signs:** Email list shows "No emails found" on first load

## Code Examples

### QA Report Structure
```markdown
# QA Report: v2.3.4 UI/UX Polish

**Date:** YYYY-MM-DD
**Tester:** Claude (automated browser QA)
**Site:** triage.vidarbhainfotech.com

## Summary
- Pages tested: X/Y
- Interactions verified: N
- Bugs found: N (N fixed, N remaining)
- Console errors: N

## Phase 1+2 Verification
### BUG-01: AI Suggestion XML Markup
- **Status:** PASS/FAIL
- **Evidence:** [screenshot link]
- **Notes:** ...

[repeat for each BUG/UX item]

## Page-by-Page Results

### Email List (`/emails/`)
**Desktop (1440px)**
- [ ] Filter selects work (status, priority, assignee)
- [ ] View tabs switch (All, Unassigned, My Emails)
- [ ] Email count updates correctly
- [ ] Card click opens detail panel
- [ ] Pagination works
- **Console errors:** None / [list]
- **Screenshot:** [link]

**Mobile (375px)**
- [ ] Stacked filter layout
- [ ] Stat card scroll-snap
- [ ] Touch-friendly selects
- **Screenshot:** [link]

[repeat for each page]

## Bugs Found & Fixed
| # | Page | Issue | Fix | Commit |
|---|------|-------|-----|--------|
| 1 | ... | ... | ... | ... |

## Remaining Issues
None / [list with severity]
```

### Console Error Checking Pattern
```
After each navigation/interaction:
1. read_console_messages(onlyErrors: true, clear: true)
2. If errors found:
   a. Document in QA report
   b. Investigate root cause
   c. Fix if within scope
   d. Re-verify
```

### Network Request Monitoring Pattern
```
For HTMX interactions:
1. read_network_requests(clear: true) -- clear before interaction
2. Perform interaction (click/submit)
3. read_network_requests(urlPattern: "/emails/") -- check response
4. Verify: status 200, content-type text/html, partial (not full page)
```

## State of the Art

| Approach | Status | Notes |
|----------|--------|-------|
| Manual browser QA | Traditional | Time-consuming, inconsistent |
| Playwright/Selenium scripts | Standard for CI | Overkill here; needs separate auth setup |
| Claude-in-Chrome MCP | Current (beta) | Perfect fit: uses real session, zero deps, AI-driven |

## Open Questions

1. **Live site data availability**
   - What we know: Site is deployed at triage.vidarbhainfotech.com
   - What's unclear: Whether there are enough emails in the database to exercise all interactions (assign, status change, etc.)
   - Recommendation: Check on first navigation; if empty, note in QA report. `test_pipeline` can seed data but only on the server.

2. **OAuth session handling**
   - What we know: Claude-in-Chrome shares the browser's login state
   - What's unclear: Whether the session will persist through the entire QA run
   - Recommendation: Start QA by navigating to `/emails/` and verifying logged-in state. Re-authenticate manually if session drops.

3. **GIF recording quality**
   - What we know: `gif_creator` tool exists with start/stop/export
   - What's unclear: File size limits, frame rate, quality of recordings
   - Recommendation: Record key flows (login, email triage, mobile interactions) and assess quality. If poor, rely on screenshots.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + Django test client |
| Config file | `pytest.ini` (project root) |
| Quick run command | `pytest -x --tb=short` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QA-01 | All interactive elements work | manual-only (browser QA) | Claude-in-Chrome MCP walkthrough | N/A -- manual QA phase |

**Justification for manual-only:** QA-01 is inherently a manual browser verification task. The "test" IS the QA walkthrough itself. pytest serves only as regression check after fixes.

### Sampling Rate
- **Per bug fix:** `pytest -x --tb=short` (quick regression check)
- **Per wave completion:** `pytest -v` (full suite)
- **Phase gate:** Full pytest suite green + QA report complete

### Wave 0 Gaps
- [ ] `.planning/qa/` directory -- create for screenshots/GIFs
- [ ] Add `.planning/qa/` to `.gitignore` -- media files are ephemeral

## Sources

### Primary (HIGH confidence)
- [Claude in Chrome docs](https://code.claude.com/docs/en/chrome) -- official tool documentation, capabilities, troubleshooting
- [Chrome Extension Internals](https://gist.github.com/sshh12/e352c053627ccbe1636781f73d6d715b) -- complete MCP tool reference (21 tools, all parameters)
- Project codebase -- `apps/emails/urls.py`, `apps/accounts/urls.py`, template files

### Secondary (MEDIUM confidence)
- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) -- alternative tool reference
- [Browser automation comparison](https://dev.to/minatoplanb/i-tested-every-browser-automation-tool-for-claude-code-heres-my-final-verdict-3hb7) -- validated Claude-in-Chrome as best for authenticated sites

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Claude-in-Chrome is the only tool needed, well-documented
- Architecture: HIGH -- all test surfaces cataloged from project source code
- Pitfalls: HIGH -- common browser QA issues well-understood from docs and experience

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (Chrome extension is beta, may change)
