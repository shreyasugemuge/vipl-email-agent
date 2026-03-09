# Testing Patterns

**Analysis Date:** 2026-03-09

## Test Framework

**Runner:**
- pytest 8.3.4
- Config: `pytest.ini`

**Assertion Library:**
- Built-in `assert` statements (no third-party assertion library)

**Coverage Tool:**
- pytest-cov 5.0.0

**Run Commands:**
```bash
# Run all unit tests (no API keys needed) — 131 tests
pytest -m "not integration" -v

# Run integration tests (requires ANTHROPIC_API_KEY)
pytest -m integration -v

# Run specific test file
pytest tests/test_ai_processor.py -v

# Run specific test
pytest tests/test_ai_processor.py -v -k "test_triage_government"

# Run with coverage
pytest -m "not integration" --cov=agent --cov-report=term-missing
```

## Test Configuration

**`pytest.ini`:**
```ini
[pytest]
testpaths = tests
markers =
    integration: tests requiring real API keys (deselect with -m "not integration")
addopts = -v --tb=short
```

**Markers:**
- `@pytest.mark.integration` — tests that make real API calls (Claude). Require `ANTHROPIC_API_KEY`.
- All other tests are unit tests that run with mocks only.

## Test File Organization

**Location:** Separate `tests/` directory (not co-located with source).

**Naming:** `test_{module_name}.py` mirrors `agent/{module_name}.py`

**Structure:**
```
tests/
├── __init__.py
├── conftest.py             # Shared fixtures (MockEmail, mock_sheet, mock_chat, default_config)
├── sample_emails.json      # Fixture data for integration tests
├── test_ai_processor.py    # 22 tests (14 unit + 8 integration)
├── test_chat_notifier.py   # 10 tests
├── test_eod_reporter.py    # 9 tests
├── test_gmail_poller.py    # 15 tests
├── test_main.py            # 19 tests
├── test_sheet_logger.py    # 16 tests
├── test_sla_monitor.py     # 20 tests
└── test_utils.py           # 10 tests
```

**Test-to-source mapping:**
| Test File | Source File |
|-----------|------------|
| `tests/test_ai_processor.py` | `agent/ai_processor.py` |
| `tests/test_chat_notifier.py` | `agent/chat_notifier.py` |
| `tests/test_eod_reporter.py` | `agent/eod_reporter.py` |
| `tests/test_gmail_poller.py` | `agent/gmail_poller.py` |
| `tests/test_main.py` | `main.py` |
| `tests/test_sheet_logger.py` | `agent/sheet_logger.py` |
| `tests/test_sla_monitor.py` | `agent/sla_monitor.py` |
| `tests/test_utils.py` | `agent/utils.py` |

## Test Structure

**Suite Organization:**
Tests are grouped into classes by feature/behavior using `class Test*:`:

```python
class TestTicketNumbering:
    """Test _next_ticket_number for various inboxes."""

    def test_info_inbox_prefix(self):
        logger, _ = _make_logger()
        assert logger._next_ticket_number("info@vidarbhainfotech.com") == "INF-0001"
        assert logger._next_ticket_number("info@vidarbhainfotech.com") == "INF-0002"

    def test_sales_inbox_prefix(self):
        logger, _ = _make_logger()
        assert logger._next_ticket_number("sales@vidarbhainfotech.com") == "SAL-0001"
```

**Naming convention:** `test_{what_is_being_tested}` using descriptive names:
- `test_basic_parse` — positive path
- `test_sender_without_name` — edge case
- `test_missing_required_exits` — error/failure path
- `test_circuit_breaker_skips_poll` — behavior verification

**Docstrings:** Present on most test methods, explaining what the test verifies:
```python
def test_poll_does_not_label(self, mock_build, mock_creds):
    """poll() should return emails WITHOUT labeling them."""
```

## Shared Fixtures

**Location:** `tests/conftest.py`

**Key fixtures:**

```python
@dataclass
class MockEmail:
    """Minimal email object matching the EmailMessage interface."""
    thread_id: str = "test_thread"
    message_id: str = "test_msg"
    inbox: str = "info@vidarbhainfotech.com"
    sender_name: str = "Test Sender"
    sender_email: str = "test@example.com"
    subject: str = "Test Subject"
    body: str = "Test body content"
    timestamp: datetime = None  # defaults to datetime.now() in __post_init__
    attachment_count: int = 0
    attachment_names: list = field(default_factory=list)
    gmail_link: str = ""


@pytest.fixture
def mock_email():
    return MockEmail()


@pytest.fixture
def mock_sheet():
    """Mock SheetLogger with sensible defaults."""
    sheet = MagicMock()
    sheet.get_open_tickets.return_value = []
    sheet.get_all_tickets.return_value = []
    sheet.is_thread_logged.return_value = False
    sheet.log_email.return_value = "INF-0001"
    sheet.spreadsheet_id = "test-sheet-id"
    return sheet


@pytest.fixture
def mock_chat():
    """Mock ChatNotifier."""
    chat = MagicMock()
    chat.notify_poll_summary.return_value = True
    chat.notify_sla_summary.return_value = True
    return chat


@pytest.fixture
def default_config():
    """Minimal config dict for testing."""
    return { ... }  # Full config with gmail, claude, sheets, sla, feature_flags
```

**Note:** `tests/test_ai_processor.py` has its own duplicate `MockEmail` dataclass (not using conftest's). This is a known inconsistency.

## Mocking

**Framework:** `unittest.mock` (standard library) — `MagicMock`, `patch`, `monkeypatch`

**Pattern 1: Patch external services at module level (Google APIs)**
```python
@patch("agent.gmail_poller.service_account.Credentials.from_service_account_file")
@patch("agent.gmail_poller.build")
def _make_poller(mock_build, mock_creds):
    return GmailPoller(service_account_key_path="/tmp/fake-sa.json")
```

**Pattern 2: Factory functions for creating mocked objects**
```python
def _make_logger(ticket_values=None):
    """Create a SheetLogger with mocked Google APIs."""
    with patch("agent.sheet_logger.service_account.Credentials.from_service_account_file"), \
         patch("agent.sheet_logger.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        # ... configure mock chain ...
        return logger, mock_sheets


def _make_reporter(config=None, mock_sheet=None, mock_chat=None):
    """Create an EODReporter with mocked dependencies."""
    sheet = mock_sheet or MagicMock()
    chat = mock_chat or MagicMock()
    sla = MagicMock()
    sla.get_breached_tickets.return_value = []
    return EODReporter(sheet, sla, chat, "/tmp/fake-sa.json", config), sheet, sla, chat
```

**Pattern 3: `monkeypatch` for environment variables**
```python
def test_loads_config_yaml(self, monkeypatch):
    monkeypatch.setenv("MONITORED_INBOXES", "info@test.com")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "test-id")
    config = load_config("config.yaml")
    assert config["gmail"]["inboxes"] == ["info@test.com"]
```

**Pattern 4: Patching datetime for time-dependent tests**
```python
@patch("main.datetime")
def test_overnight_range_during_quiet(self, mock_dt):
    mock_now = mock_dt.now.return_value
    mock_now.hour = 22
    config = {"quiet_hours": {"enabled": True, "start_hour": 20, "end_hour": 8}}
    assert is_quiet_hours(config) is True
```

**Pattern 5: Patching class methods with `patch.object`**
```python
@patch.object(EODReporter, "_send_email")
@patch.object(EODReporter, "_get_gmail_service")
def test_calls_chat_and_email(self, mock_gmail, mock_send_email, mock_sheet, mock_chat):
    reporter, _, _, chat = _make_reporter(mock_sheet=mock_sheet, mock_chat=mock_chat)
    reporter.send_report()
    chat.notify_eod_summary.assert_called_once()
    mock_send_email.assert_called_once()
```

**What to mock:**
- All Google API calls (Gmail, Sheets, Drive)
- HTTP requests (httpx.post for Chat webhook)
- Claude API calls (for unit tests)
- `datetime.now()` for time-dependent logic
- File system operations (`service_account.Credentials.from_service_account_file`)

**What NOT to mock:**
- Dataclass construction and validation
- Pure functions (`parse_sheet_datetime`, `is_quiet_hours`, `_strip_html`, `_sanitize`)
- In-memory state (`StateManager` methods)
- String/data manipulation logic

## Fixtures and Factories

**Test Data (JSON fixtures):**
```
tests/sample_emails.json  # Array of email objects with id, inbox, from_name,
                          # from_email, subject, body, expected_category, expected_priority
```

Used by integration tests:
```python
def load_sample_emails():
    fixture_path = os.path.join(os.path.dirname(__file__), "sample_emails.json")
    with open(fixture_path, "r") as f:
        return json.load(f)
```

**Inline test data:** Most tests construct data inline using dicts or dataclasses:
```python
mock_sheet.get_open_tickets.return_value = [
    {"Ticket #": "INF-0001", "Status": "New", "SLA Deadline": past_deadline, "Assigned To": ""},
]
```

## Coverage

**Requirements:** No enforced coverage threshold.

**View Coverage:**
```bash
pytest -m "not integration" --cov=agent --cov-report=term-missing
```

## Test Types

**Unit Tests (123 tests):**
- All external services mocked
- No API keys required
- Run in CI on every push/PR
- Cover: config loading, message parsing, ticket numbering, SLA breach detection, quiet hours logic, circuit breaker, dead letter retry, Chat card building, EOD stats aggregation, datetime parsing, spam filtering

**Integration Tests (8 tests, `@pytest.mark.integration`):**
- Located in `tests/test_ai_processor.py`, class `TestTriageAccuracy`
- Make real Claude API calls
- Require `ANTHROPIC_API_KEY` environment variable
- Verify triage accuracy against sample emails (category + priority assertions)
- Skipped in CI (deselected with `-m "not integration"`)

**E2E Tests:**
- Not used. The `--once` CLI flag serves as a manual end-to-end test.

## Common Patterns

**Asserting mock calls:**
```python
# Verify a mock was called
mock_sheet.log_email.assert_called_once()

# Verify specific arguments
mock_sheet.update_failed_triage_retry.assert_called_with(2, 1, "Success")

# Verify NOT called
components["gmail"].poll_all.assert_not_called()
```

**Asserting exceptions:**
```python
def test_missing_required_exits(self, monkeypatch):
    monkeypatch.delenv("MONITORED_INBOXES", raising=False)
    with pytest.raises(SystemExit):
        load_config("config.yaml")
```

**Testing dataclass defaults:**
```python
def test_default_values(self):
    result = TriageResult()
    assert result.category == "General Inquiry"
    assert result.priority == "MEDIUM"
    assert result.success is True
    assert result.error is None
```

**Testing static methods directly:**
```python
def test_removes_tags(self):
    assert "hello" in GmailPoller._strip_html("<p>hello</p>")
    assert "<p>" not in GmailPoller._strip_html("<p>hello</p>")
```

**Testing with synthetic API response data:**
```python
def _make_msg_data(self, from_header="John Doe <john@example.com>",
                   subject="Test Email", body_text="Hello world",
                   thread_id="thread_123", msg_id="msg_456",
                   internal_date="1709000000000", attachments=None):
    payload = {
        "headers": [
            {"name": "From", "value": from_header},
            {"name": "Subject", "value": subject},
        ],
        "mimeType": "text/plain",
        "body": {"data": base64.urlsafe_b64encode(body_text.encode()).decode()},
    }
    return {"id": msg_id, "threadId": thread_id, "internalDate": internal_date, "payload": payload}
```

## Adding New Tests

**For a new agent module `agent/foo.py`:**
1. Create `tests/test_foo.py`
2. Use a `_make_foo()` factory function that patches Google API credentials
3. Group tests into classes by behavior: `class TestFeatureX:`
4. Use `MagicMock()` for all external service dependencies
5. Add docstrings explaining what each test verifies
6. Use shared fixtures from `conftest.py` where applicable (`mock_email`, `mock_sheet`, `mock_chat`, `default_config`)

**For integration tests:**
1. Add `@pytest.mark.integration` decorator
2. Skip if API key missing: `pytest.skip("ANTHROPIC_API_KEY not set")`
3. Keep API calls minimal (cost-aware)

---

*Testing analysis: 2026-03-09*
