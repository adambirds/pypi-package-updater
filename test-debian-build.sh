#!/bin/bash
set -e

echo "=== Testing Debian Build Process ==="

# Install required packages
apt-get update
apt-get install -y devscripts build-essential dh-python debhelper-compat python3-all python3-aiohttp python3-setuptools-scm python3-wheel python3-build git

# Show current version from setuptools_scm
echo "=== Current version from setuptools_scm ==="
python3 -c "import setuptools_scm; print('Version:', setuptools_scm.get_version())"

# Generate Debian changelog
echo "=== Generating Debian changelog ==="
python3 scripts/changelog_to_debian.py

# Copy debian packaging files
echo "=== Setting up Debian packaging ==="
cp -r packaging/debian .
ls -la debian/

# Inject dynamic version into changelog
echo "=== Injecting dynamic version ==="
python3 scripts/inject_dynamic_version.py
echo "Updated changelog:"
head -3 debian/changelog

# Show what dpkg-buildpackage would see
echo "=== Package information ==="
python3 setup.py --name --version

# Try to run dpkg-buildpackage (this will build the actual .deb)
echo "=== Building Debian package ==="
dpkg-buildpackage -us -uc

# Show the resulting files
echo "=== Build results ==="
ls -la ../*.deb ../*.tar.gz ../*.dsc 2>/dev/null || echo "No .deb files found in parent directory"

# Show results
echo "=== Build results ==="
ls -la ../*.deb || echo "No .deb files found"
find . -name "*.deb" -ls
