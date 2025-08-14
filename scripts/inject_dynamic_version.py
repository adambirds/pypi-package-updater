#!/usr/bin/env python3
"""
Inject setuptools_scm version into the top entry of debian/changelog.
This script is used during CI builds to ensure the .deb filename reflects
the actual development version.
"""
import re
import sys
from pathlib import Path
from setuptools_scm import get_version


def inject_version():
    """Inject the setuptools_scm version into debian/changelog."""
    
    # Get the current setuptools_scm version
    try:
        raw_version = get_version()
        print(f"Got setuptools_scm version: {raw_version}")
        
        # Clean up the version by removing git hash and date parts
        # Convert "0.2.16.dev7+g50de744.d20250814" to "0.2.16.dev7"
        if '+' in raw_version:
            version = raw_version.split('+')[0]
            print(f"Cleaned version: {version}")
        else:
            version = raw_version
            
    except Exception as e:
        print(f"Error getting version: {e}")
        sys.exit(1)
    
    # Path to debian changelog
    changelog_path = Path("debian/changelog")
    if not changelog_path.exists():
        print("Error: debian/changelog not found")
        sys.exit(1)
    
    # Read current changelog
    with changelog_path.open('r') as f:
        content = f.read()
    
    # Replace the version in the first line
    # Pattern matches: package-name (version) distribution; urgency=level
    first_line_pattern = r'^([\w-]+) \(([\d\.]+(?:-\d+)?)\) (.+)$'
    lines = content.split('\n')
    
    if lines and re.match(first_line_pattern, lines[0]):
        # Replace the version in the first line
        lines[0] = re.sub(
            first_line_pattern,
            rf'\1 ({version}-1) \3',
            lines[0]
        )
        
        # Write back the modified changelog
        with changelog_path.open('w') as f:
            f.write('\n'.join(lines))
        
        print(f"Updated changelog with version: {version}")
        print(f"New first line: {lines[0]}")
    else:
        print("Error: Could not parse first line of changelog")
        sys.exit(1)


if __name__ == "__main__":
    inject_version()
