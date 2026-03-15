---
created: 2026-03-15T16:17:00.000Z
title: Category dropdown should be more elegant and inline
area: ui
files:
  - templates/emails/_editable_category.html
  - templates/emails/_editable_priority.html
  - templates/emails/_thread_detail.html
---

## Problem

The category/priority dropdowns appear as native browser `<select>` elements floating above the badge — looks clunky and out of place. They should be embedded inside the badge/bubble itself, styled to match the design system, and dismiss when clicking outside.

From screenshot: the LOW priority dropdown and category dropdown appear as default browser selects with up/down arrows, not as elegant inline chips.

## Solution

- Replace native `<select>` with a custom styled dropdown that appears inside/below the badge
- Match the badge styling (rounded pill, brand colors)
- Close on click-outside, Escape key
- Animate open/close (fade or slide)
- Keep the pencil-on-hover pattern but make the dropdown itself look like part of the badge
