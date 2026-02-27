#!/usr/bin/env python3
"""
config.py - Configuration Management System

Provides centralized configuration loading with TOML file support and sensible defaults.
Handles configuration merging, validation, and provides type-safe property access.

Architecture:
- ~/.rec/config.toml: Optional user configuration overrides
- config.toml (shipped): Reference defaults
- config.py: Fallback defaults + configuration loading logic
- Addons: Import and use `from config import config`
"""

import os
import tomllib
from pathlib import Path
from typing import List, Dict, Any


# Base directory for all rec data
REC_DIR = Path(os.environ.get("REC_DIR", "~/.rec")).expanduser()


class Config:
    """
    Configuration manager that loads settings from config.toml with fallback defaults.

    Provides type-safe property access to all configuration sections:
    - general: Output directory
    - filtering: HTTP methods, request types, noise filters, blocked patterns
    """

    def __init__(self):
        self.config = self._load_config()

    def _get_minimal_defaults(self) -> Dict[str, Any]:
        """
        Minimal fallback configuration when config.toml is missing or invalid.
        """
        return {
            "general": {
                "output_dir": str(REC_DIR),
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
                "blocked_patterns": []
            },
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load and merge configuration. Checks ~/.rec/config.toml first, then shipped config.toml."""
        defaults = self._get_minimal_defaults()

        # Try user config at ~/.rec/config.toml
        user_config_path = REC_DIR / "config.toml"
        if user_config_path.exists():
            try:
                with open(user_config_path, 'rb') as f:
                    user_config = tomllib.load(f)
                return self._merge_config(defaults, user_config)
            except Exception as e:
                print(f"Error loading {user_config_path}: {e}")

        # Try shipped config.toml next to this file
        shipped_config = Path(__file__).resolve().parent / "config.toml"
        if shipped_config.exists():
            try:
                with open(shipped_config, 'rb') as f:
                    shipped = tomllib.load(f)
                return self._merge_config(defaults, shipped)
            except Exception as e:
                print(f"Error loading {shipped_config}: {e}")

        return defaults

    def _merge_config(self, defaults: Dict, user_config: Dict) -> Dict:
        """Recursively merge user config with defaults."""
        result = defaults.copy()
        for key, value in user_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        self._validate_config(result)
        return result

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration values for common issues."""
        try:
            methods = config.get("filtering", {}).get("http_methods", [])
            valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}
            invalid_methods = [m for m in methods if m not in valid_methods]
            if invalid_methods:
                print(f"Warning: Invalid HTTP methods: {invalid_methods}")
        except Exception as e:
            print(f"Warning: Config validation error: {e}")

    # =============================================================================
    # General Settings Properties
    # =============================================================================

    @property
    def output_dir(self) -> str:
        """Directory where captured data will be saved.

        Priority: REC_OUTPUT_DIR env var > config file > default (~/.rec)
        """
        env_dir = os.environ.get("REC_OUTPUT_DIR")
        if env_dir:
            return env_dir
        return self.config["general"].get("output_dir", str(REC_DIR))

    @property
    def target_domains(self) -> List[str]:
        """Target domains to filter traffic to.

        Read from REC_DOMAINS env var (comma-separated).
        Empty list means capture all traffic.
        """
        env_domains = os.environ.get("REC_DOMAINS", "")
        if env_domains:
            return [d.strip() for d in env_domains.split(",") if d.strip()]
        return []

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
        """Patterns for blocking ads/analytics traffic."""
        return self.config["filtering"]["blocked_patterns"]


# =============================================================================
# Global Configuration Instance
# =============================================================================

# Global config instance - import this in addons with: from config import config
config = Config()
