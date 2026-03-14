---
phase: 04-chat-notification-polish
verified: 2026-03-14T23:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 4: Chat Notification Polish Verification Report

**Phase Goal:** Improve Google Chat notification cards with direct email links and richer card structure.
**Verified:** 2026-03-14T23:30:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each breach alert card row has an inline 'Open' button linking to the specific email | VERIFIED | `chat_notifier.py` lines 569-574: `item.get("pk")` gates inline `decoratedText["button"]` with `openLink` URL `f"{self._tracker_url}/emails/?selected={pk}"`. Same pattern at lines 384-389 for breach summary and lines 284-289 for new emails. Tests `test_personal_breach_has_open_button`, `test_personal_breach_open_button_uses_pk`, `test_breach_summary_top_offenders_have_open_button`, `test_new_emails_have_open_button` all pass. |
| 2 | SLA urgency labels use a consistent format across all 4 notify methods | VERIFIED | `_sla_urgency_label()` defined at line 29, called at line 183 (notify_assignment subtitle), line 276 (notify_new_emails per-email text), line 374 (notify_breach_summary offender topLabel), line 564 (notify_personal_breach topLabel). Tests `test_personal_breach_uses_urgency_label_format` and `test_breach_summary_uses_urgency_label_format` both pass. |
| 3 | breach data dicts from build_breach_summary() include 'pk' key for deep linking | VERIFIED | `sla.py` line 234: `"pk": email.pk` in per_assignee entry dict. Line 245: `"pk": email.pk` in all_overdue (top_offenders source). Tests `test_entry_contains_pk` and `test_top_offenders_contain_pk` both pass. |
| 4 | All card payloads are structurally valid Cards v2 JSON | VERIFIED | Human-verified (R4.4): user approved card payloads after testing all 4 card types against the real Google Chat webhook. Test helper `test_dump_card_payloads_for_validation` exists for re-validation. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/emails/services/sla.py` | pk field in breach entry dicts and top_offenders dicts | VERIFIED | Lines 234, 245: `"pk": email.pk` added to both entry and all_overdue dicts |
| `apps/emails/services/chat_notifier.py` | _sla_urgency_label helper, inline Open buttons, consistent urgency labels | VERIFIED | `_sla_urgency_label()` at line 29, 3 inline Open button blocks (lines 286, 386, 571), all 4 notify methods use the helper |
| `apps/emails/tests/test_sla.py` | Tests asserting pk presence in breach summary dicts | VERIFIED | `test_entry_contains_pk` at line 377, `test_top_offenders_contain_pk` at line 400 |
| `apps/emails/tests/test_chat_notifier.py` | Tests for Open buttons, urgency helper, card format validation | VERIFIED | `TestSlaUrgencyLabel` (6 tests), `TestOpenButtonsAcrossCards` (5 tests incl. skip helper), `TestUrgencyLabelConsistency` (2 tests) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sla.py` build_breach_summary | `chat_notifier.py` notify_personal_breach / notify_breach_summary | pk field in breach dicts consumed via `item.get("pk")` / `offender.get("pk")` | WIRED | sla.py produces `"pk": email.pk` at lines 234, 245; chat_notifier.py consumes at lines 569, 384 |
| `chat_notifier.py` | decoratedText.button with openLink | Inline Open button with URL | WIRED | 3 locations (lines 286, 386, 571) build `widget["decoratedText"]["button"]` with `openLink.url` containing `/emails/?selected={pk}` |
| `chat_notifier.py` _sla_urgency_label | All 4 notify methods | Function call | WIRED | Called at lines 183 (assignment), 276 (new_emails), 374 (breach_summary), 564 (personal_breach) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| R4.1 | 04-01-PLAN | Add pk to breach data structure passed to notify_personal_breach() | SATISFIED | `sla.py` lines 234, 245: `"pk": email.pk` in both per_assignee entry and top_offenders dicts. Tests `test_entry_contains_pk` and `test_top_offenders_contain_pk` pass. |
| R4.2 | 04-01-PLAN | Per-email "Open" direct link button in breach alert decoratedText | SATISFIED | `chat_notifier.py` inline `decoratedText["button"]` at lines 571 (personal_breach), 386 (breach_summary), 286 (new_emails). Tests verify URL contains `/emails/?selected=` with correct pk. |
| R4.3 | 04-01-PLAN | Consistent SLA urgency emoji/label display across all 4 notify methods | SATISFIED | `_sla_urgency_label()` at line 29 used by all 4 methods (lines 183, 276, 374, 564). `TestSlaUrgencyLabel` (6 tests) and `TestUrgencyLabelConsistency` (2 tests) verify format. |
| R4.4 | 04-01-PLAN | Validate card payloads in Google Chat Card Builder before merge | SATISFIED | Human-verified: user approved after testing all 4 card types against real webhook. Dump helper (`test_dump_card_payloads_for_validation`) available for re-validation. |

### Anti-Patterns Found

No anti-patterns detected. No TODO/FIXME/PLACEHOLDER comments in modified files. No empty implementations or stub handlers.

### Human Verification Required

None -- R4.4 (card payload validation) was already human-verified by the user.

### Gaps Summary

No gaps found. All 4 truths verified, all artifacts substantive and wired, all requirements satisfied, all tests pass (348 passed, 1 skipped -- the manual dump helper). Full test suite shows no regressions.

---

_Verified: 2026-03-14T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
