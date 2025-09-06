#!/bin/bash
# Installation script for GitStatusWaybar

set -e

echo "🚀 Installing GitStatusWaybar..."

# Check dependencies
echo "📋 Checking dependencies..."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check for git
if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed"
    exit 1
fi

# Check for rofi or wofi
if ! command -v rofi &> /dev/null && ! command -v wofi &> /dev/null; then
    echo "⚠️  Neither rofi nor wofi found. Install one for dropdown functionality:"
    echo ""
    echo "For Wayland (recommended): install 'wofi' using your package manager"
    echo "For X11 (or alternative): install 'rofi' using your package manager"
    echo ""
    echo "Examples:"
    echo "  Arch/Manjaro: sudo pacman -S wofi"
    echo "  Ubuntu/Debian: sudo apt install wofi"
    echo "  Fedora: sudo dnf install wofi"
    echo "  openSUSE: sudo zypper install wofi"
    echo ""
    echo "💡 Note: On X11 systems, only rofi will work (wofi is Wayland-only)"
    echo ""
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p ~/.config/waybar/scripts
mkdir -p ~/.config/git-waybar
mkdir -p ~/.local/share/git-waybar

# Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Copy scripts
echo "📄 Installing scripts..."
cp scripts/*.py ~/.config/waybar/scripts/
cp scripts/*.sh ~/.config/waybar/scripts/
chmod +x ~/.config/waybar/scripts/*.py
chmod +x ~/.config/waybar/scripts/*.sh

# Copy configuration if it doesn't exist
if [ ! -f ~/.config/git-waybar/config.yaml ]; then
    echo "⚙️  Installing default configuration..."
    cp config/config.yaml ~/.config/git-waybar/
else
    echo "⚙️  Configuration already exists, skipping..."
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit ~/.config/git-waybar/config.yaml to configure your repositories"
echo "2. Add the waybar module to your config (see examples/waybar/config-example.jsonc)"
echo "3. Add the CSS styles to your waybar (see examples/waybar/style-example.css)"
echo "4. Restart waybar: killall waybar && waybar &"
echo ""
echo "🔧 To update CSS based on config changes:"
echo "   ~/.config/waybar/scripts/update-git-styles.sh"
echo ""
echo "🧪 To run tests:"
echo "   source venv/bin/activate && pytest"
echo ""
echo "🗑️  To uninstall:"
echo "   ./uninstall.sh"