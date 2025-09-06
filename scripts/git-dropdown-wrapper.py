#!/usr/bin/env python3
"""Simple wrapper for git dropdown that works without virtual env."""

import os
import subprocess
import sys
from pathlib import Path

# Try to use virtual environment first
venv_path = Path.home() / "Projects" / "GitStatusWaybar" / "venv"
if venv_path.exists():
    # Try to activate virtual environment
    activate_script = venv_path / "bin" / "activate"
    if activate_script.exists():
        # Run the actual dropdown script with venv
        try:
            cmd = f'cd "{Path.home() / "Projects" / "GitStatusWaybar"}" && source venv/bin/activate && python ~/.config/waybar/scripts/git-dropdown.py'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                exit(0)
        except Exception:
            pass

# Fallback: simple git dropdown without dependencies
config_path = Path.home() / ".config" / "git-waybar" / "config.yaml"
if not config_path.exists():
    print("No configuration found")
    exit(1)

# Simple YAML parser for repositories
repositories = []
try:
    with open(config_path, 'r') as f:
        in_repos = False
        for line in f:
            line = line.strip()
            if line == 'repositories:':
                in_repos = True
                continue
            elif in_repos:
                if line.startswith('- '):
                    repo_path = line[2:].strip()
                    if repo_path.startswith('~/'):
                        repo_path = str(Path.home() / repo_path[2:])
                    repositories.append(repo_path)
                elif line and not line.startswith('#') and not line.startswith('- '):
                    break
except Exception as e:
    print(f"Error reading config: {e}")
    exit(1)

if not repositories:
    print("No repositories configured")
    exit(0)

# Build simple repository list
entries = []
for repo_path in repositories:
    if os.path.exists(repo_path) and os.path.exists(os.path.join(repo_path, '.git')):
        repo_name = os.path.basename(repo_path)
        
        # Enhanced git status check
        try:
            # Check for uncommitted changes
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         cwd=repo_path, capture_output=True, text=True, timeout=5)
            
            if status_result.returncode == 0:
                lines = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
                modified_count = len([l for l in lines if l.startswith(' M') or l.startswith('M')])
                untracked_count = len([l for l in lines if l.startswith('??')])
                total_changes = len(lines)
                
                if total_changes == 0:
                    status = "✓"
                    detail = " (clean)"
                else:
                    status = "●"
                    details = []
                    if modified_count > 0:
                        details.append(f"{modified_count} modified")
                    if untracked_count > 0:
                        details.append(f"{untracked_count} untracked")
                    if total_changes > modified_count + untracked_count:
                        details.append(f"{total_changes - modified_count - untracked_count} other changes")
                    
                    detail = f" ({', '.join(details)})"
            else:
                status = "?"
                detail = " (git error)"
        except Exception:
            status = "?"
            detail = " (error)"
        
        entries.append(f"{status} {repo_name}{detail} | {repo_path}")

if not entries:
    print("No valid git repositories found")
    exit(0)

# Check for rofi or wofi
launcher = None
try:
    subprocess.run(['rofi', '--version'], capture_output=True, check=True)
    launcher = 'rofi'
except:
    try:
        subprocess.run(['wofi', '--version'], capture_output=True, check=True) 
        launcher = 'wofi'
    except:
        pass

if not launcher:
    print("No launcher (rofi/wofi) found")
    exit(1)

# Show dropdown
input_text = '\n'.join(entries)

if launcher == 'rofi':
    cmd = [
        'rofi', '-dmenu', '-i', 
        '-p', 'Select Repository to Open:',
        '-mesg', f'Found {len(entries)} repository(ies). Select one to open in terminal.',
        '-theme-str', 'window { width: 600px; } listview { lines: 8; }',
        '-no-custom'
    ]
else:
    cmd = [
        'wofi', '--dmenu', '--insensitive',
        '--prompt', 'Select Repository to Open:',
        '--lines', str(min(10, len(entries))),
        '--width', '600'
    ]

try:
    result = subprocess.run(cmd, input=input_text, capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0 and result.stdout.strip():
        selected = result.stdout.strip()
        if ' | ' in selected:
            repo_path = selected.split(' | ')[-1]
            
            # Open terminal in repository
            terminals = ['alacritty', 'kitty', 'gnome-terminal', 'konsole', 'xterm']
            
            for terminal in terminals:
                try:
                    subprocess.run([terminal, '--version'], capture_output=True, check=True)
                    
                    if terminal == 'alacritty':
                        cmd = [terminal, '--working-directory', repo_path]
                    elif terminal == 'kitty':
                        cmd = [terminal, '--directory', repo_path]
                    elif terminal == 'gnome-terminal':
                        cmd = [terminal, '--working-directory', repo_path]
                    elif terminal == 'konsole':
                        cmd = [terminal, '--workdir', repo_path]
                    else:
                        cmd = [terminal, '-e', f'bash -c "cd {repo_path} && bash"']
                    
                    subprocess.Popen(cmd, start_new_session=True)
                    break
                except Exception:
                    continue

except Exception as e:
    print(f"Error: {e}")