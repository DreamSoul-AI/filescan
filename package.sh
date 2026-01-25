#!/bin/bash
set -e

usage() {
    echo "Usage: $0 [-n] [-p source_path] [-d dist_path] [-v version] [-P package_name]"
    echo "  -n: Do not install the generated package"
    echo "  -P: Package name (default: $PACKAGE_NAME)"
    echo "  -v: Version (default: 0.0.1)"
    echo "  -p: Source path (default: package name)"
    echo "  -d: Dist path (default: dist)"
    exit 1
}

# Defaults
INSTALL_PACKAGE=true
PACKAGE_NAME="package"
VERSION="0.0.1"
SOURCE_PATH=""
DIST_PATH="dist"

# Parse args
while getopts "np:d:v:P:h" opt; do
    case "$opt" in
        n) INSTALL_PACKAGE=false ;;
        P) PACKAGE_NAME="$OPTARG" ;;
        v) VERSION="$OPTARG" ;;
        p) SOURCE_PATH="$OPTARG" ;;
        d) DIST_PATH="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

[ -z "$SOURCE_PATH" ] && SOURCE_PATH="$PACKAGE_NAME"

echo "Packaging $PACKAGE_NAME version $VERSION"

# Prepare build metadata
if [ ! -f "setup.bak.cfg" ]; then
    echo "setup.bak.cfg not found"
    exit 1
fi

cp setup.bak.cfg setup.cfg

# Update version
sed -i "s/^version = .*/version = $VERSION/" setup.cfg

echo "setup.cfg:"
cat setup.cfg

# Clean previous builds
rm -rf build "$DIST_PATH" *.egg-info
mkdir -p "$DIST_PATH"

# Build wheel
echo "Building wheel..."
python -m build --wheel --outdir "$DIST_PATH"

# Locate wheel
WHL_FILE=$(ls "$DIST_PATH"/${PACKAGE_NAME}-${VERSION}-*.whl | head -n 1)

if [ ! -f "$WHL_FILE" ]; then
    echo "Wheel not found"
    exit 1
fi

echo "Built wheel: $WHL_FILE"

# Optional install
if $INSTALL_PACKAGE; then
    echo "Installing package..."
    pip uninstall -y "$PACKAGE_NAME" >/dev/null 2>&1 || true
    pip install "$WHL_FILE"
else
    echo "Skipping installation"
fi

# Cleanup
rm setup.cfg
echo "Cleaned up setup.cfg"

echo "Done."
