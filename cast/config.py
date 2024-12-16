"""config.py

Handles CAST configuration."""

from typing import Self

import yaml


class CastConfig:
    """Object holding CAST configuration info."""
    def __init__(self, config_dict: dict[str, str | int | bool]):
        self.website_name = str(config_dict["website_name"])
        self.cache_path = str(config_dict["cache_path"])
        self.queue = str(config_dict["song_queue"])
        self.admin_prefix = str(config_dict["admin_prefix"])

        self.client_id = str(config_dict["client_id"])
        self.client_secret = str(config_dict["client_secret"])

        self.port = int(config_dict["cast_port"])
        self.redirect_port = int(config_dict["cast_redirect_port"])
        self.redirect_uri = f"http://localhost:{self.redirect_port}"

    @classmethod
    def from_config_file(cls, config_file: str) -> Self:
        """Construct a CastConfig object from a config file."""
        with open(config_file, encoding="utf-8") as f:
            return cls(yaml.safe_load(f))
