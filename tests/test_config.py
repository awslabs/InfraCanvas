# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for configuration management.
"""
import os
import tempfile
from pathlib import Path

import pytest

from config import load_config, save_config, _parse_bool, _merge_configs
from validators.base import ValidationConfig


def test_load_default_config():
    """Test loading default configuration when no config file exists."""
    config = load_config(config_path="nonexistent.yaml")
    
    assert config.enable_syntax_validation is True
    assert config.enable_security_scanning is True
    assert config.enable_best_practices is True
    assert config.enable_dry_run is True
    assert config.max_critical_security_issues == 0
    assert config.max_high_security_issues == 3
    assert config.validation_timeout_seconds == 120
    assert config.aws_region == "us-east-1"
    assert config.use_aws_validation is True


def test_load_config_from_yaml():
    """Test loading configuration from YAML file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
validation:
  timeout_seconds: 180
  syntax:
    enabled: false
  security:
    enabled: true
    max_critical_issues: 1
    max_high_issues: 5
  dry_run:
    aws_region: us-west-2
""")
        config_path = f.name
    
    try:
        config = load_config(config_path=config_path)
        
        assert config.enable_syntax_validation is False
        assert config.enable_security_scanning is True
        assert config.max_critical_security_issues == 1
        assert config.max_high_security_issues == 5
        assert config.validation_timeout_seconds == 180
        assert config.aws_region == "us-west-2"
    finally:
        os.unlink(config_path)


def test_env_variable_overrides():
    """Test environment variable overrides."""
    # Set environment variables
    os.environ["INFRACANVAS_VALIDATION_TIMEOUT_SECONDS"] = "240"
    os.environ["INFRACANVAS_SYNTAX_ENABLED"] = "false"
    os.environ["INFRACANVAS_SECURITY_MAX_CRITICAL_ISSUES"] = "2"
    os.environ["INFRACANVAS_DRY_RUN_AWS_REGION"] = "eu-west-1"
    
    try:
        config = load_config(config_path="nonexistent.yaml")
        
        assert config.validation_timeout_seconds == 240
        assert config.enable_syntax_validation is False
        assert config.max_critical_security_issues == 2
        assert config.aws_region == "eu-west-1"
    finally:
        # Clean up environment variables
        del os.environ["INFRACANVAS_VALIDATION_TIMEOUT_SECONDS"]
        del os.environ["INFRACANVAS_SYNTAX_ENABLED"]
        del os.environ["INFRACANVAS_SECURITY_MAX_CRITICAL_ISSUES"]
        del os.environ["INFRACANVAS_DRY_RUN_AWS_REGION"]


def test_save_config():
    """Test saving configuration to YAML file."""
    config = ValidationConfig(
        enable_syntax_validation=False,
        enable_security_scanning=True,
        enable_best_practices=True,
        enable_dry_run=False,
        max_critical_security_issues=1,
        max_high_security_issues=5,
        validation_timeout_seconds=180,
        aws_region="ap-southeast-1",
        use_aws_validation=False
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_path = f.name
    
    try:
        save_config(config, config_path=config_path)
        
        # Load it back and verify
        loaded_config = load_config(config_path=config_path)
        
        assert loaded_config.enable_syntax_validation is False
        assert loaded_config.enable_security_scanning is True
        assert loaded_config.enable_best_practices is True
        assert loaded_config.enable_dry_run is False
        assert loaded_config.max_critical_security_issues == 1
        assert loaded_config.max_high_security_issues == 5
        assert loaded_config.validation_timeout_seconds == 180
        assert loaded_config.aws_region == "ap-southeast-1"
        assert loaded_config.use_aws_validation is False
    finally:
        os.unlink(config_path)


def test_parse_bool():
    """Test boolean parsing from strings."""
    assert _parse_bool("true") is True
    assert _parse_bool("True") is True
    assert _parse_bool("TRUE") is True
    assert _parse_bool("1") is True
    assert _parse_bool("yes") is True
    assert _parse_bool("on") is True
    
    assert _parse_bool("false") is False
    assert _parse_bool("False") is False
    assert _parse_bool("0") is False
    assert _parse_bool("no") is False
    assert _parse_bool("off") is False


def test_merge_configs():
    """Test configuration merging."""
    base = {
        "validation": {
            "enabled": True,
            "timeout_seconds": 120,
            "syntax": {
                "enabled": True
            }
        }
    }
    
    override = {
        "validation": {
            "timeout_seconds": 180,
            "security": {
                "enabled": False
            }
        }
    }
    
    merged = _merge_configs(base, override)
    
    assert merged["validation"]["enabled"] is True
    assert merged["validation"]["timeout_seconds"] == 180
    assert merged["validation"]["syntax"]["enabled"] is True
    assert merged["validation"]["security"]["enabled"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
