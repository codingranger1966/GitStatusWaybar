#!/usr/bin/env python3
"""Logging configuration for Git Waybar Monitor."""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str = "git-waybar",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True,
    file_logging: bool = True
) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (defaults to ~/.local/share/git-waybar/git-waybar.log)
        console: Enable console logging
        file_logging: Enable file logging
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_logging:
        if log_file is None:
            log_dir = Path.home() / ".local" / "share" / "git-waybar"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "git-waybar.log"
        else:
            log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler to prevent log files from growing too large
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        module_name: Name of the module requesting the logger
        
    Returns:
        Logger instance for the module
    """
    return logging.getLogger(f"git-waybar.{module_name}")


# Environment variable configuration
def setup_from_env() -> logging.Logger:
    """
    Set up logging based on environment variables.
    
    Environment variables:
        GIT_WAYBAR_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        GIT_WAYBAR_LOG_FILE: Path to log file
        GIT_WAYBAR_LOG_CONSOLE: Enable/disable console logging (true/false)
        GIT_WAYBAR_LOG_FILE_ENABLED: Enable/disable file logging (true/false)
        
    Returns:
        Configured logger instance
    """
    level = os.environ.get("GIT_WAYBAR_LOG_LEVEL", "INFO")
    log_file = os.environ.get("GIT_WAYBAR_LOG_FILE")
    console = os.environ.get("GIT_WAYBAR_LOG_CONSOLE", "true").lower() == "true"
    file_logging = os.environ.get("GIT_WAYBAR_LOG_FILE_ENABLED", "true").lower() == "true"
    
    log_file_path = Path(log_file) if log_file else None
    
    return setup_logging(
        level=level,
        log_file=log_file_path,
        console=console,
        file_logging=file_logging
    )