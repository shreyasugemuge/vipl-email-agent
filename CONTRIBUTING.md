# Contributing

## Development Setup

```bash
# Clone and switch to v2 branch
git clone https://github.com/shreyasugemuge/vipl-email-agent.git
cd vipl-email-agent
git checkout v2

# Create Python 3.13 venv
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Configure environment
cp .env.example .env

# Run migrations (SQLite for local dev)
python manage.py migrate

# Run tests
pytest -v
```

## Branch Strategy

- `main` — v1 (frozen, do not push)
- `v2` — active development
- Feature branches off `v2`, merge back via PR

## Commit Messages

Follow conventional commits:
- `feat(scope):` — new feature
- `fix(scope):` — bug fix
- `test(scope):` — tests
- `docs(scope):` — documentation
- `ci(scope):` — CI/CD changes

## Testing

All code must have tests. Run `pytest -v` before pushing. CI runs tests on every push to v2.

## Code Style

- Python: follow existing patterns in the codebase
- Templates: Tailwind CSS v4 + HTMX 2.0
- No React, no Node.js, no build steps
