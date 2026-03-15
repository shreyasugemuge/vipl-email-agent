---
phase: 3
slug: qa-verification
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-15
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + Django test client (regression only) |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest -x --tb=short` |
| **Full suite command** | `pytest -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every bug fix:** Run `pytest -x --tb=short`
- **After every QA wave:** Run `pytest -v`
- **Before `/gsd:verify-work`:** Full suite must be green + QA report complete
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | QA-01 | setup | `ls .planning/qa/ && grep -q '.planning/qa/' .gitignore` | N/A | ⬜ pending |
| 03-01-02 | 01 | 1 | QA-01 | manual (browser QA) | Claude-in-Chrome MCP walkthrough | N/A | ⬜ pending |
| 03-01-03 | 01 | 2 | QA-01 | manual (browser QA) | Claude-in-Chrome MCP walkthrough | N/A | ⬜ pending |
| 03-01-04 | 01 | 3 | QA-01 | manual (browser QA) | Claude-in-Chrome MCP walkthrough | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.planning/qa/` directory created for screenshots/GIFs
- [ ] `.planning/qa/` added to `.gitignore`

*Existing test infrastructure (pytest) covers regression checking.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All interactive elements work in browser | QA-01 | Entire phase IS manual browser QA | Claude-in-Chrome walks through all pages, clicks all elements, verifies responses |
| HTMX partial swaps work correctly | QA-01 | Requires real browser with JS execution | Click hx-get/hx-post elements, verify partial swap (not full page reload) |
| Mobile responsive layout correct | QA-01 | Requires viewport simulation | resize_window to 375px/768px, verify layouts |
| Console free of JS errors | QA-01 | Requires real browser console | read_console_messages after every interaction |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: regression pytest runs after every fix
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
