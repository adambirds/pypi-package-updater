#!/usr/bin/env python3
"""
Linting and formatting script for the pypi-package-updater project.

This script runs all linting and formatting tools in a consistent manner.
It can be used both in CI and locally with optional auto-fixing.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_command(cmd: List[str], description: str, fix_mode: bool = False) -> Tuple[bool, str]:
    """
    Run a command and return success status and output.
    
    Args:
        cmd: Command to run as list of strings
        description: Human-readable description of the command
        fix_mode: Whether we're in fix mode (affects output styling)
        
    Returns:
        Tuple of (success, output)
    """
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
        if result.returncode == 0:
            print(f"✅ {description} passed!")
            return True, result.stdout
        else:
            print(f"❌ {description} failed!")
            return False, result.stderr
            
    except Exception as e:
        print(f"💥 Error running {description}: {e}")
        return False, str(e)


def main():
    """Main entry point for the linting script."""
    parser = argparse.ArgumentParser(
        description="Run linting and formatting tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/lint.py                 # Run all linters (check mode)
  python scripts/lint.py --fix           # Run with auto-fixing enabled
  python scripts/lint.py --tool black    # Run only black
  python scripts/lint.py --tool mypy     # Run only mypy
        """
    )
    
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Run tools in fix mode (auto-format/fix issues where possible)"
    )
    
    parser.add_argument(
        "--tool",
        choices=["black", "isort", "mypy", "all"],
        default="all",
        help="Run specific tool only (default: all)"
    )
    
    args = parser.parse_args()
    
    # Define source directories
    source_dirs = ["pypi_updater", "tests", "update_packages.py"]
    
    # Results tracking
    results = []
    
    print("🚀 Python Package Updater - Linting & Formatting")
    print(f"Mode: {'🔧 Fix' if args.fix else '🔍 Check'}")
    print(f"Tool: {args.tool}")
    
    # Black - Python code formatter
    if args.tool in ["black", "all"]:
        black_cmd = ["python", "-m", "black"]
        if not args.fix:
            black_cmd.append("--check")
        black_cmd.extend(source_dirs)
        
        success, output = run_command(
            black_cmd,
            "Black (code formatting)",
            args.fix
        )
        results.append(("Black", success))
    
    # isort - Import sorting
    if args.tool in ["isort", "all"]:
        isort_cmd = ["python", "-m", "isort"]
        if not args.fix:
            isort_cmd.append("--check-only")
        isort_cmd.extend(source_dirs)
        
        success, output = run_command(
            isort_cmd,
            "isort (import sorting)",
            args.fix
        )
        results.append(("isort", success))
    
    # mypy - Static type checking
    if args.tool in ["mypy", "all"]:
        mypy_cmd = ["python", "-m", "mypy", "pypi_updater"]
        
        success, output = run_command(
            mypy_cmd,
            "mypy (static type checking)",
            False  # mypy doesn't have a fix mode
        )
        results.append(("mypy", success))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for tool, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{tool:10} {status}")
        if not success:
            all_passed = False
    
    print(f"\n{'🎉 All checks passed!' if all_passed else '💥 Some checks failed!'}")
    
    if not all_passed:
        if not args.fix:
            print("\n💡 Tip: Run with --fix to automatically fix formatting issues")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
