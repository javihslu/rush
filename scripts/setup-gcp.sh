#!/usr/bin/env bash
set -euo pipefail

# GCP onboarding: authenticate, create project, link billing, enable APIs,
# set up ADC, and generate terraform.tfvars.
#
# Called by setup.sh or run standalone:
#   ./scripts/setup-gcp.sh

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# -- config.yaml parser --

yaml_val() {
    awk -v section="$1" -v key="$2" '
        $0 ~ "^"section":" { in_section=1; next }
        in_section && /^[a-zA-Z]/ { in_section=0 }
        in_section && $0 ~ "^  "key":" {
            val = $0; sub(/^[^:]+:[[:space:]]*/, "", val); print val; exit
        }
    ' "$REPO_DIR/config.yaml"
}

PROJECT_NAME=$(yaml_val project name)
GCP_REGION=$(yaml_val gcp region)

echo "---------------------"
echo "GCP cloud setup"
echo "---------------------"
echo ""

# -- check tools --

if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI is not installed."
    echo "  Install it: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo "[ok] gcloud CLI"

HAVE_TERRAFORM=true
if ! command -v terraform &> /dev/null; then
    HAVE_TERRAFORM=false
    echo ""
    echo "WARNING: terraform is not available."
    echo "  You can continue GCP setup and install terraform later."
    echo ""
else
    echo "[ok] terraform"
fi

echo ""
read -r -p "Set up GCP now? [Y/n]: " SETUP_GCP
SETUP_GCP="${SETUP_GCP:-Y}"

if [[ ! "$SETUP_GCP" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Skipping GCP setup. Re-run: ./scripts/setup-gcp.sh"
    echo ""
    exit 0
fi

echo ""

# -- step 1: authenticate --

echo "Step 1/6: Authenticate with Google Cloud"
echo "  A browser window will open. Log in with your Google account."
echo ""
read -r -p "Press Enter to open the browser..."
gcloud auth login
echo ""
echo "[ok] Authenticated"
echo ""

# -- step 2: create project --

ACCOUNT=$(gcloud config get-value account 2>/dev/null)
echo "Logged in as: $ACCOUNT"
echo ""

EMAIL_PREFIX=$(echo "$ACCOUNT" | cut -d@ -f1 | tr '.' '-' | tr -cd 'a-z0-9-' | head -c 20)
DEFAULT_PROJECT_ID="${PROJECT_NAME}-${EMAIL_PREFIX}"

echo "Step 2/6: Create GCP project"
read -r -p "Project ID [$DEFAULT_PROJECT_ID]: " PROJECT_ID
PROJECT_ID="${PROJECT_ID:-$DEFAULT_PROJECT_ID}"

echo ""
echo "Available regions:"
echo "  1) europe-west6  (Zurich)"
echo "  2) europe-west1  (Belgium -- cheaper)"
read -r -p "Region [1]: " REGION_CHOICE
case "${REGION_CHOICE:-1}" in
    2) REGION="europe-west1" ;;
    *) REGION="${GCP_REGION:-europe-west6}" ;;
esac

echo ""
echo "Creating project: $PROJECT_ID (region: $REGION)"

if gcloud projects describe "$PROJECT_ID" &> /dev/null; then
    echo "  Project already exists -- reusing it."
else
    gcloud projects create "$PROJECT_ID"
    echo "  Project created."
fi

gcloud config set project "$PROJECT_ID"
echo "[ok] Active project set to $PROJECT_ID"
echo ""

# -- step 3: link billing --

echo "Step 3/6: Link billing account"

BILLING_ACCOUNTS=$(gcloud billing accounts list --format="value(name)" --filter="open=true" 2>/dev/null)
BILLING_COUNT=$(echo "$BILLING_ACCOUNTS" | grep -c . || true)

if [ "$BILLING_COUNT" -eq 0 ]; then
    echo "ERROR: No active billing accounts found."
    echo "  Set up billing at: https://console.cloud.google.com/billing"
    echo "  Then re-run: ./scripts/setup-gcp.sh"
    exit 1
elif [ "$BILLING_COUNT" -eq 1 ]; then
    BILLING_ACCOUNT_ID="$BILLING_ACCOUNTS"
    echo "  Found one billing account: $BILLING_ACCOUNT_ID"
else
    echo "  Multiple billing accounts found:"
    gcloud billing accounts list --filter="open=true"
    echo ""
    read -r -p "Enter billing account ID: " BILLING_ACCOUNT_ID
fi

gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT_ID"
echo "[ok] Billing linked"
echo ""

# -- step 4: enable APIs --

echo "Step 4/6: Enable required APIs"

for api in storage.googleapis.com bigquery.googleapis.com; do
    echo "  Enabling $api ..."
    gcloud services enable "$api"
done

echo "[ok] APIs enabled"
echo ""

# -- step 5: ADC --

echo "Step 5/6: Set up Application Default Credentials"
echo "  A browser window will open again. Use the same Google account."
echo ""
read -r -p "Press Enter to open the browser..."
gcloud auth application-default login
gcloud auth application-default set-quota-project "$PROJECT_ID" 2>/dev/null || true
echo ""
echo "[ok] ADC configured"
echo ""

# -- step 6: save config --

echo "Step 6/6: Save project configuration"

cat > "$REPO_DIR/gcp_config.json" <<JSONEOF
{
  "project_id": "$PROJECT_ID",
  "region": "$REGION",
  "billing_account_id": "$BILLING_ACCOUNT_ID"
}
JSONEOF

echo "  Saved to gcp_config.json (gitignored)"

cat > "$REPO_DIR/terraform/terraform.tfvars" <<TFEOF
project_id = "$PROJECT_ID"
region     = "$REGION"
TFEOF

echo "  Saved to terraform/terraform.tfvars (gitignored)"
echo ""

# -- terraform provisioning --

if [ "$HAVE_TERRAFORM" = true ]; then
    echo "Provisioning cloud infrastructure with Terraform ..."
    echo ""
    cd "$REPO_DIR/terraform"
    terraform init
    terraform apply -auto-approve
    cd "$REPO_DIR"
    echo ""
    echo "[ok] Cloud infrastructure provisioned"
else
    echo "Terraform is not available -- skipping cloud provisioning."
    echo "  Install terraform, then run:"
    echo "    cd terraform && terraform init && terraform apply"
fi

echo ""
echo "[ok] GCP setup complete"
