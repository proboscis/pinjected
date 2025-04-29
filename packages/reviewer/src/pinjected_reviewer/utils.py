import re
from pathlib import Path

from loguru import logger


def check_if_file_should_be_ignored(content: str, src_path: Path) -> bool:
    """
    Check if a file should be ignored by the pinjected-reviewer based on special comments.

    This looks for any of the following patterns:
    - "# pinjected-reviewer: ignore"
    - "# pinjected-reviewer:ignore"
    - "# pinjected-reviewer: skip"
    - "# pinjected-reviewer:skip"

    The comment can appear anywhere in the file.

    Args:
        content: The content of the file to check
        src_path: The path to the file (for logging purposes)

    Returns:
        bool: True if the file should be ignored, False otherwise
    """
    # Use regex to find any of the ignore patterns
    ignore_pattern = re.compile(
        r"#\s*pinjected-reviewer:\s*(ignore|skip)", re.IGNORECASE
    )

    if ignore_pattern.search(content):
        logger.info(
            f"Ignoring file {src_path} due to pinjected-reviewer ignore/skip comment"
        )
        return True

    return False
