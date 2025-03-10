# Pinjected Tools

This directory contains utility scripts for the Pinjected project.

## CI Monitoring Script

### Overview

The `wait_for_ci.py` script allows you to monitor GitHub CI workflow completion for the pinjected repository. It polls the GitHub API to check if CI workflows have completed for a specific branch, commit, or pull request.

### Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- Python 3.6+

### Usage

```bash
./wait_for_ci.py [--branch BRANCH | --commit COMMIT | --pr PR] [options]
```

#### Required Arguments (choose one)

- `--branch BRANCH`: Branch name to check CI status for
- `--commit COMMIT`: Commit SHA to check CI status for
- `--pr PR`: Pull request number to check CI status for

#### Optional Arguments

- `--workflow WORKFLOW`: Specific workflow name to check (default: all workflows)
- `--repo REPO`: Repository name in format 'owner/repo' (default: proboscis/pinjected)
- `--interval INTERVAL`: Polling interval in seconds (default: 30)
- `--timeout TIMEOUT`: Maximum time to wait in seconds (default: 1800, i.e., 30 minutes)
- `--verbose`: Enable verbose output
- `--exit-on-failure`: Exit immediately if any workflow fails

### Examples

Wait for CI to complete for a specific branch:
```bash
./wait_for_ci.py --branch main
```

Wait for CI to complete for a specific pull request:
```bash
./wait_for_ci.py --pr 42
```

Wait for a specific workflow to complete for the current commit:
```bash
./wait_for_ci.py --commit $(git rev-parse HEAD) --workflow tests
```

### Exit Codes

- `0`: All workflows completed successfully
- `1`: Some workflows failed or timed out
