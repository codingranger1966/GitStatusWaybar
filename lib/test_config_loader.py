#!/usr/bin/env python3
"""Tests for config_loader module."""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import yaml

from lib.config_loader import ConfigLoader, ConfigValidationError


class TestConfigLoader:
    """Test ConfigLoader class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.yaml"
        self.loader = ConfigLoader(config_path=self.config_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default_path(self):
        """Test ConfigLoader initialization with default path."""
        loader = ConfigLoader()
        assert loader.config_path == ConfigLoader.DEFAULT_CONFIG_PATH
        assert not loader._loaded
    
    def test_init_custom_path_string(self):
        """Test ConfigLoader initialization with custom string path."""
        custom_path = "/custom/path/config.yaml"
        loader = ConfigLoader(config_path=custom_path)
        assert loader.config_path == Path(custom_path)
    
    def test_init_custom_path_pathlib(self):
        """Test ConfigLoader initialization with Path object."""
        custom_path = Path("/custom/path/config.yaml")
        loader = ConfigLoader(config_path=custom_path)
        assert loader.config_path == custom_path
    
    def test_load_missing_file_creates_sample(self):
        """Test loading when configuration file doesn't exist creates sample."""
        config = self.loader.load()
        
        # Should return defaults
        assert config == self.loader.DEFAULT_CONFIG
        assert self.loader._loaded
        
        # Should create sample file
        assert self.config_path.exists()
        
        # Sample file should be valid YAML
        with open(self.config_path, 'r') as f:
            sample_config = yaml.safe_load(f)
        assert "repositories" in sample_config
        assert "update_interval" in sample_config
    
    def test_load_valid_config(self):
        """Test loading valid configuration."""
        # Create a valid config file
        valid_config = {
            "update_interval": 60,
            "repositories": ["~/test/repo1", "~/test/repo2"],
            "colors": {
                "clean": "#00ff00",
                "uncommitted": "#ff0000"
            }
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(valid_config, f)
        
        config = self.loader.load()
        
        assert config["update_interval"] == 60
        assert len(config["repositories"]) == 2
        assert config["colors"]["clean"] == "#00ff00"
        # Check that defaults are merged
        assert "terminal" in config
        assert config["terminal"] == self.loader.DEFAULT_CONFIG["terminal"]
    
    def test_load_invalid_yaml(self):
        """Test loading invalid YAML file."""
        # Create invalid YAML
        with open(self.config_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.load()
        assert "Invalid YAML" in str(exc_info.value)
    
    def test_merge_configs(self):
        """Test configuration merging."""
        default = {
            "a": 1,
            "b": {"c": 2, "d": 3},
            "e": [1, 2, 3]
        }
        
        user = {
            "a": 10,
            "b": {"c": 20},
            "f": 4
        }
        
        result = self.loader._merge_configs(default, user)
        
        assert result["a"] == 10  # Overridden
        assert result["b"]["c"] == 20  # Nested override
        assert result["b"]["d"] == 3  # Nested default preserved
        assert result["e"] == [1, 2, 3]  # Default preserved
        assert result["f"] == 4  # New key added
    
    def test_expand_paths(self):
        """Test path expansion."""
        config = {
            "repositories": ["~/repo1", "/absolute/repo2", ""],
            "logging": {"file": "~/logs/app.log"}
        }
        
        expanded = self.loader._expand_paths(config)
        
        home = str(Path.home())
        assert expanded["repositories"][0] == f"{home}/repo1"
        assert expanded["repositories"][1] == "/absolute/repo2"
        assert expanded["repositories"][2] == ""  # Empty preserved
        assert expanded["logging"]["file"] == f"{home}/logs/app.log"
    
    def test_validate_update_interval(self):
        """Test update interval validation."""
        # Valid interval
        config = {"update_interval": 30, "repositories": []}
        assert self.loader.validate(config)
        
        # Invalid type
        config = {"update_interval": "30", "repositories": []}
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "must be a number" in str(exc_info.value)
        
        # Out of range
        config = {"update_interval": 3601, "repositories": []}
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "between 1 and 3600" in str(exc_info.value)
    
    def test_validate_repositories(self):
        """Test repositories validation."""
        # Valid
        config = {"update_interval": 30, "repositories": ["/path/to/repo"]}
        assert self.loader.validate(config)
        
        # Invalid type
        config = {"update_interval": 30, "repositories": "not-a-list"}
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "must be a list" in str(exc_info.value)
    
    def test_validate_colors(self):
        """Test color validation."""
        # Valid hex colors
        config = {
            "update_interval": 30,
            "repositories": [],
            "colors": {
                "clean": "#00ff00",
                "uncommitted": "#f00"  # Short form
            }
        }
        assert self.loader.validate(config)
        
        # Invalid color format
        config = {
            "update_interval": 30,
            "repositories": [],
            "colors": {"clean": "green"}
        }
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "Invalid color format" in str(exc_info.value)
    
    def test_is_valid_color(self):
        """Test color format validation."""
        assert self.loader._is_valid_color("#ffffff")
        assert self.loader._is_valid_color("#000000")
        assert self.loader._is_valid_color("#abc")
        assert not self.loader._is_valid_color("ffffff")  # Missing #
        assert not self.loader._is_valid_color("#gggggg")  # Invalid hex
        assert not self.loader._is_valid_color("#ff")  # Wrong length
        assert not self.loader._is_valid_color(123)  # Not a string
    
    def test_validate_dropdown_settings(self):
        """Test dropdown settings validation."""
        # Valid
        config = {
            "update_interval": 30,
            "repositories": [],
            "dropdown": {
                "max_items": 10,
                "sort_by": "alphabetical"
            }
        }
        assert self.loader.validate(config)
        
        # Invalid max_items
        config["dropdown"]["max_items"] = -1
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "non-negative integer" in str(exc_info.value)
        
        # Invalid sort_by
        config["dropdown"]["max_items"] = 10
        config["dropdown"]["sort_by"] = "invalid"
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "sort_by must be one of" in str(exc_info.value)
    
    def test_validate_auth_settings(self):
        """Test auth settings validation."""
        # Valid
        config = {
            "update_interval": 30,
            "repositories": [],
            "auth": {
                "fetch_timeout": 10
            }
        }
        assert self.loader.validate(config)
        
        # Out of range
        config["auth"]["fetch_timeout"] = 100
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "between 1 and 60" in str(exc_info.value)
    
    def test_validate_logging_settings(self):
        """Test logging settings validation."""
        # Valid
        config = {
            "update_interval": 30,
            "repositories": [],
            "logging": {
                "level": "DEBUG"
            }
        }
        assert self.loader.validate(config)
        
        # Invalid level
        config["logging"]["level"] = "VERBOSE"
        with pytest.raises(ConfigValidationError) as exc_info:
            self.loader.validate(config)
        assert "logging.level must be one of" in str(exc_info.value)
    
    def test_reload(self):
        """Test configuration reloading."""
        # Create initial config
        config1 = {
            "update_interval": 30,
            "repositories": ["~/repo1"]
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(config1, f)
        
        # Load initial config
        self.loader.load()
        assert self.loader.config["update_interval"] == 30
        
        # Update config file
        config2 = {
            "update_interval": 60,
            "repositories": ["~/repo1", "~/repo2"]
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(config2, f)
        
        # Reload
        reloaded = self.loader.reload()
        assert reloaded["update_interval"] == 60
        assert len(reloaded["repositories"]) == 2
    
    def test_create_sample_config(self):
        """Test sample configuration creation."""
        assert not self.config_path.exists()
        
        self.loader.create_sample_config()
        
        assert self.config_path.exists()
        
        # Verify it's valid YAML
        with open(self.config_path, 'r') as f:
            sample = yaml.safe_load(f)
        
        assert "update_interval" in sample
        assert "repositories" in sample
        assert isinstance(sample["repositories"], list)
    
    def test_create_sample_config_existing(self):
        """Test that sample config doesn't overwrite existing."""
        # Create existing config
        existing_content = {"test": "data"}
        with open(self.config_path, 'w') as f:
            yaml.dump(existing_content, f)
        
        self.loader.create_sample_config()
        
        # Should not overwrite
        with open(self.config_path, 'r') as f:
            content = yaml.safe_load(f)
        assert content == existing_content
    
    def test_get_method(self):
        """Test get method with dot notation."""
        # Create config
        config = {
            "update_interval": 30,
            "repositories": ["~/repo1"],
            "auth": {
                "fetch_timeout": 5,
                "use_ssh_agent": True
            }
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
        
        # Test various get operations
        assert self.loader.get("update_interval") == 30
        assert self.loader.get("auth.fetch_timeout") == 5
        assert self.loader.get("auth.use_ssh_agent") is True
        assert self.loader.get("nonexistent", "default") == "default"
        assert self.loader.get("auth.nonexistent", 10) == 10
    
    def test_get_repositories(self):
        """Test get_repositories method."""
        config = {
            "repositories": ["~/repo1", "~/repo2"]
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
        
        repos = self.loader.get_repositories()
        assert len(repos) == 2
        # Should be expanded
        assert not repos[0].startswith("~")
    
    def test_get_colors(self):
        """Test get_colors method."""
        config = {
            "colors": {
                "clean": "#00ff00",
                "uncommitted": "#ff0000"
            }
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
        
        colors = self.loader.get_colors()
        assert colors["clean"] == "#00ff00"
        # Should include defaults for missing colors
        assert "error" in colors
    
    def test_get_update_interval(self):
        """Test get_update_interval method."""
        config = {"update_interval": 45}
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
        
        interval = self.loader.get_update_interval()
        assert interval == 45
    
    def test_lazy_loading(self):
        """Test that configuration is loaded lazily."""
        loader = ConfigLoader(config_path=self.config_path)
        assert not loader._loaded
        
        # Accessing config should trigger load
        loader.get("update_interval")
        assert loader._loaded
    
    def test_validation_error_handling(self):
        """Test that validation errors are properly raised."""
        config = {
            "update_interval": "invalid",
            "repositories": []
        }
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
        
        with pytest.raises(ConfigValidationError):
            self.loader.load()