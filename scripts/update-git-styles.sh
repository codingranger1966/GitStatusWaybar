#!/bin/bash
# Update git monitor styles in waybar CSS based on config

WAYBAR_CSS="$HOME/.config/waybar/style.css"
BACKUP_CSS="$HOME/.config/waybar/style.css.backup"

# Create backup
cp "$WAYBAR_CSS" "$BACKUP_CSS"

# Generate new CSS
NEW_CSS=$(python3 "$HOME/.config/waybar/scripts/update-git-monitor-style.py")

# Create temporary file with updated CSS
TEMP_CSS=$(mktemp)

# Copy everything before git monitor section
awk '/\/\* Git Monitor CSS/ {exit} {print}' "$WAYBAR_CSS" > "$TEMP_CSS"

# Add new git monitor CSS
echo "$NEW_CSS" >> "$TEMP_CSS"

# Copy everything after the old git monitor section
awk '
    /^#custom-update \{/ {found=1}
    found {print}
' "$WAYBAR_CSS" >> "$TEMP_CSS"

# Replace the original file
mv "$TEMP_CSS" "$WAYBAR_CSS"

echo "✅ Git monitor styles updated based on config"
echo "💡 Restart waybar to see changes: killall waybar && waybar &"
echo "📄 Backup saved to: $BACKUP_CSS"