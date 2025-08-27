from pathlib import Path

from pinjected_reviewer.pytest_reviewer.coding_rule_plugin_impl import (
    check_if_file_should_be_ignored,
)


def test_check_if_file_should_be_ignored():
    # Test cases with comments that should be ignored
    assert check_if_file_should_be_ignored(
        "# pinjected-reviewer: ignore\ndef func():\n    pass", Path("test.py")
    )
    assert check_if_file_should_be_ignored(
        "def func():\n    # pinjected-reviewer:ignore\n    pass", Path("test.py")
    )
    assert check_if_file_should_be_ignored(
        "def func():\n    pass\n# pinjected-reviewer: skip", Path("test.py")
    )
    assert check_if_file_should_be_ignored(
        "def func():\n    pass\n#pinjected-reviewer:skip", Path("test.py")
    )
    assert check_if_file_should_be_ignored(
        "def func():\n    pass\n# PINJECTED-REVIEWER: IGNORE", Path("test.py")
    )

    # Test cases with comments that should not be ignored
    assert not check_if_file_should_be_ignored(
        "# pinjected-reviewer: do not ignore\ndef func():\n    pass", Path("test.py")
    )
    assert not check_if_file_should_be_ignored(
        "def func():\n    # Not an ignore comment\n    pass", Path("test.py")
    )
    assert not check_if_file_should_be_ignored(
        "def func():\n    pass\n# pinjected reviewer ignore", Path("test.py")
    )
    assert not check_if_file_should_be_ignored("", Path("test.py"))
