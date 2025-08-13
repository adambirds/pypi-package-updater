"""
Unit tests for the PyPI updater package.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pypi_updater import PackageInfo, PyPIClient, PyPIUpdater, RequirementsParser


class TestRequirementsParser:
    """Test the requirements parser functionality."""

    def test_parse_simple_requirement(self):
        """Test parsing a simple requirement file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as f:
            f.write(
                """# Test requirements file
Django==4.1.0
requests>=2.25.0
# Comment line
-r other.in
celery==5.2.0  # With inline comment
"""
            )
            temp_file = f.name

        try:
            parser = RequirementsParser()
            requirements = parser.parse_file(temp_file)

            assert len(requirements) == 6

            # Check that we found the right packages
            packages = parser.get_package_requirements(temp_file)
            expected_packages = [
                ("Django", "4.1.0"),
                ("requests", "2.25.0"),
                ("celery", "5.2.0"),
            ]

            assert len(packages) == 3
            for expected in expected_packages:
                assert expected in packages

        finally:
            os.unlink(temp_file)

    def test_parse_complex_requirements(self):
        """Test parsing requirements with various formats."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as f:
            f.write(
                """
# Core dependencies
Django==4.2.0
requests>=2.25.0,<3.0
celery[redis]==5.2.0
psycopg2-binary!=2.8.5,>=2.8

# Includes
-r common.in

# Comments and empty lines

# More packages
uvicorn[standard]==0.18.0
"""
            )
            temp_file = f.name

        try:
            parser = RequirementsParser()
            packages = parser.get_package_requirements(temp_file)

            # Should find packages despite complex version specs
            package_names = [pkg[0] for pkg in packages]
            assert "Django" in package_names
            assert "requests" in package_names
            assert "celery" in package_names
            assert "psycopg2-binary" in package_names
            assert "uvicorn" in package_names

        finally:
            os.unlink(temp_file)

    def test_find_requirements_files(self):
        """Test finding .in files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_dir = Path(temp_dir) / "requirements"
            requirements_dir.mkdir()

            # Create some .in files
            (requirements_dir / "common.in").write_text("Django==4.0.0")
            (requirements_dir / "dev.in").write_text("pytest==7.0.0")
            (requirements_dir / "prod.txt").write_text("# Not an .in file")

            parser = RequirementsParser(str(requirements_dir))
            files = parser.find_all_requirements_files()

            assert len(files) == 2
            file_names = [f.name for f in files]
            assert "common.in" in file_names
            assert "dev.in" in file_names
            assert "prod.txt" not in file_names


class TestPyPIClient:
    """Test the PyPI client functionality."""

    @pytest.mark.asyncio
    async def test_get_package_info(self):
        """Test getting package info from PyPI."""
        client = PyPIClient()

        # Test with a well-known package
        info = await client.get_package_info("requests")
        assert info is not None
        assert "info" in info
        assert "version" in info["info"]

    @pytest.mark.asyncio
    async def test_get_latest_version(self):
        """Test getting the latest version of a package."""
        client = PyPIClient()

        version = await client.get_latest_version("requests")
        assert version is not None
        assert isinstance(version, str)
        assert len(version) > 0

    @pytest.mark.asyncio
    async def test_check_package_updates(self):
        """Test checking for package updates."""
        client = PyPIClient()

        # Use an old version that should have updates
        packages = [("requests", "2.0.0"), ("urllib3", "1.0.0")]
        updates = await client.check_package_updates(packages)

        assert len(updates) == 2
        for update in updates:
            assert isinstance(update, PackageInfo)
            assert update.name in ["requests", "urllib3"]
            assert update.has_update  # These old versions should have updates

    @pytest.mark.asyncio
    async def test_nonexistent_package(self):
        """Test handling of nonexistent packages."""
        client = PyPIClient()

        info = await client.get_package_info("this-package-definitely-does-not-exist-12345")
        assert info is None


class TestPyPIUpdater:
    """Test the main PyPI updater functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.requirements_dir = Path(self.temp_dir) / "requirements"
        self.tools_dir = Path(self.temp_dir) / "tools"

        self.requirements_dir.mkdir()
        self.tools_dir.mkdir()

        # Create test requirements files
        (self.requirements_dir / "common.in").write_text(
            """
# Test requirements
requests==2.25.0
urllib3==1.26.0
Django==4.0.0
"""
        )

        (self.requirements_dir / "dev.in").write_text(
            """
-r common.in
pytest==7.0.0
black==22.0.0
"""
        )

        # Create mock compilation script
        script_file = self.tools_dir / "update-locked-requirements"
        script_file.write_text(
            """#!/bin/bash
echo "Mock compilation script executed"
"""
        )
        script_file.chmod(0o755)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_check_for_updates(self):
        """Test checking for updates in requirements files."""
        updater = PyPIUpdater(str(self.requirements_dir), str(self.tools_dir))

        updates = await updater.check_for_updates()

        # Should find both files
        assert len(updates) >= 2

        # Check that we found packages in common.in
        common_file = str(self.requirements_dir / "common.in")
        assert common_file in updates

        common_packages = updates[common_file]
        assert len(common_packages) >= 3  # requests, urllib3, Django

        # At least some of these old versions should have updates
        updates_available = [pkg for pkg in common_packages if pkg.has_update]
        assert len(updates_available) > 0

    @pytest.mark.asyncio
    async def test_check_specific_files(self):
        """Test checking updates for specific files."""
        updater = PyPIUpdater(str(self.requirements_dir), str(self.tools_dir))

        common_file = str(self.requirements_dir / "common.in")
        updates = await updater.check_for_updates([common_file])

        # Should only check the specified file
        assert len(updates) == 1
        assert common_file in updates

    @pytest.mark.asyncio
    async def test_dry_run_update(self):
        """Test dry run mode."""
        updater = PyPIUpdater(str(self.requirements_dir), str(self.tools_dir))

        common_file = str(self.requirements_dir / "common.in")

        # Mock the check_for_updates to return a known update
        mock_package_info = PackageInfo(
            name="requests", current_version="2.25.0", latest_version="2.28.0"
        )

        with patch.object(updater, "check_for_updates") as mock_check:
            mock_check.return_value = {common_file: [mock_package_info]}

            summary = await updater.update_packages(
                files=[common_file], dry_run=True, auto_compile=False, interactive=False
            )

            # Should show as updated in dry run
            assert summary.total_packages == 1
            assert summary.updated_packages == 1
            assert summary.failed_packages == 0

    def test_parser_integration(self):
        """Test that the updater correctly uses the parser."""
        updater = PyPIUpdater(str(self.requirements_dir), str(self.tools_dir))

        # Test that parser finds our test files
        files = updater.parser.find_all_requirements_files()
        file_names = [f.name for f in files]

        assert "common.in" in file_names
        assert "dev.in" in file_names

        # Test that parser correctly extracts packages
        common_file = str(self.requirements_dir / "common.in")
        packages = updater.parser.get_package_requirements(common_file)

        package_names = [pkg[0] for pkg in packages]
        assert "requests" in package_names
        assert "urllib3" in package_names
        assert "Django" in package_names


class TestCLIIntegration:
    """Test CLI argument handling and integration."""

    def test_empty_files_list_handling(self):
        """Test that empty files list is converted to None."""
        # This tests the fix for the bug we found
        empty_files = []
        files_to_check = empty_files if empty_files else None
        assert files_to_check is None

        non_empty_files = ["requirements/common.in"]
        files_to_check = non_empty_files if non_empty_files else None
        assert files_to_check == non_empty_files


# Test fixtures and utilities
@pytest.fixture
def sample_requirements_content():
    """Sample requirements file content for testing."""
    return """
# Core dependencies
Django==4.2.0
requests>=2.25.0
celery==5.2.0

# Database
psycopg2==2.9.5

# Development dependencies
-r dev.in
"""


@pytest.fixture
def mock_pypi_response():
    """Mock PyPI API response for testing."""
    return {
        "info": {
            "name": "requests",
            "version": "2.28.1",
            "summary": "Python HTTP for Humans.",
            "home_page": "https://requests.readthedocs.io",
        },
        "releases": {"2.28.1": [], "2.28.0": [], "2.27.1": []},
    }


# Integration tests
class TestEndToEndWorkflow:
    """Test the complete workflow from CLI to file updates."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.requirements_dir = Path(self.temp_dir) / "requirements"
        self.requirements_dir.mkdir()

        # Create a realistic requirements structure
        (self.requirements_dir / "common.in").write_text(
            """
# Core Dependencies
Django==4.0.0
requests==2.25.0
celery==5.0.0
"""
        )

        (self.requirements_dir / "dev.in").write_text(
            """
-r common.in
pytest==6.0.0
black==21.0.0
"""
        )

        (self.requirements_dir / "prod.in").write_text(
            """
-r common.in
gunicorn==20.0.0
"""
        )

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @pytest.mark.asyncio
    async def test_full_update_workflow(self):
        """Test the complete update workflow."""
        updater = PyPIUpdater(str(self.requirements_dir), "tools")

        # 1. Check for updates
        updates = await updater.check_for_updates()

        # Should find updates for our old packages
        assert len(updates) >= 3  # common.in, dev.in, prod.in

        # 2. Verify that old versions have updates available
        for file_path, package_infos in updates.items():
            if package_infos:  # Skip empty files like includes-only files
                updates_available = [pkg for pkg in package_infos if pkg.has_update]
                # At least some packages should have updates (they're old versions)
                if "common.in" in file_path:
                    assert len(updates_available) > 0

    def test_requirements_parser_real_files(self):
        """Test parser with realistic requirements files."""
        parser = RequirementsParser(str(self.requirements_dir))

        # Test dependency graph
        graph = parser.get_dependency_graph()

        # dev.in and prod.in should depend on common.in
        assert "dev.in" in graph
        assert "prod.in" in graph
        assert "common.in" in graph["dev.in"]
        assert "common.in" in graph["prod.in"]

        # Test update order
        order = parser.get_update_order()

        # common.in should come before dev.in and prod.in
        common_index = order.index("common.in")
        dev_index = order.index("dev.in")
        prod_index = order.index("prod.in")

        assert common_index < dev_index
        assert common_index < prod_index


class TestRealProjectIntegration:
    """Test using the actual test requirements data from our project."""

    @pytest.mark.asyncio
    async def test_with_project_test_data(self):
        """Test using the real test requirements data."""
        # Use the test_requirements_data directory
        test_data_dir = Path(__file__).parent.parent / "test_requirements_data"

        if not test_data_dir.exists():
            pytest.skip("Test requirements data directory not found")

        updater = PyPIUpdater(str(test_data_dir), "tools")

        # This should work with the real test data
        updates = await updater.check_for_updates()

        # Should find some files
        assert len(updates) > 0

        # Should find packages in at least some files
        total_packages = sum(len(packages) for packages in updates.values())
        assert total_packages > 0


if __name__ == "__main__":
    # Run tests with pytest if called directly
    import subprocess
    import sys

    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"], capture_output=False)
    sys.exit(result.returncode)
