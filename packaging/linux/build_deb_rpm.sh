#!/bin/bash
set -e

echo "Starting DEB & RPM Packaging..."

WORKSPACE=$(pwd)
DEB_DIR="${WORKSPACE}/deb_build"
CLIENT_DIST="${WORKSPACE}/app.dist"
SERVER_DIST="${WORKSPACE}/server.dist"

# Cleanup
rm -rf "${DEB_DIR}"
mkdir -p "${DEB_DIR}/DEBIAN"
mkdir -p "${DEB_DIR}/opt/freeskoden-lighthouse/client"
mkdir -p "${DEB_DIR}/opt/freeskoden-lighthouse/server"
mkdir -p "${DEB_DIR}/usr/bin"
mkdir -p "${DEB_DIR}/usr/share/applications"
mkdir -p "${DEB_DIR}/usr/share/pixmaps"

# 1. Create Debian Control file
cat << 'EOF' > "${DEB_DIR}/DEBIAN/control"
Package: freeskoden-lighthouse
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6
Maintainer: Freeskoden Maintainers <maintainers@freeskoden.com>
Description: Freeskoden Lighthouse Remote Control Client & Server
 Freeskoden Lighthouse is a lightweight remote control utility coordinates connections over the internet.
EOF

# 2. Copy compiled standalone binaries and rename
echo "Copying compiled binaries..."
if [ -d "${CLIENT_DIST}" ]; then
    cp -r "${CLIENT_DIST}"/* "${DEB_DIR}/opt/freeskoden-lighthouse/client/"
    # Rename binary from 'app' to 'lighthouse'
    if [ -f "${DEB_DIR}/opt/freeskoden-lighthouse/client/app" ]; then
        mv "${DEB_DIR}/opt/freeskoden-lighthouse/client/app" "${DEB_DIR}/opt/freeskoden-lighthouse/client/lighthouse"
    fi
else
    echo "Warning: ${CLIENT_DIST} not found. Skipping client packaging."
fi

if [ -d "${SERVER_DIST}" ]; then
    cp -r "${SERVER_DIST}"/* "${DEB_DIR}/opt/freeskoden-lighthouse/server/"
    # Rename binary from 'server' to 'lighthouse-server'
    if [ -f "${DEB_DIR}/opt/freeskoden-lighthouse/server/server" ]; then
        mv "${DEB_DIR}/opt/freeskoden-lighthouse/server/server" "${DEB_DIR}/opt/freeskoden-lighthouse/server/lighthouse-server"
    fi
else
    echo "Warning: ${SERVER_DIST} not found. Skipping server packaging."
fi

# 3. Create Launcher Symlinks in /usr/bin
echo "Creating system symlinks..."
if [ -f "${DEB_DIR}/opt/freeskoden-lighthouse/client/lighthouse" ]; then
    ln -sf "/opt/freeskoden-lighthouse/client/lighthouse" "${DEB_DIR}/usr/bin/lighthouse"
fi
if [ -f "${DEB_DIR}/opt/freeskoden-lighthouse/server/lighthouse-server" ]; then
    ln -sf "/opt/freeskoden-lighthouse/server/lighthouse-server" "${DEB_DIR}/usr/bin/lighthouse-server"
fi

# 4. Copy Desktop Launchers and Icons
cp "${WORKSPACE}/packaging/linux/client.desktop" "${DEB_DIR}/usr/share/applications/Lighthouse.desktop"
cp "${WORKSPACE}/packaging/linux/server.desktop" "${DEB_DIR}/usr/share/applications/Lighthouse-Server.desktop"
cp "${WORKSPACE}/packaging/linux/icon.png" "${DEB_DIR}/usr/share/pixmaps/lighthouse.png"
cp "${WORKSPACE}/packaging/linux/icon.png" "${DEB_DIR}/usr/share/pixmaps/lighthouse-server.png"

# Set permissions (Debian packaging standard requirements)
find "${DEB_DIR}" -type d -exec chmod 755 {} \;
find "${DEB_DIR}" -type f -exec chmod 644 {} \;
if [ -d "${DEB_DIR}/usr/bin" ]; then
    chmod 755 "${DEB_DIR}/usr/bin"/* || true
fi
if [ -d "${DEB_DIR}/opt/freeskoden-lighthouse/client" ]; then
    chmod +x "${DEB_DIR}/opt/freeskoden-lighthouse/client/lighthouse" || true
fi
if [ -d "${DEB_DIR}/opt/freeskoden-lighthouse/server" ]; then
    chmod +x "${DEB_DIR}/opt/freeskoden-lighthouse/server/lighthouse-server" || true
fi

# 5. Build DEB Package
echo "Building DEB Package..."
dpkg-deb --build "${DEB_DIR}" "${WORKSPACE}/freeskoden-lighthouse_1.0.0_amd64.deb"

# 6. Build RPM Package via Alien
echo "Building RPM Package..."
if command -v alien &> /dev/null; then
    sudo alien --to-rpm --scripts "${WORKSPACE}/freeskoden-lighthouse_1.0.0_amd64.deb"
    mv *.rpm "${WORKSPACE}/freeskoden-lighthouse-1.0.0.rpm" || true
    echo "RPM Packaging Complete!"
else
    echo "Warning: 'alien' command not found. Skipping RPM packaging. Install 'alien' to build RPMs."
fi

echo "Packaging Complete!"
