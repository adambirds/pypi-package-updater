"""
Test specifically targeting line 250 in updater.py.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pypi_updater.pypi_client import PackageInfo
from pypi_updater.updater import PyPIUpdater, UpdateResult


class TestLine250:
    """Test targeting line 250: if skipped > 0: logger.info(f'{skipped} packages skipped')"""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.requirements_dir = self.temp_dir / "requirements"
        self.requirements_dir.mkdir(exist_ok=True)
        self.tools_dir = self.temp_dir / "tools"
        self.tools_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_line_250_skipped_packages_logging(self):
        """
        Test line 250: if skipped > 0: logger.info(f'{skipped} packages skipped')

        We need skipped = total - updated - failed > 0
        This happens when packages have updates but user chooses not to update them.
        """
        updater = PyPIUpdater(
            requirements_dir=str(self.requirements_dir), tools_dir=str(self.tools_dir)
        )

        # Create a requirements file
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests>=2.25.0\n")

        # Create mock package info with update available
        mock_package_info = PackageInfo(
            name="requests",
            current_version="2.25.0",
            latest_version="2.28.0",  # Has update
            homepage="https://example.com",
            summary="HTTP library",
        )

        with patch.object(
            updater.pypi_client,
            "check_package_updates",
            return_value=[mock_package_info],
        ):
            # Mock _update_single_package to return a skipped result (not updated, no error)
            async def mock_update_single_package(file_path, pkg_info, dry_run, interactive):
                # Return a result indicating the package was skipped by user choice
                return UpdateResult(
                    package_name="requests",
                    old_version="2.25.0",
                    new_version="2.25.0",  # No change made
                    file_path=str(file_path),
                    success=False,  # Not updated
                    error_message=None,  # No error, just skipped
                )

            with patch.object(
                updater,
                "_update_single_package",
                side_effect=mock_update_single_package,
            ):
                result = await updater.update_packages()

                # Should have:
                # total = 1 (1 package with update available)
                # updated = 0 (none were updated)
                # failed = 0 (no error_message)
                # skipped = 1 - 0 - 0 = 1

                assert result.total_packages == 1
                assert result.updated_packages == 0
                assert result.failed_packages == 0
                assert result.skipped_packages == 1

                # Line 250 should be executed: if skipped > 0: logger.info(...)

    @pytest.mark.asyncio
    async def test_line_250_alternative_skipped_scenario(self):
        """Alternative test for line 250 with multiple packages having updates."""
        updater = PyPIUpdater(
            requirements_dir=str(self.requirements_dir), tools_dir=str(self.tools_dir)
        )

        # Create requirements file with multiple packages
        req_file = self.requirements_dir / "test.in"
        req_file.write_text("requests>=2.25.0\nflask>=1.0.0\n")

        # Mock multiple packages with updates available
        mock_package_infos = [
            PackageInfo(
                name="requests",
                current_version="2.25.0",
                latest_version="2.28.0",  # Has update
                homepage="https://example.com",
                summary="HTTP library",
            ),
            PackageInfo(
                name="flask",
                current_version="1.0.0",
                latest_version="2.0.0",  # Has update
                homepage="https://flask.palletsprojects.com",
                summary="Web framework",
            ),
        ]

        with patch.object(
            updater.pypi_client,
            "check_package_updates",
            return_value=mock_package_infos,
        ):
            # Mock _update_single_package to simulate mixed results
            async def mock_update_single_package(file_path, pkg_info, dry_run, interactive):
                if pkg_info.name == "requests":
                    # This one succeeds
                    return UpdateResult(
                        package_name="requests",
                        old_version="2.25.0",
                        new_version="2.28.0",
                        file_path=str(file_path),
                        success=True,
                        error_message=None,
                    )
                else:
                    # This one is skipped (user said no, or other reason)
                    return UpdateResult(
                        package_name="flask",
                        old_version="1.0.0",
                        new_version="1.0.0",  # No change
                        file_path=str(file_path),
                        success=False,  # Not updated
                        error_message=None,  # No error, just skipped
                    )

            with patch.object(
                updater,
                "_update_single_package",
                side_effect=mock_update_single_package,
            ):
                result = await updater.update_packages()

                # Should have:
                # total = 2 (both packages have updates)
                # updated = 1 (requests)
                # failed = 0 (no error messages)
                # skipped = 2 - 1 - 0 = 1 (flask)

                assert result.total_packages == 2
                assert result.updated_packages == 1
                assert result.failed_packages == 0
                assert result.skipped_packages == 1

                # This should trigger line 250: if skipped > 0
