"""
Test setup.py file for format detection and parsing tests.
"""
from setuptools import setup, find_packages

setup(
    name="test-package",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "click>=8.0.0",
        "aiohttp>=3.8.0",
        "packaging>=21.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
        "test": [
            "pytest-asyncio>=0.18.0",
            "pytest-mock>=3.6.0",
        ],
    },
)
