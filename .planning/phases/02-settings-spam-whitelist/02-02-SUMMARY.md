---
phase: 02-settings-spam-whitelist
plan: 02
subsystem: ui, email-pipeline
tags: [htmx, whitelist-ui, settings-tabs, spam-badge, oob-swap, django-views]

requires:
  - phase: 02-settings-spam-whitelist/plan-01
    provides: SpamWhitelist model, pipeline whitelist integration, config editor improvements
provides:
  - Whitelist management tab in settings (add/delete entries)
  - Whitelist Sender button in email detail (un-spams existing emails)
  - Spam badge on email cards and detail view
  - AI summary display in email detail panel
  - Consistent save feedback banners on all settings tabs
  - Removed draft reply feature (UI, schema, DTO, pipeline, fake data)
affects: [03-branding]

tech-stack:
  added: []
  patterns: [oob-swap-pattern, inline-delete-without-confirmation]

key-files:
  created:
    - templates/emails/_whitelist_tab.html
  modified:
    - apps/emails/views.py
    - apps/emails/urls.py
    - templates/emails/settings.html
    - templates/emails/_email_detail.html
    - templates/emails/_email_card.html
    - templates/emails/_sla_config.html
    - templates/emails/_assignment_rules.html
    - templates/emails/_category_visibility.html
    - templates/emails/_inboxes_tab.html
    - apps/emails/services/ai_processor.py
    - apps/emails/services/dtos.py
    - apps/emails/services/fake_data.py
    - apps/emails/services/pipeline.py
    - apps/emails/services/spam_filter.py
    - apps/emails/tests/test_ai_processor.py
    - apps/emails/tests/test_settings_views.py
    - conftest.py

key-decisions:
  - "Removed draft reply feature entirely -- not useful, cluttered detail view"
  - "Whitelist sender un-spams all existing emails from that sender (is_spam=False)"
  - "No delete confirmation on whitelist entries -- immediate delete for snappier UX"
  - "Whitelist Sender returns OOB card swaps for all emails from same sender"
  - "Spam shown as badge/label (not part of description text)"

patterns-established:
  - "OOB swap pattern: hx-post returns primary target + hx-swap-oob for related elements"
  - "Inline delete without confirmation for low-risk CRUD entries"

requirements-completed: [R2.5, R2.6, R2.8]

duration: multi-session
completed: 2026-03-14
---

# Phase 2 Plan 2: Whitelist Settings Tab + Whitelist Sender Button Summary

**Whitelist management tab in settings with add/delete, whitelist sender button that un-spams existing emails with OOB card swaps, spam badges on cards/detail, AI summary in detail panel, draft reply feature removed**

## Performance

- **Duration:** Multi-session (TDD + implementation + visual verification + refinements)
- **Tasks:** 3 (2 auto + 1 checkpoint:human-verify)
- **Files modified:** 17

## Accomplishments
- 7th Whitelist tab in settings with inline add form and immediate-delete entries
- Whitelist Sender button in email detail that also un-spams all existing emails from that sender
- OOB swap pattern: whitelist action refreshes detail panel + all cards from same sender
- Spam shown as badge/label on email cards and detail view
- AI summary now visible in email detail panel (was only in card preview)
- Draft reply feature removed entirely (UI, DTO, pipeline, fake data, AI processor, tests)
- Consistent save success banners on all 7 settings tabs (SLA, Rules, Visibility, Inboxes, Whitelist + already-done System, Webhooks)
- 314 tests passing (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for whitelist views and save feedback** - `d14c39a` (test)
2. **Task 1 (GREEN): Whitelist management tab + save feedback** - `a301dbc` (feat)
3. **Task 2: Whitelist sender button in email detail** - `c4453f9` (feat)
4. **Task 3: Verification refinements** - `e4fbe90` (feat)

## Files Created/Modified
- `templates/emails/_whitelist_tab.html` - Whitelist management tab partial (add form, entry table, delete)
- `templates/emails/settings.html` - Added 7th Whitelist tab button
- `apps/emails/views.py` - whitelist_add, whitelist_delete, whitelist_sender views + save_success on all tabs
- `apps/emails/urls.py` - URL patterns for whitelist endpoints
- `templates/emails/_email_detail.html` - Whitelist Sender button, AI summary display, spam badge, removed draft reply
- `templates/emails/_email_card.html` - Spam badge on cards
- `templates/emails/_sla_config.html` - Save success banner
- `templates/emails/_assignment_rules.html` - Save success banner
- `templates/emails/_category_visibility.html` - Save success banner
- `templates/emails/_inboxes_tab.html` - Save success banner
- `apps/emails/services/ai_processor.py` - Removed draft_reply from AI processing
- `apps/emails/services/dtos.py` - Removed draft_reply from TriageResult dataclass
- `apps/emails/services/fake_data.py` - Removed draft_reply from fake data
- `apps/emails/services/pipeline.py` - Removed draft_reply from pipeline save
- `apps/emails/services/spam_filter.py` - Removed draft_reply from spam filter result
- `apps/emails/tests/test_ai_processor.py` - Updated tests for removed draft_reply
- `apps/emails/tests/test_settings_views.py` - Tests for whitelist views and save feedback
- `conftest.py` - Removed draft_reply from test fixtures

## Decisions Made
- Removed AI draft reply feature entirely -- it was not useful and cluttered the detail view
- Whitelist sender un-spams all existing emails from that sender (bulk is_spam=False update)
- Removed delete confirmation ("Are you sure?") on whitelist entries for snappier UX
- Whitelist Sender returns OOB card swaps so cards update without page reload
- Spam displayed as badge/label rather than embedded in description text
- AI summary shown in email detail panel (previously only visible in card preview)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed draft reply feature**
- **Found during:** Task 3 (visual verification)
- **Issue:** Draft reply was not useful and cluttered the email detail view
- **Fix:** Removed draft_reply from UI, DTO, AI processor, pipeline, spam filter, fake data, tests, conftest
- **Files modified:** 8 files across services, templates, and tests
- **Committed in:** e4fbe90

**2. [Rule 2 - Missing Critical] Whitelist sender un-spams existing emails**
- **Found during:** Task 3 (visual verification)
- **Issue:** Whitelisting a sender should retroactively mark their existing emails as not spam
- **Fix:** Added `Email.objects.filter(from_address__iexact=...).update(is_spam=False)` in whitelist_sender view
- **Files modified:** apps/emails/views.py
- **Committed in:** e4fbe90

**3. [Rule 2 - Missing Critical] OOB swaps for whitelist action**
- **Found during:** Task 3 (visual verification)
- **Issue:** After whitelisting, email cards still showed old spam state until page reload
- **Fix:** Whitelist sender view returns OOB card swaps for all emails from same sender
- **Files modified:** apps/emails/views.py, templates/emails/_email_detail.html
- **Committed in:** e4fbe90

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical)
**Impact on plan:** All fixes improve UX and correctness. Draft reply removal simplifies codebase. No scope creep.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Settings page complete with all 7 tabs and consistent UX
- Spam whitelist fully functional (model, pipeline, settings UI, email detail button)
- Ready for Phase 3 (Branding) which touches login.html and base templates

---
*Phase: 02-settings-spam-whitelist*
*Completed: 2026-03-14*
