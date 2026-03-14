# Phase 4: Chat Notification Polish - Research

**Researched:** 2026-03-14
**Domain:** Google Chat Cards v2 webhook notifications, Python service-layer refactoring
**Confidence:** HIGH

## Summary

Phase 4 is a pure service-layer refactor of `apps/emails/services/chat_notifier.py` and its upstream data supplier `apps/emails/services/sla.py`. No model changes, no migrations, no URL changes, no template changes. The scope is narrow: add email `pk` to the breach data structure so personal breach alerts can link directly to each email, add inline "Open" buttons to breach alert cards using the `decoratedText.button` property, and standardize the SLA urgency emoji+label format across all 4 notify methods.

The codebase is well-structured for this work. `ChatNotifier` already uses Cards v2 format with `cardsV2` payloads, has a `_branded_header()` helper, and has 20+ unit tests covering all 5 card types. The `build_breach_summary()` function in `sla.py` builds the `per_assignee` dict consumed by `notify_personal_breach()` -- it currently includes `subject`, `priority`, and `overdue_minutes` per entry but NOT `pk`, which is the key gap for R4.1.

**Primary recommendation:** Thread `email.pk` through `build_breach_summary()` into the per-assignee data, use `decoratedText.button` with `openLink` for per-email "Open" buttons in `notify_personal_breach()`, extract a `_sla_urgency_label()` helper for consistent emoji+priority+overdue formatting, and validate all 4 card payloads in the Google Chat Card Builder before merge.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| R4.1 | Add pk to breach data structure passed to notify_personal_breach() | `build_breach_summary()` in sla.py line 230: entry dict has `subject`, `priority`, `overdue_minutes` but no `pk`. Add `"pk": email.pk` to the entry dict. The `top_offenders` list (line 238) should also get `pk` for potential future use. |
| R4.2 | Per-email "Open" direct link button in breach alert decoratedText | `notify_personal_breach()` line 533: currently uses `decoratedText` with `topLabel`+`text` only. The Cards v2 `decoratedText` widget supports a `button` property (part of the `control` union field) that renders an inline button next to the text. Use `onClick.openLink.url` pointing to `{tracker_url}/emails/?selected={pk}`. |
| R4.3 | Consistent SLA urgency emoji/label display across all 4 notify methods | Currently inconsistent: `notify_assignment` uses `{emoji} {pri} \| {category}` in subtitle; `notify_new_emails` uses `{emoji} {subject}` as text; `notify_breach_summary` uses `{emoji} {subject}` as text with assignee+overdue in topLabel; `notify_personal_breach` uses `{emoji} {pri} \| {overdue_str} overdue` as topLabel. Extract a shared helper for the urgency label format. |
| R4.4 | Validate card payloads in Google Chat Card Builder before merge | Card Builder URL: https://gw-card-builder.web.app/chat. Write a test that captures the full JSON payload for each card type, then manually paste into Card Builder for visual validation. Add a comment in code noting this validation step. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | (existing) | HTTP POST to Google Chat webhook | Already used in chat_notifier.py |
| pytz | (existing) | IST timezone for quiet hours | Already used in chat_notifier.py |

### Supporting
No new libraries required. This phase modifies only existing Python code in `chat_notifier.py` and `sla.py`.

### Alternatives Considered
None -- this is a refactor of existing code, not a new feature requiring library choices.

## Architecture Patterns

### Recommended Project Structure (no changes)
```
apps/emails/services/
    chat_notifier.py    # MODIFY: add inline buttons, urgency helper, consistent labels
    sla.py              # MODIFY: add pk to breach entry dicts
apps/emails/tests/
    test_chat_notifier.py  # MODIFY: add tests for inline buttons, urgency helper, pk presence
    test_sla.py            # MODIFY: add tests for pk in breach summary
```

### Pattern 1: DecoratedText with Inline Button (Cards v2)
**What:** The Google Chat Cards v2 `decoratedText` widget has a `button` property (union field `control`) that renders an inline button alongside the text, without needing a separate `buttonList` section.
**When to use:** When you want a compact row with text+button (e.g., email subject + "Open" link) instead of a separate button section.
**Example:**
```python
# Source: https://developers.google.com/workspace/chat/api/reference/rest/v1/cards
{
    "decoratedText": {
        "topLabel": "HIGH | 2h 30m overdue",
        "text": "Overdue email subject",
        "button": {
            "text": "Open",
            "onClick": {
                "openLink": {
                    "url": "https://triage.vidarbhainfotech.com/emails/?selected=42"
                }
            }
        }
    }
}
```

### Pattern 2: Shared Urgency Label Helper
**What:** Extract the emoji+priority+overdue formatting into a module-level helper function.
**When to use:** Any card widget that displays SLA urgency information.
**Example:**
```python
def _sla_urgency_label(priority: str, overdue_minutes: float = None) -> str:
    """Format consistent SLA urgency label: emoji PRIORITY | Xh Ym overdue."""
    emoji = PRIORITY_EMOJI.get(priority, PRIORITY_EMOJI["MEDIUM"])
    label = f"{emoji} {priority}"
    if overdue_minutes is not None and overdue_minutes > 0:
        if overdue_minutes < 60:
            label += f" | {int(overdue_minutes)}m overdue"
        else:
            h = int(overdue_minutes // 60)
            m = int(overdue_minutes % 60)
            label += f" | {h}h {m}m overdue" if m else f" | {h}h overdue"
    return label
```

### Pattern 3: Dashboard Deep Link
**What:** Link directly to a specific email in the dashboard using the `?selected=` query parameter.
**When to use:** Any Chat card button that should open a specific email.
**Example:**
```python
# Existing pattern from notify_assignment (line 160)
dashboard_link = f"{self._tracker_url}/emails/?selected={email_pk}"
```

### Anti-Patterns to Avoid
- **Separate buttonList for per-email links:** Do NOT add a `buttonList` section per email in breach alerts. Use `decoratedText.button` inline instead -- it is more compact and the card stays readable with 5+ emails.
- **Re-querying the database in ChatNotifier:** ChatNotifier should NEVER import Django ORM models. The `pk` must be passed through from `sla.py` via the data dict, not looked up in the notifier.
- **Inconsistent overdue formatting:** Do NOT format overdue durations differently in different methods. The `_format_overdue()` helper already exists in `sla.py`; either import it or replicate the same logic in a ChatNotifier helper.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Card payload validation | Custom JSON schema validator | [Google Chat Card Builder](https://gw-card-builder.web.app/chat) (manual paste) | Official tool catches edge cases that a custom validator would miss (e.g., widget property conflicts in the `control` union field) |
| Overdue duration formatting | New formatting code in chat_notifier.py | Existing `_format_overdue()` in sla.py or replicate its exact logic | Already handles edge cases (< 60 min, exact hours, hours+minutes) |

## Common Pitfalls

### Pitfall 1: DecoratedText `control` Union Field Conflict
**What goes wrong:** The `decoratedText` widget's `control` field is a union of `button`, `switchControl`, and `endIcon`. Setting more than one of these causes unpredictable behavior -- the API may silently pick one or reject the payload.
**Why it happens:** Developer adds both an `endIcon` and a `button` to the same `decoratedText`, not realizing they are mutually exclusive.
**How to avoid:** Use ONLY `button` in the `control` slot for breach email rows. Do not combine with `endIcon` or `switchControl`.
**Warning signs:** Card renders without the button, or Card Builder shows a validation warning.

### Pitfall 2: Card Builder Validates But Webhook Rejects
**What goes wrong:** Card Builder may accept payloads that the webhook endpoint rejects (or vice versa), because the webhook may have stricter validation on certain fields (e.g., empty strings for `url`).
**Why it happens:** Card Builder is a visual tool, not an exact replica of the webhook validation engine.
**How to avoid:** After Card Builder validation, also test with `test_pipeline --with-chat` against the real webhook. Both checks are needed.
**Warning signs:** 400 status code from webhook with error message about invalid payload.

### Pitfall 3: Mixed Old/New Card Formats in Chat Space
**What goes wrong:** If deployed during business hours, the Chat space shows old-format cards (from before deploy) alongside new-format cards (after deploy), confusing users.
**Why it happens:** Old cards in Chat history are immutable -- they keep their original format forever.
**How to avoid:** Deploy outside business hours. This is cosmetic, not functional, but the user explicitly called it out as a risk.
**Warning signs:** Users asking "why do some breach alerts have Open buttons and some don't?"

### Pitfall 4: Missing pk When Email Has No Assignee
**What goes wrong:** In `build_breach_summary()`, unassigned emails are grouped under the key "Unassigned" in `per_assignee`. If the code assumes all entries have a `pk` but the email object is somehow None (shouldn't happen with current code, but defensive coding matters), accessing `.pk` would crash.
**Why it happens:** Defensive edge case -- `get_breached_emails()` returns a QuerySet, so email objects always have `pk`. Low risk but worth noting.
**How to avoid:** The `pk` is accessed from the email Django model object in the `for email in qs:` loop, which always has a pk. No special handling needed.

## Code Examples

### Current `build_breach_summary()` Entry (sla.py line 230-234)
```python
# CURRENT -- missing pk
entry = {
    "subject": email.subject[:50],
    "priority": email.priority,
    "overdue_minutes": overdue_minutes,
}
```

### Modified `build_breach_summary()` Entry (R4.1)
```python
# MODIFIED -- add pk for deep linking
entry = {
    "pk": email.pk,
    "subject": email.subject[:50],
    "priority": email.priority,
    "overdue_minutes": overdue_minutes,
}
```

### Also in `all_overdue` list (sla.py line 238-243)
```python
# CURRENT
all_overdue.append({
    "subject": email.subject[:50],
    "assignee_name": name,
    "priority": email.priority,
    "overdue_str": _format_overdue(overdue_minutes),
    "overdue_minutes": overdue_minutes,
})

# MODIFIED -- add pk
all_overdue.append({
    "pk": email.pk,
    "subject": email.subject[:50],
    "assignee_name": name,
    "priority": email.priority,
    "overdue_str": _format_overdue(overdue_minutes),
    "overdue_minutes": overdue_minutes,
})
```

### Modified `notify_personal_breach()` With Inline Button (R4.2)
```python
# MODIFIED -- decoratedText with inline "Open" button
for item in breached_emails:
    pri = item.get("priority", "MEDIUM")
    pk = item.get("pk")
    urgency_label = _sla_urgency_label(pri, item.get("overdue_minutes"))

    widget = {
        "decoratedText": {
            "topLabel": urgency_label,
            "text": item.get("subject", "")[:50],
        }
    }

    # Add inline "Open" button if pk is available
    if pk:
        widget["decoratedText"]["button"] = {
            "text": "Open",
            "onClick": {
                "openLink": {
                    "url": f"{self._tracker_url}/emails/?selected={pk}"
                }
            }
        }

    email_widgets.append(widget)
```

### Urgency Label Helper (R4.3)
```python
def _sla_urgency_label(priority: str, overdue_minutes: float = None) -> str:
    """Format consistent SLA urgency label for Chat cards.

    Returns: "{emoji} {PRIORITY}" or "{emoji} {PRIORITY} | {duration} overdue"
    """
    emoji = PRIORITY_EMOJI.get(priority, PRIORITY_EMOJI["MEDIUM"])
    label = f"{emoji} {priority}"
    if overdue_minutes is not None and overdue_minutes > 0:
        if overdue_minutes < 60:
            label += f" | {int(overdue_minutes)}m overdue"
        else:
            h = int(overdue_minutes // 60)
            m = int(overdue_minutes % 60)
            label += f" | {h}h {m}m overdue" if m else f" | {h}h overdue"
    return label
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cards v1 (simple text messages) | Cards v2 (`cardsV2` JSON) | 2023 | Richer formatting, sections, buttons |
| buttonList for per-item actions | decoratedText.button inline | Cards v2 launch | More compact layout, one widget instead of two |
| Per-ticket Chat notification | Summary-based + per-assignee alerts | v2.1 Phase 4 | Less notification spam, more actionable |

**Deprecated/outdated:**
- Cards v1 (`cards` key) is deprecated; always use `cardsV2` key (already the case in this codebase)

## Open Questions

1. **Should `notify_breach_summary` (manager view) also get per-email "Open" buttons?**
   - What we know: R4.2 specifies "breach alert cards" which most directly maps to `notify_personal_breach`. The `notify_breach_summary` shows top offenders which also have per-email rows.
   - What's unclear: Whether the manager summary should also have inline "Open" buttons on the top offenders list.
   - Recommendation: Add "Open" buttons to top offenders in `notify_breach_summary` as well -- it uses the same data structure and the pattern is the same. The `pk` will be available in `top_offenders` after R4.1 changes.

2. **Should `notify_new_emails` per-email rows also get "Open" buttons?**
   - What we know: `notify_new_emails` receives Django Email model instances (not dicts), so `email.pk` is directly available.
   - What's unclear: Whether R4.2 scope extends to poll summary cards or only breach alerts.
   - Recommendation: Add "Open" buttons to `notify_new_emails` per-email rows as well -- the pattern is identical and the pk is already available. This is a natural extension and makes all card types consistently linkable.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-django |
| Config file | pytest.ini |
| Quick run command | `pytest apps/emails/tests/test_chat_notifier.py apps/emails/tests/test_sla.py -x -q` |
| Full suite command | `pytest -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| R4.1 | pk present in breach entry dicts from build_breach_summary | unit | `pytest apps/emails/tests/test_sla.py::TestBreachSummary -x` | Exists (add assertion for pk) |
| R4.2 | decoratedText has button with openLink in notify_personal_breach | unit | `pytest apps/emails/tests/test_chat_notifier.py::TestChatPersonalBreach -x` | Exists (add button assertion) |
| R4.3 | SLA urgency label format consistent across all notify methods | unit | `pytest apps/emails/tests/test_chat_notifier.py -k urgency -x` | New tests needed |
| R4.4 | Card payloads structurally valid for Cards v2 | unit | `pytest apps/emails/tests/test_chat_notifier.py -k card_format -x` | Partially exists (extend) |

### Sampling Rate
- **Per task commit:** `pytest apps/emails/tests/test_chat_notifier.py apps/emails/tests/test_sla.py -x -q`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New test: `test_sla.py::TestBreachSummary::test_entry_contains_pk` -- assert `pk` key in per_assignee entry dicts
- [ ] New test: `test_sla.py::TestBreachSummary::test_top_offenders_contain_pk` -- assert `pk` key in top_offenders dicts
- [ ] New test: `test_chat_notifier.py::TestChatPersonalBreach::test_personal_breach_has_open_button` -- assert decoratedText has button.onClick.openLink
- [ ] New test: `test_chat_notifier.py::test_sla_urgency_label_helper` -- test the extracted helper function
- [ ] New test: `test_chat_notifier.py::test_urgency_label_consistency_across_cards` -- verify all cards use the same urgency format

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `chat_notifier.py` (553 lines, 5 notify methods), `sla.py` (351 lines, breach detection + summary builder), `test_chat_notifier.py` (444 lines, 20+ tests), `test_sla.py` (653 lines, 40+ tests)
- [Google Chat Cards v2 REST API reference](https://developers.google.com/workspace/chat/api/reference/rest/v1/cards) -- DecoratedText widget structure, button property, openLink action
- [Google Chat Card Builder](https://gw-card-builder.web.app/chat) -- validation tool for card payloads

### Secondary (MEDIUM confidence)
- [Google Chat design interactive cards](https://developers.google.com/workspace/chat/design-interactive-card-dialog) -- button onClick patterns
- Earlier v2.2 research: `.planning/research/SUMMARY.md`, `.planning/research/PITFALLS.md` -- Phase 4 rationale and pitfall mapping

### Tertiary (LOW confidence)
None -- all findings verified against codebase and official Google docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, purely refactoring existing code
- Architecture: HIGH -- Cards v2 decoratedText.button pattern verified in official docs; existing codebase patterns well understood
- Pitfalls: HIGH -- pitfalls sourced from direct code reading and official API docs; the `control` union field constraint is documented

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable domain -- Google Chat Cards v2 API and existing codebase patterns unlikely to change)
