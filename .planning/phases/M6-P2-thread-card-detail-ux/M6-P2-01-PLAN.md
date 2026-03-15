---
phase: M6-P2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - templates/emails/_thread_card.html
  - templates/emails/_context_menu.html
autonomous: true
requirements:
  - CARD-01
  - CARD-03

must_haves:
  truths:
    - "Thread cards have visibly larger text (sender 13px, subject 13px, summary 12px, badges 9px)"
    - "Cards have more vertical padding (py-3) and gap between cards (my-1 or my-1.5)"
    - "Subject line has its own clean row without badges cluttering it"
    - "AI summary shows up to 2 lines instead of single-line 80-char truncation"
    - "Badges (priority dot, confidence dot, status, SLA, inbox) are in row 3 alongside summary area"
    - "Unread indicator dot is bigger (w-2 or w-2.5)"
    - "Context menu text is clearly readable at text-sm (14px) with bright text (slate-100 or white)"
  artifacts:
    - path: "templates/emails/_thread_card.html"
      provides: "Redesigned 3-row thread card with better spacing and badge layout"
      contains: "py-3"
    - path: "templates/emails/_context_menu.html"
      provides: "Readable context menu with larger text and better contrast"
      contains: "text-sm"
  key_links:
    - from: "templates/emails/_thread_card.html"
      to: "thread list views"
      via: "{% include %} in thread list templates"
      pattern: "thread_card"
    - from: "templates/emails/_context_menu.html"
      to: "context menu fetch endpoint"
      via: "GET /emails/threads/<pk>/context-menu/"
      pattern: "context.menu"
---

<objective>
Redesign thread cards for better spacing, information density, and readability. Fix context menu font size and contrast.

Purpose: Cards currently feel like a wall of text with cramped badges on the subject line. Context menu is hard to read. These are the most-seen UI elements.
Output: Updated card template with reorganized rows and bigger text, updated context menu with readable font.
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

@templates/emails/_thread_card.html
@templates/emails/_context_menu.html
</context>

<interfaces>
<!-- Current card structure (3 rows): -->
<!-- Row 1: sender name + email + time + msg count + assignee avatar -->
<!-- Row 2: subject + priority dot + confidence dot + status badge + inbox badges + SLA -->
<!-- Row 3: AI summary (truncated 80 chars) + spam badge + AI suggested assignee -->

<!-- Template filters used (from email_tags): -->
<!-- priority_border, priority_base, priority_tooltip, confidence_base, confidence_tooltip -->
<!-- status_base, status_tooltip, sla_color, sla_countdown, time_ago -->
<!-- thread_inbox_badges (template tag) -->
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Redesign thread card layout and sizing</name>
  <files>templates/emails/_thread_card.html</files>
  <action>
Redesign the thread card template with these specific changes per user decisions:

**Card container:**
- Change `py-2.5` to `py-3` for more vertical padding
- Change `my-0.5` to `my-1.5` for visible gap between cards

**Text sizes (bump all +1-2px):**
- Sender name: `text-[11px]` to `text-[13px]`
- Sender email: `text-[9px]` to `text-[11px]`
- Time: `text-[10px]` to `text-[11px]`
- Message count badge: `text-[9px]` to `text-[10px]`
- Subject: `text-[12px]` to `text-[13px]`
- AI summary: `text-[11px]` to `text-[12px]`
- All badges (status, spam, AI assignee, SLA): `text-[8px]` to `text-[9px]`

**Unread indicator:**
- Bigger dot: `w-1.5 h-1.5` to `w-2 h-2` (or `w-2.5 h-2.5`)

**Row reorganization — move badges from Row 2 to Row 3:**
- Row 1: Sender name + email + time + msg count + assignee avatar (same structure, bigger text)
- Row 2: Subject line ONLY — clean, no badges. Remove priority dot, confidence dot, status badge, inbox badges, SLA from this row.
- Row 3: AI summary (left, flex-1) + badges cluster (right). Badges cluster contains: priority dot, confidence dot, status badge, inbox badges, SLA countdown, spam badge, AI suggested assignee. Use `flex-wrap` if needed.

**AI summary 2-line wrap:**
- Change `truncate` to `line-clamp-2` on the AI summary span
- Remove `truncatechars:80` filter — let CSS `line-clamp-2` handle truncation naturally
- Add Tailwind classes: `line-clamp-2` (which uses `-webkit-line-clamp: 2; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden;`)

**Sender row (Claude's discretion):** Keep current layout but with larger text. The row works well — name, email, time, count, avatar.
  </action>
  <verify>
    <automated>cd /Users/uge/code/vipl-email-agent-fixes && python -c "
from django.template.loader import get_template
import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev'); django.setup()
t = get_template('emails/_thread_card.html')
src = open('templates/emails/_thread_card.html').read()
assert 'py-3' in src, 'Missing py-3 padding'
assert 'my-1.5' in src or 'my-1' in src, 'Missing card gap increase'
assert 'text-[13px]' in src, 'Missing 13px text size'
assert 'line-clamp-2' in src, 'Missing 2-line clamp on summary'
assert 'w-2' in src, 'Missing bigger unread dot'
print('All card checks pass')
"</automated>
  </verify>
  <done>Thread cards have larger text, more padding/gap, clean subject row without badges, AI summary wraps to 2 lines, badges moved to row 3, bigger unread dot.</done>
</task>

<task type="auto">
  <name>Task 2: Fix context menu readability</name>
  <files>templates/emails/_context_menu.html</files>
  <action>
Update context menu for better readability per user decisions:

**Text size:** Change all `text-[12px]` on menu items (`.ctx-item`) to `text-sm` (14px Tailwind default).

**Text contrast:** Change the container text color from `text-slate-200` to `text-slate-100` for brighter base text. This applies to the outer div's class.

**Keyboard shortcuts:** Keep the kbd elements subtle — they already use `text-slate-500 text-[10px]` which is fine for power-user hints. No change needed there.

**Padding:** Optionally bump `py-1.5` to `py-2` on each button for slightly more comfortable click targets, but this is discretionary.

Do NOT change the overall dark theme (bg-slate-800), border, or shadow — just text size and contrast.
  </action>
  <verify>
    <automated>cd /Users/uge/code/vipl-email-agent-fixes && python -c "
src = open('templates/emails/_context_menu.html').read()
assert 'text-sm' in src, 'Missing text-sm on menu items'
assert 'text-slate-100' in src or 'text-white' in src, 'Missing brighter text color'
assert 'text-[12px]' not in src, 'Old 12px text still present'
print('Context menu checks pass')
"</automated>
  </verify>
  <done>Context menu items display at 14px with high-contrast text on dark background. Keyboard shortcut hints remain subtle. Menu is effortless to read.</done>
</task>

</tasks>

<verification>
- Start dev server: `python manage.py runserver 8000`
- Navigate to thread list — cards should have noticeably more spacing and larger text
- Subject line should be on its own row without any badges
- AI summary should wrap to 2 lines on cards that have long summaries
- Right-click a card — context menu text should be clearly readable at 14px
- Verify no template syntax errors by loading the pages
</verification>

<success_criteria>
- Thread cards have comfortable spacing (py-3, my-1.5 gap)
- All card text bumped +1-2px from current sizes
- Subject row is clean — badges moved to row 3
- AI summary shows 2 lines via line-clamp-2
- Context menu text is text-sm with slate-100 contrast
- No Django template errors on page load
</success_criteria>

<output>
After completion, create `.planning/phases/M6-P2-thread-card-detail-ux/M6-P2-01-SUMMARY.md`
</output>
