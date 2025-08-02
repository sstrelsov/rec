#!/usr/bin/env python3
"""
config.py - Simple Configuration Loader

Loads configuration from .env file with sensible defaults.
"""

import os
from pathlib import Path


class Config:
    """Simple configuration loader for mitm tool."""

    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self._load_env_file()

    def _load_env_file(self):
        """Load environment variables from .env file if it exists."""
        env_path = Path(self.env_file)
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

    @property
    def output_dir(self) -> str:
        """Get output directory from config."""
        return os.getenv('OUTPUT_DIR', 'output')

    @property
    def viewer_port(self) -> int:
        """Get viewer port from config."""
        try:
            return int(os.getenv('VIEWER_PORT', '8000'))
        except ValueError:
            return 8000


# Global config instance
config = Config()
