# PyPI Package Updater

[![CI/CD](https://github.com/adambirds/pypi-package-updater/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adambirds/pypi-package-updater/actions/workflows/ci-cd.yml)
[![codecov](https://codecov.io/gh/adambirds/pypi-package-updater/graph/badge.svg?token=GGMWD1CIUC)](https://codecov.io/gh/adambirds/pypi-package-updater)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Mypy coverage](https://img.shields.io/badge/mypy-100%25-green.svg)](https://mypy-lang.org/)

A Python package that automatically checks PyPI for new versions of your dependencies and updates your requirements files with comprehensive format support.

## Features

- 🔍 **Automatic Update Detection**: Checks PyPI for the latest versions of all packages in your requirements files
- 📝 **Universal Format Support**: Handles `requirements.txt`, `requirements.in`, `setup.py`, and `pyproject.toml` files
- 🔄 **Dependency-Aware Updates**: Understands your requirements file hierarchy and updates in the correct order
- 🎯 **Selective Updates**: Update specific files or packages, or update everything at once
- 🛡️ **Safe by Default**: Dry-run mode and interactive confirmation before making changes
- 🔨 **Integration**: Automatically runs your existing compilation script after updates
- 📊 **Detailed Reporting**: Comprehensive summary of what was updated, failed, or skipped
- ✅ **High Code Quality**: 99% test coverage with comprehensive branch coverage
- 🚀 **CI/CD Ready**: Full GitHub Actions workflow with automated testing and deployment

## Installation

### Via pip (Python Package Index)

```bash
pip install pypi-package-updater
```

Or install with development dependencies:

```bash
pip install pypi-package-updater[dev]
```

### Via Homebrew (macOS/Linux)

```bash
# Add the tap and install (one-time setup)
brew tap adambirds/homebrew-pypi-package-updater
brew install pypi-package-updater

# Or install directly without tapping
brew install adambirds/homebrew-pypi-package-updater/pypi-package-updater
```

### Via APT (Debian/Ubuntu)

```bash
# Add the repository (one-time setup)
curl -fsSL https://github.com/adambirds/pypi-package-updater/releases/download/latest/pubkey.gpg | sudo apt-key add -
echo "deb https://github.com/adambirds/pypi-package-updater/releases/download/latest/deb ./" | sudo tee /etc/apt/sources.list.d/pypi-package-updater.list

# Install the package
sudo apt update
sudo apt install pypi-package-updater
```

### Via Snap (Cross-platform Linux)

```bash
sudo snap install pypi-package-updater
```


### From Source

```bash
git clone https://github.com/adambirds/pypi-package-updater.git
cd pypi-package-updater
pip install -e .
```

## Requirements

- Python 3.11+
- aiohttp
- packaging
- tomli (for pyproject.toml support)

## Usage

### Command Line Interface

#### Check for available updates (without making changes):

```bash
pypi-update --check-only
```

#### Update all packages interactively:

```bash
pypi-update
```

#### Update specific files:

```bash
pypi-update requirements/common.in requirements/dev.in
```

#### Dry run (see what would be updated):

```bash
pypi-update --dry-run
```

#### Non-interactive mode (update everything automatically):

```bash
pypi-update --non-interactive
```

#### Skip compilation after updates:

```bash
pypi-update --no-compile
```

### Python API

```python
import asyncio
from pypi_updater import PyPIUpdater

async def main():
    updater = PyPIUpdater(requirements_dir="requirements", tools_dir="tools")
    
    # Check for updates
    updates = await updater.check_for_updates()
    
    # Update packages
    summary = await updater.update_packages(
        dry_run=False,
        auto_compile=True,
        interactive=True
    )
    
    # Print summary
    updater.print_update_summary(summary)

asyncio.run(main())
```

## Configuration

### Supported File Formats

The tool automatically detects and supports multiple dependency file formats:

- **requirements.txt** - Standard pip requirements files
- **requirements.in** - pip-tools input files with `-c`, `-e`, compilation comments
- **setup.py** - setuptools configuration with `install_requires`
- **pyproject.toml** - Modern Python packaging format (PEP 518)

### Directory Structure

The tool expects your project to follow this structure:

```
your-project/
├── requirements/
│   ├── common.in       # Base requirements
│   ├── dev.in          # Development requirements
│   ├── prod.in         # Production requirements
│   └── *.txt          # Compiled requirements (generated)
├── setup.py           # Optional: setuptools configuration
├── pyproject.toml     # Optional: modern Python packaging
└── tools/
    └── update-locked-requirements  # Your compilation script
```

### Requirements File Format

The tool supports multiple dependency file formats with automatic detection:

#### requirements.txt / requirements.in
Standard pip requirements format with:

- **Version pinning**: `Django==4.2.0`
- **Version ranges**: `requests>=2.25.0`
- **Includes**: `-r common.in`
- **Comments**: `# This is a comment`
- **Extras**: `django[postgres]==4.2.0`

Example `requirements/common.in`:

```
# Core Dependencies
Django==4.2.0
requests>=2.25.0
celery==5.2.0

# Database
psycopg2==2.9.5
```

#### setup.py
Supports setuptools configuration:

```python
from setuptools import setup

setup(
    name="my-package",
    install_requires=[
        "Django>=4.2.0",
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": ["pytest>=6.0"],
    }
)
```

#### pyproject.toml
Modern Python packaging format (PEP 518):

```toml
[project]
dependencies = [
    "Django>=4.2.0",
    "requests>=2.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=6.0",
    "black>=22.0",
]

# Poetry format also supported
[tool.poetry.dependencies]
python = "^3.11"
Django = "^4.2.0"
```

## How It Works

1. **Parse Requirements**: Scans your `.in` files to extract package names and current versions
2. **Check PyPI**: Queries the PyPI API to get the latest version for each package
3. **Calculate Updates**: Compares current versions with latest versions
4. **Update Files**: Modifies your `.in` files with new versions (respects dependency order)
5. **Compile Requirements**: Runs your existing compilation script to generate `.txt` files

## Advanced Features

### Dependency Resolution

The tool understands your requirements hierarchy through `-r` includes and updates files in the correct order:

```
dev.in +-> prod.in +-> common.in
   |
   v
mypy.in
```

Files with no dependencies (like `common.in`) are updated first, followed by files that depend on them.

### Interactive Mode

In interactive mode, you'll be prompted for each update:

```
Package: Django
  Current: 4.1.0
  Latest:  4.2.0
  File:    requirements/common.in
Update Django from 4.1.0 to 4.2.0? [y/N/q]:
```

- `y`: Update this package
- `N`: Skip this package (default)
- `q`: Quit the update process

### Dry Run Mode

Use `--dry-run` to see what would be updated without making any changes:

```bash
pypi-update --dry-run
```

This is useful for:
- Checking what updates are available
- Testing the tool's behavior
- Generating reports for review

## Error Handling

The tool handles various error conditions gracefully:

- **Network issues**: Retries and timeouts for PyPI API calls
- **Invalid packages**: Warns about packages not found on PyPI
- **File permissions**: Clear error messages for file access issues
- **Version parsing**: Handles non-standard version formats

## Development

### Development Setup

```bash
# Clone the repository
git clone https://github.com/adambirds/pypi-package-updater.git
cd pypi-package-updater

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Code Quality & Testing

This project maintains high code quality standards with comprehensive tooling:

#### Running Tests

```bash
# Run all tests (263 tests with 99% coverage)
pytest

# Run tests with coverage report
pytest --cov=pypi_updater --cov-report=html

# Run specific test categories
pytest tests/test_basic.py                    # Basic functionality
pytest tests/test_branch_coverage.py         # Branch coverage tests
pytest tests/test_formats.py                 # File format handling
pytest tests/test_updater.py                 # Main updater logic
```

#### Code Linting & Formatting

We use automated linting with Black, isort, and mypy:

```bash
# Run all linters (check mode)
python scripts/lint.py

# Run all linters with automatic fixes
python scripts/lint.py --fix

# Individual tools
black pypi_updater/ tests/                   # Code formatting
isort pypi_updater/ tests/                   # Import sorting  
mypy pypi_updater/                           # Type checking
```

#### Test Coverage

- **Current Coverage**: 99% (654 statements, 262 branches)
- **Statement Coverage**: 100% (all lines covered)
- **Branch Coverage**: 99% (252/262 branches covered)
- **Total Tests**: 263 comprehensive tests

### CI/CD Pipeline

The project includes a complete GitHub Actions workflow (`.github/workflows/ci-cd.yml`):

#### Continuous Integration

- **Multi-Python Testing**: Python 3.11, 3.12, 3.13
- **Code Quality Checks**: Black, isort, mypy validation
- **Test Execution**: Full test suite with coverage reporting
- **Coverage Upload**: Automatic codecov.io integration

#### Continuous Deployment

- **PyPI Publishing**: Automatic release on version tags
- **Release Automation**: GitHub releases with changelogs

### GitHub Secrets Setup

To enable full CI/CD functionality, configure these repository secrets:

#### Required Secrets

1. **`CODECOV_TOKEN`** - For coverage reporting
   ```bash
   # Get from https://codecov.io/gh/adambirds/pypi-package-updater
   # Add to GitHub repo settings → Secrets and variables → Actions
   ```

2. **`PAT_TOKEN`** - Personal Access Token for updating homebrew tap
   ```bash
   # Create at GitHub Settings → Developer settings → Personal access tokens
   # Scope: repo (full repository access)
   # Add as repository secret named: PAT_TOKEN
   # Used to update the separate homebrew tap repository
   ```

#### PyPI Publishing

This project uses **PyPI Trusted Publishing** for secure, token-free publishing to PyPI. No `PYPI_API_TOKEN` is required - the publishing is authenticated automatically through GitHub's OIDC provider.

#### Automatically Provided

- **`GITHUB_TOKEN`** - Automatically provided by GitHub Actions

### Release Process

1. **Update Version**: Bump version in `pyproject.toml`
2. **Create Tag**: `git tag v1.0.0 && git push origin v1.0.0`
3. **Automatic Deployment**: GitHub Actions builds and publishes to PyPI
4. **GitHub Release**: Automatic release creation with changelog

### Configuration Files

#### `pyproject.toml`
- Tool configuration for Black, isort, mypy
- Package metadata and dependencies
- Build system configuration

#### `codecov.yaml`
- Coverage requirements (95% project, 90% patch)
- Coverage status checks configuration

#### `scripts/lint.py`
- Automated linting script with `--fix` mode
- Colored output and comprehensive reporting

### Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with tests
4. **Run quality checks**: `python scripts/lint.py --fix && pytest`
5. **Ensure tests pass**: All 263 tests should pass with maintained coverage
6. **Submit a pull request**

#### Pull Request Requirements

- ✅ All tests pass (99%+ coverage maintained)
- ✅ Code follows Black formatting
- ✅ Imports sorted with isort
- ✅ Type hints pass mypy validation
- ✅ New features include tests
- ✅ Documentation updated if needed

## License

MIT License - see LICENSE file for details.


## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for release history and details.
