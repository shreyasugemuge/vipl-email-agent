# ============================================================
# VIPL Email Agent — Docker Container
# ============================================================
# Deploys as a single always-on container on Google Cloud Run
# or any Docker-compatible hosting.
#
# Build:  docker build -t vipl-email-agent .
# Run:    docker run --env-file .env vipl-email-agent
# ============================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security
RUN groupadd -r agent && useradd -r -g agent agent
RUN chown -R agent:agent /app
USER agent

# Health check (checks if the process is running)
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import json, os; state=json.load(open('state.json')); \
  from datetime import datetime; \
  last=datetime.fromisoformat(state.get('last_run','')); \
  assert (datetime.now()-last).seconds < 600" || exit 1

# Default entrypoint: run the full agent with scheduler
ENTRYPOINT ["python", "main.py"]
