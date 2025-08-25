# Git Waybar Monitor

A Waybar widget that monitors git repositories for uncommitted changes, unpushed commits, and upstream updates.

## Features

- Visual indicators for repository states (uncommitted, untracked, unpushed, upstream available)
- Clickable dropdown showing all repositories needing attention
- Configurable update intervals and colors
- Terminal integration for quick repository access
- SSH and GitHub CLI authentication support

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/GitStatusWaybar.git
cd GitStatusWaybar
```

2. Set up Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. The scripts are already installed in the proper locations:
- `~/.config/waybar/scripts/git-monitor.py`
- `~/.config/waybar/scripts/git-dropdown.py`

## Configuration

Create a configuration file at `~/.config/git-waybar/config.yaml`

## Logging

Logs are stored in `~/.local/share/git-waybar/git-waybar.log`

You can control logging via environment variables:
- `GIT_WAYBAR_LOG_LEVEL`: Set to DEBUG, INFO, WARNING, ERROR, or CRITICAL
- `GIT_WAYBAR_LOG_FILE`: Custom log file path
- `GIT_WAYBAR_LOG_CONSOLE`: Enable/disable console output (true/false)
- `GIT_WAYBAR_LOG_FILE_ENABLED`: Enable/disable file logging (true/false)

## Development

Run tests:
```bash
cd ~/Projects/GitStatusWaybar
source venv/bin/activate
pytest
```# Test change
