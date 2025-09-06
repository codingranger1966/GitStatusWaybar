#!/bin/bash
# Uninstallation script for GitStatusWaybar

set -e

echo "🗑️  Uninstalling GitStatusWaybar..."

# Function to prompt user
ask_user() {
    local prompt="$1"
    local default="$2"
    
    if [ "$default" = "y" ]; then
        echo -n "$prompt [Y/n]: "
    else
        echo -n "$prompt [y/N]: "
    fi
    
    read -r response
    case "$response" in
        [Yy]* ) return 0 ;;
        [Nn]* ) return 1 ;;
        "" ) [ "$default" = "y" ] && return 0 || return 1 ;;
        * ) echo "Please answer yes or no."; ask_user "$prompt" "$default" ;;
    esac
}

# Check what's installed
echo "📋 Checking installed components..."

SCRIPTS_DIR="$HOME/.config/waybar/scripts"
CONFIG_DIR="$HOME/.config/git-waybar"
LOG_DIR="$HOME/.local/share/git-waybar"

SCRIPTS_INSTALLED=false
CONFIG_INSTALLED=false
LOGS_EXIST=false

# Check for scripts
if ls "$SCRIPTS_DIR"/git-*.py &>/dev/null || ls "$SCRIPTS_DIR"/git-*.sh &>/dev/null; then
    SCRIPTS_INSTALLED=true
    echo "✓ Found GitStatusWaybar scripts in $SCRIPTS_DIR"
fi

# Check for config
if [ -d "$CONFIG_DIR" ]; then
    CONFIG_INSTALLED=true
    echo "✓ Found configuration in $CONFIG_DIR"
fi

# Check for logs
if [ -d "$LOG_DIR" ] && [ "$(ls -A "$LOG_DIR" 2>/dev/null)" ]; then
    LOGS_EXIST=true
    echo "✓ Found log files in $LOG_DIR"
fi

if ! $SCRIPTS_INSTALLED && ! $CONFIG_INSTALLED && ! $LOGS_EXIST; then
    echo "ℹ️  GitStatusWaybar doesn't appear to be installed."
    echo "   No scripts, config, or logs found."
    exit 0
fi

echo ""

# Remove scripts
if $SCRIPTS_INSTALLED; then
    if ask_user "Remove GitStatusWaybar scripts from waybar?" "y"; then
        echo "🗂️  Removing scripts..."
        rm -f "$SCRIPTS_DIR"/git-monitor.py
        rm -f "$SCRIPTS_DIR"/git-monitor.test.py
        rm -f "$SCRIPTS_DIR"/git-status-oneshot.py
        rm -f "$SCRIPTS_DIR"/git-status-oneshot-wrapper.sh
        rm -f "$SCRIPTS_DIR"/git-dropdown.py
        rm -f "$SCRIPTS_DIR"/git-dropdown-wrapper.py
        rm -f "$SCRIPTS_DIR"/git-dropdown.test.py
        rm -f "$SCRIPTS_DIR"/update-git-monitor-style.py
        rm -f "$SCRIPTS_DIR"/update-git-styles.sh
        echo "✅ Scripts removed"
    else
        echo "⏩ Keeping scripts"
    fi
fi

# Remove configuration
if $CONFIG_INSTALLED; then
    if ask_user "Remove configuration files? (This will delete your repository list and settings)" "n"; then
        echo "⚙️  Removing configuration..."
        rm -rf "$CONFIG_DIR"
        echo "✅ Configuration removed"
    else
        echo "⏩ Keeping configuration"
    fi
fi

# Remove logs
if $LOGS_EXIST; then
    if ask_user "Remove log files?" "y"; then
        echo "📄 Removing logs..."
        rm -rf "$LOG_DIR"
        echo "✅ Logs removed"
    else
        echo "⏩ Keeping logs"
    fi
fi

echo ""
echo "⚠️  Manual cleanup required:"
echo ""
echo "1. Remove the waybar module from your waybar config:"
echo "   Edit ~/.config/waybar/config.jsonc and remove:"
echo "   - \"custom/git-monitor\" from modules-right"
echo "   - The entire \"custom/git-monitor\" configuration block"
echo ""
echo "2. Remove CSS styles from ~/.config/waybar/style.css:"
echo "   Remove all #custom-git-monitor CSS rules"
echo ""
echo "3. Restart waybar:"
echo "   killall waybar && waybar &"
echo ""
echo "4. Remove this project directory if no longer needed:"
echo "   rm -rf $(pwd)"
echo ""

if ask_user "Open waybar config for manual editing?" "n"; then
    if command -v code &> /dev/null; then
        code ~/.config/waybar/config.jsonc
    elif command -v nano &> /dev/null; then
        nano ~/.config/waybar/config.jsonc
    elif command -v vim &> /dev/null; then
        vim ~/.config/waybar/config.jsonc
    else
        echo "Please manually edit ~/.config/waybar/config.jsonc"
    fi
fi

echo ""
echo "🎯 GitStatusWaybar uninstallation complete!"
echo "   Thank you for using GitStatusWaybar!"