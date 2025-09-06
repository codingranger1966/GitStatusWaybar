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
    
    # Get color configuration
    colors_config = config.get('colors', {})
    colors = {
        'clean': colors_config.get('clean', '#50fa7b'),
        'uncommitted': colors_config.get('uncommitted', '#ff5555'),
        'untracked': colors_config.get('untracked', '#ffb86c'),
        'unpushed': colors_config.get('unpushed', '#f1fa8c'),
        'upstream': colors_config.get('upstream_available', '#8be9fd'),
        'multiple': colors_config.get('multiple', '#bd93f9'),
        'error': colors_config.get('error', '#6272a4')
    }
    
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
    
    # Generate CSS using configured colors
    css_content = f"""
#custom-git-monitor {{
  min-width: {min_width};
  margin: 0 7.5px;
  padding: {padding};
  font-size: {font_size};
  font-weight: {font_weight};
}}

#custom-git-monitor.clean {{
  color: {colors['clean']};
}}

#custom-git-monitor.uncommitted {{
  color: {colors['uncommitted']};
}}

#custom-git-monitor.untracked {{
  color: {colors['untracked']};
}}

#custom-git-monitor.unpushed {{
  color: {colors['unpushed']};
}}

#custom-git-monitor.upstream {{
  color: {colors['upstream']};
}}

#custom-git-monitor.multiple {{
  color: {colors['multiple']};
}}

#custom-git-monitor.error {{
  color: {colors['error']};
}}
"""
    
    print(f"/* Git Monitor CSS - Size: {size}, Bold: {bold}, Colors: configured */{css_content}")
    
except Exception as e:
    # Output error and use default CSS with fallback colors
    print(f"/* Error loading config: {e} - using defaults */")
    
    # Default colors (same as config defaults)
    default_colors = {
        'clean': '#50fa7b',
        'uncommitted': '#ff5555', 
        'untracked': '#ffb86c',
        'unpushed': '#f1fa8c',
        'upstream': '#8be9fd',
        'multiple': '#bd93f9',
        'error': '#6272a4'
    }
    
    fallback_css = f"""
#custom-git-monitor {{
  min-width: 20px;
  margin: 0 7.5px;
  padding: 0 2px;
  font-size: 16px;
  font-weight: bold;
}}

#custom-git-monitor.clean {{
  color: {default_colors['clean']};
}}

#custom-git-monitor.uncommitted {{
  color: {default_colors['uncommitted']};
}}

#custom-git-monitor.untracked {{
  color: {default_colors['untracked']};
}}

#custom-git-monitor.unpushed {{
  color: {default_colors['unpushed']};
}}

#custom-git-monitor.upstream {{
  color: {default_colors['upstream']};
}}

#custom-git-monitor.multiple {{
  color: {default_colors['multiple']};
}}

#custom-git-monitor.error {{
  color: {default_colors['error']};
}}
"""
    print(fallback_css)