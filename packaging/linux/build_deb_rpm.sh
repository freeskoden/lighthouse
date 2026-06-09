#!/bin/bash
set -e

echo "Starting DEB & RPM Packaging..."

WORKSPACE=$(pwd)
DEB_DIR="${WORKSPACE}/deb_build"
CLIENT_DIST="${WORKSPACE}/client.dist"
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
Description: Freeskoden Lighthouse Client & Server
 Freeskoden Lighthouse is a lightweight remote control utility coordinates connections over the internet.
EOF

# 2. Copy compiled standalone binaries
echo "Copying compiled binaries..."
if [ -d "${CLIENT_DIST}" ]; then
    cp -r "${CLIENT_DIST}"/* "${DEB_DIR}/opt/freeskoden-lighthouse/client/"
else
    echo "Warning: ${CLIENT_DIST} not found. Skipping client packaging."
fi

if [ -d "${SERVER_DIST}" ]; then
    cp -r "${SERVER_DIST}"/* "${DEB_DIR}/opt/freeskoden-lighthouse/server/"
else
    echo "Warning: ${SERVER_DIST} not found. Skipping server packaging."
fi

# 3. Create Launcher Symlinks in /usr/bin
echo "Creating system symlinks..."
if [ -f "${DEB_DIR}/opt/freeskoden-lighthouse/client/app" ]; then
    ln -sf "/opt/freeskoden-lighthouse/client/app" "${DEB_DIR}/usr/bin/freeskoden-lighthouse-client"
fi
if [ -f "${DEB_DIR}/opt/freeskoden-lighthouse/server/server" ]; then
    ln -sf "/opt/freeskoden-lighthouse/server/server" "${DEB_DIR}/usr/bin/freeskoden-lighthouse-server"
fi

# 4. Copy Desktop Launcher and Icon
cp "${WORKSPACE}/packaging/linux/client.desktop" "${DEB_DIR}/usr/share/applications/freeskoden-lighthouse.desktop"
cp "${WORKSPACE}/packaging/linux/icon.png" "${DEB_DIR}/usr/share/pixmaps/freeskoden-lighthouse.png"

# Set permissions (Debian packaging standard requirements)
find "${DEB_DIR}" -type d -exec chmod 755 {} \;
find "${DEB_DIR}" -type f -exec chmod 644 {} \;
if [ -d "${DEB_DIR}/usr/bin" ]; then
    chmod 755 "${DEB_DIR}/usr/bin"/* || true
fi
if [ -d "${DEB_DIR}/opt/freeskoden-lighthouse/client" ]; then
    chmod +x "${DEB_DIR}/opt/freeskoden-lighthouse/client/app" || true
fi
if [ -d "${DEB_DIR}/opt/freeskoden-lighthouse/server" ]; then
    chmod +x "${DEB_DIR}/opt/freeskoden-lighthouse/server/server" || true
fi

# 5. Build DEB Package
echo "Building DEB Package..."
dpkg-deb --build "${DEB_DIR}" "${WORKSPACE}/freeskoden-lighthouse_1.0.0_amd64.deb"

# 6. Build RPM Package via Alien
echo "Building RPM Package..."
if command -v alien &> /dev/null; then
    sudo alien --to-rpm --scripts "${WORKSPACE}/freeskoden-lighthouse_1.0.0_amd64.deb"
    # Move generated RPM to root workspace
    mv *.rpm "${WORKSPACE}/freeskoden-lighthouse-1.0.0-2.x86_64.rpm" || mv freeskoden-lighthouse*.rpm "${WORKSPACE}/freeskoden-lighthouse-1.0.0.rpm" || true
    echo "RPM Packaging Complete!"
else
    echo "Warning: 'alien' command not found. Skipping RPM packaging. Install 'alien' to build RPMs."
fi

echo "Packaging Complete!"
