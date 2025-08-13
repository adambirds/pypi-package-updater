"""
Ultra-targeted tests for the final 5 missing lines: 148, 333, 343, 366, 407
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pypi_updater.formats import FileUpdater, UniversalParser


class TestUltraTargetedFinalFive:
    """Ultra-specific tests for the final 5 lines."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_line_148_specific_no_match_scenario(self):
        """Test line 148: Very specific no-match scenario after Requirement failure."""
        parser = UniversalParser()

        # Create file with line that fails Requirement but has no regex match
        test_file = self.temp_dir / "requirements.txt"
        # This line will fail Requirement parsing and should not match the regex pattern
        test_file.write_text("!!!invalid-start-character\n")

        # Mock Requirement to always fail
        with patch(
            "pypi_updater.formats.Requirement",
            side_effect=ValueError("Invalid requirement"),
        ):
            packages = parser.parse_file(test_file)

            # Should have no packages because regex doesn't match lines starting with !!!
            assert len(packages) == 0

    def test_line_333_specific_comment_scenario(self):
        """Test line 333: Very specific comment handling scenario."""
        updater = FileUpdater()

        # Create requirements file with specific comment format
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("requests>=2.25.0#inline-comment\n")

        # Update using the exact Requirement parsing path (not regex fallback)
        result = updater.update_file(test_file, {"requests": "2.26.0"})
        assert result is True

        content = test_file.read_text()
        # Line 333 should be hit: if comment: new_line += f"  {comment}"
        assert "#inline-comment" in content
        assert "requests>=2.26.0" in content

    def test_line_343_specific_regex_match_scenario(self):
        """Test line 343: Specific regex match scenario in requirements update."""
        updater = FileUpdater()

        # Create file that will trigger regex fallback with comment
        test_file = self.temp_dir / "requirements.txt"
        test_file.write_text("pkg>=1.0.0 # comment\n")

        # Mock Requirement to fail, forcing the regex path
        with patch("pypi_updater.formats.Requirement", side_effect=Exception("Force regex")):
            result = updater.update_file(test_file, {"pkg": "2.0.0"})
            assert result is True

            content = test_file.read_text()
            # This should hit the regex fallback path with comment handling
            assert "pkg>=2.0.0" in content
            assert "# comment" in content

    def test_line_366_setup_py_exact_scenario(self):
        """Test line 366: Exact setup.py scenario for line 366."""
        updater = FileUpdater()

        # Create setup.py that matches first pattern exactly
        setup_py = self.temp_dir / "setup.py"
        setup_py.write_text(
            """
setup(
    install_requires=[
        "pkg>=1.0.0",
    ]
)
"""
        )

        # Test the exact path that should hit line 366
        result = updater.update_file(setup_py, {"pkg": "2.0.0"})
        assert result is True

        content = setup_py.read_text()
        # Should have the >= added by setup.py updater
        assert "pkg>=2.0.0" in content

    def test_line_407_pyproject_exact_scenario(self):
        """Test line 407: Exact pyproject.toml scenario for line 407."""
        updater = FileUpdater()

        # Create pyproject.toml that hits the specific pattern
        pyproject_toml = self.temp_dir / "pyproject.toml"
        pyproject_toml.write_text(
            """
[project]
dependencies = [
    "pkg>=1.0.0",
]
"""
        )

        # Update with version that needs >= prefix added
        result = updater.update_file(pyproject_toml, {"pkg": "2.0.0"})
        assert result is True

        content = pyproject_toml.read_text()
        # Should hit line 407 where >= is added
        assert "pkg>=2.0.0" in content


class TestUltraSpecificEdgeCases:
    """Ultra-specific edge cases to hit remaining lines."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_requirements_parsing_with_invalid_characters(self):
        """Test requirements parsing with various invalid character scenarios."""
        parser = UniversalParser()

        # Test multiple scenarios that might hit line 148
        test_cases = [
            "###invalid",
            "!@#$%",
            "   ",
            "",
        ]

        for invalid_line in test_cases:
            test_file = self.temp_dir / f"test_{hash(invalid_line)}.txt"
            test_file.write_text(f"{invalid_line}\n")

            with patch("pypi_updater.formats.Requirement", side_effect=Exception("Parse error")):
                packages = parser.parse_file(test_file)
                # Should handle gracefully and return empty packages
                assert isinstance(packages, dict)

    def test_requirements_update_with_various_comment_formats(self):
        """Test requirements update with different comment formats."""
        updater = FileUpdater()

        # Test different comment scenarios
        comment_scenarios = [
            ("pkg>=1.0.0#comment", "pkg", "2.0.0"),
            ("pkg>=1.0.0 #comment", "pkg", "2.0.0"),
            ("pkg>=1.0.0  # comment with spaces", "pkg", "2.0.0"),
        ]

        for i, (line_content, pkg_name, new_version) in enumerate(comment_scenarios):
            test_file = self.temp_dir / f"comment_test_{i}.txt"
            test_file.write_text(f"{line_content}\n")

            result = updater.update_file(test_file, {pkg_name: new_version})
            assert result is True

            content = test_file.read_text()
            assert f"{pkg_name}>={new_version}" in content
            assert "#" in content  # Comment should be preserved

    def test_setup_py_various_patterns(self):
        """Test setup.py with various pattern scenarios."""
        updater = FileUpdater()

        # Test different setup.py patterns
        patterns = [
            '"pkg>=1.0.0"',
            "'pkg>=1.0.0'",
            '"pkg"',
            "'pkg'",
        ]

        for i, pattern in enumerate(patterns):
            setup_py = self.temp_dir / f"setup_{i}.py"
            setup_py.write_text(
                f"""
setup(
    install_requires=[
        {pattern},
    ]
)
"""
            )

            result = updater.update_file(setup_py, {"pkg": "2.0.0"})
            assert result is True

            content = setup_py.read_text()
            assert "pkg>=2.0.0" in content

    def test_pyproject_toml_various_formats(self):
        """Test pyproject.toml with various dependency formats."""
        updater = FileUpdater()

        # Test different pyproject.toml formats
        formats = [
            """[project]
dependencies = ["pkg>=1.0.0"]""",
            '''[tool.poetry.dependencies]
pkg = ">=1.0.0"''',
            """[project]
dependencies = [
    "pkg>=1.0.0",
]""",
        ]

        for i, toml_content in enumerate(formats):
            pyproject_toml = self.temp_dir / f"pyproject_{i}.toml"
            pyproject_toml.write_text(toml_content)

            result = updater.update_file(pyproject_toml, {"pkg": "2.0.0"})
            assert result is True

            content = pyproject_toml.read_text()
            assert "2.0.0" in content
