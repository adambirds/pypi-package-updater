"""
Ultra-specific tests for the final 2 missing lines: 148 and 343.
Both are 'if not line:' checks after inline comment processing.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from pypi_updater.formats import FileUpdater, UniversalParser


def test_line_148_exact_empty_after_comment():
    """
    Target line 148 exactly: line becomes empty after inline comment processing.
    This requires a line with ONLY whitespace + comment that becomes empty after strip.
    """
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        # This specific pattern should trigger line 148:
        # - Not a comment line (doesn't start with #)
        # - Not a directive line (doesn't start with -)
        # - Contains # so goes through inline comment processing
        # - After splitting on # and stripping, becomes empty
        f.write("package1>=1.0\n")
        f.write("   # this is just spaces and comment\n")  # This should trigger line 148
        f.write("package2>=2.0\n")
        f.flush()

        packages = parser._parse_requirements_file(Path(f.name))

        assert len(packages) == 2
        assert "package1" in packages
        assert "package2" in packages


def test_line_343_exact_empty_after_comment_in_updater():
    """
    Target line 343 exactly: line becomes empty after inline comment processing in updater.
    This is in the _update_requirements_file method.
    """
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        # Similar pattern but in the context of file updating
        f.write("package1>=1.0\n")
        f.write("   # comment only line with spaces\n")  # Should trigger line 343
        f.write("package2>=2.0\n")
        f.flush()

        # Try to update - this will process through the same logic
        updates = {"package1": "2.0.0"}
        result = updater._update_requirements_file(Path(f.name), updates)

        assert result is True  # Should have updated package1

        # Verify the content
        content = Path(f.name).read_text()
        assert "package1>=2.0.0" in content


def test_line_148_whitespace_before_hash():
    """
    Another attempt at line 148: line with only whitespace before hash.
    """
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("requests>=2.0\n")
        f.write("    # This line has spaces before hash\n")  # Target line 148
        f.write("urllib3>=1.0\n")
        f.flush()

        packages = parser._parse_requirements_file(Path(f.name))

        assert len(packages) == 2
        assert "requests" in packages
        assert "urllib3" in packages


def test_line_343_whitespace_before_hash_updater():
    """
    Another attempt at line 343: line with only whitespace before hash in updater.
    """
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("requests>=2.0\n")
        f.write("    # This line has spaces before hash\n")  # Target line 343
        f.write("urllib3>=1.0\n")
        f.flush()

        updates = {"requests": "2.28.0"}
        result = updater._update_requirements_file(Path(f.name), updates)

        assert result is True
        content = Path(f.name).read_text()
        assert "requests>=2.28.0" in content


def test_line_148_hash_only_content():
    """
    Try to hit line 148 with content that's only hash after processing.
    """
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("flask>=2.0\n")
        # Line that when split on # and stripped becomes empty
        f.write("  #\n")  # Just hash with spaces - should trigger line 148
        f.write("django>=4.0\n")
        f.flush()

        packages = parser._parse_requirements_file(Path(f.name))

        assert len(packages) == 2
        assert "flask" in packages
        assert "django" in packages


def test_line_343_hash_only_content_updater():
    """
    Try to hit line 343 with content that's only hash after processing.
    """
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("flask>=2.0\n")
        f.write("  #\n")  # Just hash with spaces - should trigger line 343
        f.write("django>=4.0\n")
        f.flush()

        updates = {"flask": "2.1.0"}
        result = updater._update_requirements_file(Path(f.name), updates)

        assert result is True
        content = Path(f.name).read_text()
        assert "flask>=2.1.0" in content
