# Codebase Structure

**Analysis Date:** 2026-03-09

## Directory Layout

```
vipl-email-agent/
├── agent/                   # Core application modules (Python package)
│   ├── __init__.py          # Package init, version string
│   ├── ai_processor.py      # Two-tier Claude AI triage + spam filter
│   ├── chat_notifier.py     # Google Chat Cards v2 webhook notifications
│   ├── eod_reporter.py      # Daily EOD summary email + Chat card
│   ├── gmail_poller.py      # Gmail API polling + email parsing
│   ├── sheet_logger.py      # Google Sheets CRUD (all 7+ tabs)
│   ├── sla_monitor.py       # SLA breach detection + summary alerts
│   ├── state.py             # In-memory ephemeral state
│   └── utils.py             # Shared utilities (datetime parsing, IST)
├── prompts/                 # AI system prompts
│   └── triage_prompt.txt    # Claude triage system prompt (with injection defense)
├── templates/               # Email templates
│   └── eod_email.html       # Jinja2 HTML template for EOD report email
├── tests/                   # Test suite (pytest)
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures (MockEmail, mock services, config)
│   ├── sample_emails.json   # Fixture data for integration tests
│   ├── test_ai_processor.py
│   ├── test_chat_notifier.py
│   ├── test_eod_reporter.py
│   ├── test_gmail_poller.py
│   ├── test_main.py
│   ├── test_sheet_logger.py
│   ├── test_sla_monitor.py
│   └── test_utils.py
├── scripts/                 # Operational scripts
│   ├── run_local.sh         # Local dev runner (loads .env, validates SA key)
│   ├── deploy_cloudrun.sh   # Manual Cloud Run deploy script
│   └── sheet_changelog.gs   # Google Apps Script for Sheet change tracking
├── docs/                    # Documentation
│   └── mahatender/          # Unrelated project docs (tender intelligence)
├── .github/workflows/
│   └── deploy.yml           # CI/CD: tag v*.*.* -> test -> build -> deploy -> release
├── main.py                  # Entry point (CLI, scheduler, health server, config)
├── config.yaml              # Non-sensitive default configuration
├── Dockerfile               # Python 3.11-slim, non-root user
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Dev/test dependencies (pytest, pytest-cov)
├── pytest.ini               # Pytest configuration
├── CLAUDE.md                # AI assistant project context
├── CHANGELOG.md             # Version history
├── README.md                # Project readme
├── .env.example             # Example environment variables (secrets not included)
├── .gitignore               # Git ignore rules
├── .dockerignore            # Docker build ignore rules
├── .gcloudignore            # GCP deploy ignore rules
└── .planning/               # Planning documents (this directory)
    └── codebase/            # Codebase analysis documents
```

## Directory Purposes

**`agent/`:**
- Purpose: All core application logic as a Python package
- Contains: One class per module, each responsible for a single integration or concern
- Key files: `sheet_logger.py` (largest, ~700 lines, central data layer), `ai_processor.py` (~437 lines, AI + spam + PDF), `gmail_poller.py` (~325 lines, Gmail API)

**`prompts/`:**
- Purpose: AI system prompts loaded at runtime
- Contains: Single text file with Claude triage instructions including prompt injection defense rules
- Key files: `triage_prompt.txt`

**`templates/`:**
- Purpose: Jinja2 HTML templates for email reports
- Contains: EOD summary email template with stats, breach tables, unassigned ticket lists
- Key files: `eod_email.html`

**`tests/`:**
- Purpose: Unit and integration test suite
- Contains: One test file per source module, plus shared fixtures and sample data
- Key files: `conftest.py` (shared fixtures), `sample_emails.json` (integration test data)

**`scripts/`:**
- Purpose: Operational and development helper scripts
- Contains: Shell scripts for local dev and deployment, Google Apps Script for Sheet automation
- Key files: `run_local.sh` (primary local dev entry point)

**`.github/workflows/`:**
- Purpose: CI/CD pipeline configuration
- Contains: Single unified workflow for test + build + deploy + release
- Key files: `deploy.yml`

## Key File Locations

**Entry Points:**
- `main.py`: Application entry point (CLI args, scheduler, health server, config loading)
- `Dockerfile`: Container entry point (`ENTRYPOINT ["python", "main.py"]`)

**Configuration:**
- `config.yaml`: Non-sensitive defaults (poll intervals, model names, SLA hours, tab names)
- `.env.example`: Template for required environment variables
- `pytest.ini`: Test runner configuration

**Core Logic:**
- `agent/gmail_poller.py`: Email ingestion (Gmail API, domain-wide delegation)
- `agent/ai_processor.py`: AI triage pipeline (spam filter, Haiku, Sonnet escalation)
- `agent/sheet_logger.py`: Data persistence layer (Google Sheets CRUD for all tabs)
- `agent/chat_notifier.py`: Notification delivery (Google Chat webhook)
- `agent/sla_monitor.py`: SLA compliance monitoring and breach alerting
- `agent/eod_reporter.py`: Daily summary report generation and delivery
- `agent/state.py`: In-memory runtime state (cooldowns, failures, dedup)
- `agent/utils.py`: Shared datetime parsing utilities

**AI Prompts:**
- `prompts/triage_prompt.txt`: System prompt for Claude email triage

**Templates:**
- `templates/eod_email.html`: Jinja2 HTML template for EOD email

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures (mock email, mock services, default config dict)
- `tests/sample_emails.json`: Sample email data for integration tests
- `tests/test_*.py`: One test file per source module

**CI/CD:**
- `.github/workflows/deploy.yml`: Unified CI/CD pipeline (test -> build -> deploy -> release)

**Deployment:**
- `Dockerfile`: Production container definition (Python 3.11-slim, non-root)
- `scripts/deploy_cloudrun.sh`: Manual Cloud Run deployment
- `scripts/run_local.sh`: Local development runner

## Naming Conventions

**Files:**
- Source modules: `snake_case.py` (e.g., `gmail_poller.py`, `ai_processor.py`, `sheet_logger.py`)
- Test files: `test_<module_name>.py` mirroring the source module (e.g., `test_gmail_poller.py`)
- Config files: `config.yaml`, `requirements.txt`, `pytest.ini`
- Shell scripts: `snake_case.sh` (e.g., `run_local.sh`, `deploy_cloudrun.sh`)

**Directories:**
- Lowercase, no separators: `agent/`, `prompts/`, `templates/`, `tests/`, `scripts/`, `docs/`

**Classes:**
- PascalCase, descriptive: `GmailPoller`, `AIProcessor`, `SheetLogger`, `ChatNotifier`, `SLAMonitor`, `EODReporter`, `StateManager`

**Functions/Methods:**
- snake_case: `process_emails()`, `load_config()`, `poll_all()`, `is_thread_logged()`
- Private methods prefixed with underscore: `_call_claude()`, `_extract_body()`, `_parse_message()`

**Constants:**
- UPPER_SNAKE_CASE: `VALID_CATEGORIES`, `VALID_PRIORITIES`, `SPAM_PATTERNS`, `MAX_BODY_CHARS`, `SCOPES`, `IST`

## Where to Add New Code

**New Agent Module (e.g., new integration):**
- Implementation: `agent/<module_name>.py` (single class, single responsibility)
- Tests: `tests/test_<module_name>.py`
- Wire into: `main.py:init_components()` for initialization, add scheduler job in `main.py:run_agent()` if recurring
- Pattern: Follow existing module pattern -- class with `__init__` taking config/dependencies, public methods for operations

**New Notification Type:**
- Add method to `agent/chat_notifier.py` following existing pattern (build Cards v2 payload, call `self._post()`)
- Call from the appropriate orchestration point in `main.py`

**New Sheet Tab Integration:**
- Add read/write methods to `agent/sheet_logger.py`
- Add tab name to `config.yaml` under `google_sheets`
- Add header initialization in `SheetLogger.ensure_headers()` if the tab needs auto-setup

**New CLI Command:**
- Add argument in `main.py:main()` argparse section
- Add dispatch logic below existing `if args.xxx:` blocks

**New AI Prompt:**
- Add prompt file to `prompts/` directory
- Load via `AIProcessor._load_system_prompt()` pattern

**New Email Template:**
- Add Jinja2 HTML template to `templates/`
- Load via Jinja2 `FileSystemLoader` (already configured in `EODReporter`)

**New Configuration Option:**
- Add default value in `config.yaml`
- Add env var overlay in `main.py:load_config()` if it should be overridable via env
- Add Sheet override handling in `main.py:load_sheet_config_overrides()` if it should be hot-reloadable

**Shared Utility:**
- Add to `agent/utils.py` for small helpers
- Import as `from agent.utils import <function>`

## Special Directories

**`.planning/`:**
- Purpose: GSD planning and codebase analysis documents
- Generated: By analysis tools
- Committed: Yes (planning artifacts tracked in git)

**`.claude/`:**
- Purpose: Claude Code agent configurations, commands, skills, helpers
- Generated: By claude-flow tooling
- Committed: Yes (part of development workflow)

**`.claude-flow/`:**
- Purpose: Claude-flow runtime data (sessions, metrics, logs)
- Generated: Yes (runtime artifacts)
- Committed: No (in .gitignore)

**`docs/mahatender/`:**
- Purpose: Unrelated project documentation (tender intelligence research)
- Generated: No (manual docs)
- Committed: Partially (new, untracked)

---

*Structure analysis: 2026-03-09*
