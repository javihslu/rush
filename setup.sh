#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

OS="$(uname -s)"

# -- config.yaml parser --

yaml_val() {
    # Extract a value from config.yaml given a section and key.
    # Usage: yaml_val section key
    awk -v section="$1" -v key="$2" '
        $0 ~ "^"section":" { in_section=1; next }
        in_section && /^[a-zA-Z]/ { in_section=0 }
        in_section && $0 ~ "^  "key":" {
            val = $0; sub(/^[^:]+:[[:space:]]*/, "", val); print val; exit
        }
    ' "$REPO_DIR/config.yaml"
}

if [ ! -f "$REPO_DIR/config.yaml" ]; then
    echo "ERROR: config.yaml not found."
    exit 1
fi

PROJECT_NAME=$(yaml_val project name)
DB_USER=$(yaml_val database user)
DB_PASSWORD=$(yaml_val database password)
DB_NAME=$(yaml_val database name)
DB_HOST=$(yaml_val database host)
DB_PORT=$(yaml_val database port)
PGADMIN_EMAIL=$(yaml_val pgadmin email)
PGADMIN_PASSWORD=$(yaml_val pgadmin password)
AIRFLOW_USER=$(yaml_val airflow user)
AIRFLOW_PASSWORD=$(yaml_val airflow password)
GCP_REGION=$(yaml_val gcp region)

echo "$PROJECT_NAME -- project setup"
echo "====================="
echo ""
echo "[ok] config.yaml loaded"
echo ""

# -- helpers --

check_command() {
    command -v "$1" &> /dev/null
}

ensure_brew() {
    if ! check_command brew; then
        echo "  Installing Homebrew ..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
    fi
}

install_package() {
    local name="$1" brew_pkg="$2" apt_pkg="$3"

    case "$OS" in
        Darwin)
            ensure_brew
            echo "  brew install $brew_pkg ..."
            brew install "$brew_pkg"
            ;;
        Linux)
            if check_command apt-get; then
                echo "  sudo apt-get install $apt_pkg ..."
                sudo apt-get update -qq && sudo apt-get install -y -qq "$apt_pkg"
            elif check_command dnf; then
                echo "  sudo dnf install $apt_pkg ..."
                sudo dnf install -y "$apt_pkg"
            elif check_command snap; then
                echo "  sudo snap install $apt_pkg --classic ..."
                sudo snap install "$apt_pkg" --classic
            else
                return 1
            fi
            ;;
        *)
            return 1
            ;;
    esac
}

offer_install() {
    local cmd="$1" name="$2" brew_pkg="$3" apt_pkg="$4" manual_url="$5"

    if check_command "$cmd"; then
        echo "[ok] $name"
        return 0
    fi

    echo ""
    echo "$name is not installed."

    local pkg_mgr=""
    case "$OS" in
        Darwin) pkg_mgr="Homebrew" ;;
        Linux)
            if check_command apt-get; then pkg_mgr="apt"
            elif check_command dnf; then pkg_mgr="dnf"
            elif check_command snap; then pkg_mgr="snap"
            fi
            ;;
    esac

    if [ -n "$pkg_mgr" ]; then
        read -r -p "  Install $name via $pkg_mgr? [Y/n]: " INSTALL_CHOICE
        INSTALL_CHOICE="${INSTALL_CHOICE:-Y}"
        if [[ "$INSTALL_CHOICE" =~ ^[Yy]$ ]]; then
            if install_package "$name" "$brew_pkg" "$apt_pkg"; then
                echo "[ok] $name installed"
                return 0
            fi
        fi
    fi

    echo "  Install manually: $manual_url"
    return 1
}

# -- check / install prerequisites --

if ! check_command git; then
    echo "ERROR: git is not installed."
    echo "  https://git-scm.com/downloads"
    exit 1
fi
echo "[ok] git"

# docker
if ! check_command docker; then
    echo ""
    echo "ERROR: Docker is not installed."
    echo "  Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
fi

if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif check_command docker-compose; then
    COMPOSE="docker-compose"
else
    echo "ERROR: docker compose is not available."
    echo "  Install Docker Desktop (includes Compose) or install the plugin:"
    echo "  https://docs.docker.com/compose/install/"
    exit 1
fi

echo "[ok] docker"
echo "[ok] docker compose"

# gcloud
HAVE_GCLOUD=true
offer_install "gcloud" "gcloud CLI" "google-cloud-sdk" "google-cloud-cli" \
    "https://cloud.google.com/sdk/docs/install" || HAVE_GCLOUD=false

# terraform
HAVE_TERRAFORM=true
offer_install "terraform" "Terraform" "hashicorp/tap/terraform" "terraform" \
    "https://developer.hashicorp.com/terraform/install" || HAVE_TERRAFORM=false

echo ""

# -- generate .env from config.yaml --

if [ ! -f ".env" ]; then
    cat > .env <<ENVEOF
# Auto-generated from config.yaml — edit config.yaml instead.
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=$DB_NAME
POSTGRES_HOST=$DB_HOST
POSTGRES_PORT=$DB_PORT
PGADMIN_DEFAULT_EMAIL=$PGADMIN_EMAIL
PGADMIN_DEFAULT_PASSWORD=$PGADMIN_PASSWORD
AIRFLOW_USER=$AIRFLOW_USER
AIRFLOW_PASSWORD=$AIRFLOW_PASSWORD
ENVEOF
    echo "[ok] .env generated from config.yaml"
else
    echo "[ok] .env already exists (delete it to regenerate from config.yaml)"
fi

# -- bring up the local stack --

echo ""
echo "Starting docker compose stack ..."
$COMPOSE up -d --build
echo ""
echo "Services:"
$COMPOSE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

# -- GCP onboarding --

GCP_CONFIGURED=false
if [ -f "$REPO_DIR/gcp_config.json" ]; then
    GCP_CONFIGURED=true
fi

if [ "$GCP_CONFIGURED" = true ]; then
    echo "[ok] GCP already configured (gcp_config.json exists)"
    echo ""
else
    echo "---------------------"
    echo "GCP cloud setup"
    echo "---------------------"
    echo ""

    # check gcloud
    if [ "$HAVE_GCLOUD" = false ]; then
        echo "gcloud CLI is not available. Skipping GCP setup."
        echo "  Install it and re-run: ./setup.sh"
        echo ""
        echo "Local stack is running. You can start working locally."
        exit 0
    fi

    echo "[ok] gcloud CLI"

    if [ "$HAVE_TERRAFORM" = false ]; then
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

    if [[ "$SETUP_GCP" =~ ^[Yy]$ ]]; then
        echo ""

        # step 1: authenticate
        echo "Step 1/6: Authenticate with Google Cloud"
        echo "  A browser window will open. Log in with your Google account."
        echo ""
        read -r -p "Press Enter to open the browser..."
        gcloud auth login
        echo ""
        echo "[ok] Authenticated"
        echo ""

        # step 2: create project
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

        # step 3: link billing
        echo "Step 3/6: Link billing account"

        BILLING_ACCOUNTS=$(gcloud billing accounts list --format="value(name)" --filter="open=true" 2>/dev/null)
        BILLING_COUNT=$(echo "$BILLING_ACCOUNTS" | grep -c . || true)

        if [ "$BILLING_COUNT" -eq 0 ]; then
            echo "ERROR: No active billing accounts found."
            echo "  Set up billing at: https://console.cloud.google.com/billing"
            echo "  Then re-run: ./setup.sh"
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

        # step 4: enable APIs
        echo "Step 4/6: Enable required APIs"

        for api in storage.googleapis.com bigquery.googleapis.com; do
            echo "  Enabling $api ..."
            gcloud services enable "$api"
        done

        echo "[ok] APIs enabled"
        echo ""

        # step 5: ADC
        echo "Step 5/6: Set up Application Default Credentials"
        echo "  A browser window will open again. Use the same Google account."
        echo ""
        read -r -p "Press Enter to open the browser..."
        gcloud auth application-default login
        gcloud auth application-default set-quota-project "$PROJECT_ID" 2>/dev/null || true
        echo ""
        echo "[ok] ADC configured"
        echo ""

        # step 6: save config
        echo "Step 6/6: Save project configuration"

        cat > "$REPO_DIR/gcp_config.json" <<JSONEOF
{
  "project_id": "$PROJECT_ID",
  "region": "$REGION",
  "billing_account_id": "$BILLING_ACCOUNT_ID"
}
JSONEOF

        echo "  Saved to gcp_config.json (gitignored)"

        if [ -d "$REPO_DIR/terraform" ]; then
            cat > "$REPO_DIR/terraform/terraform.tfvars" <<TFEOF
project_id = "$PROJECT_ID"
region     = "$REGION"
TFEOF
            echo "  Saved to terraform/terraform.tfvars (gitignored)"
        fi

        echo ""

        # -- terraform provisioning --

        if [ "$HAVE_TERRAFORM" = true ] && [ -f "$REPO_DIR/terraform/main.tf" ]; then
            echo "Provisioning cloud infrastructure with Terraform ..."
            echo ""
            cd "$REPO_DIR/terraform"
            terraform init
            terraform apply -auto-approve
            cd "$REPO_DIR"
            echo ""
            echo "[ok] Cloud infrastructure provisioned"
        elif [ "$HAVE_TERRAFORM" = false ]; then
            echo "Terraform is not available -- skipping cloud provisioning."
            echo "  Install terraform and re-run: ./setup.sh"
        else
            echo "No terraform/main.tf found -- skipping cloud provisioning."
        fi

        echo ""
    else
        echo ""
        echo "Skipping GCP setup. Re-run ./setup.sh when ready."
        echo ""
    fi
fi

echo "====================="
echo "Setup complete."
echo ""
echo "  pgAdmin:    http://localhost:8085"
echo "  Airflow:    http://localhost:8080"
echo "  PostgreSQL: localhost:5432"
echo "  Stop:       $COMPOSE down"
