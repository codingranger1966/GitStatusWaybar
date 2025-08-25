#!/usr/bin/env python3
"""Configuration loading and validation."""

import os
import copy
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import yaml

from .logger_config import get_logger

logger = get_logger("config_loader")


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """Load and validate configuration from YAML file."""
    
    DEFAULT_CONFIG_PATH = Path.home() / ".config" / "git-waybar" / "config.yaml"
    
    DEFAULT_CONFIG = {
        "update_interval": 30,
        "repositories": [],
        "colors": {
            "clean": "#50fa7b",
            "uncommitted": "#ff5555",
            "untracked": "#ffb86c",
            "unpushed": "#f1fa8c",
            "upstream_available": "#8be9fd",
            "multiple": "#bd93f9",
            "error": "#6272a4"
        },
        "terminal": "gnome-terminal",
        "terminal_command": None,
        "dropdown_launcher": "rofi",
        "dropdown": {
            "max_items": 20,
            "show_full_path": False,
            "sort_by": "alphabetical"
        },
        "auth": {
            "enable_fetch": True,
            "fetch_timeout": 5,
            "use_gh_cli": True,
            "use_ssh_agent": True
        },
        "logging": {
            "level": "INFO",
            "file": None,
            "console": False
        },
        "advanced": {
            "cache_duration": 5,
            "parallel_checks": 4,
            "ignore_patterns": []
        },
        "notifications": {
            "enabled": False,
            "notify_on": ["uncommitted", "error"],
            "cooldown": 300
        }
    }
    
    # Valid terminal emulators
    VALID_TERMINALS = [
        "gnome-terminal", "konsole", "alacritty", "kitty", 
        "xterm", "wezterm", "foot", "terminator", "tilix"
    ]
    
    # Valid dropdown launchers
    VALID_LAUNCHERS = ["rofi", "wofi"]
    
    # Valid sort options
    VALID_SORT_OPTIONS = ["alphabetical", "status", "modified"]
    
    # Valid log levels
    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    # Valid statuses
    VALID_STATUSES = [
        "clean", "uncommitted", "untracked", "unpushed", 
        "upstream_available", "multiple", "error"
    ]
    
    def __init__(self, config_path: Optional[Union[Path, str]] = None):
        """
        Initialize ConfigLoader.
        
        Args:
            config_path: Optional path to configuration file
        """
        if config_path:
            self.config_path = Path(config_path) if isinstance(config_path, str) else config_path
        else:
            self.config_path = self.DEFAULT_CONFIG_PATH
        
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self._loaded = False
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Start with defaults
        config = copy.deepcopy(self.DEFAULT_CONFIG)
        
        # Check if config file exists
        if not self.config_path.exists():
            logger.info(f"Configuration file not found at {self.config_path}, using defaults")
            logger.info("Creating sample configuration file...")
            self.create_sample_config()
            self.config = config
            self._loaded = True
            return config
        
        # Load YAML file
        try:
            with open(self.config_path, 'r') as f:
                user_config = yaml.safe_load(f) or {}
            logger.info(f"Loaded configuration from {self.config_path}")
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Error reading configuration file: {e}")
        
        # Merge user config with defaults
        config = self._merge_configs(config, user_config)
        
        # Expand paths
        config = self._expand_paths(config)
        
        # Validate configuration
        if not self.validate(config):
            raise ConfigValidationError("Configuration validation failed")
        
        self.config = config
        self._loaded = True
        return config
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """
        Recursively merge user configuration with defaults.
        
        Args:
            default: Default configuration
            user: User configuration
            
        Returns:
            Merged configuration
        """
        result = copy.deepcopy(default)
        
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                result[key] = self._merge_configs(result[key], value)
            else:
                # Override with user value
                result[key] = value
        
        return result
    
    def _expand_paths(self, config: Dict) -> Dict:
        """
        Expand ~ in paths to user home directory.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with expanded paths
        """
        # Expand repository paths
        if "repositories" in config:
            config["repositories"] = [
                str(Path(repo).expanduser()) if repo else repo
                for repo in config["repositories"]
            ]
        
        # Expand log file path
        if "logging" in config and config["logging"].get("file"):
            config["logging"]["file"] = str(Path(config["logging"]["file"]).expanduser())
        
        return config
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure and values.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            # Validate update interval
            if not isinstance(config.get("update_interval"), (int, float)):
                raise ConfigValidationError("update_interval must be a number")
            if config["update_interval"] < 1 or config["update_interval"] > 3600:
                raise ConfigValidationError("update_interval must be between 1 and 3600 seconds")
            
            # Validate repositories
            if not isinstance(config.get("repositories"), list):
                raise ConfigValidationError("repositories must be a list")
            
            # Validate colors
            if "colors" in config:
                if not isinstance(config["colors"], dict):
                    raise ConfigValidationError("colors must be a dictionary")
                for status, color in config["colors"].items():
                    if status not in self.VALID_STATUSES and status != "clean":
                        logger.warning(f"Unknown status in colors: {status}")
                    if not self._is_valid_color(color):
                        raise ConfigValidationError(f"Invalid color format for {status}: {color}")
            
            # Validate terminal
            if "terminal" in config:
                if config["terminal"] not in self.VALID_TERMINALS:
                    # Allow custom terminal if terminal_command is provided
                    if not config.get("terminal_command"):
                        logger.warning(f"Unknown terminal: {config['terminal']}, using default")
                        config["terminal"] = self.DEFAULT_CONFIG["terminal"]
            
            # Validate dropdown launcher
            if "dropdown_launcher" in config:
                if config["dropdown_launcher"] not in self.VALID_LAUNCHERS:
                    logger.warning(f"Unknown dropdown launcher: {config['dropdown_launcher']}, using rofi")
                    config["dropdown_launcher"] = "rofi"
            
            # Validate dropdown settings
            if "dropdown" in config:
                dropdown = config["dropdown"]
                if "max_items" in dropdown:
                    if not isinstance(dropdown["max_items"], int) or dropdown["max_items"] < 0:
                        raise ConfigValidationError("dropdown.max_items must be a non-negative integer")
                if "sort_by" in dropdown:
                    if dropdown["sort_by"] not in self.VALID_SORT_OPTIONS:
                        raise ConfigValidationError(f"dropdown.sort_by must be one of {self.VALID_SORT_OPTIONS}")
            
            # Validate auth settings
            if "auth" in config:
                auth = config["auth"]
                if "fetch_timeout" in auth:
                    if not isinstance(auth["fetch_timeout"], (int, float)):
                        raise ConfigValidationError("auth.fetch_timeout must be a number")
                    if auth["fetch_timeout"] < 1 or auth["fetch_timeout"] > 60:
                        raise ConfigValidationError("auth.fetch_timeout must be between 1 and 60 seconds")
            
            # Validate logging settings
            if "logging" in config:
                log_config = config["logging"]
                if "level" in log_config:
                    if log_config["level"] not in self.VALID_LOG_LEVELS:
                        raise ConfigValidationError(f"logging.level must be one of {self.VALID_LOG_LEVELS}")
            
            # Validate advanced settings
            if "advanced" in config:
                advanced = config["advanced"]
                if "cache_duration" in advanced:
                    if not isinstance(advanced["cache_duration"], (int, float)):
                        raise ConfigValidationError("advanced.cache_duration must be a number")
                    if advanced["cache_duration"] < 0 or advanced["cache_duration"] > 60:
                        raise ConfigValidationError("advanced.cache_duration must be between 0 and 60 seconds")
                if "parallel_checks" in advanced:
                    if not isinstance(advanced["parallel_checks"], int):
                        raise ConfigValidationError("advanced.parallel_checks must be an integer")
                    if advanced["parallel_checks"] < 1 or advanced["parallel_checks"] > 10:
                        raise ConfigValidationError("advanced.parallel_checks must be between 1 and 10")
            
            # Validate notifications
            if "notifications" in config:
                notif = config["notifications"]
                if "notify_on" in notif:
                    if not isinstance(notif["notify_on"], list):
                        raise ConfigValidationError("notifications.notify_on must be a list")
                    for status in notif["notify_on"]:
                        if status not in self.VALID_STATUSES:
                            logger.warning(f"Unknown status in notifications.notify_on: {status}")
                if "cooldown" in notif:
                    if not isinstance(notif["cooldown"], (int, float)):
                        raise ConfigValidationError("notifications.cooldown must be a number")
                    if notif["cooldown"] < 0 or notif["cooldown"] > 3600:
                        raise ConfigValidationError("notifications.cooldown must be between 0 and 3600 seconds")
            
            return True
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"Unexpected validation error: {e}")
    
    def _is_valid_color(self, color: str) -> bool:
        """
        Check if a color string is valid hex format.
        
        Args:
            color: Color string to validate
            
        Returns:
            True if valid hex color
        """
        if not isinstance(color, str):
            return False
        if not color.startswith("#"):
            return False
        if len(color) not in [7, 4]:  # #RRGGBB or #RGB
            return False
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False
    
    def reload(self) -> Dict[str, Any]:
        """
        Reload configuration from file.
        
        Returns:
            Updated configuration dictionary
        """
        logger.info("Reloading configuration...")
        self._loaded = False
        return self.load()
    
    def create_sample_config(self) -> None:
        """Create a sample configuration file if none exists."""
        if self.config_path.exists():
            logger.info(f"Configuration file already exists at {self.config_path}")
            return
        
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create sample configuration
        sample_config = {
            "update_interval": 30,
            "repositories": [
                "~/Projects/my-project",
                "~/Documents/notes",
            ],
            "colors": self.DEFAULT_CONFIG["colors"],
            "terminal": "gnome-terminal",
            "dropdown_launcher": "rofi",
            "auth": {
                "enable_fetch": True,
                "fetch_timeout": 5
            }
        }
        
        # Write sample configuration
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(sample_config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Created sample configuration at {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to create sample configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Supports nested keys with dot notation (e.g., "auth.fetch_timeout").
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if not self._loaded:
            self.load()
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_repositories(self) -> List[str]:
        """
        Get list of repository paths.
        
        Returns:
            List of repository paths with ~ expanded
        """
        return self.get("repositories", [])
    
    def get_colors(self) -> Dict[str, str]:
        """
        Get color configuration.
        
        Returns:
            Dictionary of status to color mappings
        """
        return self.get("colors", self.DEFAULT_CONFIG["colors"])
    
    def get_update_interval(self) -> int:
        """
        Get update interval in seconds.
        
        Returns:
            Update interval
        """
        return self.get("update_interval", 30)