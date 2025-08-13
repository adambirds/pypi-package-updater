"""
Setup configuration for PyPI Updater package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

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

setup(
    name="pypi-updater",
    version="0.1.0",
    description="Automatically update Python package versions in requirements files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Adam Birds",
    author_email="adam@adbsoftwaresolutions.com",
    url="https://github.com/yourusername/pypi-updater",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=read_requirements("common.in"),
    extras_require={
        "dev": read_requirements("dev.in"),
        "test": read_requirements("test.in"),
        "prod": read_requirements("prod.in"),
    },
    entry_points={
        "console_scripts": [
            "update-packages=update_packages:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Software Distribution",
    ],
    keywords="pip requirements pypi packages update automation",
)
