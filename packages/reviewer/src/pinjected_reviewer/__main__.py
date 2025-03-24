"""
Main CLI module for pinjected-reviewer.

This module provides command-line functionality for the pinjected-reviewer package.
"""

import fire
import loguru


def main():
    """
    Main entrypoint for the pinjected-reviewer CLI.
    """
    logger = loguru.logger
    logger.info("Starting pinjected-reviewer CLI")
    
    fire.Fire(dict(
        # Add CLI commands here
        version=lambda: "0.1.0"
    ))


if __name__ == '__main__':
    main()
