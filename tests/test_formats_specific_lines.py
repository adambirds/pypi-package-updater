"""
Tests to target specific missing lines in formats.py for better coverage.

Missing lines to cover:
130, 148, 200-204, 222-233, 260-263, 275, 323, 333, 343, 350, 363-374, 407
"""

import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from pypi_updater.formats import FileFormat, FileUpdater, FormatDetector, UniversalParser


class TestFormatsSpecificLines:
    """Test specific lines that are currently uncovered in formats.py."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_line_130_unicode_decode_error(self):
        """Test line 130: UnicodeDecodeError fallback to latin-1."""
        parser = UniversalParser()

        # Create a file with non-UTF-8 content
        test_file = self.temp_dir / "requirements.txt"
        # Write bytes that would cause UnicodeDecodeError when read as UTF-8
        test_file.write_bytes(b"requests>=2.25.0\n\xff\xfe")

        # Mock read_text to raise UnicodeDecodeError on first call (UTF-8) but succeed on second (latin-1)
        original_read_text = Path.read_text
        call_count = 0

        def mock_read_text(self, encoding="utf-8"):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and encoding == "utf-8":
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
            return "requests>=2.25.0\n"

        with patch.object(Path, "read_text", mock_read_text):
            packages = parser.parse_file(test_file)
            assert "requests" in packages

    def test_line_148_regex_fallback_parsing(self):
        """Test line 148: regex fallback when Requirement() parsing fails."""
        parser = UniversalParser()

        # Create requirements file with malformed requirement that will trigger fallback
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("malformed-package>=1.0.0-invalid-spec\n")

        # Mock Requirement to always raise exception to force regex fallback
        with patch("pypi_updater.formats.Requirement", side_effect=Exception("Parse error")):
            packages = parser.parse_file(test_file)
            assert "malformed-package" in packages
            assert packages["malformed-package"] == ">=1.0.0-invalid-spec"

    def test_lines_200_204_ast_constant_parsing(self):
        """Test lines 200-204: AST constant parsing for setup.py requirements."""
        parser = UniversalParser()

        # Create setup.py with install_requires as a list
        setup_py = self.temp_dir / "setup.py"
        setup_py.write_text(
            """
from setuptools import setup

setup(
    name="test-package",
    install_requires=[
        "requests>=2.25.0",
        "flask==1.1.0",
    ]
)
"""
        )
        packages = parser.parse_file(setup_py)
        assert "requests" in packages
        assert "flask" in packages

    def test_lines_222_233_setup_py_fallback_patterns(self):
        """Test lines 222-233: setup.py fallback regex patterns."""
        parser = UniversalParser()

        # Create setup.py that will trigger AST parsing failure and use regex fallback
        setup_py = self.temp_dir / "setup.py"
        setup_py.write_text(
            """
# This will trigger the regex fallback
install_requires = [
    "requests>=2.25.0",
    'flask==1.1.0',
]
"""
        )

        # Mock AST parsing to fail and force regex fallback
        with patch("pypi_updater.formats.ast.parse", side_effect=Exception("AST parse failed")):
            packages = parser.parse_file(setup_py)
            assert "requests" in packages
            assert "flask" in packages

    def test_lines_260_263_pyproject_dict_format(self):
        """Test lines 260-263: Poetry-style dict format in pyproject.toml."""
        parser = UniversalParser()

        # Create pyproject.toml with Poetry-style dependencies
        pyproject_toml = self.temp_dir / "pyproject.toml"
        pyproject_toml.write_text(
            """
[tool.poetry.dependencies]
python = "^3.8"
requests = {version = "^2.25.0", optional = true}
flask = "1.1.0"
"""
        )

        packages = parser.parse_file(pyproject_toml)
        assert "requests" in packages
        assert packages["requests"] == "^2.25.0"
        assert "flask" in packages
        # Should skip 'python' requirement
        assert "python" not in packages

    def test_line_275_pyproject_toml_parse_exception(self):
        """Test line 275: exception handling in pyproject.toml parsing."""
        parser = UniversalParser()

        # Create invalid TOML file
        pyproject_toml = self.temp_dir / "pyproject.toml"
        pyproject_toml.write_text(
            """
[invalid toml syntax
dependencies = [
"""
        )

        with pytest.raises(ValueError, match="Failed to parse pyproject.toml"):
            parser.parse_file(pyproject_toml)

    def test_line_323_unicode_decode_error_in_update(self):
        """Test line 323: UnicodeDecodeError fallback in file updates."""
        updater = FileUpdater()

        # Create requirements file
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("requests>=2.25.0\n")

        # Mock Path.read_text to raise UnicodeDecodeError on first call
        call_count = 0

        def mock_read_text(self, encoding="utf-8"):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and encoding == "utf-8":
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
            return "requests>=2.25.0\n"

        with patch.object(Path, "read_text", mock_read_text):
            result = updater.update_file(test_file, {"requests": "2.26.0"})
            assert result is True

    def test_line_333_comment_preservation_in_update(self):
        """Test line 333: comment preservation during updates."""
        updater = FileUpdater()

        # Create requirements file with inline comment
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("requests>=2.25.0  # HTTP library\n")

        result = updater.update_file(test_file, {"requests": "2.26.0"})
        assert result is True

        content = test_file.read_text()
        assert "# HTTP library" in content

    def test_line_343_requirement_parsing_exception_fallback(self):
        """Test line 343: fallback when Requirement parsing fails during update."""
        updater = FileUpdater()

        # Create requirements file
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("malformed-package>=1.0.0\n")

        # Mock Requirement to fail and trigger regex fallback
        with patch("pypi_updater.formats.Requirement", side_effect=Exception("Parse error")):
            result = updater.update_file(test_file, {"malformed-package": "2.0.0"})
            assert result is True

            content = test_file.read_text()
            assert "malformed-package>=2.0.0" in content

    def test_line_350_version_without_operator_prefix(self):
        """Test line 350: handling versions without operator prefix."""
        updater = FileUpdater()

        # Create requirements file
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("requests>=2.25.0\n")

        # Mock Requirement parsing to fail and use fallback
        with patch("pypi_updater.formats.Requirement", side_effect=Exception("Parse error")):
            result = updater.update_file(test_file, {"requests": "2.26.0"})  # No operator prefix
            assert result is True

            content = test_file.read_text()
            assert "requests>=2.26.0" in content  # Should add >= prefix

    def test_lines_363_374_setup_py_update_patterns(self):
        """Test lines 363-374: setup.py update with different patterns."""
        updater = FileUpdater()

        # Create setup.py with quoted requirements
        setup_py = self.temp_dir / "setup.py"
        setup_py.write_text(
            """
setup(
    install_requires=[
        "requests>=2.25.0",
        'flask',
    ]
)
"""
        )

        result = updater.update_file(setup_py, {"requests": "2.26.0", "flask": "2.0.0"})
        assert result is True

        content = setup_py.read_text()
        assert "requests>=2.26.0" in content
        assert "flask>=2.0.0" in content

    def test_line_407_pyproject_toml_update_without_operator(self):
        """Test line 407: pyproject.toml update without operator prefix."""
        updater = FileUpdater()

        # Create pyproject.toml
        pyproject_toml = self.temp_dir / "pyproject.toml"
        pyproject_toml.write_text(
            """
[project]
dependencies = [
    "requests>=2.25.0",
]
"""
        )

        result = updater.update_file(pyproject_toml, {"requests": "2.26.0"})  # No operator
        assert result is True

        content = pyproject_toml.read_text()
        assert "requests>=2.26.0" in content  # Should add >= prefix


class TestFormatsEdgeCases:
    """Test additional edge cases for better coverage."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_detect_format_content_based(self):
        """Test format detection based on file content when filename is ambiguous."""
        # Create file with generic extension that falls back to content detection
        ambiguous_file = self.temp_dir / "deps.unknown"
        ambiguous_file.write_text(
            """
setup(
    name="test",
    install_requires=["requests"]
)
"""
        )

        # Should detect as SETUP_PY based on content
        format_type = FormatDetector.detect_format(ambiguous_file)
        assert format_type == FileFormat.SETUP_PY

    def test_universal_parser_unsupported_format_update(self):
        """Test update method with unsupported file format."""
        updater = FileUpdater()

        # Create file with unknown format
        unknown_file = self.temp_dir / "unknown.xyz"
        unknown_file.write_text("some content")

        # Mock format detection to return UNKNOWN format which has no updater
        with patch(
            "pypi_updater.formats.FormatDetector.detect_format",
            return_value=FileFormat.UNKNOWN,
        ):
            with pytest.raises(ValueError, match="Unsupported file format for updates"):
                updater.update_file(unknown_file, {"package": "1.0.0"})

    def test_pyproject_toml_key_value_pattern_update(self):
        """Test pyproject.toml update with key-value pattern."""
        updater = FileUpdater()

        # Create pyproject.toml with key-value style dependencies
        pyproject_toml = self.temp_dir / "pyproject.toml"
        pyproject_toml.write_text(
            """
[tool.poetry.dependencies]
requests = "^2.25.0"
flask = ">=1.0.0"
"""
        )

        result = updater.update_file(pyproject_toml, {"requests": "^2.26.0"})
        assert result is True

        content = pyproject_toml.read_text()
        # Note: ^ is not recognized as an operator so >= is prepended
        assert 'requests = ">=^2.26.0"' in content
