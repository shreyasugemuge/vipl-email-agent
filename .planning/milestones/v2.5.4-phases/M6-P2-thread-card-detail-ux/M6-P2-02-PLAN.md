---
phase: M6-P2
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - templates/emails/_editable_priority.html
  - templates/emails/_editable_category.html
  - templates/emails/_thread_detail.html
autonomous: true
requirements:
  - CARD-02
  - CARD-04

must_haves:
  truths:
    - "Priority dropdown renders as a colored pill with hidden caret that appears on hover"
    - "Category dropdown renders as a styled pill with hidden caret that appears on hover"
    - "Clicking the pill opens native <select> dropdown (not custom popover)"
    - "HTMX submit on change still works for both priority and category"
    - "AI draft reply section has a copy-to-clipboard button"
    - "Draft reply is only shown when thread.ai_draft_reply is non-empty"
  artifacts:
    - path: "templates/emails/_editable_priority.html"
      provides: "Pill-styled priority select with hover caret"
      contains: "select"
    - path: "templates/emails/_editable_category.html"
      provides: "Pill-styled category select with hover caret"
      contains: "select"
    - path: "templates/emails/_thread_detail.html"
      provides: "AI draft reply section with copy button"
      contains: "clipboard"
  key_links:
    - from: "templates/emails/_editable_priority.html"
      to: "emails:edit_priority"
      via: "HTMX hx-post on select change"
      pattern: "hx-post.*edit_priority"
    - from: "templates/emails/_editable_category.html"
      to: "emails:edit_category"
      via: "HTMX hx-post on select change"
      pattern: "hx-post.*edit_category"
    - from: "templates/emails/_thread_detail.html"
      to: "thread.ai_draft_reply"
      via: "conditional display + copy button"
      pattern: "ai_draft_reply"
---

<objective>
Replace badge-to-select toggle dropdowns with styled pill selects, and add a copy-to-clipboard button on the AI draft reply section.

Purpose: Current dropdowns require a mode switch (click badge -> see dropdown). Pill selects are always interactive. The AI draft's main workflow is copy-paste into Gmail — a copy button saves manual selection.
Output: Pill-styled priority/category selects, AI draft with copy button.
</objective>

<execution_context>
@/Users/uge/.claude/get-shit-done/workflows/execute-plan.md
@/Users/uge/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M6-P2-thread-card-detail-ux/M6-P2-CONTEXT.md

@templates/emails/_editable_priority.html
@templates/emails/_editable_category.html
@templates/emails/_thread_detail.html
</context>

<interfaces>
<!-- Current editable priority: badge (display) + hidden select (edit mode), toggled by click/pencil -->
<!-- Current editable category: badge (display) + hidden select (edit mode) + custom input fallback -->
<!-- Both use HTMX hx-post on change, hx-target="#thread-detail-panel", hx-swap="innerHTML" -->

<!-- Priority colors from email_tags: priority_base filter returns color name (red, amber, yellow, blue, slate) -->
<!-- Category styling: neutral bg-slate-100 text-slate-500 -->

<!-- AI draft reply: currently in a <details> (collapsed by default) with font-mono whitespace-pre-wrap -->
<!-- Condition: {% if thread.ai_draft_reply %} -->

<!-- Template filters available: priority_base, priority_tooltip -->
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Convert priority and category to pill-style selects</name>
  <files>templates/emails/_editable_priority.html, templates/emails/_editable_category.html</files>
  <action>
**Replace the current badge-display + hidden-select toggle pattern with a single styled `<select>` that looks like a pill.**

Per user decisions: native `<select>` with colored background, rounded, subtle caret indicator hidden by default and revealed on hover. No custom popover. HTMX submit on change (same behavior).

**Priority pill (`_editable_priority.html`):**
- Remove the display-mode badge span and pencil button entirely
- Remove the `.pri-edit` wrapper div and its hidden class toggle JS
- Replace with a single styled `<select>` that IS the pill:
  - Appearance: `appearance-none` to hide browser default caret
  - Colors: `bg-{{ thread.priority|priority_base }}-50 text-{{ thread.priority|priority_base }}-700 border border-{{ thread.priority|priority_base }}-200/50`
  - Shape: `rounded-full px-2.5 py-0.5` (pill shape)
  - Text: `text-[10px] font-bold uppercase tracking-wider`
  - Cursor: `cursor-pointer`
  - HTMX: `hx-post="{% url 'emails:edit_priority' thread.pk %}" hx-target="#thread-detail-panel" hx-swap="innerHTML" hx-trigger="change"` with `{% csrf_token %}` in wrapping form
- Add a custom caret indicator using a pseudo-element or a sibling SVG:
  - Use a wrapper div with `group/pri` class
  - Add a small chevron SVG (`w-2.5 h-2.5`) positioned with `opacity-0 group-hover/pri:opacity-100 transition-opacity`
  - Or use CSS: `background-image: url("data:...")` on hover via group variant
- Keep the loading spinner indicator

**Category pill (`_editable_category.html`):**
- Same pattern as priority but with neutral colors: `bg-slate-100 text-slate-600 border border-slate-200/50`
- Rounded-full, appearance-none, hover caret
- Keep the custom category `__custom__` option and the text input fallback (the `onchange` handler for `__custom__` must stay)
- The custom input should appear below/beside the select when "Custom..." is chosen
- HTMX behavior unchanged

**Important:** Status dropdowns (CARD-02 decision) are NOT changed — only priority and category. The `_editable_status.html` file is not touched.

**Structure for both files:**
```html
<div class="group/xxx inline-flex items-center gap-0.5" id="editable-xxx">
  <form hx-post="..." hx-target="..." hx-swap="..." hx-indicator="...">
    {% csrf_token %}
    <select name="xxx" class="appearance-none [pill classes] cursor-pointer"
            hx-trigger="change" hx-post="..." hx-target="..." hx-swap="..."
            hx-include="closest form">
      {% for item in items %}
      <option ...>{{ item }}</option>
      {% endfor %}
    </select>
  </form>
  <!-- Hover caret -->
  <svg class="w-2.5 h-2.5 text-slate-400 opacity-0 group-hover/xxx:opacity-100 transition-opacity pointer-events-none" ...>
    <path d="M6 9l6 6 6-6"/>
  </svg>
  <!-- Loading spinner -->
  <span id="xxx-loading" class="htmx-indicator ml-1">...</span>
</div>
```
  </action>
  <verify>
    <automated>cd /Users/uge/code/vipl-email-agent-fixes && python -c "
pri = open('templates/emails/_editable_priority.html').read()
cat = open('templates/emails/_editable_category.html').read()
# Priority checks
assert 'appearance-none' in pri, 'Priority: missing appearance-none'
assert 'rounded-full' in pri or 'rounded-lg' in pri, 'Priority: missing pill shape'
assert 'group-hover' in pri, 'Priority: missing hover caret'
assert 'hx-post' in pri, 'Priority: missing HTMX post'
assert 'csrf_token' in pri, 'Priority: missing CSRF token'
# Category checks
assert 'appearance-none' in cat, 'Category: missing appearance-none'
assert 'rounded-full' in cat or 'rounded-lg' in cat, 'Category: missing pill shape'
assert 'group-hover' in cat, 'Category: missing hover caret'
assert '__custom__' in cat, 'Category: missing custom option'
assert 'hx-post' in cat, 'Category: missing HTMX post'
print('Pill dropdown checks pass')
"</automated>
  </verify>
  <done>Priority and category display as colored pill-shaped selects. No badge-to-edit toggle — the pill IS the select. Caret appears on hover. HTMX change submission works. Custom category fallback preserved.</done>
</task>

<task type="auto">
  <name>Task 2: Add copy-to-clipboard button on AI draft reply</name>
  <files>templates/emails/_thread_detail.html</files>
  <action>
Modify the existing AI draft reply `<details>` section (around line 322-342) to add a copy-to-clipboard button.

**Changes to the draft reply section:**

1. In the `<summary>` bar, add a copy button to the right side (before the chevron):
```html
<button type="button"
        class="text-[11px] text-slate-400 hover:text-primary-600 transition-colors flex items-center gap-1"
        onclick="event.stopPropagation(); navigator.clipboard.writeText(this.closest('details').querySelector('.draft-content').textContent.trim()).then(() => { this.querySelector('.copy-label').textContent = 'Copied!'; setTimeout(() => this.querySelector('.copy-label').textContent = 'Copy', 1500); })"
        title="Copy draft to clipboard">
    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
    </svg>
    <span class="copy-label">Copy</span>
</button>
```

2. Add `draft-content` class to the draft text div so the copy button can find it:
   Change the inner div to include `class="draft-content bg-slate-50 ..."`

3. **Visibility (Claude's discretion):** Keep the `<details>` collapsed by default. The section header "Draft Reply" is clear enough. Users who want the draft will expand it, then use the copy button. The copy button in the summary bar is visible even when collapsed, allowing copy-without-expand if we add the `open` attribute — but collapsed default is cleaner.

4. Ensure the copy button uses `event.stopPropagation()` so clicking it doesn't toggle the details open/closed.

5. Keep the existing condition `{% if thread.ai_draft_reply %}` — draft section only shows when content exists.

6. Keep the existing font-mono whitespace-pre-wrap styling on the draft content.
  </action>
  <verify>
    <automated>cd /Users/uge/code/vipl-email-agent-fixes && python -c "
src = open('templates/emails/_thread_detail.html').read()
assert 'clipboard' in src, 'Missing clipboard copy functionality'
assert 'draft-content' in src, 'Missing draft-content class for copy target'
assert 'Copy' in src, 'Missing Copy label'
assert 'stopPropagation' in src, 'Missing stopPropagation on copy button'
assert 'ai_draft_reply' in src, 'Missing ai_draft_reply condition'
print('AI draft copy button checks pass')
"</automated>
  </verify>
  <done>AI draft reply section has a copy-to-clipboard button visible in the summary bar. Clicking Copy puts the draft text on the clipboard with "Copied!" feedback. Draft only shows when ai_draft_reply is non-empty. Button does not interfere with details toggle.</done>
</task>

</tasks>

<verification>
- Start dev server: `python manage.py runserver 8000`
- Open a thread detail panel — priority and category should display as colored pills
- Hover over pills — a subtle caret should appear
- Click a pill — native select dropdown opens with options
- Change a value — HTMX submits and panel refreshes
- For category, select "Custom..." — text input should appear
- If thread has ai_draft_reply, "Draft Reply" section should have a Copy button
- Click Copy — draft text should be on clipboard, button briefly shows "Copied!"
</verification>

<success_criteria>
- Priority renders as colored pill select (not badge + hidden dropdown)
- Category renders as neutral pill select with custom option preserved
- Hover reveals caret on both pills
- HTMX change submission works for both
- AI draft reply has working copy-to-clipboard button
- No template errors on page load
</success_criteria>

<output>
After completion, create `.planning/phases/M6-P2-thread-card-detail-ux/M6-P2-02-SUMMARY.md`
</output>
