"""
File format detection and parsing for different types of dependency files.

Supports:
- requirements.txt files
- requirements.in files (pip-tools)
- setup.py files
- pyproject.toml files
- Auto-detection of file types
"""

import ast
import re
import tomllib  # Python 3.11+ only
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from packaging.requirements import Requirement


class FileFormat(Enum):
    """Supported file formats for dependency specification."""

    REQUIREMENTS_IN = "requirements.in"
    REQUIREMENTS_TXT = "requirements.txt"
    SETUP_PY = "setup.py"
    PYPROJECT_TOML = "pyproject.toml"
    UNKNOWN = "unknown"


class FormatDetector:
    """Detect the format of dependency files."""

    @staticmethod
    def detect_format(file_path: Union[str, Path]) -> FileFormat:
        """
        Detect the format of a dependency file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            FileFormat enum indicating the detected format
        """
        file_path = Path(file_path)

        # Check by filename first
        if file_path.name == "setup.py":
            return FileFormat.SETUP_PY
        elif file_path.name == "pyproject.toml":
            return FileFormat.PYPROJECT_TOML
        elif file_path.suffix == ".in":
            return FileFormat.REQUIREMENTS_IN
        elif file_path.suffix == ".txt" or file_path.name.startswith("requirements"):
            return FileFormat.REQUIREMENTS_TXT

        # If unclear from name, examine content
        try:
            content = file_path.read_text(encoding="utf-8")
            return FormatDetector._detect_by_content(content)
        except (IOError, UnicodeDecodeError):
            return FileFormat.UNKNOWN

    @staticmethod
    def _detect_by_content(content: str) -> FileFormat:
        """Detect format by examining file content."""
        # Check for setup.py patterns
        if any(
            pattern in content
            for pattern in ["setup(", "from setuptools import", "install_requires"]
        ):
            return FileFormat.SETUP_PY

        # Check for pyproject.toml patterns
        if any(pattern in content for pattern in ["[build-system]", "[tool.", "[project]"]):
            return FileFormat.PYPROJECT_TOML

        # Check for pip-tools patterns (requirements.in)
        if any(pattern in content for pattern in ["-c ", "--constraint", "-e .", "# pip-compile"]):
            return FileFormat.REQUIREMENTS_IN

        # Default to requirements.txt for simple dependency lists
        return FileFormat.REQUIREMENTS_TXT


class UniversalParser:
    """Universal parser that can handle multiple dependency file formats."""

    def __init__(self) -> None:
        self.parsers = {
            FileFormat.REQUIREMENTS_IN: self._parse_requirements_file,
            FileFormat.REQUIREMENTS_TXT: self._parse_requirements_file,
            FileFormat.SETUP_PY: self._parse_setup_py,
            FileFormat.PYPROJECT_TOML: self._parse_pyproject_toml,
        }

    def parse_file(
        self, file_path: Union[str, Path], file_format: Optional[FileFormat] = None
    ) -> Dict[str, str]:
        """
        Parse a dependency file and extract package requirements.

        Args:
            file_path: Path to the file to parse
            file_format: Optional explicit format specification

        Returns:
            Dictionary mapping package names to version specifications
        """
        file_path = Path(file_path)

        if file_format is None:
            file_format = FormatDetector.detect_format(file_path)

        parser = self.parsers.get(file_format)
        if parser is None:
            raise ValueError(f"Unsupported file format: {file_format}")

        try:
            return parser(file_path)
        except Exception as e:
            raise ValueError(f"Failed to parse {file_path}: {e}")

    def _parse_requirements_file(self, file_path: Path) -> Dict[str, str]:
        """Parse requirements.txt or requirements.in files."""
        packages = {}

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")

        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Skip pip-tools directives and includes
            if any(line.startswith(prefix) for prefix in ["-r ", "-c ", "--", "-e "]):
                continue

            # Handle inline comments
            if "#" in line:
                line = line.split("#")[0].strip()

            try:
                # Parse as a requirement
                req = Requirement(line)
                packages[req.name] = str(req.specifier) if req.specifier else ""
            except Exception:
                # If parsing fails, try to extract just package name and version
                match = re.match(r"^([a-zA-Z0-9_.-]+)([><=!~]+.*)?", line)
                if match:
                    name = match.group(1)
                    version = match.group(2) or ""
                    packages[name] = version

        return packages

    def _parse_setup_py(self, file_path: Path) -> Dict[str, str]:
        """Parse setup.py files to extract install_requires."""
        packages = {}

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            # Find setup() calls
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "setup"
                ):

                    # Look for install_requires argument
                    for keyword in node.keywords:
                        if keyword.arg == "install_requires":
                            packages.update(self._extract_requirements_from_ast(keyword.value))

        except Exception as e:
            # Fallback to regex parsing if AST fails
            packages = self._parse_setup_py_fallback(file_path)

        return packages

    def _extract_requirements_from_ast(self, node: ast.AST) -> Dict[str, str]:
        """Extract requirements from an AST node (typically a list)."""
        packages = {}

        if isinstance(node, ast.List):
            for item in node.elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    req_str = item.value
                    try:
                        req = Requirement(req_str)
                        packages[req.name] = str(req.specifier) if req.specifier else ""
                    except Exception:
                        # Fallback parsing
                        match = re.match(r"^([a-zA-Z0-9_.-]+)([><=!~]+.*)?", req_str)
                        if match:
                            packages[match.group(1)] = match.group(2) or ""

        return packages

    def _parse_setup_py_fallback(self, file_path: Path) -> Dict[str, str]:
        """Fallback regex-based parsing for setup.py."""
        packages = {}
        content = file_path.read_text(encoding="utf-8")

        # Look for install_requires patterns
        patterns = [
            r"install_requires\s*=\s*\[(.*?)\]",
            r"install_requires\s*=\s*\((.*?)\)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                requires_content = match.group(1)
                # Extract quoted strings
                for req_match in re.finditer(r'["\']([^"\']+)["\']', requires_content):
                    req_str = req_match.group(1)
                    try:
                        req = Requirement(req_str)
                        packages[req.name] = str(req.specifier) if req.specifier else ""
                    except Exception:
                        match = re.match(r"^([a-zA-Z0-9_.-]+)([><=!~]+.*)?", req_str)
                        if match:
                            packages[match.group(1)] = match.group(2) or ""
                break

        return packages

    def _parse_pyproject_toml(self, file_path: Path) -> Dict[str, str]:
        """Parse pyproject.toml files."""
        packages = {}

        try:
            content = file_path.read_text(encoding="utf-8")
            data = tomllib.loads(content)

            # Check different locations for dependencies
            dependency_sources = [
                data.get("project", {}).get("dependencies", []),
                data.get("tool", {}).get("poetry", {}).get("dependencies", {}),
                data.get("build-system", {}).get("requires", []),
            ]

            for deps in dependency_sources:
                if isinstance(deps, list):
                    # Standard format: list of requirement strings
                    for dep in deps:
                        if isinstance(dep, str):
                            try:
                                req = Requirement(dep)
                                packages[req.name] = str(req.specifier) if req.specifier else ""
                            except Exception:
                                match = re.match(r"^([a-zA-Z0-9_.-]+)([><=!~]+.*)?", dep)
                                if match:
                                    packages[match.group(1)] = match.group(2) or ""

                elif isinstance(deps, dict):
                    # Poetry format: dict with package names as keys
                    for name, spec in deps.items():
                        if name == "python":  # Skip Python version requirement
                            continue
                        if isinstance(spec, str):
                            packages[name] = spec
                        elif isinstance(spec, dict) and "version" in spec:
                            packages[name] = spec["version"]
                        else:
                            packages[name] = ""

        except Exception as e:
            raise ValueError(f"Failed to parse pyproject.toml: {e}")

        return packages


class FileUpdater:
    """Update dependency files with new versions."""

    def __init__(self) -> None:
        self.updaters = {
            FileFormat.REQUIREMENTS_IN: self._update_requirements_file,
            FileFormat.REQUIREMENTS_TXT: self._update_requirements_file,
            FileFormat.SETUP_PY: self._update_setup_py,
            FileFormat.PYPROJECT_TOML: self._update_pyproject_toml,
        }

    def update_file(
        self,
        file_path: Union[str, Path],
        updates: Dict[str, str],
        file_format: Optional[FileFormat] = None,
    ) -> bool:
        """
        Update a dependency file with new versions.

        Args:
            file_path: Path to the file to update
            updates: Dictionary mapping package names to new versions
            file_format: Optional explicit format specification

        Returns:
            True if file was updated, False otherwise
        """
        file_path = Path(file_path)

        if file_format is None:
            file_format = FormatDetector.detect_format(file_path)

        updater = self.updaters.get(file_format)
        if updater is None:
            raise ValueError(f"Unsupported file format for updates: {file_format}")

        return updater(file_path, updates)

    def _update_requirements_file(self, file_path: Path, updates: Dict[str, str]) -> bool:
        """Update requirements.txt or requirements.in files."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file_path.read_text(encoding="latin-1")

        lines = content.splitlines()
        updated = False

        for i, line in enumerate(lines):
            original_line = line
            line = line.strip()

            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Handle inline comments
            comment = ""
            if "#" in line:
                line_parts = line.split("#", 1)
                line = line_parts[0].strip()
                comment = "#" + line_parts[1]

            try:
                req = Requirement(line)
                if req.name in updates:
                    new_version = updates[req.name]
                    if new_version.startswith((">=", ">", "==", "<=", "<", "~=", "!=")):
                        new_line = f"{req.name}{new_version}"
                    else:
                        new_line = f"{req.name}>={new_version}"

                    if comment:
                        new_line += f"  {comment}"

                    lines[i] = new_line
                    updated = True
            except Exception:
                # Fallback for simple package==version patterns
                match = re.match(r"^([a-zA-Z0-9_.-]+)([><=!~]+.*)?", line)
                if match and match.group(1) in updates:
                    name = match.group(1)
                    new_version = updates[name]
                    if new_version.startswith((">=", ">", "==", "<=", "<", "~=", "!=")):
                        new_line = f"{name}{new_version}"
                    else:
                        new_line = f"{name}>={new_version}"

                    if comment:
                        new_line += f"  {comment}"

                    lines[i] = new_line
                    updated = True

        if updated:
            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return updated

    def _update_setup_py(self, file_path: Path, updates: Dict[str, str]) -> bool:
        """Update setup.py files (basic implementation)."""
        # This is a simplified implementation
        # A full implementation would need to modify the AST
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        for package_name, new_version in updates.items():
            # Simple regex replacement (not perfect but functional)
            patterns = [
                rf'(["\']){package_name}([><=!~]+[^"\']*)?(["\'])',
                rf'(["\']){package_name}(["\'])',
            ]

            for i, pattern in enumerate(patterns):
                new_req = f"{package_name}>={new_version}"
                if i == 0:  # First pattern has 3 groups
                    replacement = rf"\g<1>{new_req}\g<3>"
                else:  # Second pattern has 2 groups
                    replacement = rf"\g<1>{new_req}\g<2>"
                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    break

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return True

        return False

    def _update_pyproject_toml(self, file_path: Path, updates: Dict[str, str]) -> bool:
        """Update pyproject.toml files (basic implementation)."""
        # This is a simplified implementation
        # A proper implementation would use a TOML library that preserves formatting
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        for package_name, new_version in updates.items():
            # Simple regex replacement for common patterns
            patterns = [
                rf'({package_name}\s*=\s*["\'])([^"\']*?)(["\'])',
                rf'(["\']){package_name}([><=!~]+[^"\']*)?(["\'])',
            ]

            for pattern in patterns:
                if not new_version.startswith((">=", ">", "==", "<=", "<", "~=", "!=")):
                    new_version = f">={new_version}"

                if pattern == patterns[0]:  # Key-value format
                    replacement = rf"\g<1>{new_version}\g<3>"
                else:  # List format
                    replacement = rf"\g<1>{package_name}{new_version}\g<3>"

                new_content = re.sub(pattern, replacement, content)
                if new_content != content:
                    content = new_content
                    break

        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return True

        return False
