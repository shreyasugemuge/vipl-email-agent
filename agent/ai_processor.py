"""
AI Processor — Cost-optimized email triage via Claude API.

KEY COST OPTIMIZATIONS:
1. Two-tier AI: Haiku (cheap) for all emails, Sonnet only if CRITICAL/ambiguous
2. Prompt caching: system prompt cached server-side (~90% savings on repeated calls)
3. Aggressive body truncation: 1500 chars max (vs 4000 before) — ~60% fewer tokens
4. Spam pre-filter: skip Claude entirely for obvious junk — $0 cost
5. Reduced max_tokens: 512 for Haiku, 768 for Sonnet (was 1024)
6. Token tracking: log usage for cost visibility

Cost comparison (50 emails/day):
  Before: Sonnet × 1500/mo = ~$19/mo
  After:  Haiku × 1470 + Sonnet × 30 = ~$1.50/mo
"""

import logging
import os
import re
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

# Spam pre-filter patterns — skip Claude entirely for these
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

# Maximum email body length sent to Claude (tokens ≈ chars × 0.3)
MAX_BODY_CHARS = 1500


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
    model_used: str = ""            # Track which model was used
    input_tokens: int = 0           # Track for cost monitoring
    output_tokens: int = 0


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
    """Cost-optimized email triage with two-tier AI and prompt caching."""

    # Cumulative token counters for cost monitoring
    _total_input_tokens = 0
    _total_output_tokens = 0
    _total_calls = 0
    _total_cache_hits = 0

    def __init__(self, model: str, max_tokens: int = 512, temperature: float = 0.3,
                 system_prompt_path: str = "prompts/triage_prompt.txt",
                 escalation_model: str = ""):
        # Primary (cheap) model — default Haiku
        self.model = model
        # Escalation (expensive) model — only for CRITICAL/ambiguous
        self.escalation_model = escalation_model or ""
        self.max_tokens = max_tokens
        self.escalation_max_tokens = 768  # Slightly more for Sonnet's detailed output
        self.temperature = temperature

        raw_prompt = self._load_system_prompt(system_prompt_path)

        # Build system prompt with cache_control for Anthropic prompt caching.
        # The system prompt is ~700 tokens and identical across all calls.
        # With caching, subsequent calls pay ~10% of the input cost.
        self.system_prompt = [
            {
                "type": "text",
                "text": raw_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.client = anthropic.Anthropic(api_key=api_key)

        logger.info(f"AI Processor: primary={self.model}, escalation={self.escalation_model or 'disabled'}, "
                     f"max_body={MAX_BODY_CHARS} chars")

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

    # ----------------------------------------------------------------
    # Spam Pre-Filter — skip Claude entirely, cost = $0
    # ----------------------------------------------------------------

    @staticmethod
    def is_spam(email) -> Optional[TriageResult]:
        """
        Fast regex pre-filter for obvious spam/phishing.
        Returns a TriageResult if spam detected, None otherwise.
        Saves ~$0.013 per skipped Haiku call.
        """
        # Check subject + body combined
        text = f"{email.subject}\n{email.body[:2000]}"
        if _SPAM_RE.search(text):
            return TriageResult(
                category="General Inquiry",
                priority="LOW",
                summary="[Auto-filtered as likely spam/phishing — no AI processing required]",
                draft_reply="",
                reasoning="Matched spam pre-filter pattern. Skipped AI to save cost.",
                suggested_assignee="",
                tags=["spam", "auto-filtered"],
                success=True,
                model_used="spam-filter",
                input_tokens=0,
                output_tokens=0,
            )
        return None

    # ----------------------------------------------------------------
    # Build User Message — truncated for cost
    # ----------------------------------------------------------------

    def _build_user_message(self, email) -> str:
        """Build the user message with aggressive body truncation."""
        attachments_info = ""
        if email.attachment_count > 0:
            names = ", ".join(email.attachment_names[:5])
            attachments_info = f"\nAttachments ({email.attachment_count}): {names}"

        # Truncate body to MAX_BODY_CHARS (1500 default, was 4000)
        body = email.body
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS] + "\n[...truncated...]"

        return (
            f"--- INCOMING EMAIL ---\n"
            f"Inbox: {email.inbox}\n"
            f"From: {email.sender_name} <{email.sender_email}>\n"
            f"Subject: {email.subject}\n"
            f"Received: {email.timestamp.strftime('%Y-%m-%d %H:%M:%S IST')}"
            f"{attachments_info}\n"
            f"\n--- EMAIL BODY ---\n"
            f"{body}\n"
            f"--- END ---"
        )

    # ----------------------------------------------------------------
    # Core API Call — with token tracking
    # ----------------------------------------------------------------

    def _call_claude(self, user_message: str, model: str, max_tokens: int) -> TriageResult:
        """Make a single Claude API call and return structured result."""
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "triage_email"},
            messages=[{"role": "user", "content": user_message}],
        )

        # Track token usage
        usage = response.usage
        input_tokens = usage.input_tokens if usage else 0
        output_tokens = usage.output_tokens if usage else 0
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

        AIProcessor._total_input_tokens += input_tokens
        AIProcessor._total_output_tokens += output_tokens
        AIProcessor._total_calls += 1
        if cache_read > 0:
            AIProcessor._total_cache_hits += 1

        logger.info(f"Claude [{model.split('-')[1] if '-' in model else model}]: "
                     f"in={input_tokens} out={output_tokens} cache_read={cache_read}")

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
                    model_used=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

        logger.warning("Claude response did not contain expected tool_use block")
        return self._fallback_result("No tool_use block in response")

    # ----------------------------------------------------------------
    # Two-Tier Process — Haiku first, Sonnet only if needed
    # ----------------------------------------------------------------

    def process(self, email) -> TriageResult:
        """
        Process email through two-tier AI:
        1. Spam pre-filter (free)
        2. Primary model (Haiku — cheap) for all emails
        3. Escalation model (Sonnet) ONLY if Haiku says CRITICAL
           and an escalation model is configured

        This saves 10-12x on API costs for the 95%+ of emails
        that are MEDIUM/LOW/HIGH priority.
        """
        # Tier 0: Spam pre-filter — $0
        spam_result = self.is_spam(email)
        if spam_result:
            logger.info(f"Spam pre-filter caught: {email.subject[:50]}")
            return spam_result

        try:
            user_message = self._build_user_message(email)
            logger.info(f"Processing [{self.model.split('-')[1]}]: {email.subject[:60]}...")

            # Tier 1: Primary model (Haiku)
            result = self._call_claude(user_message, self.model, self.max_tokens)

            # Tier 2: Escalate to Sonnet only if CRITICAL and escalation model configured
            if (result.priority == "CRITICAL"
                    and self.escalation_model
                    and self.escalation_model != self.model):
                logger.info(f"CRITICAL detected — escalating to {self.escalation_model}")
                escalated = self._call_claude(user_message, self.escalation_model,
                                              self.escalation_max_tokens)
                escalated.reasoning = f"[Escalated from {self.model}] {escalated.reasoning}"
                return escalated

            return result

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
            model_used="fallback",
        )

    @classmethod
    def get_usage_stats(cls) -> dict:
        """Return cumulative token usage for cost monitoring."""
        return {
            "total_calls": cls._total_calls,
            "total_input_tokens": cls._total_input_tokens,
            "total_output_tokens": cls._total_output_tokens,
            "cache_hit_rate": (cls._total_cache_hits / cls._total_calls * 100) if cls._total_calls else 0,
        }
