#!/usr/bin/env python3
"""Tests for git-dropdown.py functionality."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Add project library to path
sys.path.insert(0, str(Path.home() / "Projects" / "GitStatusWaybar"))

from git_dropdown import GitDropdown


class TestGitDropdown(unittest.TestCase):
    """Test cases for GitDropdown class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.dropdown = GitDropdown()
        self.dropdown.config = {
            'repositories': [
                {'name': 'test-repo', 'path': '/path/to/test-repo'},
                {'name': 'another-repo', 'path': '/path/to/another-repo'}
            ]
        }
    
    @patch('git_dropdown.ConfigLoader')
    def test_load_config_success(self, mock_config_loader):
        """Test successful configuration loading."""
        mock_loader = Mock()
        mock_loader.load.return_value = {'repositories': []}
        mock_config_loader.return_value = mock_loader
        
        dropdown = GitDropdown()
        dropdown.load_config()
        
        self.assertEqual(dropdown.config, {'repositories': []})
        mock_loader.load.assert_called_once()
    
    @patch('git_dropdown.ConfigLoader')
    @patch('git_dropdown.logger')
    def test_load_config_failure(self, mock_logger, mock_config_loader):
        """Test configuration loading failure."""
        mock_loader = Mock()
        mock_loader.load.side_effect = Exception("Config error")
        mock_config_loader.return_value = mock_loader
        
        dropdown = GitDropdown()
        dropdown.load_config()
        
        self.assertEqual(dropdown.config, {'repositories': []})
        mock_logger.error.assert_called_once()
    
    @patch('git_dropdown.GitStatusChecker')
    def test_get_repository_statuses_success(self, mock_checker_class):
        """Test successful repository status retrieval."""
        mock_checker = Mock()
        mock_statuses = [{'name': 'test', 'status': 'clean'}]
        mock_checker.check_repositories.return_value = mock_statuses
        mock_checker_class.return_value = mock_checker
        
        result = self.dropdown.get_repository_statuses()
        
        self.assertEqual(result, mock_statuses)
        mock_checker.check_repositories.assert_called_once_with(self.dropdown.config['repositories'])
    
    @patch('git_dropdown.GitStatusChecker')
    def test_get_repository_statuses_no_repos(self, mock_checker_class):
        """Test repository status retrieval with no repositories configured."""
        self.dropdown.config = {'repositories': []}
        
        result = self.dropdown.get_repository_statuses()
        
        self.assertEqual(result, [])
        mock_checker_class.assert_not_called()
    
    @patch('git_dropdown.GitStatusChecker')
    def test_format_repository_list_empty(self, mock_checker_class):
        """Test formatting empty repository list."""
        result = self.dropdown.format_repository_list([])
        
        self.assertEqual(result, ["No repositories configured"])
    
    @patch('git_dropdown.GitStatusChecker')
    def test_format_repository_list_with_repos(self, mock_checker_class):
        """Test formatting repository list with repositories."""
        from lib.git_status_checker import RepoStatus
        
        mock_checker = Mock()
        mock_checker.get_status_icon.return_value = "●"
        mock_checker_class.return_value = mock_checker
        
        statuses = [
            {
                'name': 'test-repo',
                'path': '/path/to/test-repo',
                'priority_status': RepoStatus.UNCOMMITTED,
                'details': {
                    'uncommitted_count': 3,
                    'untracked_count': 1
                }
            }
        ]
        
        result = self.dropdown.format_repository_list(statuses)
        
        self.assertEqual(len(result), 1)
        self.assertIn('test-repo', result[0])
        self.assertIn('/path/to/test-repo', result[0])
        self.assertIn('3 modified', result[0])
        self.assertIn('1 untracked', result[0])
    
    @patch('git_dropdown.subprocess.run')
    def test_detect_launcher_rofi(self, mock_run):
        """Test launcher detection finding rofi."""
        mock_run.return_value = Mock(returncode=0)
        
        result = self.dropdown.detect_launcher()
        
        self.assertEqual(result, 'rofi')
        mock_run.assert_called_with(['rofi', '--version'], capture_output=True, check=True)
    
    @patch('git_dropdown.subprocess.run')
    def test_detect_launcher_wofi(self, mock_run):
        """Test launcher detection finding wofi when rofi fails."""
        def side_effect(cmd, **kwargs):
            if cmd[0] == 'rofi':
                raise FileNotFoundError()
            return Mock(returncode=0)
        
        mock_run.side_effect = side_effect
        
        result = self.dropdown.detect_launcher()
        
        self.assertEqual(result, 'wofi')
    
    @patch('git_dropdown.subprocess.run')
    def test_detect_launcher_none(self, mock_run):
        """Test launcher detection when no launcher found."""
        mock_run.side_effect = FileNotFoundError()
        
        result = self.dropdown.detect_launcher()
        
        self.assertEqual(result, 'none')
    
    @patch('git_dropdown.GitDropdown.detect_launcher')
    @patch('git_dropdown.subprocess.run')
    def test_show_dropdown_rofi_success(self, mock_run, mock_detect):
        """Test successful dropdown display with rofi."""
        mock_detect.return_value = 'rofi'
        mock_run.return_value = Mock(
            returncode=0,
            stdout='● test-repo (2 modified) | /path/to/test-repo\n'
        )
        
        entries = ['● test-repo (2 modified) | /path/to/test-repo']
        result = self.dropdown.show_dropdown(entries)
        
        self.assertEqual(result, '/path/to/test-repo')
    
    @patch('git_dropdown.GitDropdown.detect_launcher')
    def test_show_dropdown_no_launcher(self, mock_detect):
        """Test dropdown display when no launcher available."""
        mock_detect.return_value = 'none'
        
        entries = ['test entry']
        result = self.dropdown.show_dropdown(entries)
        
        self.assertIsNone(result)
    
    @patch('git_dropdown.subprocess.run')
    @patch('git_dropdown.os.path.exists')
    def test_open_terminal_alacritty(self, mock_exists, mock_run):
        """Test opening terminal with alacritty."""
        mock_exists.return_value = True
        
        # Mock version check to succeed for alacritty
        def side_effect(cmd, **kwargs):
            if '--version' in cmd:
                return Mock(returncode=0)
            return Mock()
        
        mock_run.side_effect = side_effect
        
        with patch('git_dropdown.subprocess.Popen') as mock_popen:
            self.dropdown.open_terminal('/path/to/repo')
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertIn('alacritty', args)
            self.assertIn('/path/to/repo', args)
    
    @patch('git_dropdown.os.path.exists')
    def test_open_terminal_invalid_path(self, mock_exists):
        """Test opening terminal with invalid path."""
        mock_exists.return_value = False
        
        with patch('git_dropdown.logger') as mock_logger:
            self.dropdown.open_terminal('/invalid/path')
            mock_logger.error.assert_called_once()
    
    @patch.object(GitDropdown, 'load_config')
    @patch.object(GitDropdown, 'get_repository_statuses')
    @patch.object(GitDropdown, 'format_repository_list')
    @patch.object(GitDropdown, 'show_dropdown')
    @patch.object(GitDropdown, 'open_terminal')
    def test_run_success(self, mock_open, mock_show, mock_format, mock_get, mock_load):
        """Test successful run of dropdown handler."""
        mock_get.return_value = [{'name': 'test', 'status': 'clean'}]
        mock_format.return_value = ['test entry']
        mock_show.return_value = '/path/to/repo'
        
        self.dropdown.run()
        
        mock_load.assert_called_once()
        mock_get.assert_called_once()
        mock_format.assert_called_once()
        mock_show.assert_called_once()
        mock_open.assert_called_once_with('/path/to/repo')
    
    @patch.object(GitDropdown, 'load_config')
    @patch.object(GitDropdown, 'get_repository_statuses')
    def test_run_no_repositories(self, mock_get, mock_load):
        """Test run when no repositories available."""
        mock_get.return_value = []
        
        with patch('git_dropdown.logger') as mock_logger:
            self.dropdown.run()
            mock_logger.info.assert_called_with("No repositories to display")


if __name__ == '__main__':
    # Import the module we're testing
    sys.path.insert(0, os.path.dirname(__file__))
    import git_dropdown
    
    unittest.main()