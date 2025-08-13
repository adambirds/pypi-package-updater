"""
Final precision tests to hit the exact missing lines: 148, 333, 343, 366, 407
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pypi_updater.formats import FileUpdater, UniversalParser


class TestExactMissingLines:
    """Tests targeting the exact missing lines."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_line_148_empty_line_after_comment_removal(self):
        """Test line 148: if not line: continue (in requirements parsing)"""
        parser = UniversalParser()

        # Create file where line becomes empty after comment removal
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("# Only comment content\nrequests>=2.25.0\n")

        packages = parser.parse_file(test_file)
        # This should hit line 148: if not line: continue
        assert "requests" in packages
        assert len(packages) == 1

    def test_line_333_empty_line_after_comment_processing_in_update(self):
        """Test line 333: if not line: continue (in requirements update)"""
        updater = FileUpdater()

        # Create file with line that becomes empty after comment processing
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("requests>=2.25.0\n# Only comment\n")

        result = updater.update_file(test_file, {"requests": "2.26.0"})
        # This should hit line 333: if not line: continue
        assert result is True

        content = test_file.read_text()
        assert "requests>=2.26.0" in content

    def test_line_343_empty_line_in_regex_fallback_path(self):
        """Test line 343: if not line: continue (in regex fallback with comment)"""
        updater = FileUpdater()

        # Create file that will trigger regex fallback and have empty line after comment
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("pkg>=1.0.0\n  # just comment\n")

        # Mock Requirement to fail for first line, forcing regex path
        call_count = 0

        def requirement_side_effect(line):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Force regex fallback")
            # Let second line (comment) pass through normal processing
            from packaging.requirements import Requirement as OrigReq

            return OrigReq(line)

        with patch("pypi_updater.formats.Requirement", side_effect=requirement_side_effect):
            result = updater.update_file(test_file, {"pkg": "2.0.0"})
            # This should process first line via regex and hit line 343 for comment line
            assert result is True

    def test_line_366_regex_fallback_with_version_operator(self):
        """Test line 366: version operator check in regex fallback"""
        updater = FileUpdater()

        # Create file that will trigger regex fallback
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("pkg>=1.0.0\n")

        # Mock Requirement to fail, forcing regex path
        with patch("pypi_updater.formats.Requirement", side_effect=Exception("Force regex")):
            # Update with version that already has operator
            result = updater.update_file(test_file, {"pkg": ">=2.0.0"})
            # This should hit line 366: if new_version.startswith(('>=', ...
            assert result is True

            content = test_file.read_text()
            assert "pkg>=2.0.0" in content

    def test_line_407_setup_py_content_changed_scenario(self):
        """Test successful setup.py update to ensure we test the True path too."""
        updater = FileUpdater()

        # Create setup.py with install_requires
        setup_py = self.temp_dir / "setup.py"
        setup_py.write_text(
            """
setup(
    install_requires=[
        "requests>=2.25.0",
    ]
)
"""
        )

        # Update existing package
        result = updater.update_file(setup_py, {"requests": "2.26.0"})

        # This should hit the True path of the setup.py updater
        assert result is True


class TestAdditionalEdgeCases:
    """Additional edge cases to ensure we hit all the lines."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_requirements_parsing_line_becomes_empty(self):
        """Test requirements parsing where line becomes empty after processing."""
        parser = UniversalParser()

        # File with line that becomes empty after comment stripping
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("requests>=2.25.0\n   # comment only line\n")

        packages = parser.parse_file(test_file)
        # Should only get the valid requirement, skipping empty line
        assert len(packages) == 1
        assert "requests" in packages

    def test_requirements_update_with_empty_lines(self):
        """Test requirements update with lines that become empty."""
        updater = FileUpdater()

        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("pkg>=1.0.0\n    \n# comment\n")

        result = updater.update_file(test_file, {"pkg": "2.0.0"})
        assert result is True

        content = test_file.read_text()
        assert "pkg>=2.0.0" in content

    def test_setup_py_pattern_matching_success(self):
        """Test setup.py update with successful pattern matching."""
        updater = FileUpdater()

        # Setup.py with install_requires that will match
        setup_py = self.temp_dir / "setup.py"
        setup_py.write_text(
            """
setup(
    install_requires=[
        "requests>=2.25.0",
    ]
)
"""
        )

        # Update existing package
        result = updater.update_file(setup_py, {"requests": "2.26.0"})
        assert result is True

    def test_requirements_regex_fallback_with_operators(self):
        """Test requirements regex fallback with different operators."""
        updater = FileUpdater()

        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("package>=1.0.0\n")

        # Force regex fallback
        with patch("pypi_updater.formats.Requirement", side_effect=Exception("Parse error")):
            # Test with version that has operator
            result = updater.update_file(test_file, {"package": "==2.0.0"})
            assert result is True

            content = test_file.read_text()
            assert "package==2.0.0" in content
