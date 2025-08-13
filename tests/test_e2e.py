"""
End-to-end tests for the PyPI updater tool.

These tests exercise the full functionality of the package update tool
including CLI integration, file processing, and PyPI integration.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from pypi_updater import PyPIUpdater


class TestEndToEnd:
    """End-to-end test suite."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_requirements_structure(self, temp_project_dir):
        """Create a sample requirements structure."""
        req_dir = temp_project_dir / "requirements"
        req_dir.mkdir()

        tools_dir = temp_project_dir / "tools"
        tools_dir.mkdir()

        # Create basic requirements files
        (req_dir / "common.in").write_text(
            """
# Core dependencies
requests>=2.25.0
click>=8.0.0
"""
        )

        (req_dir / "dev.in").write_text(
            """
-r common.in

# Development dependencies
pytest>=7.0.0
black>=22.0.0
"""
        )

        (req_dir / "prod.in").write_text(
            """
-r common.in

# Production dependencies
gunicorn>=20.0.0
"""
        )

        return temp_project_dir

    def test_cli_help_command(self):
        """Test that CLI help command works."""
        result = subprocess.run(
            [sys.executable, "update_packages.py", "--help"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "--check-only" in result.stdout

    def test_cli_check_only_mode(self, sample_requirements_structure):
        """Test CLI in check-only mode."""
        result = subprocess.run(
            [
                sys.executable,
                str(Path.cwd() / "update_packages.py"),
                "--check-only",
                "--requirements-dir",
                str(sample_requirements_structure / "requirements"),
                str(sample_requirements_structure / "requirements" / "common.in"),
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0
        assert "Checking for available updates" in result.stdout

    def test_cli_dry_run_mode(self, sample_requirements_structure):
        """Test CLI in dry-run mode."""
        result = subprocess.run(
            [
                sys.executable,
                str(Path.cwd() / "update_packages.py"),
                "--dry-run",
                "--requirements-dir",
                str(sample_requirements_structure / "requirements"),
                str(sample_requirements_structure / "requirements" / "common.in"),
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_full_update_workflow(self, sample_requirements_structure):
        """Test the complete update workflow."""
        updater = PyPIUpdater(
            str(sample_requirements_structure / "requirements"),
            str(sample_requirements_structure / "tools"),
        )

        # Check for updates
        updates = await updater.check_for_updates(
            [str(sample_requirements_structure / "requirements" / "common.in")]
        )

        # Should find some updates (unless packages are already latest)
        assert isinstance(updates, dict)

        # Test file discovery
        found_files = updater.find_requirements_files()
        assert len(found_files) >= 1
        assert any("common.in" in str(f) for f in found_files)

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_package(self, sample_requirements_structure):
        """Test error handling with invalid package names."""
        req_file = sample_requirements_structure / "requirements" / "invalid.in"
        req_file.write_text(
            """
# Invalid package
this-package-definitely-does-not-exist-on-pypi>=1.0.0
"""
        )

        updater = PyPIUpdater(
            str(sample_requirements_structure / "requirements"),
            str(sample_requirements_structure / "tools"),
        )

        # Should handle invalid packages gracefully
        updates = await updater.check_for_updates([str(req_file)])
        assert isinstance(updates, dict)

    def test_cli_with_multiple_files(self, sample_requirements_structure):
        """Test CLI with multiple requirements files."""
        result = subprocess.run(
            [
                sys.executable,
                str(Path.cwd() / "update_packages.py"),
                "--check-only",
                "--requirements-dir",
                str(sample_requirements_structure / "requirements"),
                str(sample_requirements_structure / "requirements" / "common.in"),
                str(sample_requirements_structure / "requirements" / "dev.in"),
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0

    def test_cli_with_no_files_specified(self, sample_requirements_structure):
        """Test CLI when no files are specified (should discover automatically)."""
        result = subprocess.run(
            [
                sys.executable,
                str(Path.cwd() / "update_packages.py"),
                "--check-only",
                "--requirements-dir",
                str(sample_requirements_structure / "requirements"),
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_compilation_integration(self, sample_requirements_structure):
        """Test integration with compilation tools."""
        # Create a simple compilation script
        compile_script = sample_requirements_structure / "tools" / "compile"
        compile_script.write_text(
            """#!/bin/bash
echo "Compiling requirements..."
touch requirements/common.txt
echo "# Compiled" > requirements/common.txt
"""
        )
        compile_script.chmod(0o755)

        updater = PyPIUpdater(
            str(sample_requirements_structure / "requirements"),
            str(sample_requirements_structure / "tools"),
        )

        # This should work without errors
        updates = await updater.check_for_updates(
            [str(sample_requirements_structure / "requirements" / "common.in")]
        )
        assert isinstance(updates, dict)

    def test_error_handling_invalid_directory(self):
        """Test error handling with invalid directory paths."""
        result = subprocess.run(
            [
                sys.executable,
                str(Path.cwd() / "update_packages.py"),
                "--check-only",
                "--requirements-dir",
                "/this/directory/does/not/exist",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        # Should handle gracefully and not crash
        assert result.returncode != 0 or "No packages found to check" in result.stdout

    @pytest.mark.asyncio
    async def test_large_requirements_file(self, sample_requirements_structure):
        """Test with a large requirements file."""
        large_req_file = sample_requirements_structure / "requirements" / "large.in"

        # Create a file with many packages
        packages = [
            "requests>=2.25.0",
            "click>=8.0.0",
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.900",
            "aiohttp>=3.8.0",
            "pydantic>=1.8.0",
            "fastapi>=0.70.0",
            "uvicorn>=0.15.0",
        ]

        large_req_file.write_text("\n".join(packages))

        updater = PyPIUpdater(
            str(sample_requirements_structure / "requirements"),
            str(sample_requirements_structure / "tools"),
        )

        updates = await updater.check_for_updates([str(large_req_file)])
        assert isinstance(updates, dict)
