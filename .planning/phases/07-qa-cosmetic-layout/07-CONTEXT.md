# Phase 7: QA Cosmetic & Layout - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 3 cosmetic/layout issues from QA report (#39): detail panel button overflow, reports page title format, and SLA chart rendering at 100% compliance.

</domain>

<decisions>
## Implementation Decisions

### QA-05: Detail panel action buttons overflow (#33)
- Root cause: action buttons (Assign dropdown, Whitelist, Mark Spam, Mark Unread) are in a flex row that doesn't wrap at 1440px viewport width
- Fix: add `flex-wrap: wrap` and/or reduce button padding, or convert to a more compact layout (icon-only for some actions, tooltip on hover)
- Claude's discretion on exact approach — key requirement is nothing clips or overflows

### QA-06: Reports page title inconsistent (#37)
- Root cause: `reports.html` line 2: `{% block title %}Reports - VIPL Triage{% endblock %}`
- All other pages use `VIPL Triage | Page` format
- Fix: change to `{% block title %}VIPL Triage | Reports{% endblock %}` — one-line fix

### QA-07: SLA chart empty at 100% (#38)
- The SLA tab has a **doughnut** chart (not bar) — `type: 'doughnut'` with data `[met, breached]`
- When `met > 0, breached = 0`: Chart.js renders a full green ring — this should work
- When both are 0 (no SLA data): doughnut renders as empty — this is likely the actual bug
- Also check the **trend line chart** — if `slaData.trend` is empty, the chart area is blank
- Fix: handle zero-data edge cases — show "No SLA data" message when both met and breached are 0, and handle empty trend array gracefully

### Claude's Discretion
- Button overflow: icon-only vs wrap vs smaller padding — whatever prevents clipping
- SLA chart: exact "no data" message styling
- Whether to add a "100% Compliant" center label to the donut when breached=0

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above and GitHub issues #33, #37, #38.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_thread_detail.html` — action buttons section (~line 190-230)
- `reports.html` — title block (line 2), SLA tab (line 224-564)
- Chart.js createChart() wrapper with destroy-on-navigate cleanup

### Established Patterns
- Title format: `VIPL Triage | {Page}` in all pages except reports
- Donut chart center text rendered via custom plugin (`_pct` property)
- Empty state messages used elsewhere (poll history, breaches table)

### Integration Points
- `templates/emails/_thread_detail.html` — QA-05
- `templates/emails/reports.html` — QA-06, QA-07
- `apps/emails/services/reports.py` — SLA data source (may return zeros)

### Key Files
- `templates/emails/_thread_detail.html` — QA-05
- `templates/emails/reports.html` — QA-06, QA-07

</code_context>

<specifics>
## Specific Ideas

No specific requirements — straightforward cosmetic fixes from QA report.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-qa-cosmetic-layout*
*Context gathered: 2026-03-15*
