#!/bin/bash
# Push all Kestra flow definitions to the running Kestra instance.
# Run this after 'docker compose up' or whenever flows are updated.

KESTRA_URL="http://localhost:8080"
KESTRA_USER="deng-proj@hslu.ch"
KESTRA_PASS="Admin123!"

for flow in flows/*.yml; do
  echo "Uploading $flow..."
  curl -s -o /dev/null -w "  → %{http_code}\n" \
    -X POST "$KESTRA_URL/api/v1/flows" \
    -u "$KESTRA_USER:$KESTRA_PASS" \
    -H "Content-Type: application/x-yaml" \
    --data-binary @"$flow"
done

echo "Done."
