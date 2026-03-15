---
phase: 1
slug: data-bug-fixes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-django |
| **Config file** | `pytest.ini` |
| **Quick run command** | `source .venv/bin/activate && pytest -x -q` |
| **Full suite command** | `source .venv/bin/activate && pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `source .venv/bin/activate && pytest -x -q`
- **After every plan wave:** Run `source .venv/bin/activate && pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | BUG-01 | unit | `pytest apps/emails/tests/test_ai_processor.py -x -k parse` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | BUG-01 | unit | `pytest apps/emails/tests/test_ai_processor.py -x -k migration` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | BUG-05 | unit | `pytest apps/emails/tests/test_views.py -x -k count` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | BUG-06 | unit | `pytest apps/emails/tests/test_branding.py -x -k title` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | BUG-02 | manual | Manual -- browser JS behavior | N/A | ⬜ pending |
| 01-02-02 | 02 | 1 | BUG-03 | manual | Manual -- CSS responsive layout | N/A | ⬜ pending |
| 01-02-03 | 02 | 1 | BUG-04 | manual | Manual -- CSS visual check | N/A | ⬜ pending |
| 01-02-04 | 02 | 1 | BUG-07 | manual | Manual -- CSS/JS visual check | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/emails/tests/test_ai_processor.py` — add tests for `_parse_suggested_assignee` with XML input (BUG-01)
- [ ] `apps/emails/tests/test_views.py` — add test that HTMX email_list response includes OOB count element (BUG-05)
- [ ] `apps/emails/tests/test_branding.py` — verify all pages have correct title pattern (BUG-06)

*Existing infrastructure covers most phase requirements. Wave 0 adds targeted test stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile panel slide-in with back button | BUG-02 | Browser JS + CSS animation behavior | Open on mobile viewport, tap card, verify full-screen panel with back button |
| Mobile filter bar stacking | BUG-03 | CSS responsive layout | Resize to <768px, toggle filters, verify vertical stacking |
| Activity chips not truncated | BUG-04 | CSS visual rendering | Check activity page on narrow viewport, verify "Priority Bump" fully visible |
| Toast positioning on mobile | BUG-07 | CSS positioning + touch gestures | Trigger toast on mobile, verify below header, test swipe-to-dismiss |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
