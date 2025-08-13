"""
PyPI Updater - Automatically update Python package versions in requirements files.
"""

from .formats import FileFormat, FileUpdater, FormatDetector, UniversalParser
from .parser import Requirement, RequirementsParser
from .pypi_client import PackageInfo, PyPIClient
from .updater import PyPIUpdater, UpdateResult, UpdateSummary

__version__ = "0.1.0"

__all__ = [
    "PyPIUpdater",
    "RequirementsParser",
    "PyPIClient",
    "PackageInfo",
    "UpdateResult",
    "UpdateSummary",
    "Requirement",
    "UniversalParser",
    "FileUpdater",
    "FormatDetector",
    "FileFormat",
]
