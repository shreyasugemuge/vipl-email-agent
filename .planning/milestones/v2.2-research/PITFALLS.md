# Domain Pitfalls

**Domain:** UI/UX polish, mobile responsiveness, toast notifications, and bug fixes for existing Django 4.2 + HTMX 2.0 + Tailwind v4 CDN email triage dashboard
**Researched:** 2026-03-15
**Confidence:** HIGH (direct codebase inspection of all templates, base.html, email_list.html, _email_detail.html, _email_card.html, activity_log.html)

---

> **Scope:** v2.2.1 UI/UX Polish & Bug Fixes pitfalls only. For v2.2 feature-addition pitfalls (OAuth, spam whitelist, branding), see git history.

---

## Critical Pitfalls

### Pitfall 1: Mobile Detail Panel Z-Index War With Toast Container and Sidebar Overlay

**What goes wrong:** The codebase currently has three overlapping fixed-position layers: sidebar overlay (`z-40`), sidebar (`z-50`), detail panel (`z-50`), and toast container (`z-[100]`). The HTMX progress bar sits at `z-[9999]`. When the mobile detail panel slides in (`fixed inset-0 z-50`), it covers the sidebar overlay (`z-40`) correctly, but toasts at `z-[100]` float above the detail panel. If a toast fires during detail panel interaction (e.g., after assigning an email), the dismiss button on the toast is clickable but the detail panel behind it is not -- the toast blocks interaction with the panel's action buttons. Worse, if the sidebar is also open (`z-50`), the detail panel and sidebar share the same z-index and render in DOM order, creating unpredictable stacking.

**Why it happens:** Z-index values were added incrementally as features shipped across phases. Nobody tested the three-layer overlap scenario (sidebar open + detail panel open + toast fires) because it requires a specific mobile interaction sequence.

**Consequences:** On mobile, users cannot interact with the detail panel action bar when a toast is visible. Dismissing the toast requires tapping its tiny X button. If the toast auto-dismisses (4 seconds), the user waits. If multiple toasts stack, the entire right side of the screen is blocked.

**Prevention:**
- Establish a z-index scale and document it in a comment at the top of `base.html`:
  - `z-30`: top bar (already correct)
  - `z-40`: overlays/backdrops
  - `z-50`: sidebar, detail panel
  - `z-60`: toast container (move DOWN from `z-[100]`)
  - `z-[9999]`: progress bar (keep)
- Move toast container to bottom-center on mobile (`bottom-4 left-1/2 -translate-x-1/2`) so it does not overlap the detail panel's action bar at the top.
- Close the sidebar when opening the detail panel on mobile -- never allow both to be open simultaneously.

**Detection:** Open sidebar on mobile, then tap an email card. Both the sidebar and detail panel appear. Open dev tools, check which element receives click events.

**Phase to address:** Phase 1 (Mobile Responsive) -- must be resolved before any new overlay/modal work.

---

### Pitfall 2: Tailwind v4 CDN Play Script Does Not Re-Process HTMX-Swapped HTML

**What goes wrong:** The project uses `@tailwindcss/browser@4` (the CDN play script). This script scans the DOM at page load and generates a `<style>` tag with only the utility classes found in the initial HTML. When HTMX swaps in new HTML (email cards after filtering, detail panel content, activity feed after filter click), any Tailwind classes in the swapped HTML that were NOT present in the initial page load will have no corresponding CSS rules. The styles simply do not apply.

Currently this works because the partials use the same class names as the initial HTML. But any new utility classes added only to partials (e.g., a new `ring-offset-2` on a focus state, or `backdrop-blur-md` on a new overlay) will silently fail -- no error, just unstyled elements.

**Why it happens:** The Tailwind CDN play script is designed for prototyping, not production HTMX apps. It runs once on DOMContentLoaded. It does have a MutationObserver that watches for DOM changes, but it only processes NEW class names if they map to Tailwind utilities it knows about. Custom `@theme` variables defined in `<style type="text/tailwindcss">` in base.html ARE available because they modify the theme config before the observer runs. But the observer's re-scan has edge cases with dynamically inserted `<style>` elements and complex selectors.

**Consequences:** New mobile-responsive classes added to partials (e.g., `md:hidden`, `sm:grid-cols-1`) may not render. The developer sees them working on full page reload but they disappear after an HTMX swap. This is the single most confusing debugging experience because the same HTML works on reload but not on HTMX navigation.

**Prevention:**
- **Test every new class by triggering an HTMX swap**, not just by reloading the page. The test flow is: load page -> trigger HTMX action -> inspect swapped element.
- Prefer classes that already exist somewhere in the initial page load. If you need `sm:px-2` in a partial, also include it (even hidden) in `base.html` so the CDN script generates the rule.
- For the v2.2.1 milestone, this is manageable because changes are small. But if the project grows, migrate to the Tailwind CLI with a build step.
- The MutationObserver in `@tailwindcss/browser@4` DOES handle most cases -- this pitfall is about edge cases with classes that use custom theme values or complex variants. Standard responsive prefixes (`sm:`, `md:`, `lg:`) work correctly with the observer.

**Detection:** After adding a new class to a partial, trigger an HTMX swap. If the element is unstyled, check the browser's `<style>` tag generated by Tailwind -- search for the class name. If missing, the CDN script did not generate it.

**Phase to address:** All phases -- every template change must be HTMX-swap-tested.

---

### Pitfall 3: AI Summary XML Markup Rendering as Raw Text in Email Cards

**What goes wrong:** The `ai_summary` field from Claude AI triage sometimes contains XML-like markup (e.g., `<suggestion>assign to sales</suggestion>` or `<priority>HIGH</priority>`) because the AI prompt instructs structured output. In `_email_card.html` line 34, `{{ email.ai_summary }}` is auto-escaped by Django's template engine, so `<suggestion>` renders as the literal text `&lt;suggestion&gt;` in the browser. This is safe (no XSS) but ugly -- users see raw XML tags in the card summary.

**Why it happens:** The triage prompt returns structured data mixed with natural language. The `ai_summary` field stores the raw AI response without stripping XML tags. Django's auto-escaping correctly prevents injection but does not strip the markup.

**Consequences:** Cards show cluttered summaries with visible XML tags. This is the bug explicitly called out in the milestone requirements.

**Prevention:**
- Strip XML/HTML tags from `ai_summary` before saving to the database, or in the template via a custom filter. A simple regex `re.sub(r'<[^>]+>', '', text)` in a template filter or in the `ai_processor` service before saving is sufficient.
- Do NOT use `|safe` on `ai_summary` -- that would execute the XML as HTML, creating injection risk if the AI ever outputs `<script>` (prompt injection).
- Add a `strip_tags` template filter (Django has a built-in `striptags` filter: `{{ email.ai_summary|striptags }}`). This is the simplest fix.
- Long-term, fix the AI prompt to return plain text summaries separate from structured data.

**Detection:** Search for emails where `ai_summary` contains `<` characters.

**Phase to address:** Phase 1 (Bug Fixes) -- simple template filter fix.

---

## Moderate Pitfalls

### Pitfall 4: Mobile Filter Toggle Creates Inline Layout Bugs

**What goes wrong:** The current `toggleFilters()` function in `email_list.html` (line 205-214) toggles `hidden`/`flex` on the `#mobile-filters` div and dynamically adds `flex-wrap`, `py-2`, `border-t`, `border-slate-100` classes. But the filters container is a child of a `flex items-center gap-5` parent. When filters expand on mobile, the flex parent does not wrap -- filters overflow horizontally off-screen because the parent has no `flex-wrap`. The search input and 4 `<select>` elements need ~600px minimum width but a mobile screen is 375px.

**Prevention:**
- On mobile, show filters as a stacked column below the tab bar, not inline. Use `flex-col` inside the filters container, and make each `<select>` full-width (`w-full`).
- Better: use a slide-down panel or bottom sheet pattern for mobile filters instead of toggling visibility inside a horizontal flex row.
- The search input needs special handling -- on mobile it should be full-width, not `w-44` (line 115).

**Phase to address:** Phase 1 (Mobile Responsive Filters).

---

### Pitfall 5: HTMX Target Mismatch After Assignment From Card vs Detail Panel

**What goes wrong:** The assign form in `_email_card.html` (line 137) targets `hx-target="#card-{{ email.pk }}"` with `hx-swap="outerHTML"`. The assign form in `_email_detail.html` (line 137) targets `hx-target="#card-{{ email.pk }}"` -- the CARD element in the list, not the detail panel. After assignment from the detail panel, the card updates but the detail panel still shows the old assignment state. The user sees stale data in the panel they are actively looking at.

**Why it happens:** The card and detail panel are separate HTMX targets. Updating one does not update the other. The `hx-swap-oob` attribute on cards (line 4 of `_email_card.html`) enables out-of-band swaps, but the assignment response only returns the updated card HTML, not the updated detail HTML.

**Prevention:**
- When assignment happens from the detail panel, the response should return BOTH the updated detail panel HTML AND an OOB-swapped card. The Django view should detect whether the request came from the detail panel (via an `HX-Target` header check or a hidden input) and include the card with `hx-swap-oob="outerHTML"` in the response.
- Alternatively, after a successful assignment from the detail panel, re-fetch the detail panel content via a client-side `htmx.trigger()` event.
- Test: assign from detail panel, then check -- does the detail panel show the new assignee? Does the card in the list update?

**Phase to address:** Phase 2 (HTMX Integration Polish).

---

### Pitfall 6: Toast Auto-Dismiss Timer Fires During Page Transitions

**What goes wrong:** The toast auto-dismiss script (base.html line 292-298) sets `setTimeout` at 4000ms + 500ms per toast index. If the user navigates away via HTMX before the timeout fires, the callback runs against a DOM element that has been removed or replaced by the HTMX swap. This causes a silent error (`Cannot read properties of null: 'style'`) that breaks subsequent JavaScript on the page. Additionally, Django messages are session-based -- after an HTMX swap that returns a full page (not a partial), the messages may re-render, creating duplicate toasts.

**Prevention:**
- Check if the toast element still exists before animating: `if (toast && toast.parentNode) { ... }`.
- Clear all toast timeouts on `htmx:beforeSwap` to prevent callbacks firing on stale DOM.
- For HTMX responses, use `HX-Trigger` response headers to fire client-side toast events instead of relying on Django's `messages` framework (which is session-based and persists across requests until rendered).

**Phase to address:** Phase 1 (Toast Improvements).

---

### Pitfall 7: Welcome Toast / First-Login Onboarding Overlay Accessibility

**What goes wrong:** A welcome toast or onboarding overlay for first-time users needs to be dismissible via keyboard (Escape key), announced by screen readers (`role="dialog"`, `aria-modal="true"`), and must not trap focus if it is non-modal. The current toast container has `role="status"` and `aria-live="polite"` (correct for transient notifications) but an onboarding overlay is NOT a status message -- it is a dialog that requires user interaction.

**Prevention:**
- If building a welcome toast (auto-dismissing): keep `role="status"` and `aria-live="polite"`. Add `aria-label` with the message text.
- If building an onboarding overlay/modal: use `role="dialog"`, `aria-modal="true"`, trap focus inside the dialog, dismiss on Escape key, return focus to the trigger element on close.
- Do NOT reuse the toast container for modal-like overlays. They have fundamentally different ARIA semantics.
- Track "has seen onboarding" server-side on the User model (a `BooleanField`), not in `localStorage` -- the user may log in from a different device.

**Phase to address:** Phase 2 (Welcome / Onboarding Experience).

---

### Pitfall 8: Email Count Accuracy Across View Filters

**What goes wrong:** The stat counters in the stats bar (Total, Unassigned, Urgent, Pending) are computed from `dash_stats` context variable which reflects the UNFILTERED queryset. But the "X emails" label at the right of the filter bar (line 156: `{{ total_count }} email{{ total_count|pluralize }}`) reflects the FILTERED queryset. When a user selects "Status: New" filter, the stat cards still show total counts across all statuses, while the email count shows only "new" emails. This is confusing -- are there 47 total emails or 12?

**Prevention:**
- Make it clear that stat cards are always "all emails" summaries (add a subtle "all" label) and the filter count is the filtered result.
- OR update stat cards to reflect the current filter state -- but this adds complexity and may confuse users who expect the dashboard to show the big picture.
- The simplest fix: add "of X total" to the filtered count label, e.g., "12 of 47 emails".

**Phase to address:** Phase 1 (Email Count Accuracy).

---

## Minor Pitfalls

### Pitfall 9: CSS Animation Performance on Low-End Mobile

**What goes wrong:** The codebase uses `box-shadow` transitions on card hover (`.card-hover`), `backdrop-blur-sm` on the sidebar overlay, and `animate-pulse` on the "Online" indicator. `backdrop-blur` is expensive on mobile GPUs and causes frame drops during sidebar open/close transitions on older Android devices. `box-shadow` transitions trigger paint operations and can cause jank during scroll if many cards are visible.

**Prevention:**
- Replace `backdrop-blur-sm` with a solid semi-transparent background (`bg-slate-900/60` is already there, remove the blur).
- Use `will-change: transform` on the sidebar and detail panel to promote them to compositor layers.
- The `animate-pulse` on the online indicator is fine -- it is a single small element.
- Test on a throttled CPU (Chrome DevTools > Performance > 4x slowdown) to simulate low-end mobile.

**Phase to address:** Phase 2 (Visual Polish).

---

### Pitfall 10: Page Title Inconsistency Across Templates

**What goes wrong:** Some pages override `{% block title %}` and `{% block page_title %}` separately (e.g., `email_list.html` sets both), while others may only set one. The `<title>` tag (browser tab) and the header `<h1>` can show different text. This is not a bug but a polish issue that undermines the "premium feel" goal.

**Prevention:**
- Audit all templates extending `base.html`. Ensure every template sets both `{% block title %}VIPL Triage | [Page Name]{% endblock %}` and `{% block page_title %}[Page Name]{% endblock %}`.
- Consider a pattern where `page_title` drives both: define `page_title` as a template variable and use it in both blocks.

**Phase to address:** Phase 1 (Page Title Consistency) -- simple find-and-fix.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Mobile responsive detail panel | Z-index collision with toast and sidebar (Pitfall 1) | Establish z-index scale, close sidebar on detail open |
| Mobile responsive filters | Filters overflow horizontally (Pitfall 4) | Stack filters vertically on mobile, full-width inputs |
| AI summary XML bug fix | Using `|safe` instead of `|striptags` creates XSS risk (Pitfall 3) | Use Django's built-in `striptags` filter, never `|safe` on AI output |
| Toast improvements | Auto-dismiss fires on stale DOM after HTMX swap (Pitfall 6) | Null-check elements, clear timeouts on `htmx:beforeSwap` |
| Welcome / onboarding | Wrong ARIA role on modal overlay (Pitfall 7) | Toast = `role="status"`, modal = `role="dialog"` with focus trap |
| Email count accuracy | Stat cards vs filter count confusion (Pitfall 8) | Add "of X total" to filtered count label |
| HTMX assignment sync | Detail panel shows stale data after card assignment (Pitfall 5) | Return OOB-swapped card + updated detail panel in assignment response |
| CSS animation polish | `backdrop-blur` causes mobile frame drops (Pitfall 9) | Remove blur, use solid semi-transparent overlay |

---

## "Looks Done But Isn't" Checklist

- [ ] **Mobile detail panel:** Open detail panel on mobile, then open sidebar -- they must NOT overlap. Close one before opening the other.
- [ ] **Mobile filters:** Toggle filters on a 375px screen -- all 4 dropdowns and search must be usable without horizontal scroll.
- [ ] **AI summary:** Find an email with XML in `ai_summary` (search DB for `<` in that field) and verify tags are stripped in the card view.
- [ ] **Toast + detail panel:** On mobile, trigger a toast while the detail panel is open -- toast must not block the panel's action buttons.
- [ ] **Toast dismiss:** Navigate via HTMX while a toast is visible -- no console errors after navigation.
- [ ] **HTMX assignment:** Assign from detail panel, verify BOTH the card in the list AND the detail panel update.
- [ ] **Tailwind classes:** Add a new responsive class to a partial, trigger an HTMX swap, verify it renders (not just on page reload).
- [ ] **Page titles:** Check every page's browser tab title AND header h1 -- they must be consistent.
- [ ] **Activity filter overflow:** On mobile, the filter chips row must scroll horizontally without pushing content off-screen (currently uses `overflow-x-auto` -- verify it works).
- [ ] **Email count:** Apply a filter, verify the count label matches the visible emails, not the unfiltered total.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Z-index collision blocks interaction | LOW | Adjust z-index values in base.html, redeploy |
| Tailwind class not rendering after HTMX swap | LOW | Add class to base.html hidden element as a "seed", or use inline style as fallback |
| `|safe` used on AI summary (XSS) | HIGH | Immediately revert to `|striptags`, audit for any stored XSS payloads in `ai_summary` field |
| Toast timeout causes JS error, breaks page | LOW | Add null-check guard, redeploy |
| Onboarding overlay traps keyboard | LOW | Add Escape key handler and focus return logic |
| Detail panel stale after assignment | LOW | Add OOB swap to assignment view response |

---

## Sources

- Direct codebase inspection: `templates/base.html` (z-index values, toast system, progress bar), `templates/emails/email_list.html` (mobile detail panel, filter toggle, stats bar), `templates/emails/_email_detail.html` (assignment form targets), `templates/emails/_email_card.html` (OOB swap, HTMX targets), `templates/emails/activity_log.html` (filter chips) -- HIGH confidence
- [Tailwind CSS v4 CDN play script source](https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4) -- MutationObserver behavior verified via source inspection -- HIGH confidence
- [HTMX documentation: hx-swap-oob](https://htmx.org/attributes/hx-swap-oob/) -- HIGH confidence
- [WAI-ARIA Authoring Practices: Dialog Modal](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) -- HIGH confidence
- [MDN: backdrop-filter performance](https://developer.mozilla.org/en-US/docs/Web/CSS/backdrop-filter) -- HIGH confidence

---
*Pitfalls research for: v2.2.1 UI/UX Polish & Bug Fixes*
*Researched: 2026-03-15*
