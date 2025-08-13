"""
Main PyPI updater class that orchestrates the update process.
"""

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .parser import RequirementsParser, Requirement
from .pypi_client import PyPIClient, PackageInfo

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
    
    def __init__(self, requirements_dir: str = "requirements", tools_dir: str = "tools"):
        self.requirements_dir = Path(requirements_dir)
        self.tools_dir = Path(tools_dir)
        self.parser = RequirementsParser(requirements_dir)
        self.pypi_client = PyPIClient()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def check_for_updates(self, files: Optional[List[str]] = None) -> Dict[str, List[PackageInfo]]:
        """
        Check for updates across all or specified requirements files.
        
        Args:
            files: Optional list of specific files to check. If None, checks all .in files.
            
        Returns:
            Dictionary mapping file paths to lists of PackageInfo objects
        """
        if files is None:
            file_paths = self.parser.find_all_requirements_files()
        else:
            file_paths = [Path(f) for f in files]
        
        results = {}
        
        for file_path in file_paths:
            logger.info(f"Checking updates for {file_path}")
            
            packages = self.parser.get_package_requirements(str(file_path))
            if not packages:
                logger.info(f"No packages found in {file_path}")
                results[str(file_path)] = []
                continue
            
            package_infos = await self.pypi_client.check_package_updates(packages)
            results[str(file_path)] = package_infos
            
            # Log summary for this file
            updates_available = sum(1 for pkg in package_infos if pkg.has_update)
            logger.info(f"Found {updates_available} updates available in {file_path}")
        
        return results
    
    async def update_packages(self, 
                            files: Optional[List[str]] = None,
                            dry_run: bool = False,
                            auto_compile: bool = True,
                            interactive: bool = True) -> UpdateSummary:
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
            result = await self._update_single_package(
                file_path, pkg_info, dry_run, interactive
            )
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
    
    async def _update_single_package(self, 
                                   file_path: str, 
                                   pkg_info: PackageInfo, 
                                   dry_run: bool, 
                                   interactive: bool) -> UpdateResult:
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
                True
            )
        
        # Interactive confirmation
        if interactive:
            response = input(f"Update {pkg_info.name} from {pkg_info.current_version} to {pkg_info.latest_version}? [y/N/q]: ")
            if response.lower() == 'q':
                logger.info("Update process cancelled by user")
                exit(0)
            elif response.lower() != 'y':
                logger.info(f"Skipping {pkg_info.name}")
                return UpdateResult(
                    pkg_info.name, 
                    pkg_info.current_version, 
                    pkg_info.latest_version, 
                    file_path, 
                    False,
                    "Skipped by user"
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
                True
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
                error_msg
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
                timeout=300  # 5 minute timeout
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
    
    def print_update_summary(self, summary: UpdateSummary):
        """Print a formatted summary of updates."""
        print("\n" + "="*60)
        print("UPDATE SUMMARY")
        print("="*60)
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
                print(f"{status} {update.package_name}: {update.old_version} → {update.new_version}")
                print(f"   File: {update.file_path}")
                if update.error_message:
                    print(f"   Error: {update.error_message}")
                print()
        
        print("="*60)
