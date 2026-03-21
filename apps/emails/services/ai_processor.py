"""AI Processor -- Cost-optimized email triage via Claude API.

Ported from v1's agent/ai_processor.py. Two-tier AI with prompt caching.
Returns TriageResult DTOs. Team workload context injected for assignee
suggestions (Phase 4).

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
            "reasoning": {
                "type": "string",
                "description": "Brief explanation of why this category and priority were chosen.",
            },
            "suggested_assignee": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the suggested team member, or empty string if unclear.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for this suggestion based on email content, category, and team workload.",
                    },
                },
                "required": ["name", "reason"],
                "description": "Suggested team member and reasoning.",
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
            "confidence": {
                "type": "string",
                "enum": ["HIGH", "MEDIUM", "LOW"],
                "description": "Your confidence in the category and assignee suggestion. HIGH = very clear match to a known pattern. MEDIUM = reasonable guess but ambiguous. LOW = uncertain, multiple categories could apply.",
            },
        },
        "required": ["category", "priority", "summary", "reasoning", "tags", "language", "confidence"],
    },
}


def _get_team_workload() -> list:
    """Get open email counts per active team member.

    Returns list of dicts: [{"name": "Rahul", "email": "rahul@...", "open_count": 5}, ...]
    Wrapped in try/except so it never crashes the AI processor.
    """
    try:
        from django.db.models import Count, Q

        from apps.accounts.models import User

        users = User.objects.filter(is_active=True).annotate(
            open_count=Count(
                "assigned_emails",
                filter=Q(assigned_emails__status__in=["new", "acknowledged"]),
            )
        )
        result = []
        for user in users:
            name = user.get_full_name() or user.email
            result.append({
                "name": name,
                "email": user.email,
                "open_count": user.open_count,
            })
        return result
    except Exception:
        logger.warning("Could not fetch team workload", exc_info=True)
        return []


def _clean_xml_tags(text):
    """Strip XML parameter tags from text (e.g. Claude occasionally wraps names in XML).

    Returns text as-is if falsy (None, empty string).
    """
    if not text:
        return text
    # Strip <parameter name="...">...</parameter> wrappers
    cleaned = re.sub(r'<parameter\s+name="[^"]*">(.*?)</parameter>', r'\1', text)
    # Fallback: strip any remaining XML-like tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    return cleaned.strip()


def _parse_suggested_assignee(raw) -> dict:
    """Parse suggested_assignee from Claude response into structured dict.

    Handles both new format (dict with name + reason) and old format (plain string).
    Returns empty dict for empty/None values.
    """
    if not raw:
        return {}

    if isinstance(raw, dict):
        return {
            "name": _clean_xml_tags(raw.get("name", "")),
            "reason": raw.get("reason", ""),
        }

    if isinstance(raw, str):
        if raw.strip():
            return {"name": _clean_xml_tags(raw.strip()), "reason": ""}
        return {}

    return {}


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

        # Inject correction rules from SystemConfig (if any)
        try:
            from apps.core.models import SystemConfig

            correction_rules = SystemConfig.get("correction_rules", "")
            if correction_rules and correction_rules != "No correction rules yet.":
                # Sanitize: strip XML/HTML tags and limit length to prevent prompt injection
                sanitized_rules = re.sub(r'<[^>]+>', '', correction_rules)
                sanitized_rules = sanitized_rules[:2000]
                # Prefix each line with "- " delimiter for safe injection
                rule_lines = [
                    f"- {line.strip()}"
                    for line in sanitized_rules.split("\n")
                    if line.strip()
                ]
                if rule_lines:
                    raw_prompt += (
                        "\n\n<correction_rules>\n"
                        "The following rules are based on past corrections by the team. "
                        "Follow these when making assignment suggestions:\n"
                        + "\n".join(rule_lines) + "\n"
                        "</correction_rules>"
                    )
        except Exception:
            logger.debug("Could not load correction rules (expected in tests without DB)")

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

        # Build team workload section (~50 tokens)
        workload = _get_team_workload()
        if workload:
            workload_lines = [f"- {w['name']}: {w['open_count']} open emails" for w in workload]
            workload_section = "\n\n--- TEAM WORKLOAD ---\n" + "\n".join(workload_lines) + "\n--- END WORKLOAD ---"
        else:
            workload_section = "\n\nTeam workload: No team data available"

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
            f"{workload_section}"
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

                # Parse structured assignee suggestion
                raw_assignee = data.get("suggested_assignee", "")
                assignee_detail = _parse_suggested_assignee(raw_assignee)
                assignee_name = assignee_detail.get("name", "") if assignee_detail else ""

                return TriageResult(
                    category=category,
                    priority=priority,
                    summary=data.get("summary", ""),
                    reasoning=data.get("reasoning", ""),
                    suggested_assignee=assignee_name,
                    suggested_assignee_detail=assignee_detail,
                    tags=data.get("tags", []),
                    language=data.get("language", "English"),
                    model_used=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    confidence=data.get("confidence", ""),
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
