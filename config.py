# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Configuration management for InfraCanvas validation system.
Supports loading from YAML files and environment variable overrides.
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

from validators.base import ValidationConfig

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "validation": {
        "enabled": True,
        "timeout_seconds": 120,
        "syntax": {
            "enabled": True
        },
        "security": {
            "enabled": True,
            "max_critical_issues": 0,
            "max_high_issues": 3,
            "checkov_skip_checks": []
        },
        "best_practices": {
            "enabled": True
        },
        "dry_run": {
            "enabled": True,
            "aws_region": "us-east-1",
            "use_aws_validation": True
        },
        "cfn_lint": {
            "ignore_checks": []
        }
    }
}


def load_config(config_path: Optional[str] = None) -> ValidationConfig:
    """
    Load validation configuration from YAML file with environment variable overrides.
    
    Args:
        config_path: Path to config.yaml file. If None, looks for config.yaml in current directory.
        
    Returns:
        ValidationConfig object with loaded settings
    """
    # Start with default configuration
    config_dict = _deep_copy_dict(DEFAULT_CONFIG)
    
    # Try to load from YAML file
    if config_path is None:
        config_path = "config.yaml"
    
    config_file = Path(config_path)
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    config_dict = _merge_configs(config_dict, yaml_config)
                    logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}. Using defaults.")
    else:
        logger.info(f"Config file {config_path} not found. Using default configuration.")
    
    # Apply environment variable overrides
    config_dict = _apply_env_overrides(config_dict)
    
    # Convert to ValidationConfig object
    return _dict_to_validation_config(config_dict)


def _deep_copy_dict(d: Dict) -> Dict:
    """Create a deep copy of a dictionary."""
    import copy
    return copy.deepcopy(d)


def _merge_configs(base: Dict, override: Dict) -> Dict:
    """
    Recursively merge override config into base config.
    
    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def _apply_env_overrides(config: Dict) -> Dict:
    """
    Apply environment variable overrides to configuration.
    
    Environment variables follow the pattern:
    INFRACANVAS_<SECTION>_<KEY>=value
    
    Examples:
        INFRACANVAS_VALIDATION_ENABLED=false
        INFRACANVAS_VALIDATION_TIMEOUT_SECONDS=180
        INFRACANVAS_SECURITY_MAX_CRITICAL_ISSUES=1
        INFRACANVAS_DRY_RUN_AWS_REGION=us-west-2
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration dictionary with environment overrides applied
    """
    # Validation enabled
    if os.getenv("INFRACANVAS_VALIDATION_ENABLED"):
        config["validation"]["enabled"] = _parse_bool(
            os.getenv("INFRACANVAS_VALIDATION_ENABLED")
        )
    
    # Validation timeout
    if os.getenv("INFRACANVAS_VALIDATION_TIMEOUT_SECONDS"):
        try:
            config["validation"]["timeout_seconds"] = int(
                os.getenv("INFRACANVAS_VALIDATION_TIMEOUT_SECONDS")
            )
        except ValueError:
            logger.warning("Invalid INFRACANVAS_VALIDATION_TIMEOUT_SECONDS value")
    
    # Syntax validation
    if os.getenv("INFRACANVAS_SYNTAX_ENABLED"):
        config["validation"]["syntax"]["enabled"] = _parse_bool(
            os.getenv("INFRACANVAS_SYNTAX_ENABLED")
        )
    
    # Security settings
    if os.getenv("INFRACANVAS_SECURITY_ENABLED"):
        config["validation"]["security"]["enabled"] = _parse_bool(
            os.getenv("INFRACANVAS_SECURITY_ENABLED")
        )
    
    if os.getenv("INFRACANVAS_SECURITY_MAX_CRITICAL_ISSUES"):
        try:
            config["validation"]["security"]["max_critical_issues"] = int(
                os.getenv("INFRACANVAS_SECURITY_MAX_CRITICAL_ISSUES")
            )
        except ValueError:
            logger.warning("Invalid INFRACANVAS_SECURITY_MAX_CRITICAL_ISSUES value")
    
    if os.getenv("INFRACANVAS_SECURITY_MAX_HIGH_ISSUES"):
        try:
            config["validation"]["security"]["max_high_issues"] = int(
                os.getenv("INFRACANVAS_SECURITY_MAX_HIGH_ISSUES")
            )
        except ValueError:
            logger.warning("Invalid INFRACANVAS_SECURITY_MAX_HIGH_ISSUES value")
    
    # Best practices
    if os.getenv("INFRACANVAS_BEST_PRACTICES_ENABLED"):
        config["validation"]["best_practices"]["enabled"] = _parse_bool(
            os.getenv("INFRACANVAS_BEST_PRACTICES_ENABLED")
        )
    
    # Dry run settings
    if os.getenv("INFRACANVAS_DRY_RUN_ENABLED"):
        config["validation"]["dry_run"]["enabled"] = _parse_bool(
            os.getenv("INFRACANVAS_DRY_RUN_ENABLED")
        )
    
    if os.getenv("INFRACANVAS_DRY_RUN_AWS_REGION"):
        config["validation"]["dry_run"]["aws_region"] = os.getenv(
            "INFRACANVAS_DRY_RUN_AWS_REGION"
        )
    
    if os.getenv("INFRACANVAS_DRY_RUN_USE_AWS_VALIDATION"):
        config["validation"]["dry_run"]["use_aws_validation"] = _parse_bool(
            os.getenv("INFRACANVAS_DRY_RUN_USE_AWS_VALIDATION")
        )
    
    return config


def _parse_bool(value: str) -> bool:
    """
    Parse string to boolean.
    
    Args:
        value: String value to parse
        
    Returns:
        Boolean value
    """
    return value.lower() in ("true", "1", "yes", "on")


def _dict_to_validation_config(config_dict: Dict) -> ValidationConfig:
    """
    Convert configuration dictionary to ValidationConfig object.
    
    Args:
        config_dict: Configuration dictionary
        
    Returns:
        ValidationConfig object
    """
    validation = config_dict.get("validation", {})
    syntax = validation.get("syntax", {})
    security = validation.get("security", {})
    best_practices = validation.get("best_practices", {})
    dry_run = validation.get("dry_run", {})
    cfn_lint = validation.get("cfn_lint", {})
    
    return ValidationConfig(
        enable_syntax_validation=syntax.get("enabled", True),
        enable_security_scanning=security.get("enabled", True),
        enable_best_practices=best_practices.get("enabled", True),
        enable_dry_run=dry_run.get("enabled", True),
        max_critical_security_issues=security.get("max_critical_issues", 0),
        max_high_security_issues=security.get("max_high_issues", 3),
        validation_timeout_seconds=validation.get("timeout_seconds", 120),
        checkov_skip_checks=security.get("checkov_skip_checks"),
        cfn_lint_ignore_checks=cfn_lint.get("ignore_checks"),
        aws_region=dry_run.get("aws_region", "us-east-1"),
        use_aws_validation=dry_run.get("use_aws_validation", True)
    )


def save_config(config: ValidationConfig, config_path: str = "config.yaml"):
    """
    Save ValidationConfig to YAML file.
    
    Args:
        config: ValidationConfig object to save
        config_path: Path to save config.yaml file
    """
    config_dict = {
        "validation": {
            "enabled": True,
            "timeout_seconds": config.validation_timeout_seconds,
            "syntax": {
                "enabled": config.enable_syntax_validation
            },
            "security": {
                "enabled": config.enable_security_scanning,
                "max_critical_issues": config.max_critical_security_issues,
                "max_high_issues": config.max_high_security_issues,
                "checkov_skip_checks": config.checkov_skip_checks or []
            },
            "best_practices": {
                "enabled": config.enable_best_practices
            },
            "dry_run": {
                "enabled": config.enable_dry_run,
                "aws_region": config.aws_region,
                "use_aws_validation": config.use_aws_validation
            },
            "cfn_lint": {
                "ignore_checks": config.cfn_lint_ignore_checks or []
            }
        }
    }
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save configuration to {config_path}: {e}")
        raise
