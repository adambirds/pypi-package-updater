"""
PyPI Updater - Automatically update Python package versions in requirements files.
"""

from .updater import PyPIUpdater, UpdateResult, UpdateSummary
from .parser import RequirementsParser, Requirement
from .pypi_client import PyPIClient, PackageInfo
from .formats import UniversalParser, FileUpdater, FormatDetector, FileFormat

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
    "FileFormat"
]
