"""
Final attempt to cover lines 148 and 343 with very specific edge cases.
These lines are reached when a line becomes empty AFTER inline comment processing.
"""

import tempfile
from pathlib import Path

from pypi_updater.formats import FileUpdater, UniversalParser


def test_line_148_edge_case():
    """
    Line 148: Line becomes empty after inline comment removal.
    Need a line that:
    1. Doesn't start with # (so it's not skipped as comment)
    2. Doesn't start with - (so it's not skipped as directive)
    3. Contains # (so it goes through inline comment processing)
    4. Becomes empty after splitting on # and stripping
    """
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("flask>=2.0\n")
        # This line has just whitespace before the hash
        f.write("  #comment with no package name\n")  # This should trigger line 148
        f.write("django>=4.0\n")
        f.flush()

        # Let's trace through the logic:
        # line = "  #comment with no package name"
        # line.strip() = "#comment with no package name"
        # not line.startswith('#') = False, so continue is NOT executed
        # not line.startswith('-') = True, so continue is NOT executed
        # '#' in line = True, so we enter the if block
        # line = line.split('#')[0].strip() = "".strip() = ""
        # if not line: = if not "": = True, so line 148 should execute

        packages = parser._parse_requirements_file(Path(f.name))

        assert len(packages) == 2
        assert "flask" in packages
        assert "django" in packages


def test_line_343_edge_case():
    """
    Line 343: Same logic but in the file updater method.
    """
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("requests>=2.0\n")
        # Line that becomes empty after comment processing
        f.write("  #just a comment\n")  # Should trigger line 343
        f.write("urllib3>=1.0\n")
        f.flush()

        updates = {"requests": "2.28.0"}
        result = updater._update_requirements_file(Path(f.name), updates)

        assert result is True
        content = Path(f.name).read_text()
        assert "requests>=2.28.0" in content


def test_line_148_whitespace_hash():
    """
    Another approach: line with only whitespace followed by hash.
    """
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("numpy>=1.0\n")
        f.write("   # this is a comment with leading spaces\n")  # Target line 148
        f.write("scipy>=1.0\n")
        f.flush()

        packages = parser._parse_requirements_file(Path(f.name))
        assert len(packages) == 2


def test_line_343_whitespace_hash():
    """
    Another approach: line with only whitespace followed by hash in updater.
    """
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("numpy>=1.0\n")
        f.write("   # this is a comment with leading spaces\n")  # Target line 343
        f.write("scipy>=1.0\n")
        f.flush()

        updates = {"numpy": "1.24.0"}
        result = updater._update_requirements_file(Path(f.name), updates)
        assert result is True


def test_line_148_tab_hash():
    """
    Try with tab character before hash.
    """
    parser = UniversalParser()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("matplotlib>=3.0\n")
        f.write("\t#tab before hash\n")  # Use tab character, target line 148
        f.write("seaborn>=0.11\n")
        f.flush()

        packages = parser._parse_requirements_file(Path(f.name))
        assert len(packages) == 2


def test_line_343_tab_hash():
    """
    Try with tab character before hash in updater.
    """
    updater = FileUpdater()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("matplotlib>=3.0\n")
        f.write("\t#tab before hash\n")  # Use tab character, target line 343
        f.write("seaborn>=0.11\n")
        f.flush()

        updates = {"matplotlib": "3.7.0"}
        result = updater._update_requirements_file(Path(f.name), updates)
        assert result is True
