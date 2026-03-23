#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo ""
echo "rush -- teardown"
echo "================"
echo ""

# -- docker compose --

if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    COMPOSE=""
fi

if [ -n "$COMPOSE" ]; then
    echo "Stopping containers and removing volumes ..."
    $COMPOSE down -v --remove-orphans 2>/dev/null || true
    echo "[ok] Containers and volumes removed"
else
    echo "[skip] docker compose not found"
fi

# -- remove built image --

if docker image inspect rush-dev &> /dev/null 2>&1; then
    echo "Removing rush-dev Docker image ..."
    docker rmi rush-dev 2>/dev/null || true
    echo "[ok] Image removed"
fi

# -- generated local files --

for f in .env gcp_config.json terraform/terraform.tfvars; do
    if [ -f "$REPO_DIR/$f" ]; then
        echo "Removing $f ..."
        rm -f "$REPO_DIR/$f"
        echo "[ok] $f removed"
    fi
done

# -- terraform state --

if [ -d "$REPO_DIR/terraform/.terraform" ]; then
    echo "Removing Terraform state ..."
    rm -rf "$REPO_DIR/terraform/.terraform"
    rm -f "$REPO_DIR/terraform/"*.tfstate "$REPO_DIR/terraform/"*.tfstate.backup
    echo "[ok] Terraform state removed"
fi

# -- GCP resources --

echo ""
if command -v gcloud &> /dev/null && command -v terraform &> /dev/null && [ -f "$REPO_DIR/terraform/main.tf" ]; then
    read -r -p "Destroy GCP cloud resources (Terraform)? [y/N]: " DESTROY_GCP
    DESTROY_GCP="${DESTROY_GCP:-N}"
    if [[ "$DESTROY_GCP" =~ ^[Yy]$ ]]; then
        cd "$REPO_DIR/terraform"
        terraform destroy -auto-approve
        cd "$REPO_DIR"
        echo "[ok] GCP resources destroyed"
    else
        echo "[skip] GCP resources kept"
    fi
else
    echo "[skip] No GCP resources to destroy"
fi

echo ""
echo "================"
echo "Teardown complete."
echo ""
echo "To remove the project entirely:"
echo "  cd .. && rm -rf rush"
