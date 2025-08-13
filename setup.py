"""
Setup configuration for PyPI Package Updater.
Reads dependencies from requirements files to maintain single source of truth.
"""

from setuptools import setup, find_packages
from pathlib import Path


def read_requirements(filename):
    """Read requirements from a file, filtering out comments and -r includes."""
    requirements_file = Path(__file__).parent / "requirements" / filename
    if not requirements_file.exists():
        return []
    
    requirements = []
    with open(requirements_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments, empty lines, and -r includes
            if line and not line.startswith('#') and not line.startswith('-r'):
                # Remove inline comments
                if '#' in line:
                    line = line.split('#')[0].strip()
                if line:
                    requirements.append(line)
    return requirements


def read_dev_requirements():
    """Read all development requirements from dev.in and related files."""
    dev_requirements = []
    
    # Read test requirements
    dev_requirements.extend(read_requirements("test.in"))
    
    # Read dev-specific requirements (excluding test.in include)
    dev_file = Path(__file__).parent / "requirements" / "dev.in"
    if dev_file.exists():
        with open(dev_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip -r includes, comments, and empty lines
                if (line and 
                    not line.startswith('#') and 
                    not line.startswith('-r')):
                    # Remove inline comments
                    if '#' in line:
                        line = line.split('#')[0].strip()
                    if line:
                        dev_requirements.append(line)
    
    return dev_requirements


# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read version from pypi_updater/__init__.py

setup(
    name="pypi-package-updater",  # Available PyPI name suggestion
    description="A tool to update Python package dependencies across multiple file formats",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Adam Birds",
    author_email="adam.birds@adbwebdesigns.co.uk",
    url="https://github.com/adambirds/pypi-package-updater",
    project_urls={
        "Repository": "https://github.com/adambirds/pypi-package-updater",
        "Issues": "https://github.com/adambirds/pypi-package-updater/issues",
    },
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.11",
    setup_requires=["setuptools_scm"],
    install_requires=read_requirements("common.in"),
    extras_require={
        "dev": read_dev_requirements(),
    },
    entry_points={
        "console_scripts": [
            "pypi-update=pypi_updater.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Software Distribution",
    ],
    license="MIT",
)
