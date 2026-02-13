"""
AI Processor — Uses Claude API to categorize, prioritize, and draft replies.

Makes a single structured API call per email using Claude's tool-use
feature to guarantee valid JSON output.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

# Valid categories and priorities (for validation)
VALID_CATEGORIES = [
    "Government/Tender", "Sales Lead", "Support Request", "Complaint",
    "Partnership", "Vendor", "Internal", "General Inquiry",
]
VALID_PRIORITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


@dataclass
class TriageResult:
    """Structured output from Claude's email triage."""
    category: str = "General Inquiry"
    priority: str = "MEDIUM"
    summary: str = ""
    draft_reply: str = ""
    reasoning: str = ""
    suggested_assignee: str = ""
    tags: list = field(default_factory=list)
    raw_response: dict = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


# Define the tool schema for structured output
TRIAGE_TOOL = {
    "name": "triage_email",
    "description": "Categorize, prioritize, summarize, and draft a reply for the incoming email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": VALID_CATEGORIES,
                "description": "The single best category for this email.",
            },
            "priority": {
                "type": "string",
                "enum": VALID_PRIORITIES,
                "description": "Priority level based on urgency and business impact.",
            },
            "summary": {
                "type": "string",
                "description": "A 2-3 sentence summary of the email content and intent.",
            },
            "draft_reply": {
                "type": "string",
                "description": "A professional reply draft for the team to review and send.",
            },
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why this category and priority were chosen.",
            },
            "suggested_assignee": {
                "type": "string",
                "description": "Suggested team member to handle this, or empty string if unclear.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Relevant tags for searchability (3-5 tags).",
            },
        },
        "required": ["category", "priority", "summary", "draft_reply", "reasoning", "tags"],
    },
}


class AIProcessor:
    """Processes emails through Claude for triage and response drafting."""

    def __init__(self, model: str, max_tokens: int = 1024, temperature: float = 0.3,
                 system_prompt_path: str = "prompts/triage_prompt.txt"):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = self._load_system_prompt(system_prompt_path)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.client = anthropic.Anthropic(api_key=api_key)

    @staticmethod
    def _load_system_prompt(path: str) -> str:
        """Load the system prompt from file."""
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning(f"System prompt file not found at {path}, using default")
            return (
                "You are an email triage agent for Vidarbha Infotech Private Limited (VIPL). "
                "Categorize, prioritize, summarize, and draft a reply for each email."
            )

    def _build_user_message(self, email) -> str:
        """Build the user message content from an EmailMessage."""
        attachments_info = ""
        if email.attachment_count > 0:
            names = ", ".join(email.attachment_names[:10])
            attachments_info = f"\nAttachments ({email.attachment_count}): {names}"

        return (
            f"--- INCOMING EMAIL ---\n"
            f"Inbox: {email.inbox}\n"
            f"From: {email.sender_name} <{email.sender_email}>\n"
            f"Subject: {email.subject}\n"
            f"Received: {email.timestamp.strftime('%Y-%m-%d %H:%M:%S IST')}"
            f"{attachments_info}\n"
            f"\n--- EMAIL BODY ---\n"
            f"{email.body}\n"
            f"--- END ---"
        )

    def process(self, email) -> TriageResult:
        """
        Process a single email through Claude and return structured triage results.

        Uses Claude's tool-use feature to guarantee valid structured JSON output.
        Falls back gracefully if the API call fails.
        """
        try:
            user_message = self._build_user_message(email)
            logger.info(f"Processing email: {email.subject[:60]}...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                tools=[TRIAGE_TOOL],
                tool_choice={"type": "tool", "name": "triage_email"},
                messages=[
                    {"role": "user", "content": user_message}
                ],
            )

            # Extract the tool use result
            for block in response.content:
                if block.type == "tool_use" and block.name == "triage_email":
                    data = block.input
                    return TriageResult(
                        category=data.get("category", "General Inquiry"),
                        priority=data.get("priority", "MEDIUM"),
                        summary=data.get("summary", ""),
                        draft_reply=data.get("draft_reply", ""),
                        reasoning=data.get("reasoning", ""),
                        suggested_assignee=data.get("suggested_assignee", ""),
                        tags=data.get("tags", []),
                        raw_response=data,
                        success=True,
                    )

            # If no tool_use block found (shouldn't happen with tool_choice)
            logger.warning("Claude response did not contain expected tool_use block")
            return self._fallback_result("No tool_use block in response")

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback_result(str(e))
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            return self._fallback_result(str(e))

    @staticmethod
    def _fallback_result(error_msg: str) -> TriageResult:
        """Return a fallback result when AI processing fails."""
        return TriageResult(
            category="General Inquiry",
            priority="MEDIUM",
            summary="[AI processing failed — manual triage required]",
            draft_reply="",
            reasoning=f"AI error: {error_msg}",
            suggested_assignee="",
            tags=["needs-manual-triage"],
            success=False,
            error=error_msg,
        )
