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
