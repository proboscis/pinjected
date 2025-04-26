"""
Main CLI module for pinjected-reviewer (v0.3.1).

This module provides command-line functionality for the pinjected-reviewer package:
- review: Run the code review process on staged git changes
- install: Install the git pre-commit hook
- uninstall: Remove the git pre-commit hook

When used as a pre-commit hook, it automatically checks staged changes against
the pinjected coding style guidelines and prevents commits that don't meet
the standards.
"""

# pinjected-reviewer: ignore
# we dont want this file to be reviewed as ordinal pinjected code, since this is for the CLI

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

from loguru import logger

from pinjected import IProxy
from pinjected_reviewer.schema.reviewer_def import ReviewResult, Reviewer


# We'll keep logging for the main CLI but filter noise
# The logger in entrypoint.py already handles filtering review process logs

async def run_pinjected(tgt: IProxy):
    # Run the review process
    from pinjected.helper_structure import MetaContext
    from pinjected_reviewer import entrypoint
    mc = await MetaContext.a_gather_bindings_with_legacy(Path(entrypoint.__file__))
    d = await mc.a_final_design
    from pinjected import AsyncResolver
    resolver = AsyncResolver(d)
    return await resolver.provide(tgt)


async def run_review():
    """
    Run a review of the staged git changes using pinjected.

    Uses MetaContext and AsyncResolver to provide the review_diff__pinjected_code_style
    instance, which performs the actual code review.

    Returns:
        bool: True if all changes are approved, False otherwise
    """
    # Completely disable all loguru logs
    logger.remove()  # Remove all handlers

    # Import after logger.remove() to avoid unnecessary log initialization
    from pinjected import AsyncResolver
    logger.remove()  # Remove all handlers
    from pinjected.helper_structure import MetaContext
    logger.remove()  # Remove all handlers
    from pinjected_reviewer import entrypoint
    logger.remove()  # Remove all handlers
    from pinjected_reviewer.schema.types import Review
    logger.remove()  # Remove all handlers
    from pinjected_reviewer.loader import pre_commit_reviews__phased
    reviews:list[ReviewResult] = await run_pinjected(pre_commit_reviews__phased)
    approved = all([r.result.approved for r in reviews])
    if approved:
        for i,review in enumerate(reviews):
            # Show approval messages
            msg =  f"================= BEGIN REVIEW({i}) =====================\n"
            msg += f"✓ Changes approved by {review.result.name}.\n"
            msg += f"Reviewed Target: {review.input}\n"
            msg += f"Reviewer Name: {review.result.name}\n"
            msg += f"{'-' * len(review.result.name)}\n\n{review.result.review_text}\n"
            msg += f"================= END REVIEW({i}) =====================\n"
            print(msg)
        print("✓ All changes approved.")
        return True
    else:
        for i,review in enumerate(reviews):
            if review.result.approved:
                continue
            # Show rejection messages
            msg =  f"================= BEGIN REVIEW({i}) =====================\n"
            msg += f"❌ Changes not approved by {review.result.name}.\n"
            msg += f"Reviewed Target: {review.input}\n"
            msg += f"Reviewer Name: {review.result.name}\n"
            msg += f"{'-' * len(review.result.name)}\n\n{review.result.review_text}\n"
            msg += f"================= END REVIEW({i}) =====================\n"
            print(msg,file=sys.stderr)
        return False


def install_hook():
    """
    Install the pinjected-reviewer git pre-commit hook.

    This function:
    1. Finds the git repository root
    2. Locates or creates the .git/hooks directory
    3. Creates a pre-commit hook script that runs pinjected_reviewer review
    4. Makes the hook executable
    5. Backs up any existing pre-commit hook

    Returns:
        bool: True if installation was successful, False otherwise
    """
    try:
        # Find git repo root
        git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        hooks_dir = Path(git_root) / ".git" / "hooks"
        pre_commit_path = hooks_dir / "pre-commit"

        # Ensure hooks directory exists
        hooks_dir.mkdir(exist_ok=True, parents=True)

        # Get the current Python executable path
        python_path = sys.executable

        # Create the pre-commit hook script
        script_content = f"""#!/bin/sh
# pinjected-reviewer pre-commit hook
{python_path} -m pinjected_reviewer review
"""
        # Check if pre-commit already exists
        if pre_commit_path.exists():
            with open(pre_commit_path, "r") as f:
                existing_content = f.read()
            if "pinjected-reviewer" in existing_content:
                logger.info("pre-commit hook with pinjected-reviewer already installed")
                return True

            # Backup existing hook
            backup_path = pre_commit_path.with_suffix(".backup")
            logger.info(f"Backing up existing pre-commit hook to {backup_path}")
            os.rename(pre_commit_path, backup_path)

        # Write new hook
        with open(pre_commit_path, "w") as f:
            f.write(script_content)

        # Make hook executable
        os.chmod(pre_commit_path, 0o755)
        logger.info(f"Installed pre-commit hook to {pre_commit_path}")
    except Exception as e:
        logger.error(f"Failed to install pre-commit hook: {e}")
        return False
    return True


def uninstall_hook():
    """
    Uninstall the pinjected-reviewer git pre-commit hook.

    This function:
    1. Finds the git repository root
    2. Checks if a pre-commit hook exists
    3. Verifies the hook contains pinjected-reviewer
    4. Restores any backup if available, otherwise removes the hook

    Returns:
        bool: True if uninstallation was successful, False otherwise
    """
    try:
        # Find git repo root
        git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        hooks_dir = Path(git_root) / ".git" / "hooks"
        pre_commit_path = hooks_dir / "pre-commit"

        if not pre_commit_path.exists():
            logger.info("No pre-commit hook found")
            return True

        with open(pre_commit_path, "r") as f:
            content = f.read()

        if "pinjected-reviewer" not in content:
            logger.info("Pre-commit hook doesn't contain pinjected-reviewer")
            return True

        # Check if there's a backup
        backup_path = pre_commit_path.with_suffix(".backup")
        if backup_path.exists():
            # Restore backup
            logger.info(f"Restoring backup from {backup_path}")
            os.rename(backup_path, pre_commit_path)
        else:
            # Just remove the hook
            logger.info(f"Removing pre-commit hook at {pre_commit_path}")
            os.unlink(pre_commit_path)

        logger.info("Successfully uninstalled pre-commit hook")
    except Exception as e:
        logger.error(f"Failed to uninstall pre-commit hook: {e}")
        return False
    return True


def main():
    """
    Main entrypoint for the pinjected-reviewer CLI.

    Parses command line arguments and executes the appropriate function:
    - review: Run the code review process
    - install: Install the git pre-commit hook
    - uninstall: Remove the git pre-commit hook

    If no command is specified, defaults to running the review process.

    Returns:
        None. Exits with code 1 if any operation fails.
    """
    parser = argparse.ArgumentParser(description="Pinjected Reviewer - Git pre-commit code reviewer")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Review command
    subparsers.add_parser("review", help="Review staged changes")

    # Install command
    subparsers.add_parser("install", help="Install git pre-commit hook")

    # Uninstall command
    subparsers.add_parser("uninstall", help="Uninstall git pre-commit hook")

    subparsers.add_parser("list-reviewers", help="List all reviewer definitions")

    args = parser.parse_args()

    if args.command == "review" or args.command is None:
        # Run review command or use it as default if no command specified
        success = asyncio.run(run_review())
        if not success:
            sys.exit(1)
    elif args.command == "install":
        success = install_hook()
        if not success:
            sys.exit(1)
    elif args.command == "uninstall":
        success = uninstall_hook()
        if not success:
            sys.exit(1)
    elif args.command == "list-reviewers":
        from pinjected_reviewer.loader import all_reviewers
        reviewers:list[Reviewer] = asyncio.run(run_pinjected(all_reviewers))
        print("Available reviewers:")
        for r in reviewers:
            print(f"- {r.name}: {type(r)}-{r.interests}")


if __name__ == '__main__':
    main()
