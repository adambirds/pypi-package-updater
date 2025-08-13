"""
PyPI API client for fetching package information.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, cast

import aiohttp
from packaging import version

logger = logging.getLogger(__name__)


@dataclass
class PackageInfo:
    """Information about a package from PyPI."""

    name: str
    current_version: str
    latest_version: str
    homepage: Optional[str] = None
    summary: Optional[str] = None

    @property
    def has_update(self) -> bool:
        """Check if there's a newer version available."""
        try:
            return version.parse(self.latest_version) > version.parse(self.current_version)
        except version.InvalidVersion:
            return False


class PyPIClient:
    """Client for interacting with PyPI API."""

    BASE_URL = "https://pypi.org/pypi"

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from PyPI."""
        url = f"{self.BASE_URL}/{package_name}/json"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return cast(Dict[str, Any], await response.json())
                    elif response.status == 404:
                        logger.warning(f"Package '{package_name}' not found on PyPI")
                        return None
                    else:
                        logger.error(
                            f"Failed to fetch info for '{package_name}': HTTP {response.status}"
                        )
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching info for '{package_name}'")
            return None
        except Exception as e:
            logger.error(f"Error fetching info for '{package_name}': {e}")
            return None

    async def get_latest_version(self, package_name: str) -> Optional[str]:
        """Get the latest version of a package."""
        info = await self.get_package_info(package_name)
        if info and "info" in info:
            return cast(Optional[str], info["info"].get("version"))
        return None

    async def check_package_updates(self, packages: List[tuple[str, str]]) -> List[PackageInfo]:
        """
        Check for updates for multiple packages.

        Args:
            packages: List of (package_name, current_version) tuples

        Returns:
            List of PackageInfo objects with update information
        """
        tasks = []
        for package_name, current_version in packages:
            task = self._get_package_info_with_current(package_name, current_version)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        package_infos = []
        for result in results:
            if isinstance(result, PackageInfo):
                package_infos.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error processing package: {result}")

        return package_infos

    async def _get_package_info_with_current(
        self, package_name: str, current_version: str
    ) -> Optional[PackageInfo]:
        """Get package info and compare with current version."""
        info = await self.get_package_info(package_name)

        if not info or "info" not in info:
            return None

        package_data = info["info"]
        latest_version = package_data.get("version", "")

        return PackageInfo(
            name=package_name,
            current_version=current_version,
            latest_version=latest_version,
            homepage=package_data.get("home_page"),
            summary=package_data.get("summary"),
        )
