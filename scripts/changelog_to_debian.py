#!/usr/bin/env python3
"""
Convert CHANGELOG.md to Debian changelog format for packaging.
"""
import re
from datetime import datetime
from pathlib import Path

# Paths
repo_root = Path(__file__).parent.parent
changelog_md = repo_root / "CHANGELOG.md"
debian_changelog = repo_root / "packaging/debian/changelog"

# Maintainer info (customize as needed)
MAINTAINER = "Adam Birds <adam.birds@adbwebdesigns.co.uk>"
DISTRIBUTION = "unstable"
URGENCY = "medium"

# Read CHANGELOG.md
with changelog_md.open(encoding="utf-8") as f:
    content = f.read()

# Find all version sections
version_re = re.compile(r"## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})", re.MULTILINE)
entries = version_re.findall(content)

# Split changelog by version
split_re = re.compile(r"## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})")
parts = split_re.split(content)

# Compose Debian changelog
output = []
for i in range(1, len(parts), 3):
    version, date = parts[i], parts[i+1]
    body = parts[i+2].strip()
    # Format body: remove markdown bullets and headers
    body_lines = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        body_lines.append(f"  * {line}")
    # Compose entry
    entry = f"pypi-package-updater ({version}-1) {DISTRIBUTION}; urgency={URGENCY}\n\n"
    entry += "\n".join(body_lines) + "\n\n"
    entry += f" -- {MAINTAINER}  {date} 00:00:00 +0000\n"
    output.append(entry)

# Write to debian/changelog
with debian_changelog.open("w", encoding="utf-8") as f:
    f.write("\n".join(output))
