# Product Requirements Document: Git Waybar Monitor Widget

## Introduction/Overview

The Git Waybar Monitor Widget is a system monitoring tool that provides real-time visibility of git repository statuses directly in the Waybar interface. It solves the problem of developers forgetting about uncommitted changes, unpushed commits, or pending upstream updates across multiple repositories. The widget offers at-a-glance status indicators and quick access to repositories that need attention, helping developers maintain clean repository states and stay synchronized with remote branches.

## Goals

1. Provide immediate visual feedback when any monitored git repository has uncommitted changes, untracked files, unpushed commits, or available upstream changes
2. Enable quick navigation to repositories needing attention through a dropdown interface
3. Support configurable monitoring of multiple repositories with customizable update intervals
4. Integrate seamlessly with Waybar and Wayland desktop environments
5. Minimize system resource usage while providing timely status updates

## User Stories

1. As a developer, I want to see a visual indicator in my status bar when any of my git repositories have uncommitted changes, so that I don't forget to commit my work
2. As a developer, I want to quickly see which repositories need attention without having to check each one manually, so that I can prioritize my git maintenance tasks
3. As a developer, I want to click on a repository in the dropdown to open a terminal in that directory, so that I can quickly address the issues
4. As a developer, I want to configure which repositories are monitored and how often they're checked, so that I can customize the tool to my workflow
5. As a developer, I want to see different colors for different repository states, so that I can quickly understand the type of attention needed
6. As a developer, I want to manually trigger a status check, so that I can get immediate updates without waiting for the next scheduled check
7. As a developer, I want to know when upstream changes are available, so that I can keep my local repositories synchronized

## Functional Requirements

1. The system must monitor configured git repositories for the following states:
   - Uncommitted changes (modified files)
   - Untracked files
   - Unpushed commits
   - Available upstream changes (when remote is configured)

2. The system must display a colored indicator in Waybar with the following states:
   - Green: All repositories clean
   - Yellow: Unpushed commits exist
   - Orange: Untracked files present
   - Red: Uncommitted changes detected
   - Blue: Upstream changes available
   - Purple: Multiple status types present
   - Gray/Error: Repository path invalid or not a git repository

3. The system must show a tooltip on hover displaying the count of repositories needing attention

4. The system must provide a clickable dropdown (using rofi or wofi) that:
   - Lists all repositories alphabetically
   - Shows the status of each repository
   - Indicates error states for invalid repository paths
   - Opens a terminal in the selected repository's directory when clicked

5. The system must support right-click functionality to manually trigger a status check

6. The system must read repository paths from a YAML configuration file located at `~/.config/git-waybar/config.yaml`

7. The configuration file must support:
   - List of repository paths to monitor
   - Update interval (in seconds)
   - Custom colors for each status type
   - Terminal emulator command preference

8. The system must check repository status at the configured interval (default: 30 seconds)

9. The system must handle authentication for remote checks:
   - Use SSH agent for SSH-based remotes when available
   - Fall back to GitHub CLI (`gh`) for GitHub repositories when available
   - Skip remote checks if authentication is not available

10. The system must output JSON format compatible with Waybar custom modules

11. The system must handle errors gracefully:
    - Continue monitoring other repositories if one fails
    - Display error indicators for problematic repositories
    - Log errors to a file for debugging

12. The system must be efficient:
    - Use `git status --porcelain` for quick status checks
    - Cache results between checks
    - Avoid blocking operations

## Non-Goals (Out of Scope)

1. This feature will NOT provide a full git GUI interface
2. This feature will NOT perform automatic commits or pushes
3. This feature will NOT support monitoring non-git version control systems
4. This feature will NOT provide detailed diff viewing
5. This feature will NOT handle merge conflict resolution
6. This feature will NOT support Windows or macOS-specific status bars
7. This feature will NOT provide repository statistics or analytics
8. This feature will NOT support credential storage (relies on existing SSH agent or gh auth)

## Design Considerations

- The widget should use minimal screen space in the Waybar
- Colors should be distinguishable for color-blind users (consider using icons in addition to colors)
- The dropdown interface should match the user's existing Wayland theme
- Status icons should follow common git GUI conventions where applicable

## Technical Considerations

- Python 3.8+ should be used for compatibility and async support
- GitPython library should be used for git operations
- YAML parsing should use PyYAML
- The script should handle subprocess calls safely for terminal launching
- Remote checks should timeout after 5 seconds to prevent hanging
- The system should use GitHub CLI (`gh api`) when available for better authentication handling
- SSH agent should be detected and used when available
- File watching could be considered for future optimization (using inotify)

## Success Metrics

1. Widget updates repository status within 2 seconds of the configured interval
2. Dropdown appears within 500ms of click
3. CPU usage remains below 1% during idle monitoring
4. Memory usage stays under 50MB for monitoring up to 20 repositories
5. Error recovery succeeds without manual intervention in 95% of cases
6. Manual status check completes within 3 seconds for up to 10 repositories

## Open Questions

1. Should the widget support monitoring submodules within repositories?
2. Should there be a maximum number of repositories shown in the dropdown to prevent UI overflow?
3. Should the widget support different terminal emulators beyond the system default?
4. Should there be an option to exclude certain file patterns from triggering the dirty state?
5. Would a notification system for critical changes (like conflicts) be useful?
6. Should the widget support workspace/project grouping for better organization?