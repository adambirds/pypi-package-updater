"""
Tests specifically targeting the final 3 missing lines in formats.py:
- Line 148: Empty line handling in requirements parser
- Line 343: Empty line handling in AST extraction
- Line 407: Fixed regex bug in setup.py updater second pattern
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from pypi_updater.formats import FileFormat, FileUpdater, UniversalParser


def test_line_148_empty_line_handling():
    """Target line 148: empty line after comment stripping in requirements parser."""
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        # Create content that will result in empty line after comment processing
        f.write("package1>=1.0  # this is a comment\n")
        f.write("   # this entire line is just a comment\n")  # This should trigger line 148
        f.write("package2>=2.0\n")
        f.flush()

        packages = parser._parse_requirements_file(Path(f.name))

        # Should have parsed 2 packages, skipping the comment-only line
        assert len(packages) == 2
        assert "package1" in packages
        assert "package2" in packages


def test_line_343_empty_ast_node():
    """Target line 343: empty line handling in AST extraction."""
    parser = UniversalParser()

    # Create an AST node that will result in empty requirements
    mock_node = MagicMock()
    mock_node.elts = []  # Empty list that should trigger line 343

    # This should return empty dict when processing empty list
    result = parser._extract_requirements_from_ast(mock_node)
    assert result == {}


def test_line_407_setup_py_second_regex_pattern():
    """Target line 407: setup.py updater with second regex pattern (now fixed)."""
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Create setup.py content that matches the second pattern (no version specifier)
        setup_content = """
from setuptools import setup

setup(
    name="test-package",
    install_requires=[
        "requests",
        "urllib3",
    ],
)
"""
        f.write(setup_content)
        f.flush()

        # Update with the fixed regex bug - this should now work
        updates = {"requests": "2.28.0"}
        result = updater._update_setup_py(Path(f.name), updates)

        # Should successfully update the file
        assert result is True

        # Verify the content was updated correctly
        updated_content = Path(f.name).read_text()
        assert "requests>=2.28.0" in updated_content


def test_line_407_both_regex_patterns():
    """Comprehensive test for line 407 covering both regex patterns."""
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Setup.py with both patterns: one with version spec, one without
        setup_content = """
setup(
    install_requires=[
        "requests>=2.0.0",  # First pattern: has version specifier
        "urllib3",          # Second pattern: no version specifier  
    ],
)
"""
        f.write(setup_content)
        f.flush()

        # Test updating both types
        updates = {
            "requests": "2.28.0",  # Should match first pattern
            "urllib3": "1.26.0",  # Should match second pattern (line 407)
        }

        result = updater._update_setup_py(Path(f.name), updates)
        assert result is True

        updated_content = Path(f.name).read_text()
        assert "requests>=2.28.0" in updated_content
        assert "urllib3>=1.26.0" in updated_content


def test_empty_line_after_inline_comment_strip():
    """Another test for line 148: when inline comment results in empty line."""
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        # Line that becomes empty after stripping inline comment
        f.write("package1>=1.0\n")
        f.write("    # only comment here\n")  # This line should trigger the empty check
        f.write("package2>=2.0\n")
        f.flush()

        packages = parser._parse_requirements_file(Path(f.name))

        assert len(packages) == 2
        assert "package1" in packages
        assert "package2" in packages


def test_ast_extraction_with_empty_strings():
    """Test line 343 with AST nodes containing empty strings."""
    parser = UniversalParser()

    # Create mock AST list with empty string constant
    empty_constant = MagicMock()
    empty_constant.value = ""  # Empty string should not add to packages

    mock_node = MagicMock()
    mock_node.elts = [empty_constant]

    # Mock isinstance to return True for ast.List and ast.Constant
    with patch("pypi_updater.formats.isinstance") as mock_isinstance:

        def isinstance_side_effect(obj, cls):
            if obj is mock_node and cls is ast.List:
                return True
            elif obj is empty_constant and (cls is ast.Constant):
                return True
            elif hasattr(obj, "value") and isinstance(obj.value, str) and cls is str:
                return True
            return False

        mock_isinstance.side_effect = isinstance_side_effect

        result = parser._extract_requirements_from_ast(mock_node)
        # Should be empty since empty string doesn't create valid requirement
        assert result == {}
