# Git Waybar Monitor

A Waybar widget that monitors your git repositories for uncommitted changes, unpushed commits, and upstream updates with an interactive dropdown interface.

![Git Status Widget](https://img.shields.io/badge/Waybar-Widget-blue) ![Python](https://img.shields.io/badge/Python-3.8+-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

✨ **Visual Status Indicators**
- Color-coded status dots in waybar (red for uncommitted, yellow for unpushed, etc.)
- Configurable size and appearance
- Custom icons for different git states

🎯 **Interactive Dropdown**
- Click to open wofi/rofi dropdown with repository details
- Shows detailed status information (modified files, untracked files, etc.)
- Direct terminal access to selected repositories

⚙️ **Highly Configurable**
- Custom update intervals and cache duration
- Configurable colors and display options
- Support for multiple terminal emulators
- SSH and GitHub CLI authentication support

## Quick Install

```bash
git clone https://github.com/yourusername/GitStatusWaybar.git
cd GitStatusWaybar
./install.sh
```

## Dependencies

- **Python 3.8+** with pip
- **Git** 
- **Waybar** (works on both Wayland and X11)
- **Dropdown launcher**:
  - **Wayland**: wofi (recommended) or rofi
  - **X11**: rofi (wofi won't work on X11)

Install dropdown launcher:

**Arch Linux / Manjaro:**
```bash
# For Wayland (recommended)
sudo pacman -S wofi

# For X11 or as Wayland alternative
sudo pacman -S rofi
```

**Ubuntu / Debian:**
```bash
# For Wayland (recommended)
sudo apt install wofi

# For X11 or as Wayland alternative
sudo apt install rofi
```

**Fedora:**
```bash
# For Wayland (recommended)
sudo dnf install wofi

# For X11 or as Wayland alternative
sudo dnf install rofi
```

**openSUSE:**
```bash
# For Wayland (recommended)
sudo zypper install wofi

# For X11 or as Wayland alternative
sudo zypper install rofi
```

**Note:** wofi may not be available in all distribution repositories. If not available, rofi works on both Wayland and X11 as an alternative.

## Manual Installation

1. **Clone and setup:**
   ```bash
   git clone https://github.com/yourusername/GitStatusWaybar.git
   cd GitStatusWaybar
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install scripts:**
   ```bash
   mkdir -p ~/.config/waybar/scripts ~/.config/git-waybar
   cp scripts/*.py ~/.config/waybar/scripts/
   cp scripts/*.sh ~/.config/waybar/scripts/
   cp config/config.yaml ~/.config/git-waybar/
   chmod +x ~/.config/waybar/scripts/*
   ```

3. **Configure waybar:**
   
   Add to your `~/.config/waybar/config.jsonc`:
   ```json
   {
     "modules-right": [
       "custom/git-monitor",
       // ... your other modules
     ],
     "custom/git-monitor": {
       "exec": "/home/user/.config/waybar/scripts/git-status-oneshot-wrapper.sh",
       "return-type": "json",
       "interval": 30,
       "tooltip": false,
       "on-click": "/home/user/.config/waybar/scripts/git-dropdown-wrapper.py"
     }
   }
   ```

4. **Add CSS styles:**
   
   Add to your `~/.config/waybar/style.css`:
   ```css
   #custom-git-monitor {
     min-width: 20px;
     margin: 0 7.5px;
     padding: 0 2px;
     font-size: 18px;
     font-weight: bold;
   }
   
   #custom-git-monitor.uncommitted { color: #ff5555; }
   #custom-git-monitor.untracked { color: #ffb86c; }
   #custom-git-monitor.unpushed { color: #f1fa8c; }
   #custom-git-monitor.upstream { color: #8be9fd; }
   #custom-git-monitor.multiple { color: #bd93f9; }
   #custom-git-monitor.error { color: #6272a4; }
   ```

5. **Restart waybar:**
   ```bash
   killall waybar && waybar &
   ```

## Configuration

Edit `~/.config/git-waybar/config.yaml`:

```yaml
# Update interval in seconds
update_interval: 30

# Repositories to monitor
repositories:
  - ~/Projects/MyProject
  - ~/Documents/AnotherRepo

# Display configuration
display:
  size: large          # small, medium, large, or pixel size (e.g., 20)
  bold: true
  icons:
    uncommitted: "●"    # Solid dot for uncommitted changes
    untracked: "○"      # Open circle for untracked files
    unpushed: "↑"       # Up arrow for unpushed commits
    upstream: "↓"       # Down arrow for upstream changes
    multiple: "!"       # Exclamation for multiple issues
    error: "✗"          # X for errors

# Colors for different states
colors:
  uncommitted: "#ff5555"      # Red
  untracked: "#ffb86c"        # Orange  
  unpushed: "#f1fa8c"         # Yellow
  upstream_available: "#8be9fd" # Cyan
  multiple: "#bd93f9"         # Purple
  error: "#6272a4"            # Gray

# Authentication settings
auth:
  enable_fetch: true
  fetch_timeout: 5
  use_gh_cli: true
  use_ssh_agent: true
```

## Usage

1. **Visual Status**: The widget shows a colored dot in waybar indicating git status
2. **Click for Dropdown**: Click the dot to open an interactive dropdown
3. **Repository Selection**: Choose a repository from the dropdown
4. **Terminal Access**: Selected repository opens in your terminal

## Customization

### Change Display Size or Colors
```bash
# Edit ~/.config/git-waybar/config.yaml, then update styles:
~/.config/waybar/scripts/update-git-styles.sh
killall waybar && waybar &
```

**Example color customization:**
```yaml
colors:
  uncommitted: "#ff0000"      # Bright red
  untracked: "#ffa500"        # Orange  
  unpushed: "#ffff00"         # Yellow
  upstream_available: "#00ffff" # Cyan
  multiple: "#ff00ff"         # Magenta
```

### Custom Terminal
Edit `config.yaml`:
```yaml
terminal: alacritty  # or kitty, gnome-terminal, konsole, etc.
```

### Custom Icons
Edit the `icons` section in `config.yaml` to use your preferred symbols.

## Troubleshooting

**Widget not appearing:**
- Check waybar config syntax with `waybar -l debug`
- Verify scripts are executable: `chmod +x ~/.config/waybar/scripts/*`

**Dropdown not working:**
- **Wayland**: Install wofi using your distro's package manager
- **X11**: Install rofi using your distro's package manager  
- Check script path in waybar config
- Verify launcher is in PATH: `which wofi` or `which rofi`

**No repositories shown:**
- Verify paths in `~/.config/git-waybar/config.yaml`
- Check repository permissions

## Development

**Run tests:**
```bash
source venv/bin/activate
pytest
```

**Debug mode:**
```bash
export GIT_WAYBAR_LOG_LEVEL=DEBUG
export GIT_WAYBAR_LOG_CONSOLE=true
```

## Architecture

- **git-monitor.py**: Full-featured monitoring daemon
- **git-status-oneshot.py**: Lightweight status checker for waybar
- **git-dropdown-wrapper.py**: Interactive dropdown interface
- **lib/**: Core libraries for git operations and configuration
- **scripts/**: Installation and utility scripts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Compatibility

**Operating Systems:**
- Any Linux distribution with Python 3.8+
- Should work on other Unix-like systems (BSD, macOS) with appropriate dependencies

**Display Servers:**
- **Wayland**: Full compatibility with wofi (recommended) or rofi
- **X11**: Compatible when running Waybar on X11 window managers (requires rofi)

**Window Managers/Compositors:**
- Wayland: sway, hyprland, river, wayfire, etc.
- X11: i3, bspwm, openbox, etc.
- Any system running Waybar

## Credits

Built for Waybar with support for both Wayland and X11 environments. Optimized for modern Linux desktop workflows.