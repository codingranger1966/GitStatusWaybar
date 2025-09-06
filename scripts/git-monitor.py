#!/usr/bin/env python3
"""Main git monitoring script for Waybar integration."""

import sys
import os
import json
import time
import signal
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# Add project library to path
sys.path.insert(0, str(Path.home() / "Projects" / "GitStatusWaybar"))

from lib.git_status_checker import GitStatusChecker, RepoStatus
from lib.config_loader import ConfigLoader, ConfigValidationError
from lib.logger_config import setup_from_env, get_logger

# Set up logging
logger = get_logger("git-monitor")


class GitMonitor:
    """Monitor git repositories and output Waybar-compatible JSON."""
    
    def __init__(self):
        """Initialize GitMonitor."""
        self.config_loader = ConfigLoader()
        self.status_checker = GitStatusChecker()
        self.config = {}
        self.cache = {}
        self.last_check = None
        self.running = True
        self.lock = threading.Lock()
        
        # Set up signal handlers for manual refresh
        signal.signal(signal.SIGUSR1, self.handle_refresh)
        signal.signal(signal.SIGTERM, self.handle_terminate)
        signal.signal(signal.SIGINT, self.handle_terminate)
    
    def handle_refresh(self, signum, frame):
        """Handle manual refresh signal."""
        logger.info("Manual refresh triggered via signal")
        with self.lock:
            self.cache.clear()  # Clear cache to force fresh check
    
    def handle_terminate(self, signum, frame):
        """Handle termination signal."""
        logger.info(f"Termination signal {signum} received")
        self.running = False
    
    def load_config(self) -> None:
        """
        Load configuration from file.
        
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        try:
            self.config = self.config_loader.load()
            logger.info(f"Loaded configuration with {len(self.config['repositories'])} repositories")
            
            # Update status checker timeout from config
            if 'auth' in self.config and 'fetch_timeout' in self.config['auth']:
                self.status_checker.timeout = self.config['auth']['fetch_timeout']
                
        except ConfigValidationError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def should_check_repositories(self) -> bool:
        """
        Determine if repositories should be checked based on cache and interval.
        
        Returns:
            True if repositories should be checked
        """
        if not self.last_check:
            return True
        
        update_interval = self.config.get('update_interval', 30)
        cache_duration = self.config.get('advanced', {}).get('cache_duration', 5)
        
        # Use the smaller of update_interval and cache_duration for checking
        check_interval = min(update_interval, cache_duration)
        
        elapsed = datetime.now() - self.last_check
        return elapsed.total_seconds() >= check_interval
    
    def check_repositories(self) -> List[Dict[str, Any]]:
        """
        Check all configured repositories.
        
        Returns:
            List of repository status dictionaries
        """
        repositories = self.config.get('repositories', [])
        
        if not repositories:
            logger.warning("No repositories configured for monitoring")
            return []
        
        logger.debug(f"Checking {len(repositories)} repositories")
        
        # Check if we should use cached results
        if not self.should_check_repositories() and self.cache:
            logger.debug("Using cached repository status")
            return self.cache.get('statuses', [])
        
        try:
            # Check all repositories
            with self.lock:
                statuses = self.status_checker.check_repositories(repositories)
                
                # Cache results
                self.cache = {
                    'statuses': statuses,
                    'timestamp': datetime.now()
                }
                self.last_check = datetime.now()
                
                # Log summary
                status_counts = {}
                for repo_status in statuses:
                    status = repo_status['priority_status'].value
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                logger.debug(f"Repository check complete. Status counts: {status_counts}")
                
                return statuses
                
        except Exception as e:
            logger.error(f"Error checking repositories: {e}")
            # Return cached results if available
            return self.cache.get('statuses', [])
    
    def generate_waybar_output(self, repo_statuses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate Waybar-compatible JSON output.
        
        Args:
            repo_statuses: List of repository status dictionaries
            
        Returns:
            Waybar JSON output dictionary
        """
        if not repo_statuses:
            return {
                "text": "",
                "class": "clean",
                "tooltip": "No repositories configured"
            }
        
        # Get aggregate status
        overall_status = self.status_checker.get_aggregate_status(repo_statuses)
        
        # Get icon and CSS class
        icon = self.status_checker.get_status_icon(overall_status)
        css_class = self.status_checker.get_status_class(overall_status)
        
        # Count repositories by status
        status_counts = {}
        repos_with_issues = []
        
        for repo in repo_statuses:
            status = repo['priority_status']
            if status != RepoStatus.CLEAN:
                repos_with_issues.append(repo)
            
            status_name = status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
        
        # Generate tooltip
        tooltip_lines = []
        
        if not repos_with_issues:
            tooltip_lines.append(f"All {len(repo_statuses)} repositories clean")
        else:
            tooltip_lines.append(f"{len(repos_with_issues)} of {len(repo_statuses)} repositories need attention:")
            
            # Sort repos by status priority for tooltip
            repos_with_issues.sort(key=lambda r: list(RepoStatus).index(r['priority_status']))
            
            for repo in repos_with_issues[:10]:  # Limit to 10 for tooltip
                repo_name = repo['name']
                status = repo['priority_status']
                icon = self.status_checker.get_status_icon(status)
                
                # Add details if available
                details = []
                if 'details' in repo:
                    if 'uncommitted_count' in repo['details']:
                        details.append(f"{repo['details']['uncommitted_count']} modified")
                    if 'untracked_count' in repo['details']:
                        details.append(f"{repo['details']['untracked_count']} untracked")
                    if 'unpushed_count' in repo['details']:
                        details.append(f"{repo['details']['unpushed_count']} unpushed")
                
                detail_str = f" ({', '.join(details)})" if details else ""
                tooltip_lines.append(f"  {icon} {repo_name}{detail_str}")
            
            if len(repos_with_issues) > 10:
                tooltip_lines.append(f"  ... and {len(repos_with_issues) - 10} more")
        
        tooltip = "\n".join(tooltip_lines)
        
        # Generate main text - use a simple fallback for debugging
        if overall_status == RepoStatus.CLEAN:
            text = ""  # Empty when clean (so widget disappears)
        elif overall_status == RepoStatus.MULTIPLE:
            text = "!"  # Simple exclamation mark instead of Unicode
        else:
            text = "●"  # Simple bullet point
        
        return {
            "text": text,
            "class": css_class,
            "tooltip": tooltip
        }
    
    def run(self) -> None:
        """Main monitoring loop."""
        logger.info("Starting Git Waybar Monitor")
        
        try:
            # Load configuration
            self.load_config()
            
            # Initial check
            repo_statuses = self.check_repositories()
            waybar_output = self.generate_waybar_output(repo_statuses)
            
            # Output initial JSON
            try:
                print(json.dumps(waybar_output), flush=True)
            except BrokenPipeError:
                logger.info("Waybar disconnected during initial output")
                return
            
            # Main loop
            update_interval = self.config.get('update_interval', 30)
            
            while self.running:
                try:
                    time.sleep(min(update_interval, 5))  # Check at least every 5 seconds for signals
                    
                    if not self.running:
                        break
                    
                    # Check if config should be reloaded (if file changed)
                    try:
                        # Only reload if file modification time changed
                        config_path = self.config_loader.config_path
                        if config_path.exists():
                            current_mtime = config_path.stat().st_mtime
                            if not hasattr(self, '_config_mtime') or current_mtime != self._config_mtime:
                                logger.info("Configuration file changed, reloading...")
                                self.config = self.config_loader.reload()
                                self._config_mtime = current_mtime
                                
                                # Clear cache to force fresh check with new config
                                with self.lock:
                                    self.cache.clear()
                    except Exception as e:
                        logger.debug(f"Error checking config file modification: {e}")
                    
                    # Check repositories if needed
                    if self.should_check_repositories() or not self.cache:
                        repo_statuses = self.check_repositories()
                        waybar_output = self.generate_waybar_output(repo_statuses)
                        
                        # Output JSON for Waybar
                        try:
                            print(json.dumps(waybar_output), flush=True)
                        except BrokenPipeError:
                            # Waybar disconnected, exit gracefully
                            logger.info("Waybar disconnected")
                            break
                    
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    
                    # Output error state
                    error_output = {
                        "text": "✗",
                        "class": "error", 
                        "tooltip": f"Git monitor error: {str(e)}"
                    }
                    print(json.dumps(error_output), flush=True)
                    
                    time.sleep(5)  # Wait before retrying
        
        except ConfigValidationError as e:
            logger.error(f"Configuration error: {e}")
            error_output = {
                "text": "✗",
                "class": "error",
                "tooltip": f"Configuration error: {str(e)}"
            }
            print(json.dumps(error_output), flush=True)
            sys.exit(1)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            error_output = {
                "text": "✗", 
                "class": "error",
                "tooltip": f"Fatal error: {str(e)}"
            }
            print(json.dumps(error_output), flush=True)
            sys.exit(1)
        
        logger.info("Git Waybar Monitor stopped")


def main():
    """Main entry point."""
    # Set up logging from environment or defaults
    setup_from_env()
    
    # Create and run monitor
    monitor = GitMonitor()
    monitor.run()


if __name__ == "__main__":
    main()