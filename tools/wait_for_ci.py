#!/usr/bin/env python3
"""
Script to monitor GitHub CI workflow completion for pinjected repository.
This script polls the GitHub API to check if CI workflows have completed for a specific
branch, commit, or pull request.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Wait for GitHub CI workflows to complete."
    )
    
    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--branch", 
        help="Branch name to check CI status for"
    )
    group.add_argument(
        "--commit", 
        help="Commit SHA to check CI status for"
    )
    group.add_argument(
        "--pr", 
        type=int, 
        help="Pull request number to check CI status for"
    )
    
    # Optional arguments
    parser.add_argument(
        "--workflow", 
        help="Specific workflow name to check (default: all workflows)",
        default=None
    )
    parser.add_argument(
        "--repo", 
        help="Repository name in format 'owner/repo' (default: proboscis/pinjected)",
        default="proboscis/pinjected"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        help="Polling interval in seconds (default: 30)",
        default=30
    )
    parser.add_argument(
        "--timeout", 
        type=int, 
        help="Maximum time to wait in seconds (default: 1800, i.e., 30 minutes)",
        default=1800
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    parser.add_argument(
        "--exit-on-failure", 
        action="store_true", 
        help="Exit immediately if any workflow fails"
    )
    
    return parser.parse_args()


def run_gh_command(cmd: List[str]) -> Tuple[bool, Union[Dict, List, str]]:
    """
    Run a GitHub CLI command and return the parsed JSON output.
    
    Args:
        cmd: List of command parts to execute
        
    Returns:
        Tuple of (success, result) where result is parsed JSON or error message
    """
    try:
        # Run the command and capture output
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Parse JSON output if it's not empty
        if result.stdout.strip():
            return True, json.loads(result.stdout)
        else:
            return False, "Empty response from GitHub API"
    except subprocess.CalledProcessError as e:
        return False, f"Command failed: {e.stderr}"
    except json.JSONDecodeError as e:
        return False, f"Failed to parse JSON output: {e} - Raw output: {result.stdout[:100]}..."
    except Exception as e:
        return False, f"Error: {str(e)}"


def get_pr_head_sha(repo: str, pr_number: int) -> Tuple[bool, Union[str, Dict]]:
    """
    Get the HEAD SHA for a pull request.
    
    Args:
        repo: Repository name in format 'owner/repo'
        pr_number: Pull request number
        
    Returns:
        Tuple of (success, result) where result is the HEAD SHA or error message
    """
    cmd = ["gh", "api", f"repos/{repo}/pulls/{pr_number}"]
    success, result = run_gh_command(cmd)
    
    if not success:
        return False, result
    
    try:
        return True, result["head"]["sha"]
    except KeyError:
        return False, "Could not find HEAD SHA in pull request data"


def get_workflow_runs(
    repo: str, 
    branch: Optional[str] = None, 
    commit: Optional[str] = None, 
    pr: Optional[int] = None,
    workflow: Optional[str] = None
) -> Tuple[bool, Union[List[Dict], str]]:
    """
    Get workflow runs for a specific branch, commit, or PR.
    
    Args:
        repo: Repository name in format 'owner/repo'
        branch: Branch name to filter by
        commit: Commit SHA to filter by
        pr: Pull request number to filter by
        workflow: Specific workflow name to filter by
        
    Returns:
        Tuple of (success, result) where result is list of workflow runs or error message
    """
    # If PR is provided, get the HEAD SHA
    if pr and not commit:
        success, pr_sha = get_pr_head_sha(repo, pr)
        if not success:
            return False, pr_sha
        commit = pr_sha
    
    # Build the API endpoint
    endpoint = f"repos/{repo}/actions/runs"
    
    # Add query parameters
    params = []
    if branch:
        params.append(f"branch={branch}")
    if commit:
        params.append(f"head_sha={commit}")
    
    # Add parameters to the endpoint
    if params:
        endpoint += "?" + "&".join(params)
    
    # Get workflow runs
    cmd = ["gh", "api", endpoint]
    success, result = run_gh_command(cmd)
    
    if not success:
        return False, result
    
    # Extract workflow runs
    try:
        workflow_runs = result.get("workflow_runs", [])
    except (AttributeError, KeyError):
        return False, "Could not find workflow runs in API response"
    
    # Filter by workflow name if provided
    if workflow and workflow_runs:
        filtered_runs = []
        for run in workflow_runs:
            if (workflow.lower() in run.get("name", "").lower() or 
                workflow.lower() in run.get("path", "").lower()):
                filtered_runs.append(run)
        workflow_runs = filtered_runs
    
    return True, workflow_runs


def format_duration(seconds: int) -> str:
    """Format duration in seconds to a human-readable string."""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def print_workflow_status(runs: List[Dict], verbose: bool = False) -> None:
    """
    Print the status of workflow runs.
    
    Args:
        runs: List of workflow run data
        verbose: Whether to print detailed information
    """
    if not runs:
        print("No workflow runs found.")
        return
    
    print("\nWorkflow Status:")
    print("=" * 80)
    
    for run in runs:
        status = run.get("status", "unknown")
        conclusion = run.get("conclusion")
        
        # Determine status indicator
        if status == "completed":
            if conclusion == "success":
                status_indicator = "✅"
            elif conclusion == "failure":
                status_indicator = "❌"
            elif conclusion == "cancelled":
                status_indicator = "⚠️"
            else:
                status_indicator = "⚠️"
        elif status == "in_progress":
            status_indicator = "🔄"
        elif status == "queued":
            status_indicator = "⏳"
        else:
            status_indicator = "❓"
        
        # Format created and updated times
        try:
            created_at = datetime.strptime(run.get("created_at", ""), "%Y-%m-%dT%H:%M:%SZ")
            updated_at = datetime.strptime(run.get("updated_at", ""), "%Y-%m-%dT%H:%M:%SZ")
            
            # Calculate duration
            if status == "completed":
                duration = format_duration(int((updated_at - created_at).total_seconds()))
            else:
                duration = format_duration(int((datetime.utcnow() - created_at).total_seconds()))
        except (ValueError, TypeError):
            duration = "unknown"
        
        # Print basic information
        print(f"{status_indicator} {run.get('name', 'Unknown')} (#{run.get('run_number', '?')})")
        print(f"   Status: {status.capitalize()}")
        if conclusion:
            print(f"   Conclusion: {conclusion.capitalize()}")
        print(f"   Branch: {run.get('head_branch', 'Unknown')}")
        print(f"   Commit: {run.get('head_sha', 'Unknown')[:7]}")
        print(f"   Duration: {duration}")
        print(f"   URL: {run.get('html_url', 'Unknown')}")
        
        # Print additional information if verbose
        if verbose:
            if isinstance(created_at, datetime):
                print(f"   Created: {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            if isinstance(updated_at, datetime):
                print(f"   Updated: {updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"   Run ID: {run.get('id', 'Unknown')}")
            if run.get("jobs_url"):
                print(f"   Jobs URL: {run.get('jobs_url')}")
        
        print("-" * 80)


def check_workflows_complete(runs: List[Dict]) -> Tuple[bool, bool]:
    """
    Check if all workflows are complete and successful.
    
    Args:
        runs: List of workflow run data
        
    Returns:
        Tuple of (all_complete, all_successful)
    """
    if not runs:
        return True, True
    
    all_complete = all(run.get("status") == "completed" for run in runs)
    all_successful = all(
        run.get("status") == "completed" and run.get("conclusion") == "success" 
        for run in runs
    )
    
    return all_complete, all_successful


def main() -> int:
    """Main function to wait for CI completion."""
    args = parse_arguments()
    
    # Check if GitHub CLI is installed
    try:
        subprocess.run(
            ["gh", "--version"], 
            capture_output=True, 
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: GitHub CLI (gh) is not installed or not in PATH.")
        print("Please install it from https://cli.github.com/")
        return 1
    
    # Check if authenticated with GitHub
    try:
        subprocess.run(
            ["gh", "auth", "status"], 
            capture_output=True, 
            check=True
        )
    except subprocess.CalledProcessError:
        print("Error: Not authenticated with GitHub.")
        print("Please run 'gh auth login' first.")
        return 1
    
    print(f"Waiting for CI workflows to complete for {args.repo}...")
    if args.branch:
        print(f"Branch: {args.branch}")
    elif args.commit:
        print(f"Commit: {args.commit}")
    elif args.pr:
        print(f"Pull Request: #{args.pr}")
    
    if args.workflow:
        print(f"Workflow: {args.workflow}")
    
    start_time = time.time()
    timeout_time = start_time + args.timeout
    
    while time.time() < timeout_time:
        # Get workflow runs
        success, runs = get_workflow_runs(
            repo=args.repo,
            branch=args.branch,
            commit=args.commit,
            pr=args.pr,
            workflow=args.workflow
        )
        
        if not success:
            print(f"Error: {runs}")
            return 1
        
        # Print current status
        print_workflow_status(runs, args.verbose)
        
        # Check if all workflows are complete
        all_complete, all_successful = check_workflows_complete(runs)
        
        if all_complete:
            if all_successful:
                print("\n✅ All workflows completed successfully!")
                return 0
            else:
                print("\n❌ Some workflows failed!")
                return 1
        
        # Check for failures if exit-on-failure is enabled
        if args.exit_on_failure:
            failed_runs = [
                run for run in runs 
                if run.get("status") == "completed" and run.get("conclusion") != "success"
            ]
            if failed_runs:
                print("\n❌ Some workflows failed! Exiting early due to --exit-on-failure.")
                return 1
        
        # Wait before checking again
        elapsed = time.time() - start_time
        remaining = args.timeout - elapsed
        
        if remaining <= 0:
            break
            
        print(f"\nWaiting {args.interval}s before checking again... "
              f"(Timeout in {format_duration(int(remaining))})")
        time.sleep(min(args.interval, remaining))
    
    print(f"\n⏰ Timed out after waiting {format_duration(args.timeout)}!")
    print("CI workflows did not complete within the specified timeout.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
