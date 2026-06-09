#!/bin/bash
set -e

echo "Starting AppImage Packaging..."

# Directories
WORKSPACE=$(pwd)
APP_DIR="${WORKSPACE}/AppDir"
DIST_DIR="${WORKSPACE}/app.dist"

# Cleanup
rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}/usr/bin"

# 1. Copy Nuitka standalone files into AppDir
echo "Copying compiled client files from ${DIST_DIR}..."
if [ ! -d "${DIST_DIR}" ]; then
    echo "Error: ${DIST_DIR} not found. Please compile client/app.py with Nuitka standalone first."
    exit 1
fi
cp -r "${DIST_DIR}"/* "${APP_DIR}/usr/bin/"

# 2. Copy launcher assets
cp "${WORKSPACE}/packaging/linux/client.desktop" "${APP_DIR}/freeskoden-lighthouse.desktop"
cp "${WORKSPACE}/packaging/linux/icon.png" "${APP_DIR}/freeskoden-lighthouse.png"
cp "${WORKSPACE}/packaging/linux/icon.png" "${APP_DIR}/.DirIcon"

# 3. Create AppRun script
echo "Creating AppRun entrypoint..."
cat << 'EOF' > "${APP_DIR}/AppRun"
#!/bin/sh
SELF=$(dirname "$(readlink -f "$0")")
# Nuitka standalone places binary dependencies next to the main executable
export LD_LIBRARY_PATH="${SELF}/usr/bin:${LD_LIBRARY_PATH}"
exec "${SELF}/usr/bin/app" "$@"
EOF
chmod +x "${APP_DIR}/AppRun"

# 4. Download appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# 5. Build the AppImage
echo "Building AppImage..."
export ARCH=x86_64
# We use --appimage-extract-and-run because GitHub runners don't support FUSE by default
./appimagetool-x86_64.AppImage --appimage-extract-and-run "${APP_DIR}" "${WORKSPACE}/Freeskoden_Lighthouse-x86_64.AppImage"

echo "AppImage Packaging Complete!"
