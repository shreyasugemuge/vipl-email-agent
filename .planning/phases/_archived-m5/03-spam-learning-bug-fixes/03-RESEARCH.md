# Phase 3: Spam Learning + Bug Fixes - Research

**Researched:** 2026-03-15
**Domain:** Django views, pipeline orchestration, HTMX partials, sender reputation
**Confidence:** HIGH

## Summary

Phase 3 adds user-facing spam feedback (mark spam/not-spam), sender reputation-based auto-blocking, a combined whitelist/blocklist management tab, and fixes three known bugs. All models (SpamFeedback, SenderReputation) already exist from Phase 1 migration (0015_v250_models.py). ActivityLog already has `spam_marked` and `spam_unmarked` action choices.

The implementation is primarily view-layer and pipeline-layer work. The spam feedback buttons go in the thread detail header, following the same HTMX partial-swap pattern as assign/status/whitelist buttons. Pipeline gets a block check inserted between whitelist check and spam filter. The combined Settings tab merges the existing whitelist table with blocked senders from SenderReputation.

Bug fixes are scoped and isolated: force_poll mode restriction removal (3 lines), avatar edge case investigation (existing tests pass -- research found the `_update_avatar` helper is correct), and has_spam annotation tracing (annotation is correct in queryset but may not reflect real-time feedback changes).

**Primary recommendation:** Follow existing HTMX partial-swap patterns for all new interactions. No new dependencies needed. Use `update_or_create` for SenderReputation tracking in the pipeline.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Mark Spam / Not Spam buttons live in the **detail panel only** (header bar, near assign/status buttons)
- **Instant action + toast** -- click triggers immediately, toast with 5s undo window (matches existing assignment/status change pattern)
- Marking "Not Spam" on a **blocked** sender auto-whitelists, but regular "Not Spam" is feedback-only
- **All users** (admin and member) can mark spam/not-spam -- SpamFeedback records who did it
- **Silent block** -- pipeline skips blocked senders without notification or ActivityLog entry
- Block check runs **before spam filter** in pipeline: whitelist -> block check -> spam filter -> AI triage
- Blocked sender management in **combined Whitelist/Block tab** in Settings (merge with existing SpamWhitelist management)
- Unblocking a sender affects **future emails only** -- past emails stay as-is
- Only senders with spam_count > 0 or is_blocked = True shown in the combined tab
- Auto-block threshold: spam ratio > 0.8 AND >= 3 total emails
- Reputation updates on **both** user feedback (explicit) and pipeline processing (passive)
- **FIX-03** (Force Poll in production): Remove dev/off mode restriction -- works in ALL modes
- Scheduler investigation: scheduler has stopped polling in production (0 polls in 7 days)

### Claude's Discretion
- Button styling/placement details in detail panel header
- Toast notification wording and undo implementation
- Combined tab layout (how to merge whitelist + blocked senders visually)
- Pipeline block check implementation details
- How to increment SenderReputation.total_count during pipeline (get_or_create vs update_or_create)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPAM-01 | User can mark a thread as "Spam" or "Not Spam" from detail panel | Existing HTMX partial-swap pattern (assign/status/whitelist buttons), SpamFeedback model ready |
| SPAM-02 | Spam/not-spam actions create SpamFeedback records | SpamFeedback model exists with user, thread, email, original_verdict, user_verdict fields |
| SPAM-03 | Sender reputation tracked (total emails, spam count, spam ratio) | SenderReputation model exists with total_count, spam_count, is_blocked, spam_ratio property |
| SPAM-04 | Senders with spam ratio > 0.8 and >= 3 total emails auto-blocked | Pipeline block check pattern follows existing `_is_whitelisted()` |
| SPAM-05 | Marking "Not Spam" on blocked sender auto-creates SpamWhitelist entry | SpamWhitelist model exists with entry/entry_type/added_by/reason fields |
| SPAM-06 | Spam badge displays correctly on thread cards (fix has_spam annotation) | Annotation exists at views.py:84, detail panel computes at views.py:784 -- need to trace mismatch |
| FIX-01 | Gmail avatar imports correctly on OAuth login | `_update_avatar()` helper exists in adapters.py:85-91, 6+ tests pass -- investigate remaining edge cases |
| FIX-02 | Cross-inbox dedup handles same email in info@ and sales@ | `_detect_cross_inbox_duplicate()` at pipeline.py:196-214, 7 tests exist -- investigate edge cases |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Django | 4.2 LTS | Web framework | Already in use, no version change |
| HTMX | 2.0 CDN | Partial page updates for spam buttons | Already loaded in base.html |
| nh3 | (existing) | HTML sanitization | Already in use |

### Supporting
No new dependencies needed. All functionality builds on existing models and patterns.

**Installation:**
```bash
# No new packages required
```

## Architecture Patterns

### Recommended Project Structure
No new files needed beyond views and templates. Changes go into existing files:

```
apps/emails/
  views.py              # Add mark_spam, mark_not_spam views; modify force_poll; modify settings_view
  urls.py               # Add spam feedback URL routes
  services/pipeline.py  # Add _is_blocked() check, SenderReputation increment

templates/emails/
  _thread_detail.html   # Add spam/not-spam buttons to header bar
  _whitelist_tab.html   # Extend to combined whitelist/blocklist tab
```

### Pattern 1: HTMX Partial-Swap for Spam Feedback
**What:** POST button triggers server action, returns re-rendered detail panel partial
**When to use:** All spam feedback interactions
**Example:**
```python
# Following exact pattern from whitelist_sender_from_thread (views.py:1075)
@login_required
@require_POST
def mark_spam(request, pk):
    thread = get_object_or_404(Thread, pk=pk)
    # 1. Create SpamFeedback record
    # 2. Update Email.is_spam on all thread emails
    # 3. Update SenderReputation
    # 4. Check auto-block threshold
    # 5. Create ActivityLog entry
    # 6. Re-render detail panel with toast message
    detail_context = _build_thread_detail_context(thread, request, is_admin, team_members)
    detail_context["toast_msg"] = "Marked as spam"
    return render(request, "emails/_thread_detail.html", detail_context)
```

### Pattern 2: Pipeline Block Check
**What:** Check SenderReputation.is_blocked before spam filter
**When to use:** Every email in process_single_email
**Example:**
```python
# Insert between whitelist check and spam filter in process_single_email()
def _is_blocked(sender_email: str) -> bool:
    """Check if sender is auto-blocked via reputation."""
    from apps.emails.models import SenderReputation
    return SenderReputation.objects.filter(
        sender_address__iexact=sender_email,
        is_blocked=True,
    ).exists()
```

### Pattern 3: SenderReputation Update in Pipeline
**What:** Increment total_count for every processed email, spam_count for spam emails
**When to use:** After save_email_to_db in pipeline
**Example:**
```python
# In process_single_email, after save:
from apps.emails.models import SenderReputation
rep, _ = SenderReputation.objects.get_or_create(
    sender_address=email_msg.sender_email.lower(),
)
rep.total_count = models.F("total_count") + 1
if email_obj.is_spam:
    rep.spam_count = models.F("spam_count") + 1
rep.save(update_fields=["total_count", "spam_count"])
rep.refresh_from_db()

# Auto-block check
if not rep.is_blocked and rep.total_count >= 3 and rep.spam_ratio > 0.8:
    rep.is_blocked = True
    rep.save(update_fields=["is_blocked"])
```

### Pattern 4: Combined Settings Tab
**What:** Merge whitelist entries and blocked senders into one table with type column
**When to use:** Settings whitelist tab
**Example:**
```python
# In settings_view, pass both datasets:
whitelist_entries = SpamWhitelist.objects.select_related("added_by").all()
blocked_senders = SenderReputation.objects.filter(
    models.Q(spam_count__gt=0) | models.Q(is_blocked=True)
).order_by("-is_blocked", "-spam_count")

context["whitelist_entries"] = whitelist_entries
context["blocked_senders"] = blocked_senders
```

### Anti-Patterns to Avoid
- **Separate API endpoints for spam feedback:** Use HTMX partial swap (re-render full detail panel), not JSON API. Keeps consistency with existing patterns.
- **Complex undo mechanism:** Use simple toast with 5s timer + server-side undo endpoint. Don't try client-side optimistic updates.
- **Updating past emails on unblock:** Decision says unblock affects future only. Don't retroactively change `is_spam` on existing emails when unblocking.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Spam ratio calculation | Custom aggregation | SenderReputation.spam_ratio property | Already exists, tested |
| Toast notifications | New toast system | Existing toast pattern from assignment/status | Already works with HTMX |
| Soft delete on feedback | Custom delete | SoftDeleteModel base class | SpamFeedback already inherits it |

## Common Pitfalls

### Pitfall 1: F() Expression Requires refresh_from_db
**What goes wrong:** Using `F("total_count") + 1` then immediately reading `rep.spam_ratio` returns wrong value
**Why it happens:** F() expressions are deferred to SQL; Python attribute still holds the F() object
**How to avoid:** Always call `rep.refresh_from_db()` before checking `spam_ratio` for auto-block threshold
**Warning signs:** Auto-block never triggers despite high spam count

### Pitfall 2: Race Condition on SenderReputation
**What goes wrong:** Two concurrent poll cycles create duplicate SenderReputation rows
**Why it happens:** get_or_create with concurrent inserts
**How to avoid:** Use `update_or_create` or handle IntegrityError. The unique constraint on sender_address will catch it.
**Warning signs:** IntegrityError in pipeline logs

### Pitfall 3: has_spam Not Refreshing After Feedback
**What goes wrong:** User marks thread as "not spam" but spam badge persists on thread card
**Why it happens:** Thread list queryset annotation is computed at query time; HTMX partial swap only re-renders the detail panel, not the thread card in the list
**How to avoid:** After spam feedback, also return an OOB (out-of-band) HTMX swap to update the thread card in the list, OR use hx-trigger to refresh the card
**Warning signs:** Badge shows stale state after marking spam/not-spam

### Pitfall 4: Force Poll in Production Uses Hardcoded Path
**What goes wrong:** Force poll fails on VM because `cwd` is hardcoded to local dev path
**Why it happens:** views.py:1769 has `cwd="/Users/uge/code/vipl-email-agent"`
**How to avoid:** Use `settings.BASE_DIR` or remove cwd entirely (manage.py is on PATH in Docker)
**Warning signs:** Force poll returns 500 on production VM

### Pitfall 5: Undo Window Creates Complexity
**What goes wrong:** User clicks undo but server-side state has already propagated
**Why it happens:** SenderReputation counts were already updated, auto-block may have triggered
**How to avoid:** Undo should fully reverse: delete SpamFeedback, decrement counts, re-check block status. Keep it in a single transaction.
**Warning signs:** Inconsistent counts after undo

## Code Examples

### Existing Pattern: Whitelist from Thread Detail (to follow for spam buttons)
```python
# Source: apps/emails/views.py:1075-1114
@login_required
@require_POST
def whitelist_sender_from_thread(request, pk):
    if not _require_admin(request.user):
        return HttpResponseForbidden("Admin access required.")
    thread = get_object_or_404(Thread, pk=pk)
    sender = thread.last_sender_address.strip().lower()
    # ... create whitelist entry, unspam emails ...
    detail_context = _build_thread_detail_context(thread, request, is_admin, team_members)
    detail_context["whitelist_msg"] = msg
    return render(request, "emails/_thread_detail.html", detail_context)
```

### Existing Pattern: Pipeline Whitelist Check (to follow for block check)
```python
# Source: apps/emails/services/pipeline.py:179-191
def _is_whitelisted(sender_email: str) -> bool:
    from apps.emails.models import SpamWhitelist
    domain = sender_email.split("@")[-1] if "@" in sender_email else ""
    return SpamWhitelist.objects.filter(
        db_models.Q(entry_type="email", entry__iexact=sender_email)
        | db_models.Q(entry_type="domain", entry__iexact=domain)
    ).exists()
```

### Force Poll Bug: Hardcoded CWD
```python
# Source: apps/emails/views.py:1765-1769 -- MUST FIX
result = subprocess.run(
    ["python", "manage.py", "run_scheduler", "--once"],
    capture_output=True, text=True, timeout=120,
    cwd="/Users/uge/code/vipl-email-agent",  # BUG: hardcoded local path
)
# Fix: Use settings.BASE_DIR or os.path.dirname(__file__) relative path
```

### Spam Badge Annotation (has_spam)
```python
# Source: apps/emails/views.py:84 -- annotation on thread list queryset
has_spam=Exists(Email.objects.filter(thread=OuterRef("pk"), is_spam=True)),

# Source: apps/emails/views.py:784 -- computed in detail context
has_spam = any(e.is_spam for e in emails)
```
The annotation is syntactically correct. The likely SPAM-06 bug is one of:
1. The annotation returns False because `Email.objects` (SoftDeleteManager) is used but the email record was soft-deleted
2. When a thread has zero spam emails initially, then spam feedback marks one as spam, the thread card does not refresh
3. The detail panel computes `has_spam` correctly but the thread card uses the stale annotation from the list load

Recommendation: verify by tracing a real spam email through the pipeline and checking the thread card. If the annotation query is correct but rendering is stale, add HTMX OOB swap for the card after spam status changes.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Whitelist-only spam management | Whitelist + block + reputation | Phase 3 (this phase) | Closed-loop spam feedback |
| Force poll restricted to dev/off | Force poll in all modes | Phase 3 (this phase) | Production debugging capability |

## Bug Investigation Results

### FIX-01: Gmail Avatar
**Status:** Likely already working. `_update_avatar()` at adapters.py:85-91 is clean:
- Checks `picture` exists and differs from current `avatar_url`
- Uses `save(update_fields=["avatar_url"])` for atomic update
- Called on auto-link (line 64), repeat login (line 79), and new user (line 107/122)
- 6 tests cover: existing user, auto-link, empty picture, unchanged avatar, new user, new user without avatar

**Possible remaining edge case:** Google's `picture` URL may be a temporary signed URL that expires. The `avatar_url` field stores the URL, but it may become a 404 after some time. This is not a Django bug -- it's a Google API behavior. Mitigation: could proxy/cache the image, but that's likely overkill for 4 users.

**Recommendation:** Verify manually on production. If avatar shows on login but disappears later, it's the Google URL expiry. If avatar never appears, investigate allauth version / extra_data structure.

### FIX-02: Cross-Inbox Dedup
**Status:** Implemented and tested with 7+ tests. `_detect_cross_inbox_duplicate()` at pipeline.py:196-214:
- Dedup key: same `gmail_thread_id` + same `from_address` within 5-min window
- Excludes same inbox (only catches cross-inbox)
- Reuses original's triage result

**Possible remaining edge case:** If same email arrives in both inboxes with different `message_id` but same `gmail_thread_id`, and the second arrives > 5 minutes later, it won't be detected as a duplicate. The 5-min window is configurable (`CROSS_INBOX_DEDUP_WINDOW_MINUTES`).

**Recommendation:** The existing implementation is solid. If bugs remain, they'd be in edge cases like: BCC'd emails (different thread IDs), forwarded messages (different senders), or timing edge cases. Worth adding a test for the > 5-min window case to confirm it falls through to AI triage (correct behavior).

### FIX-03: Force Poll in Production
**Two bugs found:**
1. **Mode restriction:** Line 1760-1761 blocks production mode entirely. Remove the mode check.
2. **Hardcoded CWD:** Line 1769 has `cwd="/Users/uge/code/vipl-email-agent"`. This will fail on the VM where the deploy path is `/opt/vipl-email-agent/`. Fix: use `settings.BASE_DIR`.

### Scheduler Stopped Polling
**Context:** Inspector shows PRODUCTION mode, 0 polls in 7 days, "Due now."
**Investigation needed:** This is likely a Docker container health/restart issue, not a code bug. The scheduler container runs `run_scheduler` management command via APScheduler. Possible causes:
- Scheduler container crashed and `depends_on: condition: service_healthy` prevents restart
- DB connection went stale without `close_old_connections()` being called (it IS called at start of `process_poll_cycle`)
- APScheduler thread died silently

**Recommendation:** SSH into VM and check `sudo docker logs vipl-email-scheduler --tail 100`. This is an ops investigation, not a code change. However, making Force Poll work in production (FIX-03) provides a manual workaround.

## Open Questions

1. **SPAM-06 exact reproduction steps**
   - What we know: `has_spam` annotation exists and is syntactically correct; detail panel computes it differently (Python loop)
   - What's unclear: Whether the bug is "badge never shows" or "badge shows stale state after feedback"
   - Recommendation: Add a test that creates a thread with one spam email and verifies `has_spam=True` in the annotated queryset. If that passes, the bug is likely a rendering/staleness issue.

2. **Toast undo implementation detail**
   - What we know: Toast pattern exists for assignment/status; 5s undo window decided
   - What's unclear: Best approach for reversing SenderReputation changes on undo
   - Recommendation: Store the SpamFeedback PK in the undo button's data attribute. Undo endpoint deletes the feedback and decrements counts in a transaction.

3. **Scheduler stopped in production**
   - What we know: 0 polls in 7 days on production
   - What's unclear: Root cause (container crash, APScheduler thread death, config issue)
   - Recommendation: Investigate via SSH before/during this phase. Force Poll fix provides immediate workaround.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-django |
| Config file | pytest.ini |
| Quick run command | `pytest apps/emails/tests/ -x -q` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPAM-01 | Mark spam/not-spam from detail panel | unit | `pytest apps/emails/tests/test_spam_feedback.py -x` | No -- Wave 0 |
| SPAM-02 | SpamFeedback record created | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_feedback_creates_record -x` | No -- Wave 0 |
| SPAM-03 | SenderReputation tracking | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_reputation_updated -x` | No -- Wave 0 |
| SPAM-04 | Auto-block at threshold | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_auto_block_threshold -x` | No -- Wave 0 |
| SPAM-05 | Not-spam on blocked sender auto-whitelists | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_unblock_auto_whitelist -x` | No -- Wave 0 |
| SPAM-06 | Spam badge displays on thread cards | unit | `pytest apps/emails/tests/test_spam_feedback.py::test_has_spam_annotation -x` | No -- Wave 0 |
| FIX-01 | Avatar imports on OAuth | unit | `pytest apps/accounts/tests/test_oauth.py -x` | Yes -- 6 tests |
| FIX-02 | Cross-inbox dedup | unit | `pytest apps/emails/tests/test_cross_inbox_dedup.py -x` | Yes -- 7 tests |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_spam_feedback.py -x -q`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/emails/tests/test_spam_feedback.py` -- covers SPAM-01 through SPAM-06
- [ ] No new fixtures needed -- existing conftest.py has user, admin_user, email, thread factories

## Sources

### Primary (HIGH confidence)
- Codebase inspection: models.py, views.py, pipeline.py, adapters.py, urls.py, templates
- Existing test files: test_cross_inbox_dedup.py (7 tests), test_oauth.py (6 avatar tests), test_v250_models.py (model tests)

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions and code context from discuss phase
- to_fix.md audit findings (confirmed force_poll bug independently)

### Tertiary (LOW confidence)
- Scheduler stoppage root cause -- needs VM investigation, not code-level research

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing patterns
- Architecture: HIGH -- follows established HTMX partial-swap and pipeline patterns
- Pitfalls: HIGH -- identified from direct code inspection (hardcoded path, F() expressions, race conditions)
- Bug fixes: MEDIUM -- FIX-01 and FIX-02 appear working but need manual production verification; SPAM-06 needs reproduction

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable -- Django 4.2 LTS, no fast-moving dependencies)
