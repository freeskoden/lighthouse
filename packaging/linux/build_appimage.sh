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

# Rename binary from 'app' to 'lighthouse' to match icon name 'Lighthouse'
if [ -f "${APP_DIR}/usr/bin/app" ]; then
    mv "${APP_DIR}/usr/bin/app" "${APP_DIR}/usr/bin/lighthouse"
fi

# 2. Copy launcher assets
# The client launcher must be named 'Lighthouse'
cp "${WORKSPACE}/packaging/linux/client.desktop" "${APP_DIR}/Lighthouse.desktop"
cp "${WORKSPACE}/packaging/linux/icon.png" "${APP_DIR}/lighthouse.png"
cp "${WORKSPACE}/packaging/linux/icon.png" "${APP_DIR}/.DirIcon"

# 3. Create AppRun script pointing to 'lighthouse' binary
echo "Creating AppRun entrypoint..."
cat << 'EOF' > "${APP_DIR}/AppRun"
#!/bin/sh
SELF=$(dirname "$(readlink -f "$0")")
export LD_LIBRARY_PATH="${SELF}/usr/bin:${LD_LIBRARY_PATH}"
exec "${SELF}/usr/bin/lighthouse" "$@"
EOF
chmod +x "${APP_DIR}/AppRun"

# 4. Download appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# 5. Build the AppImage as 'Lighthouse-x86_64.AppImage'
echo "Building AppImage..."
export ARCH=x86_64
./appimagetool-x86_64.AppImage --appimage-extract-and-run "${APP_DIR}" "${WORKSPACE}/Lighthouse-x86_64.AppImage"

echo "AppImage Packaging Complete!"
