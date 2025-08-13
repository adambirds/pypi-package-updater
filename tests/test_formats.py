"""
Tests for file format detection, parsing, and updating functionality.
"""

import tempfile
from pathlib import Path

import pytest

from pypi_updater.formats import FileFormat, FileUpdater, FormatDetector, UniversalParser


class TestFormatDetection:
    """Test file format detection."""

    def test_detect_requirements_in(self):
        """Test detection of requirements.in files."""
        with tempfile.NamedTemporaryFile(suffix=".in", mode="w", delete=False) as f:
            f.write("requests>=2.25.0\n")
            f.flush()

            format_detected = FormatDetector.detect_format(f.name)
            assert format_detected == FileFormat.REQUIREMENTS_IN

            Path(f.name).unlink()

    def test_detect_requirements_txt(self):
        """Test detection of requirements.txt files."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("requests>=2.25.0\n")
            f.flush()

            format_detected = FormatDetector.detect_format(f.name)
            assert format_detected == FileFormat.REQUIREMENTS_TXT

            Path(f.name).unlink()

    def test_detect_setup_py(self):
        """Test detection of setup.py files."""
        with tempfile.NamedTemporaryFile(suffix="setup.py", mode="w", delete=False) as f:
            f.write("from setuptools import setup\nsetup(install_requires=['requests>=2.25.0'])\n")
            f.flush()

            format_detected = FormatDetector.detect_format(f.name)
            assert format_detected == FileFormat.SETUP_PY

            Path(f.name).unlink()

    def test_detect_pyproject_toml(self):
        """Test detection of pyproject.toml files."""
        with tempfile.NamedTemporaryFile(suffix="pyproject.toml", mode="w", delete=False) as f:
            f.write("[project]\ndependencies = ['requests>=2.25.0']\n")
            f.flush()

            format_detected = FormatDetector.detect_format(f.name)
            assert format_detected == FileFormat.PYPROJECT_TOML

            Path(f.name).unlink()

    def test_detect_by_content_setup_py(self):
        """Test content-based detection for setup.py."""
        content = "from setuptools import setup\nsetup(install_requires=['requests'])"
        format_detected = FormatDetector._detect_by_content(content)
        assert format_detected == FileFormat.SETUP_PY

    def test_detect_by_content_pyproject_toml(self):
        """Test content-based detection for pyproject.toml."""
        content = (
            "[build-system]\nrequires = ['setuptools']\n[project]\ndependencies = ['requests']"
        )
        format_detected = FormatDetector._detect_by_content(content)
        assert format_detected == FileFormat.PYPROJECT_TOML

    def test_detect_by_content_requirements_in(self):
        """Test content-based detection for requirements.in."""
        content = "-c constraints.txt\n-e .\nrequests>=2.25.0"
        format_detected = FormatDetector._detect_by_content(content)
        assert format_detected == FileFormat.REQUIREMENTS_IN


class TestUniversalParser:
    """Test universal parser for different file formats."""

    @pytest.fixture
    def parser(self):
        return UniversalParser()

    def test_parse_test_data_requirements_in(self, parser):
        """Test parsing requirements.in test data."""
        test_file = Path(__file__).parent.parent / "test_requirements_data" / "common.in"
        packages = parser.parse_file(test_file)

        assert isinstance(packages, dict)
        assert "Django" in packages
        assert "psycopg2" in packages

    def test_parse_test_data_requirements_txt(self, parser):
        """Test parsing requirements.txt test data."""
        test_file = Path(__file__).parent.parent / "test_requirements_data" / "requirements.txt"
        packages = parser.parse_file(test_file)

        assert isinstance(packages, dict)
        assert "requests" in packages
        assert "click" in packages
        assert "aiohttp" in packages
        assert "packaging" in packages

    def test_parse_test_data_setup_py(self, parser):
        """Test parsing setup.py test data."""
        test_file = Path(__file__).parent.parent / "test_requirements_data" / "setup.py"
        packages = parser.parse_file(test_file)

        assert isinstance(packages, dict)
        assert "requests" in packages
        assert "click" in packages
        assert "aiohttp" in packages
        assert "packaging" in packages

    def test_parse_test_data_pyproject_toml(self, parser):
        """Test parsing pyproject.toml test data."""
        test_file = Path(__file__).parent.parent / "test_requirements_data" / "pyproject.toml"
        packages = parser.parse_file(test_file)

        assert isinstance(packages, dict)
        assert "requests" in packages
        assert "click" in packages
        assert "aiohttp" in packages
        assert "packaging" in packages

    def test_parse_test_data_poetry_toml(self, parser):
        """Test parsing Poetry pyproject.toml test data."""
        test_file = (
            Path(__file__).parent.parent / "test_requirements_data" / "pyproject-poetry.toml"
        )
        packages = parser.parse_file(test_file)

        assert isinstance(packages, dict)
        assert "requests" in packages
        assert "click" in packages
        assert "aiohttp" in packages
        assert "packaging" in packages
        # Poetry format includes python version requirement
        assert "python" not in packages  # Should be filtered out

    def test_parse_with_explicit_format(self, parser):
        """Test parsing with explicit format specification."""
        test_file = Path(__file__).parent.parent / "test_requirements_data" / "requirements.txt"
        packages = parser.parse_file(test_file, FileFormat.REQUIREMENTS_TXT)

        assert isinstance(packages, dict)
        assert len(packages) > 0

    def test_parse_invalid_format(self, parser):
        """Test parsing with unsupported format."""
        test_file = Path(__file__).parent.parent / "test_requirements_data" / "requirements.txt"

        with pytest.raises(ValueError, match="Unsupported file format"):
            parser.parse_file(test_file, FileFormat.UNKNOWN)

    def test_parse_nonexistent_file(self, parser):
        """Test parsing nonexistent file."""
        with pytest.raises(ValueError):
            parser.parse_file("/nonexistent/file.txt")


class TestFileUpdater:
    """Test file updating functionality."""

    @pytest.fixture
    def updater(self):
        return FileUpdater()

    def test_update_requirements_txt_file(self, updater):
        """Test updating a requirements.txt file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("requests==2.25.0\nclick==8.0.0\naiohttp>=3.8.0\n")
            f.flush()
            temp_path = Path(f.name)

        try:
            # Update packages
            updates = {
                "requests": "2.32.0",
                "click": "8.2.1",
            }

            result = updater.update_file(temp_path, updates, FileFormat.REQUIREMENTS_TXT)
            assert result is True

            # Check the file was updated
            content = temp_path.read_text()
            assert "requests>=2.32.0" in content
            assert "click>=8.2.1" in content
            assert "aiohttp>=3.8.0" in content  # Unchanged

        finally:
            temp_path.unlink()

    def test_update_requirements_in_file(self, updater):
        """Test updating a requirements.in file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as f:
            f.write("requests>=2.25.0  # HTTP library\nclick>=8.0.0\n")
            f.flush()
            temp_path = Path(f.name)

        try:
            # Update packages
            updates = {
                "requests": "2.32.0",
                "click": "8.2.1",
            }

            result = updater.update_file(temp_path, updates)
            assert result is True

            # Check the file was updated and comments preserved
            content = temp_path.read_text()
            assert "requests>=2.32.0  # HTTP library" in content
            assert "click>=8.2.1" in content

        finally:
            temp_path.unlink()

    def test_update_setup_py_file(self, updater):
        """Test updating a setup.py file."""
        setup_content = """from setuptools import setup
setup(
    name="test",
    install_requires=[
        "requests>=2.25.0",
        "click>=8.0.0",
    ],
)"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(setup_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            updates = {
                "requests": "2.32.0",
                "click": "8.2.1",
            }

            result = updater.update_file(temp_path, updates, FileFormat.SETUP_PY)
            assert result is True

            # Check updates were applied
            content = temp_path.read_text()
            assert "requests>=2.32.0" in content
            assert "click>=8.2.1" in content

        finally:
            temp_path.unlink()

    def test_update_pyproject_toml_file(self, updater):
        """Test updating a pyproject.toml file."""
        toml_content = """[project]
dependencies = [
    "requests>=2.25.0",
    "click>=8.0.0",
]"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            updates = {
                "requests": "2.32.0",
                "click": "8.2.1",
            }

            result = updater.update_file(temp_path, updates, FileFormat.PYPROJECT_TOML)
            assert result is True

            # Check updates were applied
            content = temp_path.read_text()
            assert "requests>=2.32.0" in content
            assert "click>=8.2.1" in content

        finally:
            temp_path.unlink()

    def test_update_no_changes_needed(self, updater):
        """Test updating when no changes are needed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("requests==2.25.0\nclick==8.0.0\n")
            f.flush()
            temp_path = Path(f.name)

        try:
            # Try to update with packages not in the file
            updates = {
                "nonexistent-package": "1.0.0",
            }

            result = updater.update_file(temp_path, updates)
            assert result is False  # No changes made

        finally:
            temp_path.unlink()

    def test_update_unsupported_format(self, updater):
        """Test updating with unsupported format."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Unsupported file format for updates"):
                updater.update_file(temp_path, {}, FileFormat.UNKNOWN)
        finally:
            temp_path.unlink()


class TestEndToEndFormatHandling:
    """Test end-to-end format handling with the main updater."""

    def test_updater_with_different_formats(self):
        """Test that the main updater can handle different file formats."""
        from pypi_updater import PyPIUpdater

        # Test with test data directory
        test_data_dir = Path(__file__).parent.parent / "test_requirements_data"
        updater = PyPIUpdater(
            str(test_data_dir),
            "tools",
            include_setup_py=True,
            include_pyproject_toml=True,
        )

        # Find files
        files = updater.find_requirements_files()

        # Should find various file types
        file_names = [str(f) for f in files]
        assert any("setup.py" in name for name in file_names)
        assert any("pyproject" in name for name in file_names)
        assert any(".in" in name for name in file_names)
        assert any(".txt" in name for name in file_names)

    @pytest.mark.asyncio
    async def test_check_updates_with_different_formats(self):
        """Test checking for updates across different file formats."""
        from pypi_updater import PyPIUpdater

        test_data_dir = Path(__file__).parent.parent / "test_requirements_data"
        updater = PyPIUpdater(
            str(test_data_dir),
            "tools",
            include_setup_py=True,
            include_pyproject_toml=True,
        )

        # Get specific files of different formats
        files_to_check = [
            str(test_data_dir / "requirements.txt"),
            str(test_data_dir / "setup.py"),
            str(test_data_dir / "pyproject.toml"),
        ]

        # This should work without errors
        update_info = await updater.check_for_updates(files_to_check)

        assert isinstance(update_info, dict)
        assert len(update_info) == 3

        # Each file should have been processed
        for file_path in files_to_check:
            assert file_path in update_info


class TestFormatSpecificFeatures:
    """Test format-specific parsing features."""

    @pytest.fixture
    def parser(self):
        return UniversalParser()

    def test_requirements_file_with_includes(self, parser):
        """Test parsing requirements files with -r includes."""
        content = """-r base.txt
# Comments
requests>=2.25.0
click>=8.0.0"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = Path(f.name)

        try:
            packages = parser.parse_file(temp_path)
            assert "requests" in packages
            assert "click" in packages
            # -r includes should be ignored
            assert "base.txt" not in packages
        finally:
            temp_path.unlink()

    def test_setup_py_with_extras(self, parser):
        """Test parsing setup.py with extras_require."""
        content = """from setuptools import setup
setup(
    install_requires=["requests>=2.25.0"],
    extras_require={
        "dev": ["pytest>=7.0.0"],
    }
)"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = Path(f.name)

        try:
            packages = parser.parse_file(temp_path)
            # Should only get install_requires, not extras
            assert "requests" in packages
            assert "pytest" not in packages
        finally:
            temp_path.unlink()

    def test_pyproject_toml_poetry_format(self, parser):
        """Test parsing pyproject.toml with Poetry format."""
        content = '''[tool.poetry.dependencies]
python = "^3.8"
requests = ">=2.25.0"
click = {version = ">=8.0.0", optional = true}

[tool.poetry.group.dev.dependencies]
pytest = ">=7.0.0"'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = Path(f.name)

        try:
            packages = parser.parse_file(temp_path)
            assert "requests" in packages
            assert "click" in packages
            assert "python" not in packages  # Should be filtered
            # Dev dependencies are in a different section, might not be included
        finally:
            temp_path.unlink()
