#!/usr/bin/env python3
"""
Stop hook script that runs tests and provides JSON feedback.
Handles large output gracefully by using stdin/stdout instead of command-line args.
"""

import json
import subprocess
import sys
import os


def main():
    """Run tests and return JSON decision based on results."""
    try:
        # Run make test and capture output
        result = subprocess.run(
            ["make", "test"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )

        # Combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr

        if result.returncode != 0:
            # Tests failed - block the stop
            # Truncate output if it's too long to prevent UI issues
            max_output_length = 10000  # Adjust as needed
            if len(output) > max_output_length:
                # Keep the last part of the output which usually has the summary
                output = f"...(truncated)...\n{output[-(max_output_length - 20) :]}"

            response = {"decision": "block", "reason": f"Tests failed:\n{output}"}
        else:
            # Tests passed - allow stop
            response = {"decision": "approve"}

        # Print JSON response
        print(json.dumps(response))
        sys.exit(0)

    except FileNotFoundError:
        # make command not found
        response = {
            "decision": "block",
            "reason": "Could not find 'make' command. Please ensure it's installed.",
        }
        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # Other errors - don't block but report
        response = {
            "decision": "approve",
            "reason": f"Hook error (not blocking): {e!s}",
        }
        print(json.dumps(response))
        sys.exit(1)  # Non-blocking error


if __name__ == "__main__":
    main()
