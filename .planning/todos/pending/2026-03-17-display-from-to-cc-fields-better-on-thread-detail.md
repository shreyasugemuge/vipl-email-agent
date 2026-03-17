---
created: 2026-03-17T10:22:17.406Z
title: Display from to cc fields better on thread detail
area: ui
files:
  - templates/emails/_thread_detail.html
---

## Problem

The From, To, and CC fields on thread detail view need better visual presentation. Currently they are not displayed prominently or clearly enough for quick scanning. Email metadata (sender, recipients, CC) is critical context when triaging — it should be easy to read at a glance.

## Solution

Improve the layout and styling of From/To/CC fields in the thread detail panel. Consider:
- Clearer labels with consistent formatting
- Better spacing and visual hierarchy
- Possibly showing email addresses alongside display names
- Handling long recipient lists gracefully (truncation/expansion)
