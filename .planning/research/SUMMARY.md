# Research Summary: v2.5.0 Intelligence + UX

**Domain:** AI-powered email triage system -- intelligence layer and UX completeness
**Researched:** 2026-03-15
**Overall confidence:** HIGH

## Executive Summary

The v2.5.0 milestone adds six feature groups to an already mature Django+HTMX email triage system. The critical finding is that **zero new Python dependencies and only one new frontend CDN script (Chart.js 4.5.1) are needed**. Every feature maps cleanly to existing patterns in the codebase -- Django ORM models, HTMX partial templates, vanilla JS, and prompt engineering with the existing Anthropic SDK.

The AI intelligence features (confidence scoring, spam learning, feedback loops) do not require machine learning libraries. At 50-100 emails/day with 4-5 users, rule-based approaches (sender reputation counters, prompt-injected correction history) are more appropriate than statistical ML. Claude handles the "intelligence" -- the system just needs to record corrections and feed them back as context.

The UX features (read/unread, context menus, inline edit, reports) are all well-trodden HTMX patterns. Context menus work natively with `hx-trigger="contextmenu"`. Click-to-edit is an official HTMX example. Read/unread is a standard Django M2M-through model. Reports are Django ORM aggregation piped into Chart.js.

The biggest risk is not technical but operational: the feedback loop for AI confidence requires enough user corrections to be useful. With a 3-person team, it may take weeks to accumulate meaningful correction data. The system should work well with zero corrections (Claude's base accuracy is already good) and improve incrementally.

## Key Findings

**Stack:** Zero new Python packages. Chart.js 4.5.1 CDN for reports. ~100 lines vanilla JS across all features.
**Architecture:** Three new models (ThreadReadState, SpamFeedback, SenderReputation), three new fields on existing models, five new ActivityLog action types.
**Critical pitfall:** Do not introduce ML libraries (scikit-learn, etc.) for spam learning -- rule-based sender reputation with DB counters is correct for this scale.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Models + Migrations** - Add all new models and fields in one migration batch
   - Addresses: ThreadReadState, SpamFeedback, SenderReputation, ai_confidence fields
   - Avoids: Multiple migration chains that conflict

2. **AI Confidence + Feedback Loop** - Modify prompt schema and ai_processor
   - Addresses: Confidence scoring, auto-assign threshold, correction recording
   - Avoids: Deploying auto-assign without confidence data (need baseline first)

3. **Spam Learning** - Build on SpamFeedback model + SenderReputation
   - Addresses: User corrections, sender reputation, spam filter enhancement
   - Avoids: Separate from AI confidence (different feedback mechanism)

4. **Read/Unread Tracking** - Standalone UX feature
   - Addresses: Per-user read state, visual indicators, mark as unread
   - Avoids: No dependency on other features

5. **Context Menus + Inline Edit** - UX interaction layer
   - Addresses: Right-click actions, editable category/priority
   - Avoids: Building before read/unread (context menu includes "mark unread" action)

6. **Reports Module** - Chart.js integration, new page
   - Addresses: Analytics dashboard, volume trends, team performance
   - Avoids: Building reports before the data pipeline improvements (confidence, corrections) are in place

**Phase ordering rationale:**
- Models first because multiple features depend on the same new fields
- AI confidence before spam learning because corrections infrastructure is shared
- Read/unread before context menus because the menu includes read/unread actions
- Reports last because it benefits from all other data improvements

**Research flags for phases:**
- AI confidence: May need prompt calibration after first deployment (Claude tends toward overconfidence)
- Reports: Chart.js is straightforward, but destroy instances on HTMX navigation to prevent memory leaks

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies verified against each feature requirement |
| Features | HIGH | All features map to established Django/HTMX patterns |
| Architecture | HIGH | New models are simple, integration points with existing code are clear |
| Pitfalls | HIGH | Main risks are operational (calibration, data volume) not technical |

## Gaps to Address

- Chart.js SRI integrity hash needs to be generated at implementation time (pin to exact version)
- Auto-assign confidence threshold (80%) is a reasonable default but may need tuning after deployment
- Sender reputation thresholds need real-world calibration (start with spam_ratio > 0.8 AND total_count >= 3)
