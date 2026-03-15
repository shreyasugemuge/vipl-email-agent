# Feature Landscape: v2.5.0 Intelligence + UX

**Domain:** AI email triage -- intelligence layer and UX completeness
**Researched:** 2026-03-15

## Table Stakes

Features that complete the product. Without these, the system feels like a prototype.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Read/unread tracking | Every inbox has this. Users need to know what they haven't seen. | Low | M2M-through model + CSS indicator |
| Inline-editable category/priority | Users will correct AI mistakes. Must be frictionless. | Low | HTMX click-to-edit, official pattern |
| Mark as spam / not-spam | Users need to correct spam filter without admin access. | Low | Button + SpamFeedback model |
| Basic analytics (volume, response time) | Manager needs MIS data. Currently no visibility into trends. | Medium | Chart.js + Django ORM aggregation |

## Differentiators

Features that make the product notably better than a shared Gmail inbox.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI confidence scoring | Shows HOW sure the AI is. Builds trust. Flags uncertain triages for review. | Medium | Prompt schema change + new field |
| Auto-assign with confidence threshold | Emails auto-route without human intervention when AI is confident. Saves manager time. | Medium | Depends on confidence scoring + existing AssignmentRule |
| Feedback-driven AI improvement | System gets smarter from corrections. Each correction makes future triages better. | Medium | Correction history injected into prompt context |
| Sender reputation learning | Spam filter improves over time from user feedback. Reduces false positives. | Medium | SenderReputation model + counters |
| Right-click context menu | Power-user speed. Manage emails without opening detail panel. | Low | HTMX contextmenu trigger + partial |
| CSV export for reports | Manager can share data outside the app. | Low | Python csv stdlib |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| ML-based spam classifier | Not enough training data (50-100 emails/day). Black box. Hard to debug. | Sender reputation counters + Claude AI for nuanced cases |
| Real-time collaborative editing | 4-5 users, not Google Docs. Over-engineering. | Existing ThreadViewer (presence indicator) is sufficient |
| Custom report builder / drag-drop dashboards | Manager wants 5 specific charts, not a BI tool. | Hardcoded report views with date range filters |
| Full-text search with indexing | PostgreSQL 12.3 has basic `LIKE`/`icontains`. Full-text search adds complexity. | Django ORM filtering (already works for current volume) |
| Notification preferences UI | 4-5 users. Set once in SystemConfig. | Keep notification config in admin/SystemConfig |
| A/B testing for AI prompts | Single prompt, single company. No statistical significance possible. | Manual prompt iteration based on correction patterns |

## Feature Dependencies

```
AI Confidence Scoring
  -> Auto-Assign with Threshold (requires confidence data)
  -> Feedback Loop (requires correction recording)

Spam Feedback (mark spam/not-spam)
  -> Sender Reputation (aggregates feedback)
  -> Spam Filter Enhancement (checks reputation)

Read/Unread Tracking (standalone)
  -> Context Menu "Mark as Unread" action

Inline Edit (standalone)
  -> Correction Recording in ActivityLog
  -> Feeds into AI Feedback Loop

Reports Module (standalone, benefits from all data)
  -> Chart.js CDN dependency
```

## MVP Recommendation

Prioritize (immediate user value):
1. Read/unread tracking -- most-requested basic feature for any inbox
2. Inline-editable category/priority -- users need to correct AI now, currently requires admin
3. AI confidence scoring -- foundation for auto-assign and trust-building
4. Basic reports (volume + response time charts) -- manager MIS need

Defer slightly (build on foundation):
- Auto-assign with confidence: needs baseline confidence data first (run for a week)
- Sender reputation learning: needs spam feedback corrections to accumulate
- Context menus: nice-to-have, not blocking any workflow
- CSV export: quick to add once reports views exist
