#!/bin/bash

# AppImage build script for pypi-package-updater
# This creates a portable Linux application

set -e

APP="pypi-package-updater"
VERSION="0.2.0"

# Create AppDir structure
mkdir -p ${APP}.AppDir/usr/bin
mkdir -p ${APP}.AppDir/usr/share/applications
mkdir -p ${APP}.AppDir/usr/share/icons/hicolor/256x256/apps

# Install Python and dependencies into AppDir
python3 -m pip install --target=${APP}.AppDir/usr/lib/python3.11/site-packages pypi-package-updater

# Create wrapper script
cat > ${APP}.AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PYTHONPATH="${HERE}/usr/lib/python3.11/site-packages:${PYTHONPATH}"
export PATH="${HERE}/usr/bin:${PATH}"
exec python3 -m pypi_updater.cli "$@"
EOF
chmod +x ${APP}.AppDir/AppRun

# Create desktop file
cat > ${APP}.AppDir/usr/share/applications/${APP}.desktop << EOF
[Desktop Entry]
Type=Application
Name=PyPI Package Updater
Comment=Update Python package dependencies
Exec=pypi-update
Icon=${APP}
Categories=Development;
EOF

# Create icon (you'd need to provide an actual icon)
# cp icon.png ${APP}.AppDir/usr/share/icons/hicolor/256x256/apps/${APP}.png

# Download appimagetool and create AppImage
wget -c https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage
./appimagetool-x86_64.AppImage ${APP}.AppDir ${APP}-${VERSION}-x86_64.AppImage
