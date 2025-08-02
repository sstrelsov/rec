#!/usr/bin/env python3
"""
config.py - Configuration Loader

Loads configuration from config.toml with sensible defaults.
Supports filtering options, HTTP method selection, and UI preferences.
"""

import os
import tomllib
from pathlib import Path
from typing import List, Dict, Any


class Config:
    """Configuration loader for mitm tool."""

    def __init__(self, config_file: str = "config.toml"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from TOML file with defaults."""
        config_path = Path(self.config_file)

        # Default configuration
        defaults = {
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
                "blocked_patterns": [
                    # Google Analytics & Ads
                    "google-analytics.com", "googleanalytics.com", "google-analytics",
                    "gtag", "gtm.js", "ga.js", "_ga", "googlesyndication.com",
                    "doubleclick.net", "googleadservices.com",
                    # Social Media Tracking
                    "facebook.com/tr", "connect.facebook.net", "facebook.net",
                    # Analytics Services
                    "mixpanel.com", "amplitude.com", "segment.com", "segment.io",
                    "hotjar.com", "fullstory.com", "logrocket.com", "datadog",
                    # Common tracking paths
                    "/pixel.gif", "/collect?", "/tr?", "/ads/", "/ad/", "/tracking",
                    "/analytics", "/metrics", "/telemetry", "/beacon", "/ping"
                ]
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

        if config_path.exists():
            try:
                with open(config_path, 'rb') as f:
                    file_config = tomllib.load(f)
                # Merge file config with defaults
                return self._merge_config(defaults, file_config)
            except Exception as e:
                print(f"Warning: Error loading config.toml: {e}")
                print("Using default configuration.")
        else:
            print(f"Config file {self.config_file} not found, using defaults.")

        return defaults

    def _merge_config(self, defaults: Dict, user_config: Dict) -> Dict:
        """Recursively merge user config with defaults."""
        result = defaults.copy()
        for key, value in user_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    # General settings
    @property
    def output_dir(self) -> str:
        """Get output directory from config."""
        return self.config["general"]["output_dir"]

    @property
    def viewer_port(self) -> int:
        """Get viewer port from config."""
        return self.config["general"]["viewer_port"]

    # Filtering settings
    @property
    def http_methods(self) -> List[str]:
        """Get allowed HTTP methods."""
        return self.config["filtering"]["http_methods"]

    @property
    def include_browser_requests(self) -> bool:
        """Whether to include browser requests."""
        return self.config["filtering"]["include_browser_requests"]

    @property
    def include_api_requests(self) -> bool:
        """Whether to include API requests."""
        return self.config["filtering"]["include_api_requests"]

    @property
    def include_unknown_requests(self) -> bool:
        """Whether to include unknown requests."""
        return self.config["filtering"]["include_unknown_requests"]

    @property
    def filter_static_assets(self) -> bool:
        """Whether to filter static assets."""
        return self.config["filtering"]["filter_static_assets"]

    @property
    def filter_browser_housekeeping(self) -> bool:
        """Whether to filter browser housekeeping requests."""
        return self.config["filtering"]["filter_browser_housekeeping"]

    @property
    def filter_health_checks(self) -> bool:
        """Whether to filter health check requests."""
        return self.config["filtering"]["filter_health_checks"]

    @property
    def filter_prefetch_requests(self) -> bool:
        """Whether to filter prefetch/preload requests."""
        return self.config["filtering"]["filter_prefetch_requests"]

    @property
    def blocked_patterns(self) -> List[str]:
        """Get blocked patterns for filtering."""
        return self.config["filtering"]["blocked_patterns"]

    # Timeline settings
    @property
    def timeline_auto_refresh(self) -> bool:
        """Whether timeline should auto-refresh."""
        return self.config["timeline"]["auto_refresh"]

    @property
    def timeline_items_per_page(self) -> int:
        """Default items per page in timeline."""
        return self.config["timeline"]["default_items_per_page"]

    @property
    def show_response_times(self) -> bool:
        """Whether to show response times in timeline."""
        return self.config["timeline"]["show_response_times"]

    @property
    def show_context_icons(self) -> bool:
        """Whether to show context icons in timeline."""
        return self.config["timeline"]["show_context_icons"]

    # API Extractor settings
    @property
    def api_extractor_enabled(self) -> bool:
        """Whether API extractor is enabled."""
        return self.config["api_extractor"]["enabled"]

    @property
    def min_calls_per_endpoint(self) -> int:
        """Minimum calls per endpoint to include in docs."""
        return self.config["api_extractor"]["min_calls_per_endpoint"]

    @property
    def max_examples_per_endpoint(self) -> int:
        """Maximum examples per endpoint."""
        return self.config["api_extractor"]["max_examples_per_endpoint"]

    def get_config_dict(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self.config


# Global config instance
config = Config()
