#!/usr/bin/env python3
"""One-shot git status check for Waybar."""

import sys
import json
from pathlib import Path

# Add project library to path
sys.path.insert(0, str(Path.home() / "Projects" / "GitStatusWaybar"))

try:
    from lib.git_status_checker import GitStatusChecker, RepoStatus
    from lib.config_loader import ConfigLoader
    
    # Load config and check repositories
    config_loader = ConfigLoader()
    config = config_loader.load()
    
    status_checker = GitStatusChecker()
    repositories = config.get('repositories', [])
    
    if not repositories:
        output = {
            "text": "",
            "class": "clean", 
            "tooltip": "No repositories configured"
        }
    else:
        # Check all repositories
        repo_statuses = status_checker.check_repositories(repositories)
        
        # Get aggregate status
        overall_status = status_checker.get_aggregate_status(repo_statuses)
        
        # Count repos with issues
        repos_with_issues = [r for r in repo_statuses if r['priority_status'] != RepoStatus.CLEAN]
        
        # Get display configuration
        display_config = config.get('display', {})
        icons = display_config.get('icons', {})
        
        # Use configured icons or defaults
        if overall_status == RepoStatus.CLEAN:
            text = icons.get('clean', "")
        elif overall_status == RepoStatus.UNCOMMITTED:
            text = icons.get('uncommitted', "●")
        elif overall_status == RepoStatus.UNTRACKED:
            text = icons.get('untracked', "○")
        elif overall_status == RepoStatus.UNPUSHED:
            text = icons.get('unpushed', "↑")
        elif overall_status == RepoStatus.UPSTREAM_AVAILABLE:
            text = icons.get('upstream', "↓")
        elif overall_status == RepoStatus.MULTIPLE:
            text = icons.get('multiple', "!")
        else:
            text = icons.get('error', "✗")
        
        css_class = status_checker.get_status_class(overall_status)
        
        # No tooltip since we disabled it to fix clicking issues
        tooltip = ""
        
        output = {
            "text": text,
            "class": css_class,
            "tooltip": tooltip
        }
    
    print(json.dumps(output))
    
except Exception as e:
    # Output error state
    error_output = {
        "text": "✗",
        "class": "error",
        "tooltip": f"Git monitor error: {str(e)}"
    }
    print(json.dumps(error_output))