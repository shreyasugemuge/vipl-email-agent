# Domain Pitfalls: v2.5.0 Intelligence + UX

**Domain:** AI email triage intelligence layer
**Researched:** 2026-03-15

## Critical Pitfalls

### Pitfall 1: Feedback Loop Runaway
**What goes wrong:** AI corrections get injected into prompts, which changes future triages, which generates more corrections, which further shifts behavior in unpredictable directions.
**Why it happens:** Unbounded context injection without validation. A single incorrect user correction propagates.
**Consequences:** AI starts miscategorizing entire sender domains based on one bad correction.
**Prevention:**
- Cap injected corrections to last 10 per sender domain
- Only inject corrections with >= 2 occurrences (consensus, not one person's opinion)
- Add a `verified` flag on corrections (admin can mark corrections as authoritative)
- Log what context was injected for each triage (audit trail)
**Detection:** Confidence scores trending downward over time. Increased correction rate after deploying feedback loop.

### Pitfall 2: Auto-Assign Without Escape Hatch
**What goes wrong:** Auto-assigned emails pile up on one person because assignment rules favor them, and nobody notices because "the system handled it."
**Why it happens:** Category rules are static but email volume per category fluctuates.
**Consequences:** SLA breaches, one team member overwhelmed, others idle.
**Prevention:**
- Auto-assign still sends Chat notification (do NOT skip notification for auto-assigned)
- Dashboard shows auto-assigned vs manually-assigned counts
- Daily workload check: if one user has >60% of open emails, flag in EOD report
- Manager can always reassign (existing feature)
**Detection:** Uneven workload distribution visible in reports. SLA breach rate increasing for specific assignee.

### Pitfall 3: Read State N+1 Query
**What goes wrong:** Thread list annotates read state per-user, but naive implementation does one query per thread per user.
**Why it happens:** Checking `ThreadReadState.objects.filter(thread=t, user=request.user).exists()` in a template loop.
**Consequences:** Thread list page goes from 50ms to 500ms+.
**Prevention:**
- Use `Subquery` or `Exists` annotation in the queryset: `.annotate(is_read=Exists(ThreadReadState.objects.filter(thread=OuterRef('pk'), user=request.user, is_read=True)))`
- Single query, no N+1
**Detection:** Django Debug Toolbar showing excessive queries on thread list.

## Moderate Pitfalls

### Pitfall 4: Confidence Score Miscalibration
**What goes wrong:** Claude returns confidence 90+ for everything, making the threshold meaningless.
**Why it happens:** LLMs tend toward overconfidence unless explicitly instructed to be calibrated.
**Prevention:**
- Prompt instruction: "Be honest about uncertainty. Return confidence 50-70 for ambiguous emails. Reserve 80+ for clear-cut cases."
- Monitor confidence distribution in first week. If >80% of scores are above 80, adjust prompt.
- Start with auto-assign disabled (threshold 100) for first deployment. Enable after calibration.
**Detection:** Histogram of confidence scores in reports module.

### Pitfall 5: Spam Reputation Gaming
**What goes wrong:** A single user marks many emails from a legitimate sender as spam, poisoning the sender's reputation.
**Why it happens:** User error or misunderstanding (marking promotional emails from partners as spam).
**Prevention:**
- Require `total_count >= 3` before reputation affects filtering
- Admin can reset sender reputation
- WhiteList takes precedence over reputation (already the case)
- Log who made each spam feedback (accountability)
**Detection:** SenderReputation with high spam_count but sender domain is a known partner.

### Pitfall 6: Context Menu on Mobile
**What goes wrong:** Right-click context menu doesn't work on mobile (no right-click). Users on mobile can't access those actions.
**Why it happens:** Forgetting that context menus are desktop-only.
**Prevention:**
- All context menu actions MUST also be accessible from the detail panel (buttons)
- Context menu is a shortcut, not the only path to actions
- On mobile, long-press could trigger context menu (but don't over-engineer this)
**Detection:** Test on mobile during QA.

### Pitfall 7: Chart.js Memory Leak on HTMX Navigation
**What goes wrong:** Navigating away from reports page and back creates new Chart instances without destroying old ones.
**Why it happens:** HTMX swaps content but doesn't trigger `destroy()` on Chart.js instances.
**Prevention:**
- Use `htmx:beforeSwap` event to destroy chart instances before content is replaced
- Store chart instances in a global array, destroy all on page transition
```javascript
document.addEventListener('htmx:beforeSwap', function() {
    window._charts?.forEach(c => c.destroy());
    window._charts = [];
});
```
**Detection:** Memory usage growing in browser dev tools after navigating to/from reports.

## Minor Pitfalls

### Pitfall 8: Inline Edit Race Condition
**What goes wrong:** Two users edit the same thread's category simultaneously. Last write wins silently.
**Why it happens:** No optimistic concurrency control.
**Prevention:** With 4-5 users this is extremely unlikely. Accept last-write-wins. Log both changes in ActivityLog so the history is visible. ThreadViewer already shows who else is looking at a thread.

### Pitfall 9: Report Query Performance on Large Date Ranges
**What goes wrong:** "Last 365 days" report query takes several seconds.
**Why it happens:** No index on `created_at`, full table scan on large date ranges.
**Prevention:** Ensure `created_at` is indexed (it likely already is via `ordering`). For very large ranges, consider pre-aggregated daily summary table (but premature for current volume).

### Pitfall 10: CSV Export Timeout
**What goes wrong:** CSV export of all-time data times out on slow connections.
**Prevention:** Use `StreamingHttpResponse` (not `HttpResponse`). Limit export to date range (max 90 days per export).

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| AI confidence | Overconfidence from Claude (#4) | Calibration prompt + histogram monitoring |
| Auto-assign | Workload imbalance (#2) | Keep notifications, add workload check |
| Spam learning | Reputation gaming (#5) | Minimum count threshold, admin reset |
| Read/unread | N+1 queries (#3) | Subquery annotation, not template loop |
| Context menus | Mobile inaccessible (#6) | All actions also in detail panel |
| Reports | Chart.js memory leak (#7) | Destroy charts on HTMX navigation |
| Inline edit | Race condition (#8) | Accept last-write-wins at this scale |
