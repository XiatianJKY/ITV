# src/config_manager.py
import os
import json
from pathlib import Path

CONFIG_FILE = Path('config.json')

class ConfigManager:
    _instance = None
    _config = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            # 默认值
            self._config = {
                'MAX_WORKERS': 20,
                'TIMEOUT': 8,
                'FFMPEG_ENABLE': True,
                'MAX_SOURCES_PER_CHANNEL': 3,
                'DEMO_MATCH_MODE': 'contains'
            }
            self._save()
    
    def _save(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get(self, key, default=None):
        return self._config.get(key, default)
    
    def set(self, key, value):
        self._config[key] = value
        self._save()
    
    def reload(self):
        self._load()
