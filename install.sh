#!/usr/bin/env bash
# Bootstrap script for Rush.
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/javihslu/rush/main/install.sh)
#   bash <(curl -fsSL https://raw.githubusercontent.com/javihslu/rush/main/install.sh) ~/projects/rush
set -euo pipefail

REPO="https://github.com/javihslu/rush.git"
TARGET="${1:-rush}"

echo ""
echo "rush -- bootstrap installer"
echo "============================"
echo ""

# -- check git --

if ! command -v git &> /dev/null; then
    echo "ERROR: git is not installed."
    echo "  https://git-scm.com/downloads"
    exit 1
fi

# -- check docker --

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "  https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
fi

# -- clone --

if [ -d "$TARGET" ]; then
    echo "Directory '$TARGET' already exists."
    read -r -p "Use existing directory? [Y/n]: " USE_EXISTING
    USE_EXISTING="${USE_EXISTING:-Y}"
    if [[ ! "$USE_EXISTING" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo "Cloning into '$TARGET' ..."
    git clone "$REPO" "$TARGET"
fi

# -- run setup --

cd "$TARGET"
echo ""
exec ./setup.sh
