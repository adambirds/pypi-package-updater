#!/usr/bin/env python3
"""
Script to generate Homebrew formula resources for all dependencies.
This script recursively discovers all transitive dependencies and generates
the resource blocks needed for the Homebrew formula.
"""

import json
import urllib.request
import urllib.parse
from collections import defaultdict, deque
import sys


def get_package_info(package_name, version=None):
    """Get package information from PyPI API."""
    if version:
        url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    else:
        url = f"https://pypi.org/pypi/{package_name}/json"
    
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Error fetching {package_name}: {e}")
        return None


def parse_requirement(req_string):
    """Parse a requirement string to extract package name and version constraints."""
    # Remove spaces and handle basic version specifiers
    req = req_string.strip()
    
    # Skip conditional requirements (those with semicolons)
    if ';' in req:
        return None, None
    
    # Skip extra requirements
    if 'extra ==' in req:
        return None, None
    
    # Clean up the requirement string - remove version constraints
    import re
    # Match package name at the start, followed by optional version constraints
    match = re.match(r'^([a-zA-Z0-9_-]+)', req)
    if match:
        pkg_name = match.group(1)
        return pkg_name, None
    
    return req.strip(), None


def get_dependencies(package_name, version=None):
    """Get direct dependencies for a package."""
    data = get_package_info(package_name, version)
    if not data:
        return []
    
    requires_dist = data['info'].get('requires_dist', [])
    deps = []
    
    for req in requires_dist or []:
        pkg_name, pkg_version = parse_requirement(req)
        if pkg_name and pkg_name != package_name:
            deps.append((pkg_name, pkg_version))
    
    return deps


def get_all_dependencies(root_packages):
    """Get all transitive dependencies for a set of root packages."""
    all_deps = {}
    visited = set()
    queue = deque()
    
    # Add root packages to queue
    for pkg_name, pkg_version in root_packages:
        queue.append((pkg_name, pkg_version, 0))  # (name, version, depth)
    
    while queue:
        pkg_name, pkg_version, depth = queue.popleft()
        
        if pkg_name in visited:
            continue
        
        visited.add(pkg_name)
        print(f"{'  ' * depth}Processing: {pkg_name}", file=sys.stderr)
        
        # Get package info
        data = get_package_info(pkg_name, pkg_version)
        if not data:
            continue
        
        # Use specified version or latest
        if not pkg_version:
            pkg_version = data['info']['version']
        
        # Store package info
        all_deps[pkg_name] = {
            'version': pkg_version,
            'data': data
        }
        
        # Get dependencies and add to queue
        deps = get_dependencies(pkg_name, pkg_version)
        for dep_name, dep_version in deps:
            if dep_name not in visited:
                queue.append((dep_name, dep_version, depth + 1))
    
    return all_deps


def get_source_distribution(package_data):
    """Get the source distribution URL and SHA256 for a package."""
    urls = package_data.get('urls', [])
    
    for file_info in urls:
        if file_info['filename'].endswith('.tar.gz') and file_info['packagetype'] == 'sdist':
            return file_info['url'], file_info['digests']['sha256']
    
    # Fallback: look for any .tar.gz file
    for file_info in urls:
        if file_info['filename'].endswith('.tar.gz'):
            return file_info['url'], file_info['digests']['sha256']
    
    return None, None


def generate_homebrew_resources(all_deps, exclude_packages=None):
    """Generate Homebrew resource blocks for all dependencies."""
    exclude_packages = exclude_packages or set()
    
    resources = []
    
    for pkg_name in sorted(all_deps.keys()):
        if pkg_name in exclude_packages:
            continue
        
        pkg_info = all_deps[pkg_name]
        url, sha256 = get_source_distribution(pkg_info['data'])
        
        if not url or not sha256:
            print(f"Warning: Could not find source distribution for {pkg_name}", file=sys.stderr)
            continue
        
        resource_block = f'''  resource "{pkg_name}" do
    url "{url}"
    sha256 "{sha256}"
  end'''
        
        resources.append(resource_block)
    
    return '\n\n'.join(resources)


def main():
    # Read direct dependencies from requirements/common.in
    try:
        with open('requirements/common.in', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: requirements/common.in not found. Run this script from the project root.")
        sys.exit(1)
    
    # Parse direct dependencies
    root_packages = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            pkg_name, pkg_version = parse_requirement(line)
            if pkg_name:
                root_packages.append((pkg_name, pkg_version))
    
    print(f"Root packages: {root_packages}", file=sys.stderr)
    
    # Get all transitive dependencies
    print("Discovering all dependencies...", file=sys.stderr)
    all_deps = get_all_dependencies(root_packages)
    
    print(f"\nFound {len(all_deps)} total packages:", file=sys.stderr)
    for pkg in sorted(all_deps.keys()):
        print(f"  - {pkg} ({all_deps[pkg]['version']})", file=sys.stderr)
    
    # Generate Homebrew resources
    print("\nGenerating Homebrew resources...", file=sys.stderr)
    resources = generate_homebrew_resources(all_deps)
    
    print("\n" + "="*60)
    print("# Add these resource blocks to your Homebrew formula:")
    print("="*60)
    print(resources)
    print("="*60)


if __name__ == '__main__':
    main()
