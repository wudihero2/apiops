"""
Configuration management for opsctl
"""

import os
import yaml
from pathlib import Path


class Config:
    """Configuration manager for opsctl"""

    def __init__(self):
        self.config_dir = Path.home() / ".opsctl"
        self.config_file = self.config_dir / "config.yaml"
        self._config: dict | None = None

    def ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Load configuration from file or environment"""
        if self._config is not None:
            return self._config

        self._config = {}

        # Load from file if exists
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self._config = yaml.safe_load(f) or {}

        # Override with environment variables
        if os.environ.get('OPSCTL_API_URL'):
            self._config['api_url'] = os.environ['OPSCTL_API_URL']
        if os.environ.get('OPSCTL_API_KEY'):
            self._config['api_key'] = os.environ['OPSCTL_API_KEY']

        return self._config

    def save(self, config: dict):
        """Save configuration to file"""
        self.ensure_config_dir()
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        self._config = config

    def get(self, key: str, default: any = None):
        """Get configuration value"""
        config = self.load()
        return config.get(key, default)

    def set(self, key: str, value: any):
        """Set configuration value"""
        config = self.load()
        config[key] = value
        self.save(config)

    @property
    def api_url(self) -> str | None:
        """Get API URL"""
        return self.get('api_url')

    @property
    def api_key(self) -> str | None:
        """Get API Key"""
        return self.get('api_key')

    def is_configured(self) -> bool:
        """Check if opsctl is configured"""
        return bool(self.api_url and self.api_key)


# Global config instance
config = Config()
