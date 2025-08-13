"""
Parser for requirements.in files.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """Represents a single requirement from a .in file."""

    name: str
    version: Optional[str] = None
    operator: str = "=="
    line_number: int = 0
    original_line: str = ""
    is_comment: bool = False
    is_include: bool = False
    include_path: Optional[str] = None


class RequirementsParser:
    """Parser for requirements.in files."""

    # Regex patterns for parsing requirements
    REQUIREMENT_PATTERN = re.compile(
        r"^(?P<name>[a-zA-Z0-9._-]+)(?P<extras>\[[^\]]*\])?(?P<operator>[<>=!~]+)(?P<version>[^\s#]+)?\s*(?:#.*)?$"
    )
    INCLUDE_PATTERN = re.compile(r"^-r\s+(.+)$")
    COMMENT_PATTERN = re.compile(r"^\s*#")

    def __init__(self, requirements_dir: str = "requirements"):
        self.requirements_dir = Path(requirements_dir)

    def parse_file(self, file_path: str) -> List[Requirement]:
        """Parse a single requirements file."""
        file_path_obj = Path(file_path)
        requirements: List[Requirement] = []

        if not file_path_obj.exists():
            logger.error(f"Requirements file not found: {file_path_obj}")
            return requirements

        try:
            with open(file_path_obj, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Error reading file {file_path_obj}: {e}")
            return requirements

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Check for comments
            if self.COMMENT_PATTERN.match(line):
                req = Requirement(
                    name="", line_number=line_num, original_line=line, is_comment=True
                )
                requirements.append(req)
                continue

            # Check for includes (-r other_file.in)
            include_match = self.INCLUDE_PATTERN.match(line)
            if include_match:
                include_path = include_match.group(1)
                req = Requirement(
                    name="",
                    line_number=line_num,
                    original_line=line,
                    is_include=True,
                    include_path=include_path,
                )
                requirements.append(req)
                continue

            # Parse actual requirements
            req_match = self.REQUIREMENT_PATTERN.match(line)
            if req_match:
                name = req_match.group("name")
                operator = req_match.group("operator") or "=="
                version = req_match.group("version")

                req = Requirement(
                    name=name,
                    version=version,
                    operator=operator,
                    line_number=line_num,
                    original_line=line,
                )
                requirements.append(req)
            else:
                # Handle lines that don't match any pattern
                logger.warning(f"Could not parse line {line_num} in {file_path}: {line}")
                req = Requirement(
                    name="",
                    line_number=line_num,
                    original_line=line,
                    is_comment=True,  # Treat as comment to preserve
                )
                requirements.append(req)

        return requirements

    def get_package_requirements(self, file_path: str) -> List[Tuple[str, str]]:
        """
        Extract package names and versions from a requirements file.

        Returns:
            List of (package_name, version) tuples
        """
        requirements = self.parse_file(file_path)
        packages = []

        for req in requirements:
            if not req.is_comment and not req.is_include and req.name and req.version:
                packages.append((req.name, req.version))

        return packages

    def find_all_requirements_files(self) -> List[Path]:
        """Find all .in files in the requirements directory."""
        if not self.requirements_dir.exists():
            logger.error(f"Requirements directory not found: {self.requirements_dir}")
            return []

        return list(self.requirements_dir.glob("*.in"))

    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """
        Build a dependency graph based on -r includes.

        Returns:
            Dictionary mapping file names to their dependencies
        """
        graph = {}

        for file_path in self.find_all_requirements_files():
            file_name = file_path.name
            dependencies = set()

            requirements = self.parse_file(str(file_path))
            for req in requirements:
                if req.is_include and req.include_path:
                    # Normalize the include path
                    include_name = Path(req.include_path).name
                    if not include_name.endswith(".in"):
                        include_name += ".in"
                    dependencies.add(include_name)

            graph[file_name] = dependencies

        return graph

    def get_update_order(self) -> List[str]:
        """
        Get the order in which files should be updated based on dependencies.
        Files with no dependencies should be updated first.
        """
        graph = self.get_dependency_graph()

        # Simple topological sort
        visited = set()
        temp_visited = set()
        order = []

        def visit(node: str) -> None:
            if node in temp_visited:
                # Circular dependency detected
                logger.warning(f"Circular dependency detected involving {node}")
                return
            if node in visited:
                return

            temp_visited.add(node)

            # Visit dependencies first
            for dependency in graph.get(node, set()):
                if dependency in graph:  # Only visit if the dependency file exists
                    visit(dependency)

            temp_visited.remove(node)
            visited.add(node)
            order.append(node)

        # Visit all nodes
        for file_name in graph.keys():
            if file_name not in visited:
                visit(file_name)

        return order

    def update_requirement_version(
        self, file_path: str, package_name: str, new_version: str
    ) -> bool:
        """
        Update a specific package version in a requirements file.

        Args:
            file_path: Path to the requirements file
            package_name: Name of the package to update
            new_version: New version to set

        Returns:
            True if the update was successful, False otherwise
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            logger.error(f"Requirements file not found: {file_path_obj}")
            return False

        requirements = self.parse_file(file_path)
        updated = False

        # Find and update the requirement
        for req in requirements:
            if (
                req.name.lower() == package_name.lower()
                and not req.is_comment
                and not req.is_include
            ):
                # Update the requirement
                new_line = f"{req.name}{req.operator}{new_version}"

                # Preserve any comments from the original line
                if "#" in req.original_line:
                    comment_part = req.original_line.split("#", 1)[1]
                    new_line += f"  # {comment_part}"

                req.original_line = new_line
                updated = True
                break

        if not updated:
            logger.warning(f"Package '{package_name}' not found in {file_path}")
            return False

        # Write the updated file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for req in requirements:
                    f.write(req.original_line + "\n")

            logger.info(f"Updated {package_name} to {new_version} in {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error writing to file {file_path}: {e}")
            return False
