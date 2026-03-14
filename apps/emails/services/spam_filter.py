"""Spam pre-filter -- regex-based spam detection to skip AI processing.

Ported from v1's agent/ai_processor.py SPAM_PATTERNS. All 13 patterns
preserved exactly. Returns a TriageResult on match, None on clean email.
Cost: $0 (no API call needed).
"""

import re
from typing import Optional

from .dtos import EmailMessage, TriageResult

# Spam pre-filter patterns -- skip Claude entirely for these
# Ported from v1 agent/ai_processor.py (all 13 patterns)
SPAM_PATTERNS = [
    r"unsubscribe",
    r"click here to (opt.?out|remove|stop)",
    r"you have been selected",
    r"act now.*limited time",
    r"nigerian? prince",
    r"lottery winner",
    r"earn \$?\d+[,.]?\d* (per|a) (day|week|hour)",
    r"weight loss (secret|miracle|pill)",
    r"viagra|cialis|pharmacy",
    r"bitcoin.*invest|crypto.*guaranteed",
    r"dear (winner|beneficiary|account holder)",
    r"kindly verify your (account|password|identity)",
    r"your account (has been|will be) (suspended|locked|closed)",
]

_SPAM_RE = re.compile("|".join(SPAM_PATTERNS), re.IGNORECASE)


def is_spam(email_msg: EmailMessage) -> Optional[TriageResult]:
    """Fast regex pre-filter for obvious spam/phishing.

    Returns a TriageResult if spam detected, None otherwise.
    Checks subject + body combined (case-insensitive).
    """
    text = f"{email_msg.subject}\n{email_msg.body[:2000]}"
    if _SPAM_RE.search(text):
        return TriageResult(
            category="Spam",
            priority="LOW",
            summary="[Auto-filtered as likely spam/phishing -- no AI processing required]",
            reasoning="Matched spam pre-filter pattern. Skipped AI to save cost.",
            suggested_assignee="",
            tags=["spam", "auto-filtered"],
            model_used="spam-filter",
            input_tokens=0,
            output_tokens=0,
            is_spam=True,
            spam_score=1.0,
        )
    return None
