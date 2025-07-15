"""
Device settings management for configurable parameters
"""

import json
import os
from typing import Dict, Any

class DeviceSettings:
    """Manages device configuration settings"""
    
    def __init__(self, settings_file='device_settings.json'):
        self.settings_file = settings_file
        self.default_settings = {
            'measurement_interval': 5,  # Default 5 seconds
            'auto_save_interval': 30,   # Auto-save settings every 30 seconds
        }
        self.settings = self.load_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        return self.default_settings.copy()
    
    def save_settings(self):
        """Save settings to JSON file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get_measurement_interval(self) -> int:
        """Get the current measurement interval in seconds"""
        return self.settings.get('measurement_interval', 5)
    
    def set_measurement_interval(self, interval: int):
        """Set the measurement interval in seconds"""
        if interval < 1:
            interval = 1  # Minimum 1 second
        elif interval > 300:
            interval = 300  # Maximum 5 minutes
        
        self.settings['measurement_interval'] = interval
        self.save_settings()
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings"""
        return self.settings.copy()
    
    def update_setting(self, key: str, value: Any):
        """Update a specific setting"""
        self.settings[key] = value
        self.save_settings()

# Global settings instance
device_settings = DeviceSettings()