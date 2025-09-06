#!/usr/bin/env python3
"""Update waybar CSS for git monitor based on configuration."""

import sys
from pathlib import Path

# Add project library to path
sys.path.insert(0, str(Path.home() / "Projects" / "GitStatusWaybar"))

try:
    from lib.config_loader import ConfigLoader
    
    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load()
    
    # Get display configuration
    display_config = config.get('display', {})
    size = display_config.get('size', 'medium')
    bold = display_config.get('bold', True)
    
    # Convert size to CSS values
    if size == 'small':
        font_size = '12px'
        min_width = '16px'
        padding = '0 1px'
    elif size == 'medium':
        font_size = '14px'
        min_width = '18px'
        padding = '0 2px'
    elif size == 'large':
        font_size = '18px'
        min_width = '20px'
        padding = '0 2px'
    elif isinstance(size, int) or size.isdigit():
        # Custom pixel size
        font_size = f'{size}px'
        min_width = f'{int(size) + 2}px'
        padding = '0 2px'
    else:
        # Default to medium
        font_size = '16px'
        min_width = '18px' 
        padding = '0 2px'
    
    font_weight = 'bold' if bold else 'normal'
    
    # Generate CSS
    css_content = f"""
#custom-git-monitor {{
  min-width: {min_width};
  margin: 0 7.5px;
  padding: {padding};
  font-size: {font_size};
  font-weight: {font_weight};
}}

#custom-git-monitor.clean {{
  color: #50fa7b;
}}

#custom-git-monitor.uncommitted {{
  color: #ff5555;
}}

#custom-git-monitor.untracked {{
  color: #ffb86c;
}}

#custom-git-monitor.unpushed {{
  color: #f1fa8c;
}}

#custom-git-monitor.upstream {{
  color: #8be9fd;
}}

#custom-git-monitor.multiple {{
  color: #bd93f9;
}}

#custom-git-monitor.error {{
  color: #6272a4;
}}
"""
    
    print(f"/* Git Monitor CSS - Size: {size}, Bold: {bold} */{css_content}")
    
except Exception as e:
    # Output error and use default CSS
    print(f"/* Error loading config: {e} - using defaults */")
    print("""
#custom-git-monitor {
  min-width: 24px;
  margin: 0 7.5px;
  padding: 0 6px;
  font-size: 16px;
  font-weight: bold;
}

#custom-git-monitor.clean {
  color: #50fa7b;
}

#custom-git-monitor.uncommitted {
  color: #ff5555;
}

#custom-git-monitor.untracked {
  color: #ffb86c;
}

#custom-git-monitor.unpushed {
  color: #f1fa8c;
}

#custom-git-monitor.upstream {
  color: #8be9fd;
}

#custom-git-monitor.multiple {
  color: #bd93f9;
}

#custom-git-monitor.error {
  color: #6272a4;
}
""")