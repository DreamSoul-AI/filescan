#!/bin/bash
set -euo pipefail

usage() {
  echo "Usage: $0 [-n] [-d dist_path] [-P package_name]"
  echo "  -n: Do not install the generated package"
  echo "  -d: Dist path (default: dist)"
  echo "  -P: Package name (default: $PACKAGE_NAME)"
  exit 1
}

INSTALL_PACKAGE=true
DIST_PATH="dist"
PACKAGE_NAME="filescan"
PKG_DIR="src/$PACKAGE_NAME"

STAGE_FILES=("README.md" "README_zh.md" "LICENSE" "requirements.txt")

while getopts "nd:P:h" opt; do
  case "$opt" in
    n) INSTALL_PACKAGE=false ;;
    d) DIST_PATH="$OPTARG" ;;
    P) PACKAGE_NAME="$OPTARG"; PKG_DIR="src/$PACKAGE_NAME" ;;
    h) usage ;;
    *) usage ;;
  esac
done

if [ ! -d "$PKG_DIR" ]; then
  echo "❌ Package dir not found: $PKG_DIR"
  exit 1
fi

echo "📦 Building $PACKAGE_NAME from pyproject.toml"
mkdir -p "$DIST_PATH"

echo "🧩 Staging package data into $PKG_DIR"
STAGED_FILES=()
for f in "${STAGE_FILES[@]}"; do
  if [ -f "$f" ]; then
    cp -f "$f" "$PKG_DIR/$f"
    STAGED_FILES+=("$PKG_DIR/$f")
  fi
done

cleanup() {
  echo "🧹 Cleaning up staged files"
  for p in "${STAGED_FILES[@]}"; do
    rm -f "$p" || true
  done
}

trap cleanup ERR

rm -rf build "$DIST_PATH" *.egg-info src/*.egg-info

echo "🔧 Building wheel..."
python -m build --wheel --outdir "$DIST_PATH"

WHL_FILE="$(ls -1 "$DIST_PATH"/*.whl | head -n 1)"
echo "✅ Built wheel: $WHL_FILE"

if $INSTALL_PACKAGE; then
  pip uninstall -y "$PACKAGE_NAME" >/dev/null 2>&1 || true
  pip install "$WHL_FILE"
fi

cleanup
echo "🎉 Done."
