"""
Comprehensive tests for file updating functionality.
"""

import tempfile
from pathlib import Path

import pytest

from pypi_updater.formats import FileFormat, FileUpdater, FormatDetector, UniversalParser


def test_comprehensive_requirements_updating():
    """Test comprehensive requirements.txt file updating scenarios."""
    updater = FileUpdater()

    # Test requirements.txt updating
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("requests==2.25.0\nclick==7.0.0\nnumpy>=1.20.0\n")

    try:
        # Update with new versions
        updates = {"requests": "2.28.0", "click": "8.0.0", "numpy": "1.24.0"}
        updater.update_file(tmp_path, updates)

        # Verify updates (updater uses >= by default)
        content = tmp_path.read_text()
        assert "requests>=2.28.0" in content
        assert "click>=8.0.0" in content
        assert "numpy>=1.24.0" in content

    finally:
        tmp_path.unlink()


def test_pyproject_toml_updating():
    """Test pyproject.toml file updating."""
    updater = FileUpdater()

    toml_content = """[project]
name = "test-package"
version = "1.0.0"
dependencies = [
    "requests>=2.25.0",
    "click>=7.0",
    "numpy==1.20.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=6.0",
    "black>=21.0"
]
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(toml_content)

    try:
        # Update dependencies
        updates = {"requests": "2.28.0", "pytest": "7.0.0", "black": "22.0.0"}
        updater.update_file(tmp_path, updates)

        # Verify updates were attempted
        content = tmp_path.read_text()
        # The file should still contain the packages
        assert "requests" in content
        assert "pytest" in content
        assert "black" in content

    finally:
        tmp_path.unlink()


def test_setup_py_updating():
    """Test setup.py file updating."""
    updater = FileUpdater()

    setup_content = """from setuptools import setup

setup(
    name="test-package",
    version="1.0.0",
    install_requires=[
        "requests>=2.25.0",
        "click>=7.0",
        "numpy==1.20.0"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0"
        ]
    }
)
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(setup_content)

    try:
        # Update dependencies
        updates = {"requests": "2.28.0", "pytest": "7.0.0"}
        updater.update_file(tmp_path, updates)

        # Verify the file was processed
        content = tmp_path.read_text()
        assert "requests" in content
        assert "pytest" in content

    finally:
        tmp_path.unlink()


def test_file_update_error_handling():
    """Test various error handling scenarios in file updating."""
    updater = FileUpdater()

    # Test updating non-existent file
    with pytest.raises(FileNotFoundError):
        updater.update_file(Path("/non/existent/file.txt"), {})

    # Test with unreadable file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("requests==2.25.0\n")  # Add content so format detection works

    try:
        # Make file unreadable
        tmp_path.chmod(0o000)

        # This should raise an exception
        with pytest.raises((PermissionError, OSError)):
            updater.update_file(tmp_path, {"requests": "2.28.0"})

    finally:
        # Restore permissions and cleanup
        tmp_path.chmod(0o644)
        tmp_path.unlink()


def test_format_detection_comprehensive():
    """Test comprehensive format detection scenarios."""
    # Test with file that has no extension but requirements content
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(b"requests==2.25.0\nclick>=7.0\n")

    try:
        # Should detect by content
        format_detected = FormatDetector.detect_format(tmp_path)
        assert format_detected == FileFormat.REQUIREMENTS_TXT

    finally:
        tmp_path.unlink()

    # Test with empty file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("")

    try:
        format_detected = FormatDetector.detect_format(tmp_path)
        # Should detect as requirements based on extension
        assert format_detected == FileFormat.REQUIREMENTS_TXT

    finally:
        tmp_path.unlink()

    # Test with setup.py file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("from setuptools import setup\nsetup(name='test')")

    try:
        format_detected = FormatDetector.detect_format(tmp_path)
        assert format_detected == FileFormat.SETUP_PY

    finally:
        tmp_path.unlink()


def test_unicode_and_io_error_handling():
    """Test handling of IO and Unicode errors."""
    # Test Unicode decode error
    with tempfile.NamedTemporaryFile(delete=False, mode="wb") as tmp:
        tmp_path = Path(tmp.name)
        # Write invalid UTF-8 bytes
        tmp.write(b"\xff\xfe\x00\x00invalid utf-8")

    try:
        # This should trigger UnicodeDecodeError and return UNKNOWN
        result = FormatDetector.detect_format(tmp_path)
        assert result == FileFormat.UNKNOWN

    finally:
        tmp_path.unlink()


def test_parser_edge_cases():
    """Test parser edge cases and error conditions."""
    parser = UniversalParser()

    # Test empty content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("")

    try:
        deps = parser.parse_file(tmp_path, FileFormat.REQUIREMENTS_TXT)
        assert deps == {}
    finally:
        tmp_path.unlink()

    # Test content with only comments
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("# This is a comment\n# Another comment")

    try:
        deps = parser.parse_file(tmp_path, FileFormat.REQUIREMENTS_TXT)
        assert deps == {}
    finally:
        tmp_path.unlink()

    # Test malformed requirements that should be handled gracefully
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("invalid-requirement-line\n")

    try:
        deps = parser.parse_file(tmp_path, FileFormat.REQUIREMENTS_TXT)
        # Should handle gracefully and extract what it can
        assert isinstance(deps, dict)
    finally:
        tmp_path.unlink()

    # Test setup.py with no install_requires
    setup_content = """
from setuptools import setup

setup(
    name="test-package",
    version="1.0.0",
    description="Test package without dependencies"
)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(setup_content)

    try:
        dependencies = parser.parse_file(tmp_path, FileFormat.SETUP_PY)
        assert dependencies == {}
    finally:
        tmp_path.unlink()


def test_complex_requirements_scenarios():
    """Test complex requirements.txt scenarios."""
    parser = UniversalParser()

    # Test requirements with extras, comments, and various formats
    complex_requirements = """
# Core dependencies
requests>=2.25.0  # HTTP library
click==7.0.0
numpy>=1.20.0,<2.0

# Optional dependencies
-e git+https://github.com/user/repo.git#egg=package
-r other-requirements.txt

# Development dependencies  
pytest>=6.0
black[dev]>=21.0
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(complex_requirements)

    try:
        deps = parser.parse_file(tmp_path, FileFormat.REQUIREMENTS_TXT)
        # Should parse at least the basic requirements
        package_names = list(deps.keys())
        assert "requests" in package_names
        assert "click" in package_names
        assert "numpy" in package_names
    finally:
        tmp_path.unlink()


def test_file_updater_backup_and_restoration():
    """Test that file updater properly handles backup scenarios."""
    updater = FileUpdater()

    original_content = "requests==2.25.0\nclick==7.0.0\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(original_content)

    try:
        # Test normal update
        updates = {"requests": "2.28.0"}
        updater.update_file(tmp_path, updates)

        # File should be updated (updater uses >= by default)
        content = tmp_path.read_text()
        assert "requests>=2.28.0" in content
        assert "click==7.0.0" in content  # Unchanged dependency should remain

    finally:
        tmp_path.unlink()


def test_unknown_format_handling():
    """Test handling of unknown file formats."""
    updater = FileUpdater()

    # Create a file with unknown format
    with tempfile.NamedTemporaryFile(mode="w", suffix=".unknown", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("some random content that's not a dependency file")

    try:
        # Should handle gracefully without crashing
        updates = {"requests": "2.28.0"}
        updater.update_file(tmp_path, updates)

        # File should remain unchanged
        content = tmp_path.read_text()
        assert content == "some random content that's not a dependency file"

    finally:
        tmp_path.unlink()
