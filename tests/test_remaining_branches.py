"""
Additional branch coverage tests for the remaining 10 missed branches.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from pypi_updater.formats import FileFormat, FileUpdater, FormatDetector, UniversalParser
from pypi_updater.updater import PyPIUpdater


def test_format_detector_fallback_to_unknown():
    """Test formats.py line 204->195: exception handling in format detection."""
    detector = FormatDetector()

    # Test with a file that causes an IOError during read
    with tempfile.NamedTemporaryFile(delete=False) as f:
        file_path = Path(f.name)

    # Remove the file to cause IOError
    file_path.unlink()

    # This should trigger the exception branch and return UNKNOWN
    result = detector.detect_format(file_path)
    assert result.value == "unknown"


def test_setup_py_fallback_parsing():
    """Test formats.py lines 232->225, 257->256, 263->256, 266->253: setup.py fallback patterns."""
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Setup.py content with direct install_requires list that regex can parse
        setup_content = """
from setuptools import setup

setup(
    name="complex-package",
    version="1.0.0",
    install_requires=[
        "requests>=2.25.0",
        "click>=7.0"
    ],
)
"""
        f.write(setup_content)
        f.flush()

        # Test fallback parsing (regex-based)
        packages = parser._parse_setup_py_fallback(Path(f.name))

        # Should find packages using regex patterns
        assert len(packages) >= 2  # Should find requests and click


def test_pyproject_toml_edge_cases():
    """Test pyproject.toml parsing edge cases."""
    parser = UniversalParser()

    # Test with malformed TOML that triggers exception handling
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # Malformed TOML that will cause parsing issues
        f.write("[invalid toml content")
        f.flush()

        # Should raise ValueError due to TOML parsing error
        with pytest.raises(ValueError, match="Failed to parse pyproject.toml"):
            parser._parse_pyproject_toml(Path(f.name))


def test_updater_file_filtering_branches():
    """Test updater.py branches 92->95, 96->100, 103->106: file filtering logic."""
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_dir = Path(temp_dir)

        # Create various file types to test filtering
        (requirements_dir / "requirements.in").write_text("requests>=2.0\n")
        (requirements_dir / "requirements.txt").write_text("click>=8.0\n")
        (requirements_dir / "dev.in").write_text("pytest>=6.0\n")

        # Test default behavior (should include both .in and .txt files)
        updater = PyPIUpdater(requirements_dir=requirements_dir)
        files_default = updater.find_requirements_files()

        # Should find both .in and .txt files by default
        assert any(str(f).endswith(".in") for f in files_default)
        assert any(str(f).endswith(".txt") for f in files_default)

        # Test with format override to requirements.txt specifically
        updater.format_override = FileFormat.REQUIREMENTS_TXT
        files_txt = updater.find_requirements_files()

        # Should still include .in files (primary format) plus .txt files
        file_extensions = [Path(str(f)).suffix for f in files_txt]
        assert ".in" in file_extensions or ".txt" in file_extensions


def test_updater_file_vs_directory_processing():
    """Test updater.py line 371->385: single file vs directory processing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_dir = Path(temp_dir)
        single_file = requirements_dir / "requirements.txt"
        single_file.write_text("requests>=2.0\nclick>=8.0\n")

        updater = PyPIUpdater(requirements_dir=requirements_dir)

        # Test the branch by providing specific files vs no files
        async def test_file_processing():
            # Mock to avoid actual PyPI calls
            with patch.object(updater.pypi_client, "check_package_updates", return_value=[]):
                # Test with specific files provided (branch 371->385)
                results = await updater.check_for_updates(files=[str(single_file)])
                assert isinstance(results, dict)

                # Test without files (should scan directory)
                results = await updater.check_for_updates()
                assert isinstance(results, dict)

        import asyncio

        asyncio.run(test_file_processing())


def test_file_content_edge_cases():
    """Test edge cases in file content reading."""
    # Test that empty file still gets detected as requirements.txt (default behavior)
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("")  # Empty file
        f.flush()

        detector = FormatDetector()
        result = detector.detect_format(Path(f.name))
        # Empty files default to requirements.txt format
        assert result.value == "requirements.txt"


def test_regex_pattern_misses():
    """Test cases where regex patterns don't match anything."""
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Setup.py with no recognizable dependency patterns
        setup_content = """
from setuptools import setup

setup(
    name="no-deps-package",
    version="1.0.0",
    description="A package with no dependencies"
)
"""
        f.write(setup_content)
        f.flush()

        # Use fallback parsing (force AST to fail)
        with patch("ast.parse", side_effect=SyntaxError("Force fallback")):
            packages = parser._parse_setup_py_fallback(Path(f.name))
            # Should return empty dict when no patterns match
            assert packages == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
