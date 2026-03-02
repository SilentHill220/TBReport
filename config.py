import json
import os
from typing import Dict, Any

import sys

class Config:
    def __init__(self, config_path: str = "config.json"):
        if getattr(sys, 'frozen', False):
             # If frozen, config is next to the executable
             base_path = os.path.dirname(sys.executable)
        else:
             # If source, config is next to this file
             base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.config_path = os.path.join(base_path, config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_teambition_config(self) -> Dict[str, Any]:
        return self.config.get('teambition', {})

    def get_export_config(self) -> Dict[str, Any]:
        return self.config.get('export', {})

    def get_scheduler_config(self) -> Dict[str, Any]:
        return self.config.get('scheduler', {})

    def get_output_config(self) -> Dict[str, Any]:
        return self.config.get('output', {})

    def load(self) -> Dict[str, Any]:
        """Reload config from disk."""
        self.config = self._load_config()
        return self.config

    def save(self, new_config: Dict[str, Any]):
        """Save config to disk."""
        self.config = new_config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
