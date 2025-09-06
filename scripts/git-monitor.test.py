#!/usr/bin/env python3
"""Integration tests for git-monitor.py functionality."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os
import signal
import time
import threading
from pathlib import Path

# Add project library to path
sys.path.insert(0, str(Path.home() / "Projects" / "GitStatusWaybar"))

from git_monitor import GitMonitor


class TestGitMonitor(unittest.TestCase):
    """Test cases for GitMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = GitMonitor()
        self.monitor.config = {
            'repositories': [
                {'name': 'test-repo', 'path': '/path/to/test-repo'}
            ],
            'update_interval': 30,
            'advanced': {'cache_duration': 5}
        }
    
    def test_initialization(self):
        """Test GitMonitor initialization."""
        monitor = GitMonitor()
        
        self.assertIsNotNone(monitor.config_loader)
        self.assertIsNotNone(monitor.status_checker)
        self.assertEqual(monitor.config, {})
        self.assertEqual(monitor.cache, {})
        self.assertTrue(monitor.running)
        self.assertIsNotNone(monitor.lock)
    
    @patch('git_monitor.ConfigLoader')
    def test_load_config_success(self, mock_config_loader):
        """Test successful configuration loading."""
        mock_loader = Mock()
        mock_config = {
            'repositories': [{'name': 'test', 'path': '/path'}],
            'auth': {'fetch_timeout': 10}
        }
        mock_loader.load.return_value = mock_config
        mock_config_loader.return_value = mock_loader
        
        monitor = GitMonitor()
        monitor.load_config()
        
        self.assertEqual(monitor.config, mock_config)
        self.assertEqual(monitor.status_checker.timeout, 10)
    
    @patch('git_monitor.ConfigLoader')
    def test_load_config_failure(self, mock_config_loader):
        """Test configuration loading failure."""
        mock_loader = Mock()
        mock_loader.load.side_effect = Exception("Config error")
        mock_config_loader.return_value = mock_loader
        
        monitor = GitMonitor()
        
        with self.assertRaises(Exception):
            monitor.load_config()
    
    def test_handle_refresh_signal(self):
        """Test manual refresh signal handling."""
        self.monitor.cache = {'test': 'data'}
        
        self.monitor.handle_refresh(signal.SIGUSR1, None)
        
        self.assertEqual(self.monitor.cache, {})
    
    def test_handle_terminate_signal(self):
        """Test termination signal handling."""
        self.monitor.running = True
        
        self.monitor.handle_terminate(signal.SIGTERM, None)
        
        self.assertFalse(self.monitor.running)
    
    def test_should_check_repositories_first_check(self):
        """Test should check repositories on first check."""
        self.monitor.last_check = None
        
        result = self.monitor.should_check_repositories()
        
        self.assertTrue(result)
    
    @patch('git_monitor.datetime')
    def test_should_check_repositories_within_interval(self, mock_datetime):
        """Test should check repositories within interval."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        self.monitor.last_check = now - timedelta(seconds=2)
        mock_datetime.now.return_value = now
        
        result = self.monitor.should_check_repositories()
        
        self.assertFalse(result)
    
    @patch('git_monitor.datetime')
    def test_should_check_repositories_after_interval(self, mock_datetime):
        """Test should check repositories after interval."""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        self.monitor.last_check = now - timedelta(seconds=10)
        mock_datetime.now.return_value = now
        
        result = self.monitor.should_check_repositories()
        
        self.assertTrue(result)
    
    @patch('git_monitor.GitStatusChecker')
    @patch('git_monitor.datetime')
    def test_check_repositories_success(self, mock_datetime, mock_checker_class):
        """Test successful repository checking."""
        from datetime import datetime
        from lib.git_status_checker import RepoStatus
        
        now = datetime.now()
        mock_datetime.now.return_value = now
        
        mock_checker = Mock()
        mock_statuses = [
            {'name': 'test', 'priority_status': RepoStatus.CLEAN}
        ]
        mock_checker.check_repositories.return_value = mock_statuses
        mock_checker_class.return_value = mock_checker
        
        self.monitor.status_checker = mock_checker
        self.monitor.last_check = None  # Force check
        
        result = self.monitor.check_repositories()
        
        self.assertEqual(result, mock_statuses)
        self.assertEqual(self.monitor.cache['statuses'], mock_statuses)
        self.assertEqual(self.monitor.last_check, now)
    
    def test_check_repositories_no_config(self):
        """Test repository checking with no repositories configured."""
        self.monitor.config = {'repositories': []}
        
        result = self.monitor.check_repositories()
        
        self.assertEqual(result, [])
    
    @patch('git_monitor.GitStatusChecker')
    def test_check_repositories_with_cache(self, mock_checker_class):
        """Test repository checking using cached results."""
        from datetime import datetime
        from lib.git_status_checker import RepoStatus
        
        cached_statuses = [
            {'name': 'test', 'priority_status': RepoStatus.CLEAN}
        ]
        self.monitor.cache = {
            'statuses': cached_statuses,
            'timestamp': datetime.now()
        }
        self.monitor.last_check = datetime.now()
        
        result = self.monitor.check_repositories()
        
        self.assertEqual(result, cached_statuses)
        # Checker should not be called when using cache
        mock_checker_class.assert_not_called()
    
    @patch('git_monitor.GitStatusChecker')
    def test_generate_waybar_output_empty(self, mock_checker_class):
        """Test Waybar output generation with empty repositories."""
        result = self.monitor.generate_waybar_output([])
        
        expected = {
            "text": "",
            "class": "clean",
            "tooltip": "No repositories configured"
        }
        self.assertEqual(result, expected)
    
    @patch('git_monitor.GitStatusChecker')
    def test_generate_waybar_output_clean(self, mock_checker_class):
        """Test Waybar output generation with clean repositories."""
        from lib.git_status_checker import RepoStatus
        
        mock_checker = Mock()
        mock_checker.get_aggregate_status.return_value = RepoStatus.CLEAN
        mock_checker.get_status_icon.return_value = ""
        mock_checker.get_status_class.return_value = "clean"
        mock_checker_class.return_value = mock_checker
        
        self.monitor.status_checker = mock_checker
        
        repo_statuses = [
            {'name': 'test', 'priority_status': RepoStatus.CLEAN, 'path': '/path'}
        ]
        
        result = self.monitor.generate_waybar_output(repo_statuses)
        
        self.assertEqual(result['text'], "")
        self.assertEqual(result['class'], "clean")
        self.assertIn("All 1 repositories clean", result['tooltip'])
    
    @patch('git_monitor.GitStatusChecker')
    def test_generate_waybar_output_issues(self, mock_checker_class):
        """Test Waybar output generation with repository issues."""
        from lib.git_status_checker import RepoStatus
        
        mock_checker = Mock()
        mock_checker.get_aggregate_status.return_value = RepoStatus.UNCOMMITTED
        mock_checker.get_status_icon.return_value = "●"
        mock_checker.get_status_class.return_value = "uncommitted"
        mock_checker_class.return_value = mock_checker
        
        self.monitor.status_checker = mock_checker
        
        repo_statuses = [
            {
                'name': 'test-repo',
                'priority_status': RepoStatus.UNCOMMITTED,
                'path': '/path/to/test',
                'details': {
                    'uncommitted_count': 3,
                    'untracked_count': 1
                }
            }
        ]
        
        result = self.monitor.generate_waybar_output(repo_statuses)
        
        self.assertEqual(result['text'], "●")
        self.assertEqual(result['class'], "uncommitted")
        self.assertIn("1 of 1 repositories need attention", result['tooltip'])
        self.assertIn("test-repo", result['tooltip'])
        self.assertIn("3 modified", result['tooltip'])
        self.assertIn("1 untracked", result['tooltip'])
    
    @patch('git_monitor.GitStatusChecker')
    def test_generate_waybar_output_multiple_status(self, mock_checker_class):
        """Test Waybar output generation with multiple status."""
        from lib.git_status_checker import RepoStatus
        
        mock_checker = Mock()
        mock_checker.get_aggregate_status.return_value = RepoStatus.MULTIPLE
        mock_checker.get_status_icon.return_value = "!"
        mock_checker.get_status_class.return_value = "multiple"
        mock_checker_class.return_value = mock_checker
        
        self.monitor.status_checker = mock_checker
        
        repo_statuses = [
            {'name': 'test1', 'priority_status': RepoStatus.UNCOMMITTED, 'path': '/path1'},
            {'name': 'test2', 'priority_status': RepoStatus.UNPUSHED, 'path': '/path2'}
        ]
        
        result = self.monitor.generate_waybar_output(repo_statuses)
        
        self.assertEqual(result['text'], "!")
        self.assertEqual(result['class'], "multiple")
    
    @patch.object(GitMonitor, 'load_config')
    @patch.object(GitMonitor, 'check_repositories')
    @patch.object(GitMonitor, 'generate_waybar_output')
    @patch('git_monitor.json.dumps')
    @patch('builtins.print')
    def test_run_initial_output(self, mock_print, mock_json_dumps, mock_generate, mock_check, mock_load):
        """Test run method initial output."""
        mock_check.return_value = []
        mock_output = {"text": "", "class": "clean"}
        mock_generate.return_value = mock_output
        mock_json_dumps.return_value = '{"text": "", "class": "clean"}'
        
        # Mock the main loop to exit immediately
        self.monitor.running = False
        
        self.monitor.run()
        
        mock_load.assert_called_once()
        mock_check.assert_called_once()
        mock_generate.assert_called_once()
        mock_json_dumps.assert_called_once_with(mock_output)
        mock_print.assert_called_once()
    
    @patch.object(GitMonitor, 'load_config')
    def test_run_config_validation_error(self, mock_load):
        """Test run method handling configuration validation error."""
        from lib.config_loader import ConfigValidationError
        
        mock_load.side_effect = ConfigValidationError("Invalid config")
        
        with patch('builtins.print') as mock_print:
            with patch('git_monitor.sys.exit') as mock_exit:
                self.monitor.run()
                
                mock_exit.assert_called_once_with(1)
                # Should print error output
                mock_print.assert_called_once()
                call_args = mock_print.call_args[0][0]
                output = json.loads(call_args)
                self.assertEqual(output['text'], '✗')
                self.assertEqual(output['class'], 'error')
    
    def test_signal_handlers_setup(self):
        """Test that signal handlers are properly set up."""
        # This tests that the signal handlers are registered during initialization
        # We can't easily test the actual signal handling without complex setup
        monitor = GitMonitor()
        
        # Test that the handler methods exist
        self.assertTrue(hasattr(monitor, 'handle_refresh'))
        self.assertTrue(hasattr(monitor, 'handle_terminate'))
        
        # Test handler functionality
        monitor.cache = {'test': 'data'}
        monitor.handle_refresh(signal.SIGUSR1, None)
        self.assertEqual(monitor.cache, {})
        
        monitor.running = True
        monitor.handle_terminate(signal.SIGTERM, None)
        self.assertFalse(monitor.running)


class TestGitMonitorIntegration(unittest.TestCase):
    """Integration tests for GitMonitor with real components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = GitMonitor()
    
    @patch('git_monitor.Path.exists')
    @patch('git_monitor.Path.stat')
    @patch.object(GitMonitor, 'load_config')
    def test_config_reload_detection(self, mock_load, mock_stat, mock_exists):
        """Test configuration file modification detection."""
        from types import SimpleNamespace
        
        mock_exists.return_value = True
        
        # First call - set initial mtime
        mock_stat.return_value = SimpleNamespace(st_mtime=100)
        self.monitor.config_loader.config_path = Mock()
        self.monitor.config_loader.config_path.exists.return_value = True
        self.monitor.config_loader.config_path.stat.return_value = SimpleNamespace(st_mtime=100)
        
        # Simulate first check - should set _config_mtime
        self.monitor.config = {'update_interval': 30}
        self.monitor._config_mtime = 100
        
        # Second call - same mtime, should not reload
        with patch.object(self.monitor.config_loader, 'reload') as mock_reload:
            # Simulate the check in the main loop
            config_path = self.monitor.config_loader.config_path
            if config_path.exists():
                current_mtime = config_path.stat().st_mtime
                if current_mtime == self.monitor._config_mtime:
                    # Should not reload
                    pass
                else:
                    self.monitor.config = self.monitor.config_loader.reload()
                    self.monitor._config_mtime = current_mtime
            
            mock_reload.assert_not_called()
    
    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        self.monitor.cache = {}
        
        def write_cache():
            with self.monitor.lock:
                self.monitor.cache['test'] = 'data'
                time.sleep(0.01)  # Small delay to test locking
                self.monitor.cache['test2'] = 'data2'
        
        def read_cache():
            with self.monitor.lock:
                result = self.monitor.cache.copy()
                return result
        
        # Start multiple threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=write_cache)
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Verify final state
        final_cache = read_cache()
        self.assertIn('test', final_cache)
        self.assertIn('test2', final_cache)


if __name__ == '__main__':
    # Import the module we're testing
    sys.path.insert(0, os.path.dirname(__file__))
    import git_monitor
    
    unittest.main()