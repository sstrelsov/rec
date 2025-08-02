#!/usr/bin/env python3
"""
config.py - Configuration Management System

Provides centralized configuration loading with TOML file support and sensible defaults.
Handles configuration merging, validation, and provides type-safe property access.

Architecture:
- config.toml: User configuration (single source of truth)
- config.py: Fallback defaults + configuration loading logic
- Addons: Import and use `from config import config` 
"""

import tomllib
from pathlib import Path
from typing import List, Dict, Any, Optional


class Config:
    """
    Configuration manager that loads settings from config.toml with fallback defaults.
    
    Provides type-safe property access to all configuration sections:
    - general: Output directory, viewer port
    - filtering: HTTP methods, request types, noise filters, blocked patterns  
    - timeline: Display preferences, pagination
    - api_extractor: Documentation generation settings
    """

    def __init__(self, config_file: str = "config.toml"):
        self.config_file = config_file
        self.config = self._load_config()

    def _get_minimal_defaults(self) -> Dict[str, Any]:
        """
        Minimal fallback configuration when config.toml is missing or invalid.
        
        Design principle: Provide safe defaults that allow the tool to function,
        but encourage users to customize via config.toml for optimal experience.
        """
        return {
            "general": {
                "output_dir": "output",
                "viewer_port": 8000
            },
            "filtering": {
                "http_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                "include_browser_requests": True,
                "include_api_requests": True,
                "include_unknown_requests": True,
                "filter_static_assets": True,
                "filter_browser_housekeeping": True,
                "filter_health_checks": True,
                "filter_prefetch_requests": True,
                "blocked_patterns": []  # Empty by design - user should configure in config.toml
            },
            "timeline": {
                "auto_refresh": False,
                "default_items_per_page": 50,
                "show_response_times": True,
                "show_context_icons": True
            },
            "api_extractor": {
                "enabled": True,
                "min_calls_per_endpoint": 1,
                "max_examples_per_endpoint": 3,
                "include_request_headers": True,
                "include_response_examples": True
            }
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load and merge configuration from TOML file with defaults."""
        config_path = Path(self.config_file)
        defaults = self._get_minimal_defaults()

        if not config_path.exists():
            print(f"Config file {self.config_file} not found, using minimal defaults.")
            print("Create config.toml to customize behavior (see documentation).")
            return defaults

        try:
            with open(config_path, 'rb') as f:
                user_config = tomllib.load(f)
            return self._merge_config(defaults, user_config)
        except Exception as e:
            print(f"Error loading {self.config_file}: {e}")
            print("Using minimal defaults. Fix config.toml syntax to customize settings.")
            return defaults

    def _merge_config(self, defaults: Dict, user_config: Dict) -> Dict:
        """Recursively merge user config with defaults and validate."""
        result = defaults.copy()
        for key, value in user_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        # Basic validation
        self._validate_config(result)
        return result

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration values for common issues."""
        try:
            # Validate port range
            port = config.get("general", {}).get("viewer_port", 8000)
            if not isinstance(port, int) or not (1024 <= port <= 65535):
                print(f"Warning: viewer_port {port} should be between 1024-65535")
            
            # Validate HTTP methods
            methods = config.get("filtering", {}).get("http_methods", [])
            valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}
            invalid_methods = [m for m in methods if m not in valid_methods]
            if invalid_methods:
                print(f"Warning: Invalid HTTP methods: {invalid_methods}")
                
        except Exception as e:
            print(f"Warning: Config validation error: {e}")
            
    def get_config_dict(self) -> Dict[str, Any]:
        """Get the full configuration dictionary for introspection.""" 
        return self.config.copy()

    # =============================================================================
    # General Settings Properties
    # =============================================================================
    
    @property
    def output_dir(self) -> str:
        """Directory where captured data (timeline, API docs) will be saved."""
        return self.config["general"]["output_dir"]

    @property
    def viewer_port(self) -> int:
        """Port for the built-in documentation viewer."""
        return self.config["general"]["viewer_port"]

    # =============================================================================
    # Traffic Filtering Properties  
    # =============================================================================
    
    @property
    def http_methods(self) -> List[str]:
        """HTTP methods to capture (e.g., ['GET', 'POST', 'PUT'])."""
        return self.config["filtering"]["http_methods"]

    @property
    def include_browser_requests(self) -> bool:
        """Whether to include browser navigation, page loads, form submissions."""
        return self.config["filtering"]["include_browser_requests"]

    @property
    def include_api_requests(self) -> bool:
        """Whether to include JSON/REST API calls, GraphQL, RPC requests."""
        return self.config["filtering"]["include_api_requests"]

    @property
    def include_unknown_requests(self) -> bool:
        """Whether to include requests that don't fit other categories."""
        return self.config["filtering"]["include_unknown_requests"]

    @property
    def filter_static_assets(self) -> bool:
        """Whether to filter images, CSS, JS, fonts, icons (.css, .js, .png, etc.)."""
        return self.config["filtering"]["filter_static_assets"]

    @property
    def filter_browser_housekeeping(self) -> bool:
        """Whether to filter browser metadata (favicon.ico, robots.txt, manifest.json)."""
        return self.config["filtering"]["filter_browser_housekeeping"]

    @property
    def filter_health_checks(self) -> bool:
        """Whether to filter service monitoring endpoints (/ping, /healthz, /status)."""
        return self.config["filtering"]["filter_health_checks"]

    @property
    def filter_prefetch_requests(self) -> bool:
        """Whether to filter browser optimization requests (prefetch, preload, dns-prefetch)."""
        return self.config["filtering"]["filter_prefetch_requests"]

    @property
    def blocked_patterns(self) -> List[str]:
        """
        Patterns for blocking ads/analytics traffic.
        
        Returns list of strings that are matched against URLs, hostnames, and paths.
        Configure in config.toml under [filtering].blocked_patterns.
        """
        return self.config["filtering"]["blocked_patterns"]

    # =============================================================================
    # Timeline Display Properties
    # =============================================================================
    
    @property
    def timeline_auto_refresh(self) -> bool:
        """Whether timeline view should automatically refresh."""
        return self.config["timeline"]["auto_refresh"]

    @property
    def timeline_items_per_page(self) -> int:
        """Number of requests to show per page in timeline."""
        return self.config["timeline"]["default_items_per_page"]

    @property
    def show_response_times(self) -> bool:
        """Whether to display request duration times in timeline."""
        return self.config["timeline"]["show_response_times"]

    @property
    def show_context_icons(self) -> bool:
        """Whether to show icons indicating request type (browser/API/unknown) in timeline."""
        return self.config["timeline"]["show_context_icons"]

    # =============================================================================
    # API Documentation Generation Properties
    # =============================================================================
    
    @property
    def api_extractor_enabled(self) -> bool:
        """Whether to generate OpenAPI-style documentation from captured traffic."""
        return self.config["api_extractor"]["enabled"]

    @property
    def min_calls_per_endpoint(self) -> int:
        """Minimum requests needed before endpoint appears in generated documentation."""
        return self.config["api_extractor"]["min_calls_per_endpoint"]

    @property
    def max_examples_per_endpoint(self) -> int:
        """Maximum request/response examples to include per endpoint in documentation."""
        return self.config["api_extractor"]["max_examples_per_endpoint"]


# =============================================================================
# Global Configuration Instance
# =============================================================================

# Global config instance - import this in addons with: from config import config
config = Config()
