"""Data Transfer Objects for the email pipeline.

Ported from v1's agent/gmail_poller.py (EmailMessage) and
agent/ai_processor.py (TriageResult). These are plain dataclasses
with no Django dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# Valid categories and priorities (for validation)
VALID_CATEGORIES = [
    "Government/Tender",
    "Sales Lead",
    "Support Request",
    "Complaint",
    "Partnership",
    "Vendor",
    "Internal",
    "General Inquiry",
]
VALID_PRIORITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


@dataclass
class EmailMessage:
    """Parsed email data ready for AI processing.

    Matches v1's agent.gmail_poller.EmailMessage interface exactly.
    """

    thread_id: str
    message_id: str
    inbox: str
    sender_name: str
    sender_email: str
    subject: str
    body: str
    timestamp: datetime
    attachment_count: int = 0
    attachment_names: list = field(default_factory=list)
    attachment_details: list = field(default_factory=list)
    gmail_link: str = ""


@dataclass
class TriageResult:
    """Structured output from email triage (AI or spam filter).

    Matches v1's agent.ai_processor.TriageResult interface, with
    is_spam and spam_score added for the spam pre-filter.
    """

    category: str = "General Inquiry"
    priority: str = "MEDIUM"
    summary: str = ""
    draft_reply: str = ""
    reasoning: str = ""
    language: str = "English"
    tags: list = field(default_factory=list)
    suggested_assignee: str = ""
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    is_spam: bool = False
    spam_score: float = 0.0
