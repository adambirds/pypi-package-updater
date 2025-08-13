# Changelog

## [0.2.15] - 2025-08-14

### 🔧 Build System
- Fixed duplicate setuptools_scm configuration causing "version already set" warnings during package builds.
- Removed `use_scm_version=True` from setup.py since setuptools_scm is already configured in pyproject.toml.
- Added `setup_requires=['setuptools_scm']` to setup.py for proper version detection.
- Maintained existing requirements file structure while resolving version conflicts.

## [0.2.14] - 2025-08-13

### 🔧 CI/CD
- Fixed version generation for release builds by making publish job independent from build artifacts.
- Removed build job dependency from release publishing to ensure fresh package builds from tags.
- Added condition to exclude release events from the build job, preventing version conflicts.
- Release job now builds packages directly from the tag checkout instead of using development artifacts.
- Enhanced debug logging to track git state and setuptools_scm version detection during releases.

## [0.2.13] - 2025-08-13

### 🔧 CI/CD
- Fixed version generation for tag-based releases to prevent changelog conversion commits during tag builds.
- Added conditional logic to skip changelog conversion when building from tags, ensuring proper version calculation.
- Improved Debian build reliability by using dynamic tarball detection instead of wildcard patterns for sdist extraction.

## [0.2.11] - 2025-08-13

### 🚀 Features
- Added `.github/FUNDING.yml` for GitHub Sponsors support.

### 🛠️ CI/CD
- CI now tests Debian and Snap builds after publishing to Test PyPI, catching packaging issues before release.
- Added `scripts/changelog_to_debian.py` to convert `CHANGELOG.md` to Debian changelog format.
- CI step now runs the changelog conversion script and commits the updated Debian changelog before building the Debian package.
- Fixed permissions for automated commits by adding `contents: write` to CI jobs.
- Added proper checkout steps to CI jobs that need repository access.
- Improved snap build by installing snapcraft in CI environment.
- Fixed debian changelog formatting to use proper RFC 2822 date format.
- Fixed Debian build directory pattern to use underscores (`pypi_package_updater-*`) matching actual sdist extraction.
- Added proper snapd setup in CI with core24 base installation for reliable snap builds.
- Fixed step labels to correctly distinguish between test and production builds.

### 🏗️ Build System
- Refactored version management to use setuptools_scm `write_to` feature for consistent versioning across all packaging formats.
- Updated debian packaging to build from sdist with embedded version information.
- Simplified snapcraft versioning to use `craftctl` and package version dynamically.
- Added dummy `_version.py` for development fallback when setuptools_scm hasn't run.
- Moved `snapcraft.yaml` to project root for better source access and conventional structure.
- Upgraded snap base from core22 to core24 for better Python 3.12+ support and modern Ubuntu 24.04 LTS foundation.
- Updated snapcraft to use `adopt-info` with setuptools_scm for consistent version formatting across all package types.

### 📦 Dependencies
- Pinned all dependency versions for reproducible builds and better stability.
- Added setuptools_scm to development dependencies for local version management.

### 🔧 Configuration
- Added VSCode configuration to ignore debian packaging file errors.

## [0.2.10] - 2025-08-13

### Build - 2025-08-13
- Fix missing comma in dependency setup.

## [0.2.9] - 2025-08-13

### Build
- Remove AppImage as no longer required.

## [0.2.8] - 2025-08-13

### �️ CI/CD
- Added FUSE installation step to CI workflow to fix AppImage build errors caused by missing `libfuse.so.2`.

## [0.2.7] - 2025-08-13

### 🛠️ Packaging
- Fixed AppImage build script to install `setuptools_scm` before using it for version detection, preventing missing module errors in CI.

## [0.2.6] - 2025-08-13

### 🛠️ Packaging
- Disabled `dh_usrlocal` in `debian/rules` to prevent build errors when installing console scripts. This ensures correct installation paths for Python scripts and resolves CI build failures.

## [0.2.5] - 2025-08-13

### 🏗️ Packaging
- Removed `debian/compat` file to follow Debian packaging best practices and avoid debhelper compat level conflicts.

# Changelog

## [0.2.4] - 2025-08-13

### 🛠️ Maintenance
- Setuptools_scm now uses `local_scheme = "no-local-version"` to remove `+` from dev version strings, improving PyPI/TestPyPI compatibility for non-tagged builds.

# Changelog

## [0.2.3] - 2025-08-13

### 🚀 Features
- CI/CD workflow now builds Snap packages with dynamic versioning from setuptools_scm.
- All package formats (PyPI, Debian, AppImage, Snap) now use the same automated version.

### 🛠️ Maintenance
- Improved workflow automation and consistency for releases.

# Changelog

## [0.2.2] - 2025-08-13

### 🛠️ Fixes
- CI/CD workflow now always fetches tags for all jobs, ensuring setuptools_scm correctly detects the version from Git tags in all build and publish steps.

# Changelog

## [0.2.1] - 2025-08-13

### 🛠️ Improvements
- CI/CD workflow now triggers on both tag creation and GitHub release events.
- Debian build step now installs all required dependencies (`debhelper-compat`, `python3-all`, `python3-aiohttp`).
- Versioning is now automated using `setuptools_scm`.

### 🧹 Maintenance
- Moved changelog from README.md to this file for easier tracking.
- Linked changelog from README.md.

## [0.2.0] - Latest

### 🚀 New Features
- Universal Format Support: Added support for `setup.py` and `pyproject.toml` files
- Enhanced CLI: Improved command-line interface with better error handling
- Format Detection: Automatic detection and parsing of multiple dependency formats

### 🏗️ Infrastructure 
- CI/CD Pipeline: Complete GitHub Actions workflow with multi-Python testing
- Code Quality: Comprehensive linting with Black, isort, and mypy
- Coverage: 99% test coverage with 263 comprehensive tests
- Documentation: Enhanced README with complete setup instructions

### 🧪 Testing
- Branch Coverage: Added comprehensive branch coverage tests
- Error Handling: Extensive error condition testing
- Format Testing: Tests for all supported file formats

### ⚙️ Configuration
- pyproject.toml: Complete tool configuration for development
- codecov.yaml: Strict coverage requirements and reporting
- Automated Linting: scripts/lint.py for easy code quality checks

## [0.1.0] - Initial Release
- Basic package update functionality
- Support for requirements.in files with includes
- Interactive and non-interactive modes
- Dry-run capability
- Integration with existing compilation scripts
- Comprehensive error handling and logging
