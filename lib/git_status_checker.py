#!/usr/bin/env python3
"""Git repository status checking functionality."""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from datetime import datetime
import git
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

from .logger_config import get_logger

logger = get_logger("git_status_checker")


class RepoStatus(Enum):
    """Repository status types."""
    CLEAN = "clean"
    UNCOMMITTED = "uncommitted"
    UNTRACKED = "untracked"
    UNPUSHED = "unpushed"
    UPSTREAM_AVAILABLE = "upstream_available"
    ERROR = "error"
    NOT_A_REPO = "not_a_repo"
    MULTIPLE = "multiple"


class GitStatusChecker:
    """Check git repository status for various conditions."""
    
    # Status to CSS class mapping for Waybar
    STATUS_CLASSES = {
        RepoStatus.CLEAN: "clean",
        RepoStatus.UNCOMMITTED: "uncommitted",
        RepoStatus.UNTRACKED: "untracked",
        RepoStatus.UNPUSHED: "unpushed",
        RepoStatus.UPSTREAM_AVAILABLE: "upstream",
        RepoStatus.MULTIPLE: "multiple",
        RepoStatus.ERROR: "error",
        RepoStatus.NOT_A_REPO: "error"
    }
    
    # Status to icon mapping
    STATUS_ICONS = {
        RepoStatus.CLEAN: "✓",
        RepoStatus.UNCOMMITTED: "●",
        RepoStatus.UNTRACKED: "◉",
        RepoStatus.UNPUSHED: "↑",
        RepoStatus.UPSTREAM_AVAILABLE: "↓",
        RepoStatus.MULTIPLE: "⚠",
        RepoStatus.ERROR: "✗",
        RepoStatus.NOT_A_REPO: "✗"
    }
    
    def __init__(self, timeout: int = 5):
        """
        Initialize GitStatusChecker.
        
        Args:
            timeout: Timeout in seconds for remote operations
        """
        self.timeout = timeout
        self._ssh_agent_available = None
        self._gh_cli_available = None
    
    def validate_repository_path(self, repo_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a repository path before checking.
        
        Args:
            repo_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for empty or None path
        if not repo_path:
            return False, "Empty repository path"
        
        path = Path(repo_path)
        
        # Expand user home directory
        if repo_path.startswith("~"):
            path = Path(repo_path).expanduser()
        
        # Check if path exists
        if not path.exists():
            return False, f"Path does not exist: {repo_path}"
        
        # Check if it's a directory
        if not path.is_dir():
            return False, f"Path is not a directory: {repo_path}"
        
        # Check if it's a git repository
        git_dir = path / ".git"
        if not git_dir.exists():
            return False, f"Not a git repository (no .git directory): {repo_path}"
        
        return True, None
    
    def check_repository(self, repo_path: str) -> Dict[str, any]:
        """
        Check a single repository for all status conditions.
        
        Args:
            repo_path: Path to the git repository
            
        Returns:
            Dictionary containing status information with keys:
                - path: Repository path
                - name: Repository name (basename)
                - statuses: Set of RepoStatus values
                - priority_status: Highest priority status
                - error: Error message if any
                - details: Additional details (uncommitted count, etc.)
        """
        # Expand user home directory if present
        if repo_path and repo_path.startswith("~"):
            repo_path = str(Path(repo_path).expanduser())
        
        result = {
            "path": repo_path,
            "name": Path(repo_path).name if repo_path else "unknown",
            "statuses": set(),
            "priority_status": RepoStatus.CLEAN,
            "error": None,
            "details": {}
        }
        
        # Validate path first
        is_valid, error_msg = self.validate_repository_path(repo_path)
        if not is_valid:
            logger.warning(f"Invalid repository path: {error_msg}")
            result["statuses"].add(RepoStatus.ERROR if "not exist" in error_msg.lower() 
                                 else RepoStatus.NOT_A_REPO)
            result["priority_status"] = result["statuses"].pop()
            result["statuses"].add(result["priority_status"])
            result["error"] = error_msg
            return result
        
        # Try to open as git repository
        try:
            repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            logger.warning(f"Not a git repository: {repo_path}")
            result["statuses"].add(RepoStatus.NOT_A_REPO)
            result["priority_status"] = RepoStatus.NOT_A_REPO
            result["error"] = "Not a git repository"
            return result
        except Exception as e:
            logger.error(f"Error opening repository {repo_path}: {e}")
            result["statuses"].add(RepoStatus.ERROR)
            result["priority_status"] = RepoStatus.ERROR
            result["error"] = str(e)
            return result
        
        # Check various conditions
        try:
            # Check for uncommitted changes
            if self.check_uncommitted_changes(repo):
                result["statuses"].add(RepoStatus.UNCOMMITTED)
                # Count actual modified files more accurately
                status_output = repo.git.status('--porcelain')
                uncommitted_count = sum(1 for line in status_output.splitlines() 
                                      if line and line[:2] not in ["??", "!!"])
                result["details"]["uncommitted_count"] = uncommitted_count
            
            # Check for untracked files
            untracked = self.check_untracked_files(repo)
            if untracked:
                result["statuses"].add(RepoStatus.UNTRACKED)
                result["details"]["untracked_count"] = len(untracked)
            
            # Check for unpushed commits
            unpushed_count = self.check_unpushed_commits(repo)
            if unpushed_count > 0:
                result["statuses"].add(RepoStatus.UNPUSHED)
                result["details"]["unpushed_count"] = unpushed_count
            
            # Check for upstream changes (if remote exists)
            if repo.remotes:
                upstream_count = self.check_upstream_changes(repo)
                if upstream_count > 0:
                    result["statuses"].add(RepoStatus.UPSTREAM_AVAILABLE)
                    result["details"]["upstream_count"] = upstream_count
            
            # Determine priority status
            if result["statuses"]:
                result["priority_status"] = self.get_status_priority(list(result["statuses"]))
            else:
                result["priority_status"] = RepoStatus.CLEAN
                
        except Exception as e:
            logger.error(f"Error checking repository status for {repo_path}: {e}")
            result["statuses"].add(RepoStatus.ERROR)
            result["priority_status"] = RepoStatus.ERROR
            result["error"] = str(e)
        
        return result
    
    def check_uncommitted_changes(self, repo: Repo) -> bool:
        """
        Check if repository has uncommitted changes.
        
        Uses git status --porcelain for efficient detection of:
        - Modified files (staged or unstaged)
        - Deleted files (staged or unstaged)
        - Renamed files
        - Added files (staged)
        
        Args:
            repo: GitPython Repo object
            
        Returns:
            True if there are uncommitted changes
        """
        try:
            # Using git status --porcelain for efficiency
            # This gives us a machine-readable format
            git_cmd = repo.git
            status_output = git_cmd.status('--porcelain')
            
            if not status_output:
                return False
            
            # Parse the output to check for modified/staged files
            # Format: XY filename where X=staged, Y=unstaged
            # We're looking for any changes except untracked (which start with ??)
            for line in status_output.splitlines():
                if not line:
                    continue
                
                # First two characters indicate the status
                status_code = line[:2] if len(line) >= 2 else ""
                
                # ?? means untracked file - we handle those separately
                # !! means ignored file - we don't care about those
                if status_code not in ["??", "!!"]:
                    logger.debug(f"Found uncommitted change: {line}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking uncommitted changes: {e}")
            # In case of error, we conservatively report no changes
            # The error will be caught by the calling method
            return False
    
    def check_untracked_files(self, repo: Repo) -> List[str]:
        """
        Check if repository has untracked files.
        
        Args:
            repo: GitPython Repo object
            
        Returns:
            List of untracked file paths (empty if none)
        """
        try:
            # Using git status --porcelain for consistency
            git_cmd = repo.git
            status_output = git_cmd.status('--porcelain')
            
            if not status_output:
                return []
            
            untracked_files = []
            
            # Parse the output to find untracked files
            # Untracked files are marked with ?? at the beginning
            for line in status_output.splitlines():
                if not line:
                    continue
                
                # First two characters indicate the status
                status_code = line[:2] if len(line) >= 2 else ""
                
                # ?? means untracked file
                if status_code == "??":
                    # Extract filename (everything after the status code and space)
                    filename = line[3:] if len(line) > 3 else ""
                    if filename:
                        untracked_files.append(filename)
                        logger.debug(f"Found untracked file: {filename}")
            
            return untracked_files
            
        except Exception as e:
            logger.error(f"Error checking untracked files: {e}")
            # In case of error, return empty list
            return []
    
    def check_unpushed_commits(self, repo: Repo) -> int:
        """
        Check if repository has unpushed commits.
        
        Compares the local branch with its upstream tracking branch
        to find commits that exist locally but not on the remote.
        
        Args:
            repo: GitPython Repo object
            
        Returns:
            Number of unpushed commits
        """
        try:
            # Check if we have a HEAD (not in detached state)
            if repo.head.is_detached:
                logger.debug("Repository is in detached HEAD state")
                return 0
            
            # Get the current branch
            try:
                current_branch = repo.active_branch
            except TypeError:
                logger.debug("Could not determine active branch")
                return 0
            
            # Check if the branch has a tracking branch
            tracking_branch = current_branch.tracking_branch()
            if not tracking_branch:
                logger.debug(f"Branch '{current_branch.name}' has no tracking branch")
                # No tracking branch means we can't determine unpushed commits
                # Could be a local-only branch
                return 0
            
            # Count commits that are in local branch but not in tracking branch
            # Using git rev-list to count commits
            try:
                # Format: local_branch..remote_branch shows commits in local but not remote
                rev_list_cmd = f"{tracking_branch.name}..{current_branch.name}"
                commits = list(repo.iter_commits(rev_list_cmd))
                unpushed_count = len(commits)
                
                if unpushed_count > 0:
                    logger.debug(f"Found {unpushed_count} unpushed commits on branch '{current_branch.name}'")
                
                return unpushed_count
                
            except git.GitCommandError as e:
                logger.warning(f"Error counting unpushed commits: {e}")
                return 0
                
        except Exception as e:
            logger.error(f"Error checking unpushed commits: {e}")
            return 0
    
    def check_upstream_changes(self, repo: Repo) -> int:
        """
        Check if repository has upstream changes available.
        
        Performs a git fetch with timeout and then compares remote
        tracking branch with local branch to find new commits.
        
        Args:
            repo: GitPython Repo object
            
        Returns:
            Number of commits available from upstream
        """
        try:
            # Check if we have a HEAD (not in detached state)
            if repo.head.is_detached:
                logger.debug("Repository is in detached HEAD state")
                return 0
            
            # Get the current branch
            try:
                current_branch = repo.active_branch
            except TypeError:
                logger.debug("Could not determine active branch")
                return 0
            
            # Check if the branch has a tracking branch
            tracking_branch = current_branch.tracking_branch()
            if not tracking_branch:
                logger.debug(f"Branch '{current_branch.name}' has no tracking branch")
                return 0
            
            # Get the remote name from tracking branch
            remote_name = tracking_branch.remote_name
            
            # Check if remote uses GitHub and gh CLI is available
            remote_url = ""
            try:
                remote = repo.remote(remote_name)
                remote_url = next(remote.urls, "")
            except (ValueError, StopIteration):
                logger.warning(f"Could not get URL for remote '{remote_name}'")
            
            # Determine if we should try to fetch
            should_fetch = False
            fetch_method = None
            
            if "github.com" in remote_url:
                if self.gh_cli_available:
                    should_fetch = True
                    fetch_method = "gh"
                    logger.debug("Using GitHub CLI for fetch")
                elif self.ssh_agent_available:
                    should_fetch = True
                    fetch_method = "ssh"
                    logger.debug("Using SSH agent for fetch")
                else:
                    logger.info("No authentication available for GitHub remote")
            elif self.ssh_agent_available and ("git@" in remote_url or "ssh://" in remote_url):
                should_fetch = True
                fetch_method = "ssh"
                logger.debug("Using SSH agent for fetch")
            elif "http" in remote_url:
                # Try fetch for HTTP/HTTPS remotes (might have stored credentials)
                should_fetch = True
                fetch_method = "http"
                logger.debug("Attempting fetch for HTTP remote")
            
            # Perform fetch if we have authentication
            if should_fetch:
                try:
                    logger.debug(f"Fetching from remote '{remote_name}' using {fetch_method}")
                    
                    # Use subprocess for better timeout control
                    fetch_cmd = ["git", "-C", repo.working_dir, "fetch", remote_name]
                    
                    # For GitHub repos with gh CLI, we could potentially use gh api
                    # but git fetch should work with gh auth
                    
                    result = subprocess.run(
                        fetch_cmd,
                        capture_output=True,
                        timeout=self.timeout,
                        check=False
                    )
                    
                    if result.returncode != 0:
                        stderr = result.stderr.decode('utf-8', errors='ignore')
                        # Don't log authentication failures as errors
                        if "authentication" in stderr.lower() or "permission" in stderr.lower():
                            logger.debug(f"Authentication failed for fetch: {stderr}")
                        else:
                            logger.warning(f"Fetch failed: {stderr}")
                    else:
                        logger.debug("Fetch completed successfully")
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"Fetch timed out after {self.timeout} seconds")
                except Exception as e:
                    logger.warning(f"Error during fetch: {e}")
            
            # Count commits in tracking branch but not in local branch
            # This works whether or not the fetch succeeded
            try:
                # Format: local_branch..remote_branch shows commits in remote but not local
                rev_list_cmd = f"{current_branch.name}..{tracking_branch.name}"
                commits = list(repo.iter_commits(rev_list_cmd))
                upstream_count = len(commits)
                
                if upstream_count > 0:
                    logger.debug(f"Found {upstream_count} upstream commits available on branch '{current_branch.name}'")
                
                return upstream_count
                
            except git.GitCommandError as e:
                logger.warning(f"Error counting upstream commits: {e}")
                return 0
                
        except Exception as e:
            logger.error(f"Error checking upstream changes: {e}")
            return 0
    
    def get_status_priority(self, statuses: List[RepoStatus]) -> RepoStatus:
        """
        Determine the highest priority status from a list.
        
        Args:
            statuses: List of repository statuses
            
        Returns:
            Highest priority status
        """
        # Priority order (highest to lowest)
        priority_order = [
            RepoStatus.ERROR,
            RepoStatus.NOT_A_REPO,
            RepoStatus.UNCOMMITTED,
            RepoStatus.UNTRACKED,
            RepoStatus.UNPUSHED,
            RepoStatus.UPSTREAM_AVAILABLE,
            RepoStatus.CLEAN
        ]
        
        # If multiple statuses, return MULTIPLE unless there's an error
        if len(statuses) > 1:
            if RepoStatus.ERROR in statuses or RepoStatus.NOT_A_REPO in statuses:
                return RepoStatus.ERROR if RepoStatus.ERROR in statuses else RepoStatus.NOT_A_REPO
            return RepoStatus.MULTIPLE
        
        # Find highest priority status
        for status in priority_order:
            if status in statuses:
                return status
        
        return RepoStatus.CLEAN
    
    @property
    def ssh_agent_available(self) -> bool:
        """Check if SSH agent is available."""
        if self._ssh_agent_available is None:
            try:
                result = subprocess.run(
                    ["ssh-add", "-l"],
                    capture_output=True,
                    timeout=2,
                    check=False
                )
                # Exit code 0 or 1 means agent is available (0 = keys, 1 = no keys)
                self._ssh_agent_available = result.returncode in [0, 1]
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._ssh_agent_available = False
        return self._ssh_agent_available
    
    @property
    def gh_cli_available(self) -> bool:
        """Check if GitHub CLI is available and authenticated."""
        if self._gh_cli_available is None:
            try:
                result = subprocess.run(
                    ["gh", "auth", "status"],
                    capture_output=True,
                    timeout=2,
                    check=False
                )
                self._gh_cli_available = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self._gh_cli_available = False
        return self._gh_cli_available
    
    def get_status_class(self, status: RepoStatus) -> str:
        """
        Get CSS class for a given status.
        
        Args:
            status: Repository status
            
        Returns:
            CSS class name for Waybar styling
        """
        return self.STATUS_CLASSES.get(status, "unknown")
    
    def get_status_icon(self, status: RepoStatus) -> str:
        """
        Get icon for a given status.
        
        Args:
            status: Repository status
            
        Returns:
            Icon character for the status
        """
        return self.STATUS_ICONS.get(status, "?")
    
    def check_repositories(self, repo_paths: List[str]) -> List[Dict[str, any]]:
        """
        Check multiple repositories with error resilience.
        
        Args:
            repo_paths: List of repository paths
            
        Returns:
            List of status dictionaries for all repositories
        """
        results = []
        
        # Handle empty list
        if not repo_paths:
            logger.info("No repositories configured for monitoring")
            return results
        
        # Check each repository
        for repo_path in repo_paths:
            try:
                # Skip empty paths
                if not repo_path or not repo_path.strip():
                    logger.debug("Skipping empty repository path")
                    continue
                
                result = self.check_repository(repo_path.strip())
                results.append(result)
                
            except Exception as e:
                # Ensure we don't crash on unexpected errors
                logger.error(f"Unexpected error checking repository {repo_path}: {e}")
                results.append({
                    "path": repo_path,
                    "name": Path(repo_path).name if repo_path else "unknown",
                    "statuses": {RepoStatus.ERROR},
                    "priority_status": RepoStatus.ERROR,
                    "error": f"Unexpected error: {str(e)}",
                    "details": {}
                })
        
        return results
    
    def get_aggregate_status(self, repo_statuses: List[Dict[str, any]]) -> RepoStatus:
        """
        Get the overall status from multiple repository statuses.
        
        This determines what color/icon the main Waybar widget should show
        based on all monitored repositories.
        
        Args:
            repo_statuses: List of repository status dictionaries
            
        Returns:
            Overall status for the widget
        """
        if not repo_statuses:
            return RepoStatus.CLEAN
        
        # Collect all priority statuses
        all_statuses = [repo["priority_status"] for repo in repo_statuses]
        
        # Count repositories with issues
        repos_with_issues = sum(1 for status in all_statuses 
                               if status not in [RepoStatus.CLEAN])
        
        if repos_with_issues == 0:
            return RepoStatus.CLEAN
        elif repos_with_issues == 1:
            # Return the single issue status
            for status in all_statuses:
                if status != RepoStatus.CLEAN:
                    return status
        else:
            # Multiple repos with issues
            # Check if any have errors
            if RepoStatus.ERROR in all_statuses or RepoStatus.NOT_A_REPO in all_statuses:
                return RepoStatus.ERROR
            # Otherwise return MULTIPLE to indicate multiple repos need attention
            return RepoStatus.MULTIPLE
        
        return RepoStatus.CLEAN