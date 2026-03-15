# Phase 7: QA Cosmetic & Layout - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 3 cosmetic/layout issues from QA report: detail panel button overflow (#33), reports page title format (#37), and SLA chart rendering at 100% compliance (#38).

</domain>

<decisions>
## Implementation Decisions

### QA-05: Detail panel action buttons overflow (#33)
- Root cause: action bar uses `flex items-center justify-between gap-3` without wrapping — at 1440px, Mark Spam clips and Mark Unread hides
- Fix: **flex-wrap to second row** — add `flex-wrap` so buttons wrap naturally when space is limited
- Row 1: Assignment controls (dropdown + note + assign button) + status action (Acknowledge/Close)
- Row 2: Secondary actions (Whitelist Sender, Mark Spam, Mark Unread) wrap below
- CSS-only fix, no JS needed

### QA-06: Reports page title inconsistent (#37)
- Root cause: `reports.html` line 2 uses `Reports - VIPL Triage` while all others use `VIPL Triage | Page`
- Fix: change to `{% block title %}VIPL Triage | Reports{% endblock %}` — one-line fix

### QA-07: SLA donut chart empty at 100% (#38)
- The SLA tab has a doughnut chart (`type: 'doughnut'`) with data `[met, breached]`
- When breached=0, Chart.js may not render the zero segment properly
- Fix: **full green donut** — when breached is 0, either filter out the zero-value dataset entry or replace 0 with a tiny epsilon value so Chart.js renders a complete green ring with "100%" center text
- Also handle the edge case where both met and breached are 0 (no SLA data) — show "No SLA data" message

### Claude's Discretion
- Exact gap/padding adjustments for wrapped button rows
- SLA "no data" message styling
- Whether epsilon hack or dataset filtering is cleaner for Chart.js zero-value handling

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above and GitHub issues #33, #37, #38.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_thread_detail.html` — action bar section (lines 115-258): outer div is `flex items-center justify-between gap-3`
- `reports.html` — title block (line 2), SLA tab doughnut chart (lines 496-518), center text plugin (lines 283-301)
- Chart.js `createChart()` wrapper with destroy-on-navigate cleanup

### Established Patterns
- Title format: `VIPL Triage | {Page}` in all pages except reports (the bug)
- Donut chart center text rendered via custom `centerText` plugin using `chart.config._pct`
- Empty state messages used in breaches table (line 570: "No SLA breaches in this period")

### Integration Points
- `templates/emails/_thread_detail.html` — QA-05 (action bar div at line 116)
- `templates/emails/reports.html` — QA-06 (line 2), QA-07 (initSLA function)
- `apps/emails/services/reports.py` — SLA data source (may return met=N, breached=0)

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
