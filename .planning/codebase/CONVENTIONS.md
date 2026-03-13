# Coding Conventions

**Analysis Date:** 2026-03-09

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python modules: `gmail_poller.py`, `ai_processor.py`, `sheet_logger.py`
- Test files mirror source: `agent/gmail_poller.py` -> `tests/test_gmail_poller.py`
- Config files use lowercase with dots: `config.yaml`, `pytest.ini`

**Functions:**
- Use `snake_case` for all functions and methods: `process_emails()`, `load_config()`, `is_quiet_hours()`
- Private methods prefixed with `_`: `_post()`, `_parse_message()`, `_extract_body()`, `_sanitize()`
- Static helper methods also prefixed with `_`: `_fallback_result()`, `_strip_html()`, `_fallback_plain_text()`

**Variables:**
- Use `snake_case` for all variables: `poll_interval`, `sla_defaults`, `processed_items`
- Constants use `UPPER_SNAKE_CASE`: `VALID_CATEGORIES`, `VALID_PRIORITIES`, `MAX_BODY_CHARS`, `SCOPES`, `IST`
- Private class attributes prefixed with `_`: `_thread_id_cache`, `_total_calls`, `_last_summary_hour`

**Classes:**
- Use `PascalCase`: `GmailPoller`, `AIProcessor`, `SheetLogger`, `ChatNotifier`, `SLAMonitor`, `EODReporter`, `StateManager`

**Dataclasses:**
- Use `PascalCase`: `EmailMessage`, `TriageResult`, `MockEmail`

## Code Style

**Formatting:**
- No formatter tool configured (no `.prettierrc`, `.flake8`, `ruff.toml`, `pyproject.toml`, or `setup.cfg` detected)
- Indentation: 4 spaces (Python standard)
- Max line length: approximately 120 characters (informal)
- String quotes: double quotes (`"`) used consistently throughout
- f-strings used everywhere for string formatting (no `.format()` or `%` formatting)

**Linting:**
- No linter configured. Follow Python standard conventions (PEP 8).

**Type Hints:**
- Used for function signatures: `def load_config(config_path: str = "config.yaml") -> dict:`
- Use `Optional` from typing for nullable returns: `-> Optional[str]`, `-> Optional[EmailMessage]`
- Use `list[str]`, `list[dict]`, `dict[str, str]` for collection types (Python 3.9+ syntax)
- Dataclass fields use type annotations: `category: str = "General Inquiry"`

## Import Organization

**Order:**
1. Standard library (`import json`, `import logging`, `import os`, `import threading`)
2. Third-party packages (`import pytz`, `import anthropic`, `from tenacity import ...`)
3. Local imports (`from agent.utils import IST`, `from agent.gmail_poller import GmailPoller`)

**Style:**
- `import module` for standard library modules
- `from module import specific_thing` for specific classes/functions
- No blank lines between groups (inconsistent; some files have blank lines, some don't)
- No path aliases configured

## Module Structure

**Every module follows this pattern:**
```python
"""
Module Name — One-line description.

Multi-line explanation of purpose and key design decisions.
"""

import logging
# ... other imports ...

logger = logging.getLogger(__name__)

# Module-level constants (UPPER_SNAKE_CASE)
SOME_CONSTANT = "value"


class MainClass:
    """Docstring explaining the class purpose."""

    def __init__(self, ...):
        # Initialize instance variables

    def public_method(self):
        """Docstring."""
        ...

    def _private_method(self):
        """Docstring."""
        ...
```

**Key files demonstrating the pattern:**
- `agent/ai_processor.py` — detailed module docstring with cost optimization notes
- `agent/gmail_poller.py` — clear class/method docstrings
- `agent/state.py` — clean, minimal module with docstrings explaining design trade-offs

## Docstrings

**Module-level:** Always present. Use triple-quoted strings with a title line, blank line, then details.
```python
"""
AI Processor — Cost-optimized email triage via Claude API.

KEY COST OPTIMIZATIONS:
1. Two-tier AI: Haiku (cheap) for all emails, Sonnet only if CRITICAL/ambiguous
...
"""
```

**Class-level:** Always present. One-liner or multi-line explaining purpose.

**Method-level:** Present on all public methods and most private methods. Use imperative mood.
```python
def mark_processed(self, email_msg):
    """Apply the 'Agent/Processed' label to an email AFTER successful Sheet log."""
```

## Error Handling

**Pattern 1: Try/except with logging (most common)**
```python
try:
    result = some_api_call()
except Exception as e:
    logger.error(f"Descriptive error message: {e}")
    # Either: return fallback value, raise, or pass
```

**Pattern 2: Nested try/except for non-critical secondary operations**
```python
try:
    # Primary operation
    sheet.log_email(email, triage, sla_hours)
except Exception as e:
    logger.error(f"Failed to process email: {e}")
    # Secondary: log to dead letter (allowed to fail silently)
    try:
        sheet.log_failed_triage(email, str(e))
    except Exception:
        pass
```

**Pattern 3: Fallback returns for API failures (`agent/ai_processor.py`)**
```python
@staticmethod
def _fallback_result(error_msg: str) -> TriageResult:
    """Return a fallback result when AI processing fails."""
    return TriageResult(
        category="General Inquiry",
        priority="MEDIUM",
        summary="[AI processing failed -- manual triage required]",
        success=False,
        error=error_msg,
    )
```

**Pattern 4: Retry with tenacity (`agent/ai_processor.py`, `agent/sheet_logger.py`)**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
    before_sleep=lambda rs: logger.warning(f"Retry #{rs.attempt_number}"),
)
def _call_claude(self, ...):
```

**Rules:**
- Never silently swallow exceptions on primary operations
- Always log errors with `logger.error()` or `logger.warning()`
- Use `pass` in nested try/except only for non-critical secondary operations
- Return safe fallback values rather than crashing

## Logging

**Framework:** Python `logging` module with structured JSON output in production.

**Logger initialization (every module):**
```python
logger = logging.getLogger(__name__)
```

**Production format:** JSON via `JSONFormatter` in `main.py`:
```python
{"timestamp": "2026-03-07T14:30:00+05:30", "severity": "INFO", "component": "agent.gmail_poller", "message": "..."}
```

**Log levels used:**
- `logger.info()` — successful operations, routine status: `"Poll complete -- no new emails"`
- `logger.warning()` — recoverable issues, degraded state: `"Chat webhook returned 400"`
- `logger.error()` — failures requiring attention: `"Gmail poll failed for inbox"`
- `logger.critical()` — circuit breaker open: `"Circuit breaker OPEN -- 3 consecutive failures"`
- `logger.debug()` — verbose details (rarely used): `"No new emails in inbox"`

**Patterns:**
- Include context in log messages: ticket IDs, inbox names, counts, truncated subjects
- Truncate user content in logs: `email.subject[:50]`, `str(e)[:60]`
- Use emoji in highlight logs: `"Ticket INF-0001 processed"` (via `log_buffer.add("HIGHLIGHT", ...)`)

## Configuration Pattern

**Three-tier config priority (highest to lowest):**
1. Environment variables (secrets + org-specific)
2. Google Sheet "Agent Config" tab (runtime hot-reload)
3. `config.yaml` (non-sensitive defaults)

**Config access pattern:** Dictionary access with `.get()` and defaults:
```python
poll_interval = config.get("gmail", {}).get("poll_interval_seconds", 300)
```

**Validation pattern:** Range checks with warning logs:
```python
val = int(overrides["Poll Interval (seconds)"])
if 60 <= val <= 3600:
    config["gmail"]["poll_interval_seconds"] = val
else:
    logger.warning(f"Poll Interval out of range (60-3600): {val}")
```

## Dataclass Usage

**Use `@dataclass` for structured data objects:**
```python
@dataclass
class EmailMessage:
    thread_id: str
    message_id: str
    inbox: str
    # ... fields with type annotations
    attachment_count: int = 0
    attachment_names: list = field(default_factory=list)
```

- Required fields first, optional fields with defaults after
- Use `field(default_factory=list)` for mutable defaults
- Use `Optional[str]` for nullable fields with `None` default

## Class Design

**Dependency injection via constructor:**
```python
class SLAMonitor:
    def __init__(self, sheet_logger, chat_notifier, state_manager, config: dict):
        self.sheet = sheet_logger
        self.chat = chat_notifier
        self.state = state_manager
        self.config = config
```

**Components dictionary pattern** (in `main.py`):
```python
components = {
    "state": state, "gmail": gmail, "ai": ai, "sheet": sheet,
    "chat": chat, "sla": sla, "eod": eod, "config": config,
}
```

All components are initialized in `init_components()` and passed around as a dict.

## Section Headers

Use comment blocks to separate logical sections within files:
```python
# ----------------------------------------------------------------
# Section Title
# ----------------------------------------------------------------
```

This pattern is used consistently in `main.py`, `agent/ai_processor.py`, and test files.

---

*Convention analysis: 2026-03-09*
