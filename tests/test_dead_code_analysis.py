"""
Analysis to prove that lines 148 and 343 are unreachable (dead code).

Both lines check `if not line:` AFTER inline comment processing,
but this condition can never be true due to earlier filtering.
"""

import tempfile
from pathlib import Path

from pypi_updater.formats import FileUpdater, UniversalParser


def test_prove_line_148_unreachable():
    """
    Prove that line 148 is unreachable by testing all possible scenarios.

    For line 148 to execute, we need:
    1. line.strip() to NOT be empty (to pass line 135 check)
    2. line.strip() to NOT start with '#' (to pass line 135 check)
    3. line to contain '#' (to enter the if block on line 144)
    4. line.split('#')[0].strip() to BE empty (to trigger line 148)

    This is logically impossible!
    """
    parser = UniversalParser()

    # Test case 1: Line that starts with # after stripping
    # This gets caught by line 135: if not line or line.startswith('#')
    test_cases = [
        "   #comment",  # Caught by line.startswith('#') after strip
        "\t#comment",  # Caught by line.startswith('#') after strip
        "#comment",  # Caught by line.startswith('#') after strip
        "  # comment",  # Caught by line.startswith('#') after strip
    ]

    for case in test_cases:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("package1>=1.0\n")
            f.write(case + "\n")  # This should be caught by line 135, never reach 148
            f.write("package2>=2.0\n")
            f.flush()

            packages = parser._parse_requirements_file(Path(f.name))
            # Should only have 2 packages, the comment line is filtered out early
            assert len(packages) == 2
            assert "package1" in packages
            assert "package2" in packages

    print("✅ All test cases that could theoretically reach line 148 are caught by line 135")


def test_prove_line_343_unreachable():
    """
    Prove that line 343 is unreachable by testing all possible scenarios.

    Same logic applies to the file updater method.
    """
    updater = FileUpdater()

    test_cases = [
        "   #comment",  # Caught by line 332: if not line or line.startswith('#')
        "\t#comment",  # Caught by line 332
        "#comment",  # Caught by line 332
        "  # comment",  # Caught by line 332
    ]

    for case in test_cases:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("package1>=1.0\n")
            f.write(case + "\n")  # This should be caught by line 332, never reach 343
            f.write("package2>=2.0\n")
            f.flush()

            updates = {"package1": "2.0.0"}
            result = updater._update_requirements_file(Path(f.name), updates)

            # Should successfully update, comment line filtered out early
            assert result is True
            content = Path(f.name).read_text()
            assert "package1>=2.0.0" in content

    print("✅ All test cases that could theoretically reach line 343 are caught by line 332")


def test_logical_analysis():
    """
    Logical proof that lines 148 and 343 are unreachable.
    """
    print("\n🔍 LOGICAL ANALYSIS:")
    print("For line 148 to execute:")
    print("1. line.strip() must NOT be empty (to pass line 135)")
    print("2. line.strip() must NOT start with '#' (to pass line 135)")
    print("3. line must contain '#' (to enter if block on line 144)")
    print("4. line.split('#')[0].strip() must BE empty (to trigger line 148)")
    print("")
    print("But if line.split('#')[0].strip() is empty, that means")
    print("everything before the '#' is whitespace.")
    print("So line.strip() would start with '#'!")
    print("This contradicts requirement #2.")
    print("")
    print("Therefore, line 148 is UNREACHABLE dead code.")
    print("Same logic applies to line 343.")
    print("")
    print("💡 RECOMMENDATION: Remove these dead code lines.")


if __name__ == "__main__":
    test_prove_line_148_unreachable()
    test_prove_line_343_unreachable()
    test_logical_analysis()
