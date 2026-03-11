"""AI Processor -- Cost-optimized email triage via Claude API.

Ported from v1's agent/ai_processor.py. Two-tier AI with prompt caching.
Django-agnostic: no Django ORM imports. Returns TriageResult DTOs.

KEY COST OPTIMIZATIONS:
1. Two-tier AI: Haiku (cheap) for all emails, Sonnet only if CRITICAL
2. Prompt caching: system prompt cached server-side (~90% savings)
3. Aggressive body truncation: 1500 chars max
4. Spam pre-filter extracted to spam_filter.py (called by pipeline)
5. Reduced max_tokens: 512 for Haiku, 768 for Sonnet
6. Token tracking: log usage for cost visibility
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .dtos import (
    VALID_CATEGORIES,
    VALID_PRIORITIES,
    EmailMessage,
    TriageResult,
)

logger = logging.getLogger(__name__)

# IST timezone for timestamp formatting in prompts
import pytz

IST = pytz.timezone("Asia/Kolkata")

# Maximum email body length sent to Claude (tokens ~ chars x 0.3)
MAX_BODY_CHARS = 1500

# Default models
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
ESCALATION_MODEL = "claude-sonnet-4-5-20250929"

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
            "language": {
                "type": "string",
                "enum": ["English", "Hindi", "Marathi", "Mixed"],
                "description": "Primary language of the email.",
            },
        },
        "required": ["category", "priority", "summary", "draft_reply", "reasoning", "tags", "language"],
    },
}


class AIProcessor:
    """Cost-optimized email triage with two-tier AI and prompt caching."""

    # Cumulative token counters for cost monitoring
    _total_input_tokens = 0
    _total_output_tokens = 0
    _total_calls = 0
    _total_cache_hits = 0

    def __init__(
        self,
        anthropic_api_key: str,
        model: str = DEFAULT_MODEL,
        escalation_model: str = ESCALATION_MODEL,
        max_tokens: int = 512,
        temperature: float = 0.3,
        system_prompt_path: str = "prompts/triage_prompt_v2.txt",
    ):
        self.model = model
        self.escalation_model = escalation_model
        self.max_tokens = max_tokens
        self.escalation_max_tokens = 768
        self.temperature = temperature

        raw_prompt = self._load_system_prompt(system_prompt_path)

        # Build system prompt with cache_control for Anthropic prompt caching
        self.system_prompt = [
            {
                "type": "text",
                "text": raw_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

        logger.info(
            f"AI Processor: primary={self.model}, escalation={self.escalation_model}, "
            f"max_body={MAX_BODY_CHARS} chars"
        )

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
    # Input sanitization
    # ----------------------------------------------------------------

    @staticmethod
    def _sanitize(text: str) -> str:
        """Strip control characters and null bytes that could confuse the model."""
        if not text:
            return ""
        # Remove null bytes and other control chars (keep newlines/tabs)
        return "".join(c for c in text if c == "\n" or c == "\t" or (ord(c) >= 32))

    def _build_user_message(self, email: EmailMessage, pdf_text: str = "") -> str:
        """Build the user message with aggressive body truncation and input sanitization."""
        attachments_info = ""
        if email.attachment_count > 0:
            names = ", ".join(email.attachment_names[:5])
            attachments_info = f"\nAttachments ({email.attachment_count}): {names}"

        # Sanitize + truncate body to MAX_BODY_CHARS (1500 default)
        body = self._sanitize(email.body)
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS] + "\n[...truncated...]"

        subject = self._sanitize(email.subject)[:200]
        sender_name = self._sanitize(email.sender_name)[:100]

        pdf_section = ""
        if pdf_text:
            pdf_section = f"\n\n--- ATTACHED PDF CONTENT ---\n{self._sanitize(pdf_text)}\n--- END PDF ---"

        return (
            f"--- INCOMING EMAIL ---\n"
            f"Inbox: {email.inbox}\n"
            f"From: {sender_name} <{email.sender_email}>\n"
            f"Subject: {subject}\n"
            f"Received: {email.timestamp.astimezone(IST).strftime('%Y-%m-%d %H:%M:%S IST')}"
            f"{attachments_info}\n"
            f"\n--- EMAIL BODY ---\n"
            f"{body}\n"
            f"--- END ---"
            f"{pdf_section}"
        )

    # ----------------------------------------------------------------
    # Core API Call -- with token tracking
    # ----------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(
            (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError)
        ),
        before_sleep=lambda rs: logger.warning(
            f"Claude API retry #{rs.attempt_number} after {rs.outcome.exception()}"
        ),
    )
    def _call_claude(self, user_message: str, model: str, max_tokens: int) -> TriageResult:
        """Make a single Claude API call with automatic retry on transient errors."""
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

        logger.info(
            f"Claude [{model.split('-')[1] if '-' in model else model}]: "
            f"in={input_tokens} out={output_tokens} cache_read={cache_read}"
        )

        # Extract the tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "triage_email":
                data = block.input

                # Validate against allowed enums
                category = data.get("category", "General Inquiry")
                if category not in VALID_CATEGORIES:
                    logger.warning(f"Invalid category from Claude: '{category}', defaulting to General Inquiry")
                    category = "General Inquiry"
                priority = data.get("priority", "MEDIUM")
                if priority not in VALID_PRIORITIES:
                    logger.warning(f"Invalid priority from Claude: '{priority}', defaulting to MEDIUM")
                    priority = "MEDIUM"

                return TriageResult(
                    category=category,
                    priority=priority,
                    summary=data.get("summary", ""),
                    draft_reply=data.get("draft_reply", ""),
                    reasoning=data.get("reasoning", ""),
                    suggested_assignee=data.get("suggested_assignee", ""),
                    tags=data.get("tags", []),
                    language=data.get("language", "English"),
                    model_used=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

        logger.warning("Claude response did not contain expected tool_use block")
        return self._fallback_result("No tool_use block in response")

    # ----------------------------------------------------------------
    # Two-Tier Process -- Haiku first, Sonnet only if needed
    # ----------------------------------------------------------------

    def process(self, email: EmailMessage, gmail_poller=None) -> TriageResult:
        """Process email through two-tier AI.

        1. Primary model (Haiku -- cheap) for all emails
        2. Escalation model (Sonnet) ONLY if Haiku says CRITICAL

        Spam pre-filter is NOT called here -- it's called by the pipeline
        orchestrator, per the separation of concerns from Plan 01.
        """
        # Extract PDF text from attachments if poller is available
        pdf_text = ""
        if gmail_poller and getattr(email, "attachment_details", None):
            from .pdf_extractor import extract_pdf_text

            for att in email.attachment_details:
                if att.get("mime_type") == "application/pdf" and att.get("attachment_id"):
                    if att.get("size", 0) > 5 * 1024 * 1024:
                        logger.info(f"Skipping large PDF: {att['filename']} ({att['size']} bytes)")
                        continue
                    raw = gmail_poller.download_attachment(email.inbox, email.message_id, att["attachment_id"])
                    if raw:
                        extracted = extract_pdf_text(raw)
                        if extracted:
                            pdf_text += f"\n[{att['filename']}]\n{extracted}\n"
                            break  # Only extract the first PDF to save tokens

        try:
            user_message = self._build_user_message(email, pdf_text=pdf_text)
            logger.info(f"Processing [{self.model.split('-')[1]}]: {email.subject[:60]}...")

            # Tier 1: Primary model (Haiku)
            result = self._call_claude(user_message, self.model, self.max_tokens)

            # Tier 2: Escalate to Sonnet only if CRITICAL and escalation model configured
            if (
                result.priority == "CRITICAL"
                and self.escalation_model
                and self.escalation_model != self.model
            ):
                logger.info(f"CRITICAL detected -- escalating to {self.escalation_model}")
                escalated = self._call_claude(
                    user_message, self.escalation_model, self.escalation_max_tokens
                )
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
            summary="[AI processing failed -- manual triage required]",
            draft_reply="",
            reasoning=f"AI error: {error_msg}",
            suggested_assignee="",
            tags=["needs-manual-triage"],
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
