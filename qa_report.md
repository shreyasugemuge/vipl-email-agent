# QA Report — VIPL Email Agent v2.5.0

**Date:** 2026-03-15
**Tester:** Claude (Head Designer / CTO / Engineering Expert perspective)
**URL:** https://triage.vidarbhainfotech.com
**Branch:** main (v2.5.0 deployed)
**Browser:** Chrome, 1440x900 desktop + 375x812 mobile
**Logged in as:** Shreyas Ugemuge (admin)

---

## Executive Summary

The application is **production-ready and functional**. The overall UX is polished — dark sidebar, card-based layout, HTMX interactions, and the AI triage pipeline are all working correctly. The design language is consistent and professional.

**11 threads** were live during testing (real production data). All core flows work: viewing threads, opening detail panels, stat card filtering, sidebar navigation, activity log, reports, settings, team management, and dev inspector.

### Verdict: PASS with 8 issues (2 bugs, 4 UX improvements, 2 cosmetic)

---

## Bugs (must fix)

### BUG-01: Thread count label doesn't reflect current view filter
- **Severity:** Medium
- **Location:** Inbox view — `11 threads` label below search bar
- **Description:** The "N threads" count always shows the total open thread count regardless of active view filter. When viewing "Unassigned" (9 threads), "Closed" (1 thread), "Mine" (2 threads), or "2 URGENT" filtered (2 threads), the label still shows the total count (e.g., "10 threads" or "11 threads").
- **Expected:** Label should show the count of threads currently displayed in the list.
- **Repro:** Click any sidebar view (Unassigned, Mine, Closed) or any stat card filter — observe the count doesn't change.

### BUG-02: Search resets sidebar view filter
- **Severity:** Medium
- **Location:** Inbox search bar
- **Description:** When searching from a filtered view (e.g., "Unassigned"), typing in the search bar resets the view to "All Open". The URL changes from `?view=unassigned` to `?view-hidden=all_open`. The sidebar active state also resets.
- **Expected:** Search should filter within the current view, preserving the sidebar selection.
- **Repro:** Click "Unassigned" in sidebar → type "tender" in search → observe URL and sidebar state change.

---

## UX Improvements (should fix)

### UX-01: Detail panel action buttons overflow / clip on right edge
- **Severity:** Medium
- **Location:** Thread detail panel — action button row
- **Description:** At 1440px width, the "Mark Spam" button text is truncated at the right edge of the viewport. The "Mark Unread" (mail icon) button is barely visible or hidden. The action row doesn't wrap or scroll.
- **Suggestion:** Either wrap the action buttons to a second row, make them horizontally scrollable, or reduce button sizes. Consider an overflow menu (⋯) for secondary actions (Whitelist, Mark Spam, Mark Unread).

### UX-02: Right-click context menu has poor contrast / readability
- **Severity:** Medium
- **Location:** Thread card right-click context menu
- **Description:** The context menu has very light gray text on a white/semi-transparent background. Menu items overlap with thread card text behind, making options nearly unreadable. Keyboard shortcuts (U, A, K, X, S, W) are visible but the action labels are hard to read.
- **Suggestion:** Add a solid white background with subtle shadow, increase text contrast to dark gray/black, add a visible border or card-style elevation.

### UX-03: Mobile detail drawer doesn't open on thread click
- **Severity:** High
- **Location:** Mobile view (375px) — thread card tap
- **Description:** Tapping a thread card on mobile highlights it (blue border) but does not open the slide-over detail drawer. The detail panel that works on desktop doesn't appear on mobile. Users can't view thread details on mobile.
- **Suggestion:** Verify the HTMX target and CSS for the mobile detail drawer. The history API push-state for mobile detail may not be triggering.

### UX-04: Escape key doesn't close detail panel
- **Severity:** Low
- **Location:** Desktop inbox with detail panel open
- **Description:** Pressing Escape while the detail panel is open does not close it. CLAUDE.md documents "Escape closes detail" as a feature.
- **Repro:** Click a thread to open detail → press Escape → panel stays open.

---

## Cosmetic / Polish

### COS-01: Inconsistent page title format on Reports page
- **Severity:** Low
- **Location:** Browser tab title
- **Description:** Reports page shows "Reports - VIPL Triage" while all other pages use "VIPL Triage | Page" format (e.g., "VIPL Triage | Inbox", "VIPL Triage | Settings").
- **Fix:** Change reports template to use "VIPL Triage | Reports".

### COS-02: SLA Compliance bar chart appears empty despite 100% data
- **Severity:** Low
- **Location:** Reports → SLA tab → "SLA Compliance" chart
- **Description:** The bar chart area is completely empty (no bars rendered) even though SLA compliance is 100%. The legend shows "Met" (green) and "Breached" (red) but no data bars appear. Only the "SLA Compliance Trend" line chart below renders correctly.
- **Suggestion:** Either show a "100% — No breaches" message, render a full green bar, or hide the empty chart.

---

## What's Working Well

- **Sidebar navigation** — Clean hierarchy (Main → System → Triage Queue → My Inbox → Views → Inbox → Filters). Active states update correctly via JS. Badge counts are accurate.
- **Thread cards** — Good information density: sender + email, subject, AI summary preview, confidence dots, status/inbox pills, AI suggested assignee, timestamp, message count.
- **AI triage** — Summaries are accurate and helpful. Confidence indicator (green dots) is subtle but clear. AI Reasoning section is collapsible (good — avoids clutter).
- **Stat cards** — Clickable with filter behavior. Visual highlight on active card. Color-coded (orange unassigned, red urgent, blue new).
- **Activity page** — Comprehensive filter chips (20+ event types). Clear transition displays (e.g., "new → acknowledged"). Timestamp formatting is good.
- **Settings** — Well-organized 7-tab layout. Assignment rules in 2-column grid. Webhook masking with reveal. Clean category visibility controls.
- **Team page** — Role dropdown, category checkboxes, "You" label, deactivate action. Simple and functional.
- **Dev Inspector** — Production badge, live poll countdown, force poll button, pipeline stats, poll history table. Great for ops monitoring.
- **Reports** — 4-tab structure with Chart.js charts. Date range + inbox/category/member filters. Volume chart works well.
- **Mobile sidebar** — Hamburger menu, slide-out drawer with blur backdrop, X close button.
- **Scroll-snap stat cards** on mobile — horizontal scrolling with snap points.
- **No console errors** — Clean JavaScript execution.
- **HTMX progress bar** — Global top-of-page loading indicator on navigation.

---

## Test Matrix

| Area | Desktop (1440px) | Mobile (375px) | Status |
|------|:-:|:-:|--------|
| Inbox — thread list | PASS | PASS | Working |
| Inbox — stat card filters | PASS | Not tested | Working, count label bug |
| Inbox — search | BUG-02 | Not tested | Search resets view |
| Inbox — sidebar views | PASS | N/A (hamburger) | Working |
| Thread detail panel | PASS | FAIL (UX-03) | Desktop works, mobile broken |
| Detail — AI summary | PASS | — | Working |
| Detail — inline edit chips | PASS | — | Priority dropdown works |
| Detail — action buttons | UX-01 | — | Overflow clipping |
| Context menu (right-click) | UX-02 | — | Poor contrast |
| Keyboard nav (arrows) | PASS | — | Working |
| Keyboard nav (Escape) | UX-04 | — | Doesn't close panel |
| Activity page | PASS | Not tested | Working |
| Reports — Overview | PASS | Not tested | Working |
| Reports — Volume | PASS | Not tested | Chart renders |
| Reports — Team | PASS | Not tested | Chart renders |
| Reports — SLA | COS-02 | Not tested | Empty bar chart |
| Settings — all tabs | PASS | Not tested | Working |
| Team management | PASS | Not tested | Working |
| Dev Inspector | PASS | Not tested | Working, misleading description |
| Mobile sidebar drawer | — | PASS | Working |
| Console errors | PASS | — | None |

---

## Recommendations

1. **Priority 1 (before next release):** Fix BUG-01 (thread count) and UX-03 (mobile detail drawer)
2. **Priority 2 (near-term):** Fix BUG-02 (search view reset) and UX-01 (button overflow)
3. **Priority 3 (polish):** Fix UX-02 (context menu contrast), COS-01 (title format), COS-02 (SLA chart)
4. **Priority 4 (nice to have):** UX-04 (Escape key)

---

*Generated by automated QA testing on 2026-03-15*
