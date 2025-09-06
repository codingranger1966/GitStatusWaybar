#!/usr/bin/env python3
"""Dropdown handler for git repository status display."""

import sys
import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Add project library to path
sys.path.insert(0, str(Path.home() / "Projects" / "GitStatusWaybar"))

from lib.config_loader import ConfigLoader
from lib.logger_config import setup_logging, get_logger

# Set up logging
logger = get_logger("git-dropdown")


class GitDropdown:
    """Handle dropdown display for git repositories."""
    
    def __init__(self):
        """Initialize GitDropdown."""
        self.config_loader = ConfigLoader()
        self.config = {}
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            self.config = self.config_loader.load()
            logger.debug(f"Loaded configuration with {len(self.config.get('repositories', []))} repositories")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.config = {'repositories': []}
    
    def get_repository_statuses(self) -> List[Dict[str, any]]:
        """
        Get current repository statuses from cache or fresh check.
        
        Returns:
            List of repository status dictionaries
        """
        try:
            from lib.git_status_checker import GitStatusChecker
            
            repositories = self.config.get('repositories', [])
            if not repositories:
                logger.warning("No repositories configured")
                return []
            
            status_checker = GitStatusChecker()
            
            # Update timeout from config if available
            if 'auth' in self.config and 'fetch_timeout' in self.config['auth']:
                status_checker.timeout = self.config['auth']['fetch_timeout']
            
            return status_checker.check_repositories(repositories)
            
        except Exception as e:
            logger.error(f"Failed to get repository statuses: {e}")
            return []
    
    def format_repository_list(self, statuses: List[Dict[str, any]]) -> List[str]:
        """
        Format repository list for dropdown display.
        
        Args:
            statuses: List of repository status dictionaries
            
        Returns:
            List of formatted repository entries
        """
        if not statuses:
            return ["No repositories configured"]
        
        from lib.git_status_checker import GitStatusChecker, RepoStatus
        
        status_checker = GitStatusChecker()
        entries = []
        
        # Sort by priority status (issues first)
        sorted_statuses = sorted(statuses, key=lambda r: list(RepoStatus).index(r['priority_status']))
        
        for repo in sorted_statuses:
            name = repo['name']
            status = repo['priority_status']
            path = repo['path']
            
            # Get status icon
            icon = status_checker.get_status_icon(status)
            
            # Build details string
            details = []
            if 'details' in repo:
                if repo['details'].get('uncommitted_count', 0) > 0:
                    details.append(f"{repo['details']['uncommitted_count']} modified")
                if repo['details'].get('untracked_count', 0) > 0:
                    details.append(f"{repo['details']['untracked_count']} untracked")
                if repo['details'].get('unpushed_count', 0) > 0:
                    details.append(f"{repo['details']['unpushed_count']} unpushed")
                if repo['details'].get('upstream_available', False):
                    details.append("updates available")
            
            # Format entry
            if details:
                detail_str = f" ({', '.join(details)})"
            else:
                detail_str = ""
            
            # Format: "icon name (details) | path"
            entry = f"{icon} {name}{detail_str} | {path}"
            entries.append(entry)
        
        return entries
    
    def detect_launcher(self) -> str:
        """
        Detect available launcher (rofi or wofi).
        
        Returns:
            Name of available launcher
        """
        # Check for rofi first (more common)
        try:
            subprocess.run(['rofi', '--version'], capture_output=True, check=True)
            logger.debug("Detected rofi launcher")
            return 'rofi'
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Check for wofi
        try:
            subprocess.run(['wofi', '--version'], capture_output=True, check=True)
            logger.debug("Detected wofi launcher")
            return 'wofi'
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        logger.warning("No launcher detected (rofi or wofi)")
        return 'none'
    
    def show_dropdown(self, entries: List[str]) -> Optional[str]:
        """
        Show dropdown with repository list.
        
        Args:
            entries: List of formatted repository entries
            
        Returns:
            Selected repository path or None
        """
        if not entries:
            return None
        
        launcher = self.detect_launcher()
        
        if launcher == 'none':
            logger.error("No launcher available for dropdown")
            return None
        
        try:
            # Prepare input for launcher
            input_text = '\n'.join(entries)
            
            if launcher == 'rofi':
                cmd = [
                    'rofi', '-dmenu', '-i', 
                    '-p', 'Git Repository:',
                    '-theme-str', 'listview { lines: 10; }',
                    '-no-custom'
                ]
            else:  # wofi
                cmd = [
                    'wofi', '--dmenu', '--insensitive',
                    '--prompt', 'Git Repository:',
                    '--lines', '10'
                ]
            
            # Run launcher
            result = subprocess.run(
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                selected = result.stdout.strip()
                logger.debug(f"Selected entry: {selected}")
                
                # Extract path from selection (after the " | " separator)
                if ' | ' in selected:
                    return selected.split(' | ')[-1]
                else:
                    logger.warning(f"Could not extract path from selection: {selected}")
                    return None
            else:
                logger.debug("No selection made or launcher cancelled")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Launcher timed out")
            return None
        except Exception as e:
            logger.error(f"Error showing dropdown: {e}")
            return None
    
    def open_terminal(self, repo_path: str) -> None:
        """
        Open terminal in repository directory.
        
        Args:
            repo_path: Path to repository
        """
        if not os.path.exists(repo_path):
            logger.error(f"Repository path does not exist: {repo_path}")
            return
        
        # List of terminal emulators to try (in order of preference)
        terminals = [
            'alacritty',
            'kitty', 
            'wezterm',
            'gnome-terminal',
            'konsole',
            'xterm'
        ]
        
        for terminal in terminals:
            try:
                # Check if terminal is available
                subprocess.run([terminal, '--version'], capture_output=True, check=True)
                
                # Launch terminal in repository directory
                if terminal == 'alacritty':
                    cmd = [terminal, '--working-directory', repo_path]
                elif terminal == 'kitty':
                    cmd = [terminal, '--directory', repo_path]
                elif terminal == 'wezterm':
                    cmd = [terminal, 'start', '--cwd', repo_path]
                elif terminal == 'gnome-terminal':
                    cmd = [terminal, '--working-directory', repo_path]
                elif terminal == 'konsole':
                    cmd = [terminal, '--workdir', repo_path]
                else:  # xterm and others
                    # Use shell command to cd into directory
                    cmd = [terminal, '-e', f'bash -c "cd {repo_path} && bash"']
                
                # Start terminal in background
                subprocess.Popen(cmd, start_new_session=True)
                logger.info(f"Opened {terminal} in {repo_path}")
                return
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        logger.error("No terminal emulator found")
    
    def run(self) -> None:
        """Main dropdown handler."""
        try:
            # Load configuration
            self.load_config()
            
            # Get repository statuses
            statuses = self.get_repository_statuses()
            
            if not statuses:
                logger.info("No repositories to display")
                return
            
            # Format entries for dropdown
            entries = self.format_repository_list(statuses)
            
            # Show dropdown and get selection
            selected_path = self.show_dropdown(entries)
            
            if selected_path:
                # Open terminal in selected repository
                self.open_terminal(selected_path)
            else:
                logger.debug("No repository selected")
                
        except Exception as e:
            logger.error(f"Error in dropdown handler: {e}")
            # Try to show error notification if available
            try:
                subprocess.run(['notify-send', 'Git Monitor', f'Error: {str(e)}'], 
                             capture_output=True, timeout=5)
            except:
                pass


def main():
    """Main entry point."""
    # Set up logging from environment or defaults
    from lib.logger_config import setup_from_env
    setup_from_env()
    
    # Create and run dropdown
    dropdown = GitDropdown()
    dropdown.run()


if __name__ == "__main__":
    main()