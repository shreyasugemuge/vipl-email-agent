# Architecture Patterns: v2.5.0 Intelligence + UX

**Domain:** AI email triage -- intelligence layer additions
**Researched:** 2026-03-15

## New Component Boundaries

No new services or containers. All features integrate into existing components.

| Component | New Responsibility | Communicates With |
|-----------|-------------------|-------------------|
| `ai_processor.py` | Parse confidence score from Claude response | `pipeline.py` (passes confidence to save) |
| `spam_filter.py` | Check sender reputation before regex | `pipeline.py` (receives reputation data as param) |
| `pipeline.py` | Save confidence, check auto-assign threshold | `assignment.py`, models |
| `assignment.py` | Auto-assign when confidence >= threshold | `ActivityLog`, `ChatNotifier` |
| `views.py` | Context menu, inline edit, read-state, reports endpoints | Templates, models |
| New: `reports.py` (in services/) | Report data aggregation queries | Django ORM, returns dicts for views |

## Data Flow: AI Confidence + Feedback Loop

```
Email arrives
  -> spam_filter.py (check SenderReputation + regex)
  -> ai_processor.py (Claude returns JSON with confidence: 0-100)
  -> pipeline.py saves Email with ai_confidence
  -> IF confidence >= threshold AND AssignmentRule exists:
       -> assignment.py auto-assigns (logs AUTO_ASSIGNED)
     ELSE:
       -> Thread stays unassigned (manual assignment)

User corrects category/priority:
  -> views.py inline-edit endpoint
  -> ActivityLog records CATEGORY_CORRECTED (old_value, new_value)
  -> Thread.category updated

Next triage for same sender/domain:
  -> ai_processor.py queries recent corrections for sender
  -> Injects as context: "Previous corrections: [sender] was recategorized from X to Y"
  -> Claude adjusts based on context (prompt engineering, not retraining)
```

## Data Flow: Spam Feedback Learning

```
User clicks "Mark as Spam" (on a non-spam email):
  -> SpamFeedback(email, user, action="mark_spam") created
  -> SenderReputation.spam_count incremented for sender domain
  -> Email.is_spam = True, Email.status = "closed"
  -> IF SenderReputation.spam_ratio > 0.8 AND total >= 3:
       -> Auto-add domain to SPAM_PATTERNS (or new SpamBlacklist model)

User clicks "Not Spam" (on a spam-filtered email):
  -> SpamFeedback(email, user, action="mark_not_spam") created
  -> SenderReputation.ham_count incremented
  -> Email.is_spam = False, processing re-triggered through AI
  -> IF sender already in SpamWhitelist: no-op
  -> IF repeated not-spam for same sender: suggest whitelisting
```

## Data Flow: Read/Unread

```
User opens thread detail panel (existing HTMX flow):
  -> ThreadViewer upserted (already exists)
  -> ThreadReadState upserted: is_read=True, read_at=now()
  -> Card in list gets "read" CSS class (via OOB swap or next list refresh)

User clicks "Mark as Unread":
  -> POST /emails/<pk>/toggle-read/
  -> ThreadReadState.is_read = False
  -> Card gets "unread" CSS class
  -> Response: HTMX swaps card partial with unread styling

Thread list query:
  -> Annotate with read state: .annotate(is_read=Subquery(ThreadReadState...))
  -> Template: {% if not thread.is_read %}<span class="unread-dot"></span>{% endif %}
```

## Patterns to Follow

### Pattern 1: Prompt Schema Extension (for confidence)

**What:** Add a field to the Claude JSON response schema without breaking existing parsing.

**When:** Adding any new AI output field.

**Example:**
```python
# In ai_processor.py, extend the response format instruction:
RESPONSE_FORMAT = """
{
  "category": "...",
  "priority": "...",
  "confidence": 85,  // NEW: 0-100 how confident you are
  "summary": "...",
  ...
}
"""

# Parse with fallback for backwards compatibility:
confidence = parsed.get("confidence", 50)  # default 50 if missing
```

### Pattern 2: HTMX Click-to-Edit

**What:** Display field as text, click to load edit form, save returns display partial.

**When:** Any inline-editable field.

**Example:**
```html
<!-- Display mode -->
<span id="category-{{ thread.pk }}"
      hx-get="/emails/{{ thread.pk }}/edit-category/"
      hx-trigger="click"
      hx-target="this"
      hx-swap="outerHTML"
      class="cursor-pointer hover:bg-gray-100 px-2 py-1 rounded">
    {{ thread.category }}
    <svg class="inline w-3 h-3 text-gray-400"><!-- pencil icon --></svg>
</span>

<!-- Edit mode (returned by server) -->
<form hx-post="/emails/{{ thread.pk }}/edit-category/"
      hx-target="this"
      hx-swap="outerHTML">
    <select name="category">
        {% for cat in categories %}
        <option {% if cat == thread.category %}selected{% endif %}>{{ cat }}</option>
        {% endfor %}
    </select>
    <button type="submit">Save</button>
    <button hx-get="/emails/{{ thread.pk }}/category-display/"
            hx-target="this" hx-swap="outerHTML closest form">Cancel</button>
</form>
```

### Pattern 3: Server-Rendered Context Menu

**What:** Right-click loads a positioned menu partial from server.

**When:** Card-level bulk actions.

**Example:**
```javascript
// ~30 lines in base.html or email_list.html
function positionMenu(event) {
    event.preventDefault();
    const menu = document.getElementById('context-menu');
    menu.style.left = Math.min(event.clientX, window.innerWidth - 200) + 'px';
    menu.style.top = Math.min(event.clientY, window.innerHeight - 300) + 'px';
    menu.classList.remove('hidden');
}

document.addEventListener('click', () => {
    document.getElementById('context-menu')?.classList.add('hidden');
});
```

### Pattern 4: Report Aggregation Service

**What:** Separate service module for report queries, keeping views thin.

**When:** Any complex ORM aggregation.

**Example:**
```python
# services/reports.py (Django imports: YES)
from django.db.models import Count
from django.db.models.functions import TruncDate

def volume_by_date(days=30, inbox=None):
    qs = Thread.objects.filter(created_at__gte=cutoff)
    if inbox:
        qs = qs.filter(emails__to_inbox=inbox)
    return list(
        qs.annotate(date=TruncDate('created_at'))
          .values('date')
          .annotate(count=Count('id'))
          .order_by('date')
    )
```

### Pattern 5: Django json_script for Chart Data

**What:** Pass Python data to Chart.js safely without a REST API.

**When:** Rendering charts on server-rendered pages.

**Example:**
```html
<!-- In template -->
{{ chart_data|json_script:"volume-data" }}

<canvas id="volumeChart"></canvas>
<script>
const data = JSON.parse(document.getElementById('volume-data').textContent);
new Chart(document.getElementById('volumeChart'), {
    type: 'line',
    data: { labels: data.labels, datasets: [{ data: data.values }] }
});
</script>
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Client-Side State for Read/Unread
**What:** Storing read state in localStorage or cookies.
**Why bad:** Not synced across devices/browsers. Lost on cache clear. Can't query server-side.
**Instead:** Database model with per-user FK. Query with Django ORM.

### Anti-Pattern 2: Separate REST API for Reports
**What:** Building DRF endpoints that return JSON consumed by a JS SPA.
**Why bad:** Two rendering paradigms (server templates + client JSON). Maintenance burden.
**Instead:** Django views return HTML with embedded Chart.js data via `json_script` template tag.

### Anti-Pattern 3: Eager Feedback Injection
**What:** Injecting ALL historical corrections into every AI triage prompt.
**Why bad:** Token bloat, prompt confusion, cost increase.
**Instead:** Query only corrections for the specific sender domain, limited to last 10 corrections.

### Anti-Pattern 4: ML Pipeline for Spam
**What:** Training a Bayesian classifier or neural network on the spam corpus.
**Why bad:** Not enough data, needs retraining infrastructure, black box.
**Instead:** Sender reputation counters (transparent, debuggable, no training step).

## Scalability Considerations

Not a concern. 4-5 users, 50-100 emails/day, single VM.

| Concern | Current (100/day) | If 1000/day | Notes |
|---------|-------------------|-------------|-------|
| ThreadReadState rows | ~500/month | ~5K/month | Trivial for PostgreSQL |
| SenderReputation rows | ~200 unique senders | ~2K senders | Index on domain |
| Report queries | < 100ms | < 500ms | Add DB indexes on created_at if needed |
| Prompt context (corrections) | 0-5 corrections/sender | 0-50 | Cap at 10 most recent per query |
