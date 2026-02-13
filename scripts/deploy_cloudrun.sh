#!/bin/bash
# ============================================================
# VIPL Email Agent — Google Cloud Run Deployment Script
# ============================================================
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. Google Cloud project created with billing enabled
#   3. APIs enabled: Gmail, Sheets, Drive
#   4. Service account configured with domain-wide delegation
#   5. config.yaml filled in with correct values
#   6. ANTHROPIC_API_KEY ready
# ============================================================

set -euo pipefail

# --- Configuration ---
PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID environment variable}"
REGION="${GCP_REGION:-asia-south1}"
SERVICE_NAME="vipl-email-agent"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "VIPL Email Agent — Cloud Run Deployment"
echo "=========================================="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Service:  ${SERVICE_NAME}"
echo "=========================================="

# --- Step 1: Enable required APIs ---
echo ""
echo "[1/5] Enabling required APIs..."
gcloud services enable \
    gmail.googleapis.com \
    sheets.googleapis.com \
    drive.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    --project="${PROJECT_ID}"

# --- Step 2: Build the container ---
echo ""
echo "[2/5] Building container image..."
gcloud builds submit \
    --tag "${IMAGE}" \
    --project="${PROJECT_ID}"

# --- Step 3: Create secret for Anthropic API key ---
echo ""
echo "[3/5] Setting up secrets..."
if ! gcloud secrets describe anthropic-api-key --project="${PROJECT_ID}" 2>/dev/null; then
    echo "Creating Anthropic API key secret..."
    echo -n "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY}" | \
        gcloud secrets create anthropic-api-key \
            --data-file=- \
            --project="${PROJECT_ID}"
else
    echo "Secret 'anthropic-api-key' already exists. To update:"
    echo "  echo -n 'NEW_KEY' | gcloud secrets versions add anthropic-api-key --data-file=-"
fi

# --- Step 4: Deploy to Cloud Run ---
echo ""
echo "[4/5] Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 1 \
    --no-allow-unauthenticated \
    --set-env-vars "ANTHROPIC_API_KEY=placeholder" \
    --set-secrets "ANTHROPIC_API_KEY=anthropic-api-key:latest" \
    --project="${PROJECT_ID}" \
    --timeout=300

# --- Step 5: Verify ---
echo ""
echo "[5/5] Verifying deployment..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "  1. Send a test email to info@vidarbhainfotech.com"
echo "  2. Wait 3 minutes for the agent to process it"
echo "  3. Check the Google Sheet for a new row"
echo "  4. Check Google Chat Space for a notification"
echo "=========================================="
