"""
PyPI Updater - Automatically update Python package versions in requirements files.
"""

try:
    from ._version import version as __version__  # type: ignore
except ImportError:
    # Fallback for development without installed package
    __version__ = "unknown"

from .formats import FileFormat, FileUpdater, FormatDetector, UniversalParser
from .parser import Requirement, RequirementsParser
from .pypi_client import PackageInfo, PyPIClient
from .updater import PyPIUpdater, UpdateResult, UpdateSummary

__all__ = [
    "__version__",
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
