# Technology Stack: v2.5.0 Intelligence + UX

**Project:** VIPL Email Agent
**Researched:** 2026-03-15
**Scope:** Additions only -- existing stack (Django 4.2, HTMX 2.0, Tailwind v4, Anthropic SDK, etc.) is validated and unchanged.

## Recommended Additions

### Zero New Dependencies

The headline finding: **v2.5.0 needs zero new Python packages and zero new JS libraries**. Every feature can be built with what is already in the stack plus vanilla JS and Django ORM patterns. This is intentional -- the existing stack was chosen for its simplicity and adding dependencies for 4-5 users would be over-engineering.

---

## Feature-by-Feature Stack Analysis

### 1. AI Confidence Scoring + Auto-Assignment Feedback

**What's needed:** Claude returns a confidence score with each triage, auto-assign triggers above threshold, user corrections feed back into prompt context.

**Stack addition: NONE.**

| Concern | Solution | Why |
|---------|----------|-----|
| Confidence score | Add `confidence` field to `TriageResult` DTO + prompt instruction | Claude already returns structured JSON; add a `confidence: 0-100` field to the prompt schema |
| Storage | `FloatField` on `Email` and `Thread` models | Standard Django field, no library needed |
| Auto-assign threshold | `SystemConfig` key `auto_assign_confidence_threshold` (default: 80) | Already have runtime config store |
| Feedback loop | Store corrections in `ActivityLog` (action=`CATEGORY_CORRECTED`, `PRIORITY_CORRECTED`) | Already have append-only activity log model |
| Prompt context injection | Query recent corrections, inject as few-shot examples in system prompt | `ai_processor.py` already does team workload injection; same pattern |

**How the feedback loop works without ML:**
1. Claude returns `confidence: 85, category: "Sales Lead"` in structured output
2. If confidence >= threshold AND assignment rule exists -> auto-assign
3. If user corrects category/priority -> `ActivityLog` records old/new values
4. On next triage, query last N corrections for that sender/domain -> inject as context: "Note: emails from acme.com were previously recategorized from X to Y"
5. This is prompt engineering, not ML. Claude adapts from context window, not model weights.

**Confidence:** HIGH -- prompt-based confidence scoring is a well-established pattern with LLMs. The Anthropic SDK already parses structured JSON responses in this codebase.

### 2. Spam Feedback Learning

**What's needed:** Users mark emails as spam/not-spam, system learns sender and pattern reputation over time.

**Stack addition: NONE.**

| Concern | Solution | Why |
|---------|----------|-----|
| User corrections | New model `SpamFeedback(email, user, action, created_at)` where action is `mark_spam` or `mark_not_spam` | Simple Django model, 4 fields |
| Sender reputation | New model `SenderReputation(address, domain, spam_count, ham_count, last_updated)` | Aggregated stats from feedback, no ML |
| Pattern learning | When user marks spam: extract sender domain, increment `spam_count`. If `spam_count / total > 0.8` and total >= 3 -> add to spam patterns | Rule-based threshold, stored in DB |
| Whitelist integration | `mark_not_spam` on whitelisted sender -> already handled by existing `SpamWhitelist` model | v2.2 already built this |
| Spam filter enhancement | `spam_filter.py` checks `SenderReputation` before regex patterns | Pure Python, no Django imports needed if reputation is passed as param |

**Why NOT use scikit-learn or similar:**
- 4-5 users, ~50-100 emails/day. Statistical ML needs thousands of labeled examples.
- Rule-based reputation (sender domain spam ratio) is more transparent and debuggable.
- Claude AI already handles nuanced spam detection -- this is just learning from corrections to the regex pre-filter.

**Confidence:** HIGH -- sender reputation scoring is a well-understood pattern (SpamAssassin uses similar approach). No external dependencies needed.

### 3. Per-User Read/Unread Tracking

**What's needed:** Each user sees which threads they have/haven't read. Mark as unread support.

**Stack addition: NONE.**

| Concern | Solution | Why |
|---------|----------|-----|
| Read state storage | New model `ThreadReadState(thread, user, read_at, is_read)` with `unique_together` | Standard through-table pattern for per-user state |
| Mark as read | On detail panel open (already tracked via `ThreadViewer`), upsert `ThreadReadState` | Piggyback on existing viewer tracking |
| Mark as unread | POST endpoint, sets `is_read=False` on `ThreadReadState` | Simple HTMX button |
| Unread count | `Thread.objects.exclude(read_states__user=user, read_states__is_read=True).count()` | Django ORM query, no special library |
| Visual indicator | Bold text + dot indicator on unread cards (CSS only) | Tailwind classes, conditional in template |
| Bulk mark read | Select multiple + POST, standard HTMX multi-select pattern | Already have card selection CSS |

**Design choice: `ThreadReadState` model vs. JSONField on User:**
- Model is correct. JSONField would grow unbounded and can't be queried efficiently.
- `ThreadReadState` can be indexed, queried with joins, and cleaned up (delete old read states for soft-deleted threads).
- PostgreSQL handles this fine at scale -- even 1M read-state rows is trivial.

**Confidence:** HIGH -- this is a textbook Django M2M-through pattern. No novel design needed.

### 4. Right-Click Context Menu

**What's needed:** Right-click on email/thread card shows actions (assign, change status, mark spam, mark read/unread).

**Stack addition: NONE.** Vanilla JS + HTMX.

| Concern | Solution | Why |
|---------|----------|-----|
| Trigger | `hx-trigger="contextmenu"` is supported natively by HTMX (standard DOM event) | Confirmed via HTMX GitHub issue #1941 -- works out of the box |
| Menu rendering | Server-rendered partial template `_context_menu.html` loaded via HTMX | Consistent with existing partial pattern (`_assign_dropdown.html`, etc.) |
| Positioning | ~15 lines of vanilla JS to position at cursor coordinates | `event.clientX/Y` + boundary detection |
| Dismiss | Click-outside listener (vanilla JS, `document.addEventListener`) | Standard pattern, no library |
| Actions | Each menu item is an HTMX-powered button/link (POST with `hx-target`) | Same pattern as existing assign/status buttons |

**Implementation pattern:**
```html
<!-- On the card -->
<div hx-trigger="contextmenu"
     hx-get="/emails/{{ thread.pk }}/context-menu/"
     hx-target="#context-menu"
     hx-swap="innerHTML"
     oncontextmenu="positionMenu(event); return false;">
```

```html
<!-- _context_menu.html partial -->
<div id="context-menu" class="absolute z-50 bg-white shadow-lg rounded-lg border py-1 w-48">
  <button hx-post="/emails/{{ thread.pk }}/assign/" ...>Assign to...</button>
  <button hx-post="/emails/{{ thread.pk }}/status/" ...>Change Status</button>
  <hr>
  <button hx-post="/emails/{{ thread.pk }}/mark-spam/">Mark as Spam</button>
  <button hx-post="/emails/{{ thread.pk }}/toggle-read/">Mark as Unread</button>
</div>
```

**Why NOT use a JS context menu library (e.g., vanilla-context-menu, @radix-ui):**
- Server-rendered menus are more secure (actions validated server-side).
- Consistent with the HTMX-first architecture -- menu content comes from server.
- No build step, no npm, no bundle.
- ~30 lines of vanilla JS total (positioning + dismiss).

**Confidence:** HIGH -- HTMX contextmenu trigger is confirmed working. The partial template pattern is already used extensively in this codebase.

### 5. Inline-Editable Form Fields

**What's needed:** Click on category/priority on thread detail to edit inline without page navigation.

**Stack addition: NONE.** HTMX click-to-edit is a documented pattern.

| Concern | Solution | Why |
|---------|----------|-----|
| Pattern | HTMX "Click to Edit" (official example at htmx.org/examples/click-to-edit/) | Well-documented, battle-tested |
| Display mode | Static text with pencil icon, `hx-get` to fetch edit form partial | Same as existing HTMX partials |
| Edit mode | Server-rendered `<select>` or `<input>` with `hx-put`/`hx-post` | Django form or manual HTML |
| Save | POST to endpoint, returns updated display partial via HTMX swap | Standard HTMX response pattern |
| Cancel | Escape key or click-outside, re-fetches display partial | `hx-trigger="keyup[key=='Escape']"` or vanilla JS |
| Validation | Server-side via Django (return form with errors if invalid) | Already have inline save feedback pattern from settings |
| Activity log | Record change in `ActivityLog` (action=`CATEGORY_CORRECTED` etc.) | Feeds into confidence feedback loop (feature #1) |

**Fields to make editable:**
- Category (dropdown from `VALID_CATEGORIES`)
- Priority (dropdown from `VALID_PRIORITIES`)
- Assigned to (dropdown from active users -- already exists as `_assign_dropdown.html`)

**Confidence:** HIGH -- HTMX click-to-edit is an official documented pattern. Django-htmx-patterns repo has complete Django examples.

### 6. Analytics/Reporting Dashboard with Charts

**What's needed:** MIS reports page with volume trends, category breakdown, response times, team performance.

**Stack addition: Chart.js 4.5.x via CDN only.**

| Concern | Solution | Why |
|---------|----------|-----|
| Chart library | Chart.js 4.5.1 via jsDelivr CDN | Already planned per PROJECT.md. No build step. Most popular charting library. |
| CDN tag | `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>` | Pin version for reproducibility (not `@latest`) |
| Data source | Django views return JSON via `JsonResponse` or inline `<script>` with template data | No REST API framework needed for 4-5 users |
| Chart types | Line (volume over time), Doughnut (category split), Bar (team workload), Horizontal bar (response times) | All native Chart.js types, no plugins needed |
| Date filtering | URL params (`?period=7d&from=2026-03-01`), parsed in Django view | Same URL-based filtering pattern as email list |
| Aggregation | Django ORM aggregation (`annotate`, `Count`, `Avg`, `TruncDate`) | PostgreSQL handles this natively, no need for a reporting library |
| Export | CSV download endpoint (Django `StreamingHttpResponse` with `csv` module) | Python stdlib, no library needed |
| Date picker | HTML5 `<input type="date">` with HTMX `hx-get` on change | No JS date picker library needed |

**Why NOT use a heavier solution (Metabase, Apache Superset, django-report-builder):**
- 4-5 users. A full BI tool is absurd.
- Chart.js CDN + Django ORM aggregation covers every chart type needed.
- Reports are internal MIS, not customer-facing analytics.
- Zero infrastructure (no Redis, no Celery, no separate service).

**Key Chart.js notes for this project:**
- Chart.js 4.x uses tree-shakeable ESM, but the UMD build (`chart.umd.min.js`) works with `<script>` tags and is ~70KB gzipped.
- No date adapter needed unless using time-series x-axis with Date objects. For this project, format dates server-side as strings.
- Chart.js 4.x dropped IE support (irrelevant for this project).

**Confidence:** HIGH -- Chart.js 4.5.1 is stable, CDN delivery is straightforward, and Django ORM aggregation is well-documented.

---

## Alternatives Considered

| Feature | Recommended | Alternative Considered | Why Not |
|---------|-------------|----------------------|---------|
| Confidence scoring | Prompt engineering (Claude JSON output) | scikit-learn classifier | 50 emails/day is not enough training data; Claude already understands context |
| Spam learning | Sender reputation model (DB counters) | Bayesian classifier (nltk/sklearn) | Over-engineering for 4-5 users; rule-based is transparent and debuggable |
| Read/unread | `ThreadReadState` Django model | Redis sorted sets | Adding Redis for 4-5 users is unjustified infrastructure |
| Context menu | Vanilla JS + HTMX partial | vanilla-context-menu npm package | Adds npm/build step; server-rendered menus are more secure |
| Inline edit | HTMX click-to-edit pattern | Alpine.js or React component | Already committed to HTMX-only; Alpine adds a second reactive framework |
| Charts | Chart.js 4.5.1 CDN | D3.js, ApexCharts, Recharts | D3 is too low-level; ApexCharts is heavier; Recharts needs React |
| CSV export | Python `csv` stdlib | django-import-export | Adding a dependency for one CSV download endpoint is wasteful |
| Date picker | HTML5 `<input type="date">` | flatpickr, Pikaday | Native HTML5 is sufficient; all modern browsers support it |

---

## Complete Dependency Change

### requirements.txt: NO CHANGES

The existing `requirements.txt` remains exactly as-is. No new Python packages.

### Frontend: ONE addition

```html
<!-- Add to base.html or reports page only -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"
        integrity="sha384-[integrity-hash]"
        crossorigin="anonymous"></script>
```

Load Chart.js only on the reports page (not globally) to avoid unnecessary payload on the main dashboard.

### Vanilla JS additions (~100 lines total across all features)

| Feature | JS Needed | Lines (est.) |
|---------|-----------|-------------|
| Context menu positioning + dismiss | `positionMenu()`, click-outside listener | ~30 |
| Inline edit cancel (Escape key) | Event listener on edit forms | ~10 |
| Chart initialization | `new Chart(ctx, config)` per chart | ~50 |
| Read/unread visual toggle | CSS class toggle (optional, HTMX swap handles most) | ~10 |

---

## New Django Models Summary

| Model | Fields | Purpose |
|-------|--------|---------|
| `ThreadReadState` | thread (FK), user (FK), read_at (DateTime), is_read (Bool) | Per-user read/unread tracking |
| `SpamFeedback` | email (FK), user (FK), action (CharField), created_at (auto) | User spam/not-spam corrections |
| `SenderReputation` | address, domain, spam_count, ham_count, last_updated | Aggregated sender trust score |

**Model additions to existing models:**
- `Email`: add `ai_confidence` (FloatField, default=0.0)
- `Thread`: add `ai_confidence` (FloatField, default=0.0)
- `TriageResult` DTO: add `confidence` (float, default=0.0)

**New `ActivityLog.Action` choices:**
- `CATEGORY_CORRECTED` -- user changed category
- `PRIORITY_CORRECTED` -- user changed priority
- `MARKED_SPAM` -- user marked as spam
- `MARKED_NOT_SPAM` -- user marked as not-spam
- `MARKED_UNREAD` -- user marked as unread

---

## Integration Points with Existing Stack

| Existing Component | How New Features Integrate |
|-------------------|---------------------------|
| `ai_processor.py` | Add `confidence` to prompt schema + parse from response |
| `spam_filter.py` | Check `SenderReputation` before regex (pass as param to keep Django-free) |
| `pipeline.py` | Save `ai_confidence` to Email/Thread, check auto-assign threshold |
| `assignment.py` | Auto-assign when confidence >= threshold + rule exists |
| `SystemConfig` | New keys: `auto_assign_confidence_threshold`, `spam_reputation_threshold` |
| `ActivityLog` | New action types for corrections, spam feedback, read state |
| `_thread_card.html` | Add unread indicator (bold + dot), `hx-trigger="contextmenu"` |
| `_thread_detail.html` | Add click-to-edit on category/priority fields |
| `views.py` | New views: context menu partial, inline edit endpoints, reports page, read-state toggle |
| `urls.py` | New URL patterns for above endpoints |
| `base.html` | Chart.js script tag (conditional, reports page only) |

---

## What NOT to Add

| Temptation | Why Resist |
|-----------|-----------|
| Django REST Framework | No SPA, no mobile app, no external API consumers. HTMX partials are the API. |
| Celery + Redis | 4-5 users, APScheduler already handles background tasks. No queue needed. |
| Alpine.js | Already have HTMX. Two reactive frameworks = confusion. Vanilla JS for the ~100 lines needed. |
| pandas / numpy | Django ORM `annotate()` + `TruncDate` handles all reporting aggregation. |
| django-tables2 | Reports are charts, not paginated tables. HTML tables with Tailwind for any tabular data. |
| django-filter | URL params parsed manually in views (already the pattern). 4 filter fields don't justify a library. |
| Any npm package | No `package.json`, no `node_modules`, no build step. CDN scripts only. |

---

## Sources

- [Chart.js Installation Docs](https://www.chartjs.org/docs/latest/getting-started/installation.html) -- CDN usage, version 4.5.1 confirmed
- [Chart.js Releases](https://github.com/chartjs/Chart.js/releases) -- latest stable version
- [HTMX Click to Edit Example](https://htmx.org/examples/click-to-edit/) -- official inline edit pattern
- [HTMX contextmenu Issue #1941](https://github.com/bigskysoftware/htmx/issues/1941) -- confirmed standard DOM event works natively
- [django-htmx-patterns](https://github.com/spookylukey/django-htmx-patterns) -- Django + HTMX form patterns
- [HTMX hx-on Attribute](https://htmx.org/attributes/hx-on/) -- custom event handling
