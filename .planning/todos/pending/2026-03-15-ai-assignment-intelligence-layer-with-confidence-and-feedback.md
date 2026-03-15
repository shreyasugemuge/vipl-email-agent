---
created: 2026-03-15T10:58:00.000Z
title: AI assignment intelligence layer with confidence and feedback
area: api
files:
  - apps/emails/services/ai_processor.py
  - apps/emails/services/assignment.py
  - apps/emails/models.py
  - apps/emails/views.py
  - templates/emails/_thread_detail.html
  - templates/emails/_thread_card.html
  - prompts/triage_prompt_v2.txt
---

## Problem

The current AI assignment system has no confidence scoring, no feedback loop, and no learning from user actions:

1. **No confidence level**: `ai_suggested_assignee` is a flat dict `{name, user_id, reason}` — no confidence score. Users can't tell if the AI is 90% sure or guessing.
2. **No auto-assign**: Every suggestion requires manual Accept/Dismiss — even when AI is highly confident.
3. **No feedback loop**: When a user rejects an AI suggestion or reassigns, that signal is lost. The AI makes the same mistakes repeatedly.
4. **No learning from corrections**: Accept/reject/reassign actions should feed back into future assignment decisions.

This may require a broader intelligence layer revamp beyond just assignment.

## Solution

### 1. Confidence scoring
- Modify AI triage prompt to return `confidence: 0-100` alongside assignment suggestion
- Store in `ai_suggested_assignee` dict: `{name, user_id, reason, confidence}`
- Display confidence as a visual bar/percentage on thread detail and card badges
- Color-code: green (>80%), amber (50-80%), red (<50%)

### 2. Auto-assignment (confidence > 80%)
- New SystemConfig key: `auto_assign_threshold` (default 80)
- Pipeline: if confidence >= threshold AND assignee is active → auto-assign
- ActivityLog: `AUTO_ASSIGNED` action type with confidence in detail
- Chat notification: include "(auto-assigned, 92% confidence)" in card

### 3. Feedback model
- New `AssignmentFeedback` model:
  - thread, email, suggested_user, actual_user, action (accepted/rejected/reassigned/auto_assigned)
  - confidence_at_time, user_who_acted, timestamp
- Record on: accept AI suggestion, reject AI suggestion, manual reassign after auto-assign, manual assign when AI had a different suggestion

### 4. Learning from feedback
- Before generating assignment suggestion, query last N feedback entries for this category/priority combo
- Include in AI prompt: "Recent corrections: [user X was suggested for BILLING but admin assigned to user Y 3 times]"
- Adjust confidence based on historical accuracy for this category
- Export feedback data for offline analysis

### 5. Intelligence layer architecture
- `apps/emails/services/intelligence.py` — new service module:
  - `get_assignment_suggestion(email, team)` → `{user, confidence, reason, factors}`
  - `record_feedback(thread, suggested, actual, action)`
  - `get_accuracy_stats(category, priority)` → hit rate, common corrections
- Factors influencing confidence: category match, workload balance, past accuracy, user expertise, availability
