"""
Branch coverage tests to achieve 100% branch coverage.

These tests target specific branch conditions that aren't fully covered.
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pypi_updater.formats import FileUpdater, FormatDetector, UniversalParser
from pypi_updater.parser import RequirementsParser
from pypi_updater.updater import PyPIUpdater


def test_format_detector_io_error_branch():
    """Test FormatDetector when file read fails (branch 204->195 in formats.py)."""
    detector = FormatDetector()

    # Create a file that will cause read errors
    with tempfile.NamedTemporaryFile(delete=False) as f:
        file_path = Path(f.name)

    # Make file unreadable by removing it after creation
    file_path.unlink()

    # This should trigger the IOError branch and return UNKNOWN
    result = detector.detect_format(file_path)
    assert result.value == "unknown"


def test_format_detector_unicode_error_branch():
    """Test FormatDetector with Unicode decode error (branch 204->195 in formats.py)."""
    detector = FormatDetector()

    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        # Write invalid UTF-8 bytes
        f.write(b"\xff\xfe\xfd\xfc")
        f.flush()
        file_path = Path(f.name)

    # This should trigger UnicodeDecodeError and return UNKNOWN
    result = detector.detect_format(file_path)
    assert result.value == "unknown"


def test_universal_parser_fallback_patterns_branch():
    """Test fallback regex patterns in setup.py parser (branches 232->225, etc.)."""
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Setup.py content that will trigger fallback parsing
        setup_content = """
from setuptools import setup

# Complex setup that might fail AST parsing
setup(
    name="test",
    install_requires=[
        "requests>=2.0",
        "click>=8.0",
    ]
)
"""
        f.write(setup_content)
        f.flush()

        # Force AST to fail by mocking it to raise an exception
        with patch("ast.parse", side_effect=SyntaxError("Forced AST failure")):
            packages = parser._parse_setup_py(Path(f.name))

            # Should have parsed packages using fallback despite AST failure
            assert len(packages) >= 1


def test_universal_parser_no_match_patterns():
    """Test when no regex patterns match in fallback parser."""
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Setup.py with no install_requires
        setup_content = """
from setuptools import setup

setup(
    name="test-package",
    version="1.0.0",
)
"""
        f.write(setup_content)
        f.flush()

        packages = parser._parse_setup_py_fallback(Path(f.name))

        # Should return empty dict when no patterns match
        assert packages == {}


def test_pyproject_toml_missing_sections():
    """Test pyproject.toml parsing with missing dependency sections."""
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # TOML with no dependency sections
        toml_content = """
[build-system]
requires = ["setuptools"]

[project]
name = "test"
version = "1.0.0"
"""
        f.write(toml_content)
        f.flush()

        packages = parser._parse_pyproject_toml(Path(f.name))

        # Should handle missing sections gracefully
        assert isinstance(packages, dict)


def test_parser_circular_dependency_detection():
    """Test circular dependency detection in parser (branch 188->187)."""
    parser = RequirementsParser("/tmp")

    # Mock the dependency graph to have circular dependencies
    mock_graph = {
        "file1.in": {"file2.in"},
        "file2.in": {"file3.in"},
        "file3.in": {"file1.in"},  # Circular!
    }

    with patch.object(parser, "get_dependency_graph", return_value=mock_graph):
        # This should trigger the circular dependency detection branch
        order = parser.get_update_order()

        # Should still return some order despite circular deps
        assert isinstance(order, list)


def test_updater_glob_pattern_branches():
    """Test different glob pattern branches in updater (branches 85->89, 92->95, etc.)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_dir = Path(temp_dir)

        # Create various file types
        (requirements_dir / "common.in").touch()
        (requirements_dir / "dev.txt").touch()
        (requirements_dir / "prod.in").touch()

        updater = PyPIUpdater(requirements_dir=requirements_dir)

        # Test different branches based on format override
        files_default = updater.find_requirements_files()
        assert len(files_default) >= 2  # Should find .in files

        # Test with format override
        updater.format_override = "requirements.txt"
        files_txt = updater.find_requirements_files()
        assert len(files_txt) >= 1  # Should find .txt files


def test_updater_single_file_vs_directory():
    """Test updater with single file vs directory (branch 371->385)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        requirements_dir = Path(temp_dir)
        single_file = requirements_dir / "requirements.txt"
        single_file.write_text("requests>=2.0\n")

        # Test with single file
        updater = PyPIUpdater(requirements_dir=requirements_dir)

        # Mock check_package_updates to avoid actual PyPI calls
        async def mock_check():
            with patch.object(updater.pypi_client, "check_package_updates", return_value=[]):
                # Test single file path
                results = await updater.check_for_updates(files=[str(single_file)])
                assert isinstance(results, dict)

                # Test directory scanning
                results = await updater.check_for_updates()
                assert isinstance(results, dict)

        import asyncio

        asyncio.run(mock_check())


def test_file_updater_pattern_matching_branches():
    """Test different pattern matching branches in file updater."""
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        # pyproject.toml with different dependency formats
        toml_content = """
[project]
dependencies = [
    "requests>=2.0",
    "click",
]

[tool.poetry.dependencies]
python = "^3.8"
requests = "2.28.0"
"""
        f.write(toml_content)
        f.flush()

        # Test updates that trigger different regex patterns
        updates = {"requests": "2.30.0", "click": "8.1.0"}
        result = updater._update_pyproject_toml(Path(f.name), updates)

        # Should successfully update
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
