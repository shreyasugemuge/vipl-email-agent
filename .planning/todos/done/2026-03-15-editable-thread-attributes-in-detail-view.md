---
created: 2026-03-15T11:10:00.000Z
title: Editable thread attributes in detail view
area: ui
files:
  - templates/emails/_thread_detail.html
  - apps/emails/views.py
  - apps/emails/urls.py
  - apps/emails/models.py
  - apps/emails/services/dtos.py
---

## Problem

In the thread detail view, most attributes are read-only badges. Users cannot:
1. Edit category (AI-assigned, may be wrong)
2. Edit priority/criticality (AI-assigned, may need override)
3. Add/edit/remove categories (no category management)
4. Edit any other thread attributes inline

The only editable actions are: assign, change status, whitelist sender, and edit AI summary (added in v2.4.1). Category and priority — two of the most important triage fields — are locked to whatever the AI decided.

## Solution

### 1. Inline-editable badges in detail view
Each badge in the badges row becomes clickable/editable:
- **Priority**: Click badge → dropdown with CRITICAL/HIGH/MEDIUM/LOW → POST to update
- **Category**: Click badge → dropdown with existing categories + "Custom..." option → POST to update
- **Status**: Already editable via Acknowledge/Close buttons — keep as-is

### 2. New endpoints
- `threads/<pk>/edit-priority/` — POST, updates `thread.priority`, creates ActivityLog (`PRIORITY_CHANGED`)
- `threads/<pk>/edit-category/` — POST, updates `thread.category`, creates ActivityLog (`CATEGORY_CHANGED`)

### 3. New ActivityLog actions
- `PRIORITY_CHANGED = "priority_changed", "Priority Changed"`
- `CATEGORY_CHANGED = "category_changed", "Category Changed"`

### 4. Category management (Settings page)
- Settings → Categories tab (new tab or extend existing):
  - List all categories (from `VALID_CATEGORIES` + any custom)
  - Add new category
  - Rename category (with migration of existing threads/emails)
  - Disable category (soft removal)
- Store custom categories in SystemConfig or dedicated model

### 5. UI pattern
- Badge shows current value with a tiny pencil icon on hover
- Click opens inline dropdown (same pattern as AI summary edit)
- HTMX POST → re-render detail panel with updated badge
- ActivityLog records old_value → new_value for audit trail

### 6. Feedback to AI
- When user changes priority/category, record as correction (ties into AI intelligence layer todo)
- Include in future AI prompts: "User corrected [N] emails from [old] to [new] category"
