"""
PyPI Updater - A tool to automatically update Python package versions in requirements files.
"""

__version__ = "0.1.0"
__author__ = "Adam Birds"
__email__ = "adam@adbsoftwaresolutions.com"

from .updater import PyPIUpdater
from .parser import RequirementsParser
from .pypi_client import PyPIClient, PackageInfo

__all__ = ["PyPIUpdater", "RequirementsParser", "PyPIClient", "PackageInfo"]
