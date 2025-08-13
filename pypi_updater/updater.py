"""
Main PyPI updater class that orchestrates the update process.
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .formats import FileFormat, FileUpdater, FormatDetector, UniversalParser
from .parser import Requirement, RequirementsParser
from .pypi_client import PackageInfo, PyPIClient

logger = logging.getLogger(__name__)


@dataclass
class UpdateResult:
    """Result of an update operation."""

    package_name: str
    old_version: str
    new_version: str
    file_path: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class UpdateSummary:
    """Summary of all updates performed."""

    total_packages: int
    updated_packages: int
    failed_packages: int
    skipped_packages: int
    updates: List[UpdateResult]

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of updates."""
        if self.total_packages == 0:
            return 0.0
        return (self.updated_packages / self.total_packages) * 100


class PyPIUpdater:
    """Main class for updating package versions in requirements files."""

    def __init__(
        self,
        requirements_dir: str = "requirements",
        tools_dir: str = "tools",
        include_setup_py: bool = False,
        include_pyproject_toml: bool = False,
        format_override: Optional[FileFormat] = None,
    ):
        self.requirements_dir = Path(requirements_dir)
        self.tools_dir = Path(tools_dir)
        self.include_setup_py = include_setup_py
        self.include_pyproject_toml = include_pyproject_toml
        self.format_override = format_override
        self.parser = RequirementsParser(requirements_dir)
        self.universal_parser = UniversalParser()
        self.file_updater = FileUpdater()
        self.pypi_client = PyPIClient()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def find_requirements_files(self) -> List[Path]:
        """Find all requirements files based on configuration."""
        files: List[Path] = []

        # Always include .in files (our primary format)
        if self.requirements_dir.exists():
            files.extend(self.requirements_dir.glob("*.in"))

            # Also include .txt files if no format override
            if self.format_override is None or self.format_override == FileFormat.REQUIREMENTS_TXT:
                files.extend(self.requirements_dir.glob("*.txt"))

        # Include setup.py if requested - check both current dir and requirements dir
        if self.include_setup_py:
            # Check current directory
            setup_py = Path("setup.py")
            if setup_py.exists():
                files.append(setup_py)
            # Also check requirements directory
            setup_py_req = self.requirements_dir / "setup.py"
            if setup_py_req.exists():
                files.append(setup_py_req)

        # Include pyproject.toml if requested - check both current dir and requirements dir
        if self.include_pyproject_toml:
            # Check current directory
            pyproject = Path("pyproject.toml")
            if pyproject.exists():
                files.append(pyproject)
            # Also check requirements directory
            pyproject_req = self.requirements_dir / "pyproject.toml"
            if pyproject_req.exists():
                files.append(pyproject_req)
            # Also check for Poetry format
            pyproject_poetry = self.requirements_dir / "pyproject-poetry.toml"
            if pyproject_poetry.exists():
                files.append(pyproject_poetry)

        # If specific files are in the current directory, include them
        for pattern in ["requirements.txt", "requirements.in"]:
            file_path = Path(pattern)
            if file_path.exists() and file_path not in files:
                files.append(file_path)

        return sorted(set(files))

    async def check_for_updates(
        self, files: Optional[List[str]] = None
    ) -> Dict[str, List[PackageInfo]]:
        """
        Check for updates across all or specified requirements files.

        Args:
            files: Optional list of specific files to check. If None, discovers files automatically.

        Returns:
            Dictionary mapping file paths to lists of PackageInfo objects
        """
        if files is None:
            file_paths = self.find_requirements_files()
        else:
            file_paths = [Path(f) for f in files]

        results: Dict[str, Any] = {}

        for file_path in file_paths:
            logger.info(f"Checking updates for {file_path}")

            # Use universal parser for different file formats
            packages: Union[Dict[str, str], List[Tuple[str, str]]]
            try:
                file_format = self.format_override or FormatDetector.detect_format(file_path)
                packages = self.universal_parser.parse_file(file_path, file_format)
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
                # Fallback to original parser for .in/.txt files
                if file_path.suffix in [".in", ".txt"]:
                    packages = self.parser.get_package_requirements(str(file_path))
                else:
                    packages = {}

            if not packages:
                logger.info(f"No packages found in {file_path}")
                results[str(file_path)] = []
                continue

            # Convert to list of tuples for PyPI client
            package_tuples = []

            # Handle both dictionary format (from universal parser) and list format (from fallback parser)
            if isinstance(packages, dict):
                for name, version_spec in packages.items():
                    # Extract just the version number from version specs like ">=1.0.0"
                    import re

                    version_match = re.search(r"[\d.]+", version_spec)
                    current_version = version_match.group() if version_match else "0.0.0"
                    package_tuples.append((name, current_version))
            elif isinstance(packages, list):
                # packages is already a list of tuples from fallback parser
                package_tuples = packages

            package_infos = await self.pypi_client.check_package_updates(package_tuples)
            results[str(file_path)] = package_infos

            # Log summary for this file
            updates_available = sum(1 for pkg in package_infos if pkg.has_update)
            logger.info(f"Found {updates_available} updates available in {file_path}")

        return results

    async def update_packages(
        self,
        files: Optional[List[str]] = None,
        dry_run: bool = False,
        auto_compile: bool = True,
        interactive: bool = True,
    ) -> UpdateSummary:
        """
        Update package versions in requirements files.

        Args:
            files: Optional list of specific files to update
            dry_run: If True, only show what would be updated without making changes
            auto_compile: If True, run the compilation script after updates
            interactive: If True, ask for confirmation before each update

        Returns:
            UpdateSummary with details of all updates
        """
        logger.info("Starting package update process...")

        # Check for updates first
        update_info = await self.check_for_updates(files)

        if not update_info:
            logger.info("No requirements files found to update")
            return UpdateSummary(0, 0, 0, 0, [])

        # Collect all updates to perform
        updates_to_perform = []
        for file_path, package_infos in update_info.items():
            for pkg_info in package_infos:
                if pkg_info.has_update:
                    updates_to_perform.append((file_path, pkg_info))

        if not updates_to_perform:
            logger.info("No updates available for any packages")
            return UpdateSummary(0, 0, 0, 0, [])

        logger.info(f"Found {len(updates_to_perform)} packages with available updates")

        # Process updates
        update_results = []
        updated_files = set()

        for file_path, pkg_info in updates_to_perform:
            result = await self._update_single_package(file_path, pkg_info, dry_run, interactive)
            update_results.append(result)

            if result.success and not dry_run:
                updated_files.add(file_path)

        # Compile requirements if requested and updates were made
        if auto_compile and updated_files and not dry_run:
            logger.info("Running requirements compilation...")
            await self._compile_requirements()

        # Generate summary
        total = len(update_results)
        updated = sum(1 for r in update_results if r.success)
        failed = sum(1 for r in update_results if not r.success and r.error_message)
        skipped = total - updated - failed

        summary = UpdateSummary(total, updated, failed, skipped, update_results)

        # Log summary
        logger.info(f"Update complete: {updated}/{total} packages updated")
        if failed > 0:
            logger.warning(f"{failed} packages failed to update")
        if skipped > 0:
            logger.info(f"{skipped} packages skipped")

        return summary

    async def _update_single_package(
        self, file_path: str, pkg_info: PackageInfo, dry_run: bool, interactive: bool
    ) -> UpdateResult:
        """Update a single package in a file."""

        logger.info(f"Package: {pkg_info.name}")
        logger.info(f"  Current: {pkg_info.current_version}")
        logger.info(f"  Latest:  {pkg_info.latest_version}")
        logger.info(f"  File:    {file_path}")

        if dry_run:
            logger.info("  [DRY RUN] Would update package")
            return UpdateResult(
                pkg_info.name,
                pkg_info.current_version,
                pkg_info.latest_version,
                file_path,
                True,
            )

        # Interactive confirmation
        if interactive:
            response = input(
                f"Update {pkg_info.name} from {pkg_info.current_version} to {pkg_info.latest_version}? [y/N/q]: "
            )
            if response.lower() == "q":
                logger.info("Update process cancelled by user")
                exit(0)
            elif response.lower() != "y":
                logger.info(f"Skipping {pkg_info.name}")
                return UpdateResult(
                    pkg_info.name,
                    pkg_info.current_version,
                    pkg_info.latest_version,
                    file_path,
                    False,
                    "Skipped by user",
                )

        # Perform the update
        success = self.parser.update_requirement_version(
            file_path, pkg_info.name, pkg_info.latest_version
        )

        if success:
            logger.info(f"✓ Updated {pkg_info.name} to {pkg_info.latest_version}")
            return UpdateResult(
                pkg_info.name,
                pkg_info.current_version,
                pkg_info.latest_version,
                file_path,
                True,
            )
        else:
            error_msg = f"Failed to update {pkg_info.name} in {file_path}"
            logger.error(error_msg)
            return UpdateResult(
                pkg_info.name,
                pkg_info.current_version,
                pkg_info.latest_version,
                file_path,
                False,
                error_msg,
            )

    async def _compile_requirements(self) -> bool:
        """Run the requirements compilation script."""
        script_path = self.tools_dir / "update-locked-requirements"

        if not script_path.exists():
            logger.warning(f"Compilation script not found: {script_path}")
            return False

        try:
            result = subprocess.run(
                [str(script_path)],
                cwd=script_path.parent.parent,  # Run from project root
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info("Requirements compilation completed successfully")
                return True
            else:
                logger.error(f"Requirements compilation failed:")
                logger.error(f"STDOUT: {result.stdout}")
                logger.error(f"STDERR: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Requirements compilation timed out")
            return False
        except Exception as e:
            logger.error(f"Error running compilation script: {e}")
            return False

    def print_update_summary(self, summary: UpdateSummary) -> None:
        """Print a formatted summary of updates."""
        print("\n" + "=" * 60)
        print("UPDATE SUMMARY")
        print("=" * 60)
        print(f"Total packages checked: {summary.total_packages}")
        print(f"Packages updated: {summary.updated_packages}")
        print(f"Packages failed: {summary.failed_packages}")
        print(f"Packages skipped: {summary.skipped_packages}")
        print(f"Success rate: {summary.success_rate:.1f}%")
        print()

        if summary.updates:
            print("DETAILED RESULTS:")
            print("-" * 60)

            for update in summary.updates:
                status = "✓" if update.success else "✗"
                print(
                    f"{status} {update.package_name}: {update.old_version} → {update.new_version}"
                )
                print(f"   File: {update.file_path}")
                if update.error_message:
                    print(f"   Error: {update.error_message}")
                print()

        print("=" * 60)
