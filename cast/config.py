"""config.py

Handles CAST configuration."""

import yaml


def parse_config(config_file: str) -> dict[str, str|int|bool]:
    """Parse configuration options."""
    with open(config_file, encoding="utf-8") as config_file_handle:
        return yaml.safe_load(config_file_handle)
