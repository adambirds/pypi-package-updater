#!/usr/bin/env python3
"""
Command-line interface for the PyPI updater.
"""

import asyncio
import argparse
import sys
from pathlib import Path

from pypi_updater import PyPIUpdater


async def main():
    parser = argparse.ArgumentParser(
        description="Automatically update Python package versions in requirements files"
    )
    
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific requirements files to update (default: all .in files in requirements/)"
    )
    
    parser.add_argument(
        "--requirements-dir",
        default="requirements",
        help="Directory containing requirements files (default: requirements)"
    )
    
    parser.add_argument(
        "--tools-dir",
        default="tools",
        help="Directory containing the compilation script (default: tools)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    
    parser.add_argument(
        "--no-compile",
        action="store_true",
        help="Don't run the compilation script after updates"
    )
    
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Don't ask for confirmation before each update"
    )
    
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for available updates, don't perform any updates"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize updater
    updater = PyPIUpdater(
        requirements_dir=args.requirements_dir,
        tools_dir=args.tools_dir
    )
    
    try:
        if args.check_only:
            # Only check for updates
            print("Checking for available updates...")
            # Convert empty list to None to check all files
            files_to_check = args.files if args.files else None
            update_info = await updater.check_for_updates(files_to_check)
            
            total_updates = 0
            files_checked = 0
            
            for file_path, package_infos in update_info.items():
                if not package_infos:
                    # Skip files with no packages (like files that only contain -r includes)
                    continue
                    
                files_checked += 1
                updates_in_file = [pkg for pkg in package_infos if pkg.has_update]
                
                if updates_in_file:
                    print(f"\nUpdates available in {file_path}:")
                    for pkg in updates_in_file:
                        print(f"  {pkg.name}: {pkg.current_version} → {pkg.latest_version}")
                    total_updates += len(updates_in_file)
                else:
                    print(f"\nNo updates available in {file_path}")
            
            if files_checked == 0:
                print("\nNo packages found to check!")
            elif total_updates == 0:
                print("\nAll packages are up to date!")
            else:
                print(f"\nTotal packages with updates available: {total_updates}")
        
        else:
            # Perform updates
            print("Starting package update process...")
            # Convert empty list to None to check all files
            files_to_update = args.files if args.files else None
            summary = await updater.update_packages(
                files=files_to_update,
                dry_run=args.dry_run,
                auto_compile=not args.no_compile,
                interactive=not args.non_interactive
            )
            
            # Print summary
            updater.print_update_summary(summary)
            
            if summary.failed_packages > 0:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\nUpdate process cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
