#!/usr/bin/env python3
"""Tests for git_status_checker module."""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import git
from git import Repo

from lib.git_status_checker import GitStatusChecker, RepoStatus


class TestGitStatusChecker:
    """Test GitStatusChecker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = GitStatusChecker()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test GitStatusChecker initialization."""
        checker = GitStatusChecker(timeout=10)
        assert checker.timeout == 10
        assert checker._ssh_agent_available is None
        assert checker._gh_cli_available is None
    
    def test_validate_repository_path_empty(self):
        """Test validation with empty path."""
        is_valid, error = self.checker.validate_repository_path("")
        assert not is_valid
        assert "Empty repository path" in error
    
    def test_validate_repository_path_nonexistent(self):
        """Test validation with non-existent path."""
        is_valid, error = self.checker.validate_repository_path("/nonexistent/path")
        assert not is_valid
        assert "Path does not exist" in error
    
    def test_validate_repository_path_not_directory(self):
        """Test validation with file instead of directory."""
        # Create a file
        test_file = Path(self.temp_dir) / "testfile.txt"
        test_file.write_text("test")
        
        is_valid, error = self.checker.validate_repository_path(str(test_file))
        assert not is_valid
        assert "not a directory" in error
    
    def test_validate_repository_path_not_git(self):
        """Test validation with directory that's not a git repo."""
        is_valid, error = self.checker.validate_repository_path(self.temp_dir)
        assert not is_valid
        assert "Not a git repository" in error
    
    def test_validate_repository_path_valid(self):
        """Test validation with valid git repository."""
        # Create a git repository
        repo = Repo.init(self.temp_dir)
        
        is_valid, error = self.checker.validate_repository_path(self.temp_dir)
        assert is_valid
        assert error is None
    
    def test_check_repository_invalid_path(self):
        """Test checking non-existent repository path."""
        result = self.checker.check_repository("/nonexistent/path")
        
        assert result["path"] == "/nonexistent/path"
        assert result["priority_status"] == RepoStatus.ERROR
        assert RepoStatus.ERROR in result["statuses"]
        assert "not exist" in result["error"].lower()
    
    def test_check_repository_not_git(self):
        """Test checking directory that is not a git repository."""
        result = self.checker.check_repository(self.temp_dir)
        
        assert result["path"] == self.temp_dir
        assert result["priority_status"] == RepoStatus.NOT_A_REPO
        assert RepoStatus.NOT_A_REPO in result["statuses"]
        assert "not a git repository" in result["error"].lower()
    
    def test_check_repository_clean(self):
        """Test checking clean repository."""
        # Create a clean git repository
        repo = Repo.init(self.temp_dir)
        
        # Add a file and commit it
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial commit")
        
        result = self.checker.check_repository(self.temp_dir)
        
        assert result["path"] == self.temp_dir
        assert result["priority_status"] == RepoStatus.CLEAN
        assert len(result["statuses"]) == 0 or RepoStatus.CLEAN in result["statuses"]
        assert result["error"] is None
    
    def test_check_uncommitted_changes(self):
        """Test detection of uncommitted changes."""
        mock_repo = Mock()
        mock_repo.git.status.return_value = "M  modified_file.txt\nD  deleted_file.txt"
        
        result = self.checker.check_uncommitted_changes(mock_repo)
        assert result is True
        
        # Test with clean repo
        mock_repo.git.status.return_value = ""
        result = self.checker.check_uncommitted_changes(mock_repo)
        assert result is False
        
        # Test with only untracked files
        mock_repo.git.status.return_value = "?? untracked.txt"
        result = self.checker.check_uncommitted_changes(mock_repo)
        assert result is False
    
    def test_check_untracked_files(self):
        """Test detection of untracked files."""
        mock_repo = Mock()
        mock_repo.git.status.return_value = "?? untracked1.txt\n?? untracked2.txt"
        
        result = self.checker.check_untracked_files(mock_repo)
        assert len(result) == 2
        assert "untracked1.txt" in result
        assert "untracked2.txt" in result
        
        # Test with no untracked files
        mock_repo.git.status.return_value = "M  modified.txt"
        result = self.checker.check_untracked_files(mock_repo)
        assert len(result) == 0
    
    def test_check_unpushed_commits(self):
        """Test detection of unpushed commits."""
        mock_repo = Mock()
        mock_repo.head.is_detached = False
        
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        
        mock_tracking = Mock()
        mock_tracking.name = "origin/main"
        mock_branch.tracking_branch.return_value = mock_tracking
        
        # Mock 3 unpushed commits
        mock_commits = [Mock(), Mock(), Mock()]
        mock_repo.iter_commits.return_value = mock_commits
        
        result = self.checker.check_unpushed_commits(mock_repo)
        assert result == 3
        
        # Test with no tracking branch
        mock_branch.tracking_branch.return_value = None
        result = self.checker.check_unpushed_commits(mock_repo)
        assert result == 0
    
    def test_get_status_priority_single(self):
        """Test status priority with single status."""
        statuses = [RepoStatus.UNCOMMITTED]
        result = self.checker.get_status_priority(statuses)
        assert result == RepoStatus.UNCOMMITTED
        
        statuses = [RepoStatus.CLEAN]
        result = self.checker.get_status_priority(statuses)
        assert result == RepoStatus.CLEAN
    
    def test_get_status_priority_multiple(self):
        """Test status priority with multiple statuses."""
        statuses = [RepoStatus.UNCOMMITTED, RepoStatus.UNPUSHED]
        result = self.checker.get_status_priority(statuses)
        assert result == RepoStatus.MULTIPLE
        
        # Error should take priority
        statuses = [RepoStatus.UNCOMMITTED, RepoStatus.ERROR]
        result = self.checker.get_status_priority(statuses)
        assert result == RepoStatus.ERROR
    
    def test_get_status_class(self):
        """Test CSS class mapping."""
        assert self.checker.get_status_class(RepoStatus.CLEAN) == "clean"
        assert self.checker.get_status_class(RepoStatus.UNCOMMITTED) == "uncommitted"
        assert self.checker.get_status_class(RepoStatus.ERROR) == "error"
    
    def test_get_status_icon(self):
        """Test icon mapping."""
        assert self.checker.get_status_icon(RepoStatus.CLEAN) == "✓"
        assert self.checker.get_status_icon(RepoStatus.UNCOMMITTED) == "●"
        assert self.checker.get_status_icon(RepoStatus.UNPUSHED) == "↑"
    
    def test_get_aggregate_status(self):
        """Test aggregate status calculation."""
        # All clean
        repos = [
            {"priority_status": RepoStatus.CLEAN},
            {"priority_status": RepoStatus.CLEAN}
        ]
        result = self.checker.get_aggregate_status(repos)
        assert result == RepoStatus.CLEAN
        
        # One with issue
        repos = [
            {"priority_status": RepoStatus.CLEAN},
            {"priority_status": RepoStatus.UNCOMMITTED}
        ]
        result = self.checker.get_aggregate_status(repos)
        assert result == RepoStatus.UNCOMMITTED
        
        # Multiple with issues
        repos = [
            {"priority_status": RepoStatus.UNCOMMITTED},
            {"priority_status": RepoStatus.UNPUSHED}
        ]
        result = self.checker.get_aggregate_status(repos)
        assert result == RepoStatus.MULTIPLE
    
    def test_check_repositories(self):
        """Test checking multiple repositories."""
        # Create two repos
        repo1_dir = Path(self.temp_dir) / "repo1"
        repo2_dir = Path(self.temp_dir) / "repo2"
        repo1_dir.mkdir()
        repo2_dir.mkdir()
        
        Repo.init(str(repo1_dir))
        # repo2 is not a git repo
        
        results = self.checker.check_repositories([str(repo1_dir), str(repo2_dir)])
        
        assert len(results) == 2
        assert results[0]["priority_status"] == RepoStatus.CLEAN
        assert results[1]["priority_status"] == RepoStatus.NOT_A_REPO
    
    @patch('subprocess.run')
    def test_ssh_agent_available(self, mock_run):
        """Test SSH agent detection."""
        # Reset cache
        self.checker._ssh_agent_available = None
        
        # Test with SSH agent available
        mock_run.return_value.returncode = 0
        assert self.checker.ssh_agent_available is True
        
        # Test with cached value (shouldn't call subprocess again)
        mock_run.reset_mock()
        assert self.checker.ssh_agent_available is True
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_gh_cli_available(self, mock_run):
        """Test GitHub CLI detection."""
        # Reset cache
        self.checker._gh_cli_available = None
        
        # Test with gh CLI available
        mock_run.return_value.returncode = 0
        assert self.checker.gh_cli_available is True
        
        # Test with cached value
        mock_run.reset_mock()
        assert self.checker.gh_cli_available is True
        mock_run.assert_not_called()