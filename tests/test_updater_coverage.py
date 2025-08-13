"""
Tests to improve coverage of updater.py interactive and compilation functionality.
"""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pypi_updater.pypi_client import PackageInfo
from pypi_updater.updater import PyPIUpdater, UpdateResult


class TestUpdaterInteractiveConfirmation:
    """Test interactive confirmation scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.requirements_dir = self.temp_dir / "requirements"
        self.tools_dir = self.temp_dir / "tools"
        self.requirements_dir.mkdir()
        self.tools_dir.mkdir()

        # Create a test requirements file
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests==2.25.0\n")

        self.updater = PyPIUpdater(
            requirements_dir=str(self.requirements_dir), tools_dir=str(self.tools_dir)
        )

    @pytest.mark.asyncio
    async def test_interactive_confirmation_yes(self):
        """Test interactive confirmation with 'y' response."""
        pkg_info = PackageInfo(name="requests", current_version="2.25.0", latest_version="2.28.0")

        with patch("builtins.input", return_value="y"):
            with patch.object(self.updater.parser, "update_requirement_version", return_value=True):
                result = await self.updater._update_single_package(
                    "test.in", pkg_info, dry_run=False, interactive=True
                )

                assert result.success is True
                assert result.package_name == "requests"
                assert result.new_version == "2.28.0"

    @pytest.mark.asyncio
    async def test_interactive_confirmation_no(self):
        """Test interactive confirmation with 'n' response."""
        pkg_info = PackageInfo(name="requests", current_version="2.25.0", latest_version="2.28.0")

        with patch("builtins.input", return_value="n"):
            result = await self.updater._update_single_package(
                "test.in", pkg_info, dry_run=False, interactive=True
            )

            assert result.success is False
            assert result.error_message == "Skipped by user"
            assert result.package_name == "requests"

    @pytest.mark.asyncio
    async def test_interactive_confirmation_quit(self):
        """Test interactive confirmation with 'q' response."""
        pkg_info = PackageInfo(name="requests", current_version="2.25.0", latest_version="2.28.0")

        with patch("builtins.input", return_value="q"):
            with patch("builtins.exit") as mock_exit:
                await self.updater._update_single_package(
                    "test.in", pkg_info, dry_run=False, interactive=True
                )
                mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_interactive_confirmation_uppercase(self):
        """Test interactive confirmation with uppercase responses."""
        pkg_info = PackageInfo(name="requests", current_version="2.25.0", latest_version="2.28.0")

        # Test uppercase Y
        with patch("builtins.input", return_value="Y"):
            with patch.object(self.updater.parser, "update_requirement_version", return_value=True):
                result = await self.updater._update_single_package(
                    "test.in", pkg_info, dry_run=False, interactive=True
                )
                assert result.success is True

        # Test uppercase Q
        with patch("builtins.input", return_value="Q"):
            with patch("builtins.exit") as mock_exit:
                await self.updater._update_single_package(
                    "test.in", pkg_info, dry_run=False, interactive=True
                )
                mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_non_interactive_mode(self):
        """Test non-interactive mode bypasses confirmation."""
        pkg_info = PackageInfo(name="requests", current_version="2.25.0", latest_version="2.28.0")

        with patch.object(self.updater.parser, "update_requirement_version", return_value=True):
            result = await self.updater._update_single_package(
                "test.in", pkg_info, dry_run=False, interactive=False
            )

            assert result.success is True
            assert result.package_name == "requests"

    @pytest.mark.asyncio
    async def test_update_failure_scenario(self):
        """Test scenario where parser update fails."""
        pkg_info = PackageInfo(name="requests", current_version="2.25.0", latest_version="2.28.0")

        with patch.object(self.updater.parser, "update_requirement_version", return_value=False):
            result = await self.updater._update_single_package(
                "test.in", pkg_info, dry_run=False, interactive=False
            )

            assert result.success is False
            assert "Failed to update requests in test.in" in result.error_message
            assert result.package_name == "requests"


class TestCompilationScript:
    """Test compilation script functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.requirements_dir = self.temp_dir / "requirements"
        self.tools_dir = self.temp_dir / "tools"
        self.requirements_dir.mkdir()
        self.tools_dir.mkdir()

        self.updater = PyPIUpdater(
            requirements_dir=str(self.requirements_dir), tools_dir=str(self.tools_dir)
        )

    @pytest.mark.asyncio
    async def test_compile_requirements_script_missing(self):
        """Test compilation when script doesn't exist."""
        result = await self.updater._compile_requirements()
        assert result is False

    @pytest.mark.asyncio
    async def test_compile_requirements_success(self):
        """Test successful compilation."""
        # Create a mock script
        script_path = self.tools_dir / "update-locked-requirements"
        script_path.write_text("#!/bin/bash\necho 'Success'\nexit 0")
        script_path.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

            result = await self.updater._compile_requirements()
            assert result is True

            # Verify subprocess was called correctly
            mock_run.assert_called_once_with(
                [str(script_path)],
                cwd=script_path.parent.parent,
                capture_output=True,
                text=True,
                timeout=300,
            )

    @pytest.mark.asyncio
    async def test_compile_requirements_failure(self):
        """Test failed compilation."""
        script_path = self.tools_dir / "update-locked-requirements"
        script_path.write_text("#!/bin/bash\necho 'Error' >&2\nexit 1")
        script_path.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error occurred")

            result = await self.updater._compile_requirements()
            assert result is False

    @pytest.mark.asyncio
    async def test_compile_requirements_timeout(self):
        """Test compilation timeout."""
        script_path = self.tools_dir / "update-locked-requirements"
        script_path.write_text("#!/bin/bash\nsleep 10")
        script_path.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)

            result = await self.updater._compile_requirements()
            assert result is False

    @pytest.mark.asyncio
    async def test_compile_requirements_exception(self):
        """Test compilation with unexpected exception."""
        script_path = self.tools_dir / "update-locked-requirements"
        script_path.write_text("#!/bin/bash\necho 'test'")
        script_path.chmod(0o755)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Permission denied")

            result = await self.updater._compile_requirements()
            assert result is False


class TestUpdaterWorkflowEdgeCases:
    """Test edge cases in the update workflow."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.requirements_dir = self.temp_dir / "requirements"
        self.tools_dir = self.temp_dir / "tools"
        self.requirements_dir.mkdir()
        self.tools_dir.mkdir()

        self.updater = PyPIUpdater(
            requirements_dir=str(self.requirements_dir), tools_dir=str(self.tools_dir)
        )

    @pytest.mark.asyncio
    async def test_update_packages_no_files_found(self):
        """Test update_packages when no files are found."""
        # Empty requirements directory
        summary = await self.updater.update_packages()

        assert summary.total_packages == 0
        assert summary.updated_packages == 0
        assert summary.failed_packages == 0
        assert summary.skipped_packages == 0

    @pytest.mark.asyncio
    async def test_update_packages_no_updates_available(self):
        """Test update_packages when no updates are available."""
        # Create a requirements file
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests==2.28.0\n")

        # Mock check_for_updates to return no updates
        with patch.object(self.updater, "check_for_updates") as mock_check:
            mock_check.return_value = {str(req_file): [PackageInfo("requests", "2.28.0", "2.28.0")]}

            summary = await self.updater.update_packages()

            assert summary.total_packages == 0
            assert summary.updated_packages == 0

    @pytest.mark.asyncio
    async def test_update_packages_with_compilation(self):
        """Test update_packages with auto compilation enabled."""
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests==2.25.0\n")

        # Create compilation script
        script_path = self.tools_dir / "update-locked-requirements"
        script_path.write_text("#!/bin/bash\necho 'compiled'")
        script_path.chmod(0o755)

        pkg_info = PackageInfo("requests", "2.25.0", "2.28.0")

        with patch.object(self.updater, "check_for_updates") as mock_check:
            mock_check.return_value = {str(req_file): [pkg_info]}

            with patch.object(self.updater.parser, "update_requirement_version", return_value=True):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stdout="compiled", stderr="")

                    summary = await self.updater.update_packages(
                        interactive=False, auto_compile=True
                    )

                    assert summary.updated_packages == 1
                    mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_packages_dry_run_mode(self):
        """Test update_packages in dry run mode."""
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests==2.25.0\n")

        pkg_info = PackageInfo("requests", "2.25.0", "2.28.0")

        with patch.object(self.updater, "check_for_updates") as mock_check:
            mock_check.return_value = {str(req_file): [pkg_info]}

            summary = await self.updater.update_packages(dry_run=True)

            assert summary.total_packages == 1
            assert summary.updated_packages == 1  # Shows as "updated" in dry run

    @pytest.mark.asyncio
    async def test_update_packages_mixed_results(self):
        """Test update_packages with mixed success/failure results."""
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests==2.25.0\nclick==7.0.0\n")

        pkg_info1 = PackageInfo("requests", "2.25.0", "2.28.0")
        pkg_info2 = PackageInfo("click", "7.0.0", "8.0.0")

        with patch.object(self.updater, "check_for_updates") as mock_check:
            mock_check.return_value = {str(req_file): [pkg_info1, pkg_info2]}

            # Mock parser to succeed for requests, fail for click
            def mock_update(file_path, pkg_name, version):
                return pkg_name == "requests"

            with patch.object(
                self.updater.parser,
                "update_requirement_version",
                side_effect=mock_update,
            ):
                summary = await self.updater.update_packages(interactive=False)

                assert summary.total_packages == 2
                assert summary.updated_packages == 1
                assert summary.failed_packages == 1
                assert summary.success_rate == 50.0


class TestDryRunBehavior:
    """Test dry run specific behavior."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.requirements_dir = self.temp_dir / "requirements"
        self.tools_dir = self.temp_dir / "tools"
        self.requirements_dir.mkdir()
        self.tools_dir.mkdir()

        self.updater = PyPIUpdater(
            requirements_dir=str(self.requirements_dir), tools_dir=str(self.tools_dir)
        )

    @pytest.mark.asyncio
    async def test_dry_run_single_package(self):
        """Test dry run mode for single package update."""
        pkg_info = PackageInfo("requests", "2.25.0", "2.28.0")

        result = await self.updater._update_single_package(
            "test.in", pkg_info, dry_run=True, interactive=False
        )

        assert result.success is True
        assert result.package_name == "requests"
        assert result.old_version == "2.25.0"
        assert result.new_version == "2.28.0"
        # In dry run, no actual update should occur

    @pytest.mark.asyncio
    async def test_dry_run_no_compilation(self):
        """Test that dry run mode doesn't trigger compilation."""
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests==2.25.0\n")

        pkg_info = PackageInfo("requests", "2.25.0", "2.28.0")

        with patch.object(self.updater, "check_for_updates") as mock_check:
            mock_check.return_value = {str(req_file): [pkg_info]}

            with patch.object(self.updater, "_compile_requirements") as mock_compile:
                summary = await self.updater.update_packages(dry_run=True, auto_compile=True)

                # Compilation should not be called in dry run mode
                mock_compile.assert_not_called()
                assert summary.updated_packages == 1


def test_print_update_summary():
    """Test the print_update_summary method."""
    from pypi_updater.updater import UpdateSummary

    temp_dir = Path(tempfile.mkdtemp())
    updater = PyPIUpdater(requirements_dir=str(temp_dir))

    # Create a summary with mixed results
    results = [
        UpdateResult("requests", "2.25.0", "2.28.0", "test.in", True),
        UpdateResult("click", "7.0.0", "8.0.0", "test.in", False, "Update failed"),
    ]

    summary = UpdateSummary(2, 1, 1, 0, results)

    # Capture the output
    import io
    import sys

    captured_output = io.StringIO()
    sys.stdout = captured_output

    try:
        updater.print_update_summary(summary)
        output = captured_output.getvalue()

        # Verify key information is in the output
        assert "UPDATE SUMMARY" in output
        assert "Total packages checked: 2" in output
        assert "Packages updated: 1" in output
        assert "Packages failed: 1" in output
        assert "Success rate: 50.0%" in output
        assert "requests: 2.25.0 → 2.28.0" in output
        assert "click: 7.0.0 → 8.0.0" in output
        assert "Error: Update failed" in output

    finally:
        sys.stdout = sys.__stdout__
