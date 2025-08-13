"""
Basic smoke tests for the PyPI updater package.
"""

import asyncio

import pytest

from pypi_updater import PyPIClient, RequirementsParser


@pytest.mark.asyncio
async def test_pypi_client_basic():
    """Basic test that PyPI client can fetch package info."""
    client = PyPIClient()

    # Test with a well-known package
    info = await client.get_package_info("requests")
    assert info is not None
    assert "info" in info


def test_requirements_parser_basic():
    """Basic test that requirements parser can parse a simple file."""
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".in", delete=False) as f:
        f.write("Django==4.1.0\nrequests>=2.25.0\n")
        temp_file = f.name

    try:
        parser = RequirementsParser()
        packages = parser.get_package_requirements(temp_file)
        assert len(packages) == 2
        assert ("Django", "4.1.0") in packages
        assert ("requests", "2.25.0") in packages
    finally:
        os.unlink(temp_file)


def test_imports():
    """Test that all main components can be imported."""
    from pypi_updater import PackageInfo, PyPIClient, PyPIUpdater, RequirementsParser

    # Just check they can be instantiated
    parser = RequirementsParser()
    client = PyPIClient()
    updater = PyPIUpdater()

    assert parser is not None
    assert client is not None
    assert updater is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
