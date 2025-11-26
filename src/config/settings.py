"""
Configuration management for MP4 to MP3 Converter application.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings, QObject, pyqtSignal


class Settings(QObject):
    """Application settings manager with macOS native storage."""
    
    settings_changed = pyqtSignal(str, object)  # key, value
    
    # Default settings
    DEFAULTS = {
        'audio_quality': '192',  # kbps: 128, 192, 320
        'output_suffix': '_converted',  # Suffix for output files
        'auto_open_folder': True,  # Auto-open output folder after conversion
        'delete_original': False,  # Delete original files after conversion
        'max_concurrent_conversions': 4,  # Maximum concurrent conversions
        'output_directory': '',  # Default output directory
        'window_geometry': '',  # Main window geometry
        'window_state': '',  # Main window state
        'file_naming_pattern': '{original}_converted',  # File naming pattern
        'preserve_metadata': True,  # Preserve metadata tags
        'volume_normalization': False,  # Normalize audio volume
        'fade_in': 0,  # Fade in duration (seconds)
        'fade_out': 0,  # Fade out duration (seconds)
    }
    
    def __init__(self):
        super().__init__()
        self._settings = QSettings(
            "MP4toMP3Converter",
            "MP4toMP3Converter"
        )
        self._ensure_defaults()
    
    def _ensure_defaults(self):
        """Ensure all default settings exist."""
        for key, default_value in self.DEFAULTS.items():
            if not self._settings.contains(key):
                self._settings.setValue(key, default_value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key (str): Setting key
            default (Any): Default value if key doesn't exist
            
        Returns:
            Any: Setting value
        """
        if default is None:
            default = self.DEFAULTS.get(key)
        
        value = self._settings.value(key, default)
        
        # Convert to correct type based on default
        if isinstance(default, bool) and not isinstance(value, bool):
            value = value.lower() == 'true' if isinstance(value, str) else bool(value)
        elif isinstance(default, int) and not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                value = default
        elif isinstance(default, float) and not isinstance(value, float):
            try:
                value = float(value)
            except (ValueError, TypeError):
                value = default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key (str): Setting key
            value (Any): Setting value
        """
        self._settings.setValue(key, value)
        self.settings_changed.emit(key, value)
    
    def get_audio_quality_options(self) -> Dict[str, str]:
        """Get available audio quality options."""
        return {
            '128': '128 kbps - 小ファイル、標準品質',
            '192': '192 kbps - バランスの取れた品質',
            '320': '320 kbps - 最高品質'
        }
    
    def get_naming_pattern_options(self) -> Dict[str, str]:
        """Get available file naming pattern options."""
        return {
            '{original}_converted': '元ファイル名_converted.mp3',
            '{original}_audio': '元ファイル名_audio.mp3',
            '{original}': '元ファイル名.mp3',
            'converted_{original}': 'converted_元ファイル名.mp3'
        }
    
    def export_settings(self, file_path: str) -> bool:
        """
        Export settings to JSON file.
        
        Args:
            file_path (str): Export file path
            
        Returns:
            bool: Success status
        """
        try:
            settings_dict = {}
            for key in self.DEFAULTS.keys():
                settings_dict[key] = self.get(key)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """
        Import settings from JSON file.
        
        Args:
            file_path (str): Import file path
            
        Returns:
            bool: Success status
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings_dict = json.load(f)
            
            for key, value in settings_dict.items():
                if key in self.DEFAULTS:
                    self.set(key, value)
            
            return True
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        for key, default_value in self.DEFAULTS.items():
            self.set(key, default_value)
    
    def get_output_directory(self) -> str:
        """Get output directory, creating default if empty."""
        output_dir = self.get('output_directory')
        if not output_dir:
            # Default to Desktop/Music folder
            output_dir = str(Path.home() / "Desktop" / "MP3_Conversions")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            self.set('output_directory', output_dir)
        
        return output_dir