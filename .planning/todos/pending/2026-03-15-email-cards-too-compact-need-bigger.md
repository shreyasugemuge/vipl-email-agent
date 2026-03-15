---
created: 2026-03-15T16:28:00.000Z
title: Email/thread cards too compact — need more height and spacing
area: ui
files:
  - templates/emails/_thread_card.html
---

## Problem

Thread cards in the list view are too compact/dense. Hard to scan quickly. Need more breathing room — taller cards, more padding, better spacing between elements (sender, subject, summary, badges).

## Solution

- Increase card padding (py-3 → py-4 or more)
- Add more line-height / spacing between sender row and subject
- Consider showing more of the AI summary (2-3 lines instead of 1)
- Ensure badges don't crowd the content
- Test at different screen sizes to ensure cards are scannable at a glance
