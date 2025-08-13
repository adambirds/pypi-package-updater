# PyPI Updater

A Python package that automatically checks PyPI for new versions of your dependencies and updates your requirements files.

## Features

- 🔍 **Automatic Update Detection**: Checks PyPI for the latest versions of all packages in your requirements files
- 📝 **Smart Parsing**: Handles complex requirements files with includes (`-r` directives), comments, and various version operators
- 🔄 **Dependency-Aware Updates**: Understands your requirements file hierarchy and updates in the correct order
- 🎯 **Selective Updates**: Update specific files or packages, or update everything at once
- 🛡️ **Safe by Default**: Dry-run mode and interactive confirmation before making changes
- 🔨 **Integration**: Automatically runs your existing compilation script after updates
- 📊 **Detailed Reporting**: Comprehensive summary of what was updated, failed, or skipped

## Installation

```bash
pip install -e .
```

Or install with development dependencies:

```bash
pip install -e ".[dev]"
```

## Requirements

- Python 3.8+
- aiohttp
- packaging

## Usage

### Command Line Interface

#### Check for available updates (without making changes):

```bash
python update_packages.py --check-only
```

#### Update all packages interactively:

```bash
python update_packages.py
```

#### Update specific files:

```bash
python update_packages.py requirements/common.in requirements/dev.in
```

#### Dry run (see what would be updated):

```bash
python update_packages.py --dry-run
```

#### Non-interactive mode (update everything automatically):

```bash
python update_packages.py --non-interactive
```

#### Skip compilation after updates:

```bash
python update_packages.py --no-compile
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

### Directory Structure

The tool expects your project to follow this structure:

```
your-project/
├── requirements/
│   ├── common.in       # Base requirements
│   ├── dev.in          # Development requirements
│   ├── prod.in         # Production requirements
│   └── *.txt          # Compiled requirements (generated)
└── tools/
    └── update-locked-requirements  # Your compilation script
```

### Requirements File Format

The tool supports standard pip requirements format with:

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
python update_packages.py --dry-run
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

### Running Tests

The package includes a comprehensive test suite using pytest:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run only specific test files
pytest tests/test_basic.py
pytest tests/test_updater.py

# Run tests with coverage
pip install pytest-cov
pytest --cov=pypi_updater --cov-report=html
```

### Test Structure

- `tests/test_basic.py` - Basic smoke tests and import verification
- `tests/test_updater.py` - Comprehensive unit and integration tests

The test suite covers:
- Requirements file parsing
- PyPI API client functionality  
- Update detection and processing
- CLI argument handling
- End-to-end workflows
- Error handling scenarios

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd python-package-updater

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black pypi_updater/ tests/
isort pypi_updater/ tests/

# Type checking
mypy pypi_updater/
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black pypi_updater/
isort pypi_updater/
```

### Type Checking

```bash
mypy pypi_updater/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

### 0.1.0 (Initial Release)

- Basic package update functionality
- Support for requirements.in files with includes
- Interactive and non-interactive modes
- Dry-run capability
- Integration with existing compilation scripts
- Comprehensive error handling and logging
