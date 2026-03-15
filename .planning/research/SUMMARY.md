# Project Research Summary

**Project:** VIPL Email Agent v2.2.1 UI/UX Polish & Bug Fixes
**Domain:** Django + HTMX + Tailwind v4 email triage dashboard — mobile responsiveness, bug fixes, and polish
**Researched:** 2026-03-15
**Confidence:** HIGH

## Executive Summary

This milestone is a polish-and-fix pass on a fully functional v2.2 dashboard. The codebase is a server-rendered Django 4.2 app with HTMX 2.0 for partial updates and Tailwind CSS v4 via CDN browser script. All research confirms zero new dependencies are required — every feature in scope is achievable with template/CSS/JS changes to existing files. The most important finding is that the existing implementation is nearly correct on mobile; the issues are CSS positioning bugs and missing edge-case handling rather than architectural gaps.

The recommended approach is to sequence work as: (1) backend data fixes first since they are independent and self-contained, (2) mobile layout fixes next since they are CSS-only and testable by resizing a browser, (3) polish features last since they are purely additive. This ordering minimizes risk — each phase can ship independently without breaking anything from the prior phase. The only genuinely new integration pattern introduced is the HTMX `HX-Trigger` response header for firing client-side toast events from HTMX partial swaps, which is a built-in HTMX 2.0 capability requiring no new library.

The primary risk area is z-index layering on mobile where three overlapping fixed-position layers (sidebar, detail panel, toast container) were built incrementally and have undocumented interaction bugs. This must be addressed before any other overlay work or mobile testing will produce reliable results. The secondary risk is the Tailwind v4 CDN play script's MutationObserver behavior — any new utility classes added only to HTMX-swapped partials must be tested via swap (not page reload) to confirm they render.

## Key Findings

### Recommended Stack

Zero new dependencies for v2.2.1. The existing stack — Django 4.2 LTS, HTMX 2.0.8 (CDN), Tailwind CSS v4 (CDN browser script), django-htmx, nh3 — covers all feature requirements. The only new integration pattern is `HX-Trigger` response headers for HTMX-triggered toasts, which is built into HTMX 2.0 core and requires only ~20 lines of vanilla JS in `base.html`.

**Core technologies:**
- **Django 4.2 LTS**: Backend views and data layer — unchanged
- **HTMX 2.0.8**: Partial page updates, OOB swaps, lifecycle events (`htmx:afterSwap`, `htmx:beforeSwap`) — `HX-Trigger` header is the one new pattern used
- **Tailwind CSS v4 CDN**: All responsive utilities (sm/md/lg breakpoints, grid, flex, animate-pulse) already available
- **Vanilla JS (inline)**: All JS lives in `{% block extra_js %}` — no framework additions

**What NOT to add:** Intro.js, Alpine.js, htmx-ext-class-tools, htmx-ext-sse, django-htmx-messages-framework, Tailwind CLI/PostCSS. Each was evaluated and rejected as overkill for a 4-user internal tool.

### Expected Features

**Must fix (bugs — table stakes):**
- **AI summary XML markup stripping** — raw tags render in every email card; fix in `ai_processor.py` before DB save with `re.sub(r'<[^>]+>', '', text)`
- **Mobile detail panel** — slide-in mechanism exists but CSS positioning has bugs; panel is non-functional on phones
- **Mobile filter bar layout** — 5 inputs in a non-wrapping flex row overflow on 375px screens
- **Email count label clarity** — "12 emails" vs "12 of 47 emails" confusion when filters are active

**Should fix (polish users will notice):**
- Activity page filter chip overflow — `flex-wrap` instead of horizontal scroll on mobile
- Toast positioning on mobile — move below header bar, increase close button touch target to 44px
- Page title consistency — audit all templates for `VIPL Triage | [Page]` pattern

**Nice to have (differentiators, defer if time-constrained):**
- Welcome banner on first login — session flag + existing toast system, no schema change
- Active filter indicators — count badge and clear-all link
- Stat cards scroll snap — one CSS line (`snap-x snap-mandatory`)

**Defer entirely:** PWA, client-side search, dark mode, drag-and-drop, real-time websockets, inline reply composer. All overkill for 4-5 concurrent users.

### Architecture Approach

The architecture is stable and well-suited to this milestone. All v2.2.1 changes are modifications to existing components — no new templates, no new URL routes, no new models, no migrations. The data flow (user action → HTMX request → Django view → partial swap + OOB sync) must be preserved for all changes. The three key patterns to follow are: (1) HTMX OOB swaps for cross-component sync after mutations, (2) mobile-first Tailwind responsive classes (base → `md:` override), (3) Django messages framework for transient feedback rather than custom notification systems.

**Components touched in this milestone:**
1. `apps/emails/services/ai_processor.py` — strip XML from AI response before DB save
2. `apps/emails/templatetags/email_tags.py` — `strip_xml` template filter as defense-in-depth
3. `templates/emails/email_list.html` — mobile layout for stats bar, filter section, count label, body scroll lock
4. `templates/emails/activity_log.html` — filter chip wrapping on mobile
5. `apps/accounts/adapters.py` — welcome message on first login via Django messages
6. `apps/emails/views.py` — `has_active_filters` context bool for count label

### Critical Pitfalls

1. **Z-index collision on mobile (sidebar + detail panel + toast)** — three `z-50` elements were built incrementally with no documented scale. Establish a z-index scale in `base.html` comments: overlays=`z-40`, panels/sidebar=`z-50`, toasts=`z-60`. Move toast container to bottom-center on mobile. Close sidebar when opening detail panel.

2. **Tailwind CDN play script does not re-process HTMX-swapped HTML** — new classes added only to partials may have no CSS rules after an HTMX swap. Prevention: test every template change by triggering an HTMX swap, not just a page reload. Add new classes to `base.html` as hidden seeds if needed.

3. **`|safe` filter on AI summary creates XSS risk** — never use `|safe` on `ai_summary`. Use Django's built-in `striptags` filter in templates and strip at data source in `ai_processor.py`. The primary fix is at the data layer; template filter is defense-in-depth only.

4. **Toast auto-dismiss fires on stale DOM after HTMX navigation** — `setTimeout` callbacks run against removed elements. Guard with null-check (`if (toast && toast.parentNode)`), and clear all toast timeouts on `htmx:beforeSwap`.

5. **HTMX assignment from detail panel leaves stale state** — assigning from the detail panel updates the card list via OOB swap but the detail panel itself shows old data. Assignment response must return both the updated card (OOB) AND the updated detail panel content.

## Implications for Roadmap

Based on research, a 3-phase structure matches the dependency graph and risk profile.

### Phase 1: Data & Bug Fixes
**Rationale:** Backend data fixes are independent of all UI work and have the highest user-visible impact. Starting here unblocks template work (the XML bug affects every email card) and carries zero risk of breaking existing functionality.
**Delivers:** Clean data at rest, accurate email counts, consistent page titles
**Addresses:** AI summary XML bug, email count label clarity, page title consistency
**Avoids:** XSS risk from incorrect `|safe` usage (Pitfall 3); stale DOM toast errors (Pitfall 6)
**Files:** `ai_processor.py`, `email_tags.py`, `views.py`, title-related templates

### Phase 2: Mobile Layout
**Rationale:** CSS and HTML restructuring — completely independent of Phase 1 data fixes (can be done in parallel or sequentially). Mobile layout changes are testable by resizing a browser window and cannot break desktop behavior if Tailwind breakpoints are applied correctly. Must address z-index scale before any overlay testing.
**Delivers:** Functional mobile experience — usable detail panel, accessible filter bar, readable stat cards, working activity filter chips
**Addresses:** Mobile detail panel, mobile filter bar, stats bar grid, activity filter overflow
**Avoids:** Z-index collision (Pitfall 1), Tailwind CDN HTMX swap edge cases (Pitfall 2), filter overflow (Pitfall 4)
**Files:** `email_list.html`, `activity_log.html`, `_email_detail.html`, `base.html` (z-index scale)

### Phase 3: Polish & UX Improvements
**Rationale:** Purely additive features — cannot break anything in Phase 1 or 2. Welcome experience depends on the toast system working correctly (established in Phase 2). Active filter indicators build on the filter layout from Phase 2.
**Delivers:** Toast improvements (mobile positioning, HTMX-triggered toasts), welcome banner for new team members, active filter indicators, stat card scroll snap
**Addresses:** Toast positioning, welcome experience, active filter indicators, stat cards scroll snap
**Avoids:** Wrong ARIA role on onboarding overlay (Pitfall 7); detail panel stale after assignment (Pitfall 5); backdrop-blur mobile performance (Pitfall 9)
**Files:** `base.html` (toast JS), `adapters.py`, `email_list.html` (filter indicators)

### Phase Ordering Rationale

- Data fix first because the XML bug is visible on every email card and fixing it at the source (`ai_processor.py`) makes template work cleaner
- Mobile layout second because it is CSS-only and completely reversible — no state, no migrations, no service calls
- Polish third because it depends on Phase 2's mobile layout (filter indicators, toast positioning) being stable
- This order also matches risk profile: backend fix (lowest risk) → CSS (low risk) → additive JS features (lowest risk)

### Research Flags

No phase requires a `/gsd:research-phase` deep dive. All patterns are either already in the codebase or documented with working code examples in STACK.md.

Phases with well-documented patterns (skip research-phase for planning):
- **Phase 1 (Data Fixes):** Pure Python regex strip and Django template filters — standard, no research needed
- **Phase 2 (Mobile Layout):** Tailwind responsive classes and HTMX lifecycle events — thoroughly documented in existing codebase
- **Phase 3 (Polish):** `HX-Trigger` pattern is new but fully documented in HTMX 2.0 docs — STACK.md has the exact code pattern

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Firsthand codebase analysis; all existing packages verified; zero new deps needed |
| Features | HIGH | Features derived from direct code inspection + WCAG standards; no guesswork |
| Architecture | HIGH | Complete template and view analysis; component boundaries verified from running code |
| Pitfalls | HIGH | Pitfalls identified via direct inspection of z-index values, JS timers, and HTMX targets |

**Overall confidence:** HIGH

### Gaps to Address

- **Tailwind CDN MutationObserver edge cases:** STACK.md notes the observer handles standard responsive prefixes correctly but has edge cases with custom `@theme` variables and complex variants. Validate each new responsive class in a real HTMX swap during implementation.
- **Welcome toast vs. onboarding banner decision:** Research documents both approaches (Django messages = simple, localStorage cookie = richer). Decision deferred to planning — either works; choose based on desired richness.
- **HTMX assignment OOB fix scope:** Pitfall 5 (stale detail panel after assignment) may affect multiple views (assign, claim, status change). Scope of fix needs verification during Phase 3 implementation.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `base.html`, `email_list.html`, `_email_card.html`, `_email_detail.html`, `_email_list_body.html`, `activity_log.html`, `views.py`, `ai_processor.py`, `adapters.py`
- [HTMX 2.0 Animations and Class Lifecycle](https://htmx.org/examples/animations/) — htmx-settling, htmx-swapping, htmx-added behavior
- [HTMX hx-swap-oob](https://htmx.org/attributes/hx-swap-oob/) — out-of-band swap behavior
- [Tailwind CSS v4 Responsive Design](https://tailwindcss.com/docs/responsive-design) — sm/md/lg/xl/2xl breakpoints
- [WAI-ARIA Dialog Modal Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) — ARIA semantics for welcome overlay

### Secondary (MEDIUM confidence)
- [Django HTMX Toast Pattern](https://blog.benoitblanchon.fr/django-htmx-toasts/) — HX-Trigger header pattern for toast notifications
- [Django HTMX Messages Framework](https://joshkaramuth.com/blog/django-messages-toast-htmx/) — pattern reference (library not recommended)

### Tertiary (LOW confidence)
- Tailwind CDN play script MutationObserver behavior — inferred from source inspection; edge cases in complex variants not fully documented

---
*Research completed: 2026-03-15*
*Ready for roadmap: yes*
