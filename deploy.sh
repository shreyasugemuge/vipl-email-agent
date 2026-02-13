#!/bin/bash
# VIPL Email Agent — One-command deploy
# Usage: ./deploy.sh
set -euo pipefail

echo "=== Pulling latest code ==="
git reset --hard origin/main
git pull origin main

echo "=== Building container ==="
gcloud builds submit \
  --tag asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent:latest \
  --project=utilities-vipl

echo "=== Deploying to Cloud Run ==="
gcloud run deploy vipl-email-agent \
  --image=asia-south1-docker.pkg.dev/utilities-vipl/vipl-repo/vipl-email-agent:latest \
  --region=asia-south1 \
  --memory=512Mi --cpu=1 \
  --min-instances=1 --max-instances=1 \
  --no-allow-unauthenticated \
  --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest \
  --set-secrets=GOOGLE_CHAT_WEBHOOK_URL=chat-webhook-url:latest \
  --set-secrets=/secrets/service-account.json=sa-key:latest \
  --env-vars-file=/dev/stdin \
  --project=utilities-vipl <<EOF
GOOGLE_SHEET_ID: "1fV9AZR22WTS8CY7kxniwX-WtWVdnCp1SRlqjCFlXQ9o"
MONITORED_INBOXES: "info@vidarbhainfotech.com,sales@vidarbhainfotech.com"
ADMIN_EMAIL: "shreyas@vidarbhainfotech.com"
EOD_RECIPIENTS: "shreyas@vidarbhainfotech.com"
EOF

echo ""
echo "=== Deployed! ==="
echo ""
echo "=== Recent logs ==="
sleep 5
gcloud run services logs read vipl-email-agent \
  --region=asia-south1 --project=utilities-vipl --limit=15
