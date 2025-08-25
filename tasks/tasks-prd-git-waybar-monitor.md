## Relevant Files

- `~/.config/waybar/scripts/git-monitor.py` - Main monitoring script that checks repository statuses and outputs JSON for Waybar
- `~/.config/waybar/scripts/git-monitor.test.py` - Unit tests for git-monitor.py
- `~/.config/waybar/scripts/git-dropdown.py` - Click handler script that displays repository dropdown using rofi/wofi
- `~/.config/waybar/scripts/git-dropdown.test.py` - Unit tests for git-dropdown.py
- `~/.config/git-waybar/config.yaml` - Configuration file for repository paths and settings
- `~/.config/waybar/config` - Waybar configuration file that needs module definition added
- `~/.config/waybar/style.css` - Waybar styles that need CSS classes for the git monitor widget
- `lib/git_status_checker.py` - Core library for git status checking operations
- `lib/git_status_checker.test.py` - Unit tests for git_status_checker.py
- `lib/config_loader.py` - Configuration file loader and validator
- `lib/config_loader.test.py` - Unit tests for config_loader.py

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `git-monitor.py` and `git-monitor.test.py` in the same directory).
- Use `npx jest [optional/path/to/test/file]` to run tests. Running without a path executes all tests found by the Jest configuration.

## Tasks

- [x] 1.0 Set up project structure and core libraries
  - [x] 1.1 Create directory structure for the project (~/.config/waybar/scripts, ~/.config/git-waybar, lib)
  - [x] 1.2 Set up Python virtual environment and install required dependencies (GitPython, PyYAML, pytest)
  - [x] 1.3 Create initial file stubs for all Python modules
  - [x] 1.4 Set up basic logging configuration for debugging
- [x] 2.0 Implement git status checking functionality
  - [x] 2.1 Create GitStatusChecker class with methods for checking repository status
  - [x] 2.2 Implement uncommitted changes detection using git status --porcelain
  - [x] 2.3 Implement untracked files detection
  - [x] 2.4 Implement unpushed commits detection by comparing local and remote branches
  - [x] 2.5 Implement upstream changes detection with git fetch (with timeout and auth handling)
  - [x] 2.6 Add SSH agent detection and GitHub CLI fallback for authentication
  - [x] 2.7 Create status priority system for determining overall widget color
  - [x] 2.8 Add error handling for invalid paths and non-git directories
  - [x] 2.9 Write unit tests for GitStatusChecker class
- [x] 3.0 Create configuration system
  - [x] 3.1 Define configuration schema in YAML format
  - [x] 3.2 Implement ConfigLoader class to read and parse config.yaml
  - [x] 3.3 Add configuration validation and default values
  - [x] 3.4 Create sample configuration file with example repositories
  - [x] 3.5 Implement configuration reload functionality
  - [x] 3.6 Write unit tests for ConfigLoader class
- [ ] 4.0 Develop Waybar integration script
  - [x] 4.1 Create main git-monitor.py script structure
  - [ ] 4.2 Implement repository status checking loop with configurable interval
  - [ ] 4.3 Generate Waybar-compatible JSON output with text, class, and tooltip
  - [ ] 4.4 Implement color/icon selection based on repository states
  - [ ] 4.5 Add manual refresh capability via signal handling
  - [ ] 4.6 Implement caching mechanism to improve performance
  - [ ] 4.7 Add Waybar module configuration to ~/.config/waybar/config
  - [ ] 4.8 Add CSS styles for different status classes to ~/.config/waybar/style.css
  - [ ] 4.9 Write integration tests for git-monitor.py
- [ ] 5.0 Implement dropdown interface
  - [ ] 5.1 Create git-dropdown.py script for handling click events
  - [ ] 5.2 Implement rofi/wofi detection and selection
  - [ ] 5.3 Generate formatted repository list with status indicators
  - [ ] 5.4 Implement terminal launcher for selected repository
  - [ ] 5.5 Add support for right-click manual refresh trigger
  - [ ] 5.6 Handle dropdown styling to match system theme
  - [ ] 5.7 Write tests for dropdown functionality