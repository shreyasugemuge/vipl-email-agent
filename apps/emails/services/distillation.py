"""Distillation service -- summarize assignment corrections into compact AI rules.

Queries AssignmentFeedback for rejected/reassigned actions, calls Haiku to
distill into compact rules, stores in SystemConfig for prompt injection.
Non-critical: failures are logged and swallowed, never crash the pipeline.
"""

import logging
import os
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

from apps.core.models import SystemConfig
from apps.emails.models import AssignmentFeedback

logger = logging.getLogger(__name__)

DISTILLATION_PROMPT = """You are an assignment rule summarizer for an email triage system.

Given a list of corrections (where AI suggested one person but the team assigned someone else),
distill them into compact assignment rules.

Output format: One rule per line, like:
- Sales leads from acme.com domains: assign to Rahul
- Government/Tender emails about STPI: assign to Shreyas
- Support requests in Marathi: assign to Priya

Rules should be specific, actionable, and based on patterns in the corrections.
Maximum 10 rules. Merge similar corrections. Drop one-off corrections that don't form patterns.
If no clear patterns exist, output "No correction rules yet."
"""


def distill_correction_rules():
    """Distill AssignmentFeedback into compact rules for prompt injection.

    Only runs when new feedback exists since last distillation.
    Non-critical -- failures logged and swallowed.
    """
    try:
        _do_distill()
    except Exception:
        logger.exception("Distillation failed -- using stale rules")


def _do_distill():
    """Inner distillation logic (separated for testability)."""
    # Check if new feedback exists since last distillation
    last_epoch = SystemConfig.get("last_distillation_epoch", "0")
    try:
        last_dt = datetime.fromtimestamp(int(last_epoch), tz=dt_timezone.utc)
    except (ValueError, TypeError, OSError):
        last_dt = datetime.min.replace(tzinfo=dt_timezone.utc)

    new_feedback_count = AssignmentFeedback.objects.filter(
        action__in=[
            AssignmentFeedback.FeedbackAction.REJECTED,
            AssignmentFeedback.FeedbackAction.REASSIGNED,
        ],
        created_at__gt=last_dt,
    ).count()

    if new_feedback_count == 0:
        logger.debug("No new feedback since last distillation -- skipping")
        return

    # Get recent corrections (last 50)
    feedbacks = (
        AssignmentFeedback.objects.filter(
            action__in=[
                AssignmentFeedback.FeedbackAction.REJECTED,
                AssignmentFeedback.FeedbackAction.REASSIGNED,
            ],
        )
        .select_related("thread", "suggested_user", "actual_user")
        .order_by("-created_at")[:50]
    )

    if not feedbacks:
        return

    corrections_text = _format_corrections(feedbacks)
    rules_text = _call_haiku_distill(corrections_text)

    if rules_text:
        SystemConfig.objects.update_or_create(
            key="correction_rules",
            defaults={
                "value": rules_text,
                "value_type": SystemConfig.ValueType.STR,
                "description": "AI-distilled assignment correction rules",
                "category": "ai",
            },
        )
        # Update last distillation epoch
        SystemConfig.objects.update_or_create(
            key="last_distillation_epoch",
            defaults={
                "value": str(int(timezone.now().timestamp())),
                "value_type": SystemConfig.ValueType.INT,
                "description": "Timestamp of last distillation run",
                "category": "ai",
            },
        )
        logger.info("Distilled %d corrections into rules", len(feedbacks))


def _format_corrections(feedbacks):
    """Format AssignmentFeedback queryset into readable text for Haiku."""
    lines = []
    for fb in feedbacks:
        thread_cat = fb.thread.category if fb.thread else "Unknown"
        thread_subject = fb.thread.subject[:60] if fb.thread else "Unknown"
        suggested = fb.suggested_user.get_full_name() if fb.suggested_user else "Unknown"
        actual = fb.actual_user.get_full_name() if fb.actual_user else "Unassigned"
        sender = fb.thread.last_sender_address if fb.thread else "Unknown"
        lines.append(
            f"- Category: {thread_cat}, Subject: {thread_subject}, "
            f"Sender: {sender}, AI suggested: {suggested}, "
            f"Team assigned: {actual}, Action: {fb.action}"
        )
    return "\n".join(lines)


def _call_haiku_distill(corrections_text):
    """Call Haiku to distill corrections into compact rules.

    Returns rules text string, or None on failure.
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("No ANTHROPIC_API_KEY -- skipping distillation")
        return None

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        temperature=0.2,
        system=DISTILLATION_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here are the recent corrections:\n\n{corrections_text}\n\n"
                    "Distill these into assignment rules."
                ),
            }
        ],
    )

    if response.content:
        return response.content[0].text.strip()
    return None
