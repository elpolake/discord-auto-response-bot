import os
from pathlib import Path
import json
from typing import Dict, Any

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"


class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default configuration
            default_config = {
                "max_saved_messages": 50,
                "bot_token": "",
                "cooldown_seconds": 10,
                "selected_channels": [],
                "api_url": "http://localhost:11434/api/chat",
                "log_level": "INFO",
                "max_retries": 3,
                "bot_prompt": "Roast {name} briefly and harshly."
            }
            self.save_config(default_config)
            return default_config

    def save_config(self, config: Dict[str, Any]):
        """Save configuration to config.json"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

    def update_selected_channels(self, channels: list):
        """Update selected channel IDs in config"""
        self.config["selected_channels"] = channels
        self.save_config(self.config)


config_manager = ConfigManager()