"""
Application settings management for the Medical Software Analysis Tool.

This module provides application settings that persist user preferences
and application state across sessions.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging

from .config_manager import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class RecentProject:
    """Information about a recently opened project."""
    path: str
    name: str
    last_opened: str
    description: Optional[str] = None


@dataclass
class UserPreferences:
    """User-specific preferences and settings."""
    default_project_path: str = ""
    default_output_dir: str = ""
    auto_save_enabled: bool = True
    auto_save_interval: int = 300  # seconds
    show_welcome_screen: bool = True
    check_for_updates: bool = True
    theme: str = "default"
    language: str = "en"
    max_recent_projects: int = 10
    window_geometry: Optional[str] = None
    window_state: Optional[str] = None


class AppSettings:
    """Manages application settings and user preferences."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize application settings."""
        self.config_manager = config_manager
        self.settings_file = config_manager.config_dir / "app_settings.json"
        
        # Initialize settings
        self.user_preferences = UserPreferences()
        self.recent_projects: List[RecentProject] = []
        self.custom_settings: Dict[str, Any] = {}
        
        # Load settings
        self.load_settings()
    
    def load_settings(self) -> None:
        """Load application settings from file."""
        logger.info("Loading application settings")
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                
                # Load user preferences
                if 'user_preferences' in settings_data:
                    prefs_data = settings_data['user_preferences']
                    self.user_preferences = UserPreferences(
                        default_project_path=prefs_data.get('default_project_path', ''),
                        default_output_dir=prefs_data.get('default_output_dir', ''),
                        auto_save_enabled=prefs_data.get('auto_save_enabled', True),
                        auto_save_interval=prefs_data.get('auto_save_interval', 300),
                        show_welcome_screen=prefs_data.get('show_welcome_screen', True),
                        check_for_updates=prefs_data.get('check_for_updates', True),
                        theme=prefs_data.get('theme', 'default'),
                        language=prefs_data.get('language', 'en'),
                        max_recent_projects=prefs_data.get('max_recent_projects', 10),
                        window_geometry=prefs_data.get('window_geometry'),
                        window_state=prefs_data.get('window_state')
                    )
                
                # Load recent projects
                if 'recent_projects' in settings_data:
                    self.recent_projects = []
                    for project_data in settings_data['recent_projects']:
                        project = RecentProject(
                            path=project_data['path'],
                            name=project_data['name'],
                            last_opened=project_data['last_opened'],
                            description=project_data.get('description')
                        )
                        self.recent_projects.append(project)
                
                # Load custom settings
                if 'custom_settings' in settings_data:
                    self.custom_settings = settings_data['custom_settings']
                
                logger.info("Application settings loaded successfully")
            else:
                logger.info("No settings file found, using defaults")
                
        except Exception as e:
            logger.error(f"Error loading application settings: {e}")
    
    def save_settings(self) -> None:
        """Save application settings to file."""
        logger.info("Saving application settings")
        
        try:
            settings_data = {
                'user_preferences': asdict(self.user_preferences),
                'recent_projects': [asdict(project) for project in self.recent_projects],
                'custom_settings': self.custom_settings
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Application settings saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving application settings: {e}")
    
    def add_recent_project(self, project_path: str, project_name: str, description: Optional[str] = None) -> None:
        """Add a project to the recent projects list."""
        from datetime import datetime
        
        # Remove if already exists
        self.recent_projects = [p for p in self.recent_projects if p.path != project_path]
        
        # Add new project at the beginning
        project = RecentProject(
            path=project_path,
            name=project_name,
            last_opened=datetime.now().isoformat(),
            description=description
        )
        self.recent_projects.insert(0, project)
        
        # Limit the number of recent projects
        max_projects = self.user_preferences.max_recent_projects
        if len(self.recent_projects) > max_projects:
            self.recent_projects = self.recent_projects[:max_projects]
        
        # Save settings
        self.save_settings()
    
    def remove_recent_project(self, project_path: str) -> None:
        """Remove a project from the recent projects list."""
        self.recent_projects = [p for p in self.recent_projects if p.path != project_path]
        self.save_settings()
    
    def clear_recent_projects(self) -> None:
        """Clear all recent projects."""
        self.recent_projects.clear()
        self.save_settings()
    
    def get_recent_projects(self) -> List[RecentProject]:
        """Get the list of recent projects."""
        return self.recent_projects.copy()
    
    def update_user_preferences(self, **kwargs) -> None:
        """Update user preferences."""
        for key, value in kwargs.items():
            if hasattr(self.user_preferences, key):
                setattr(self.user_preferences, key, value)
            else:
                logger.warning(f"Unknown user preference key: {key}")
        
        self.save_settings()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a custom setting value."""
        return self.custom_settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a custom setting value."""
        self.custom_settings[key] = value
        self.save_settings()
    
    def get_default_project_path(self) -> str:
        """Get the default project path."""
        return self.user_preferences.default_project_path
    
    def set_default_project_path(self, path: str) -> None:
        """Set the default project path."""
        self.user_preferences.default_project_path = path
        self.save_settings()
    
    def get_default_output_dir(self) -> str:
        """Get the default output directory."""
        return self.user_preferences.default_output_dir
    
    def set_default_output_dir(self, path: str) -> None:
        """Set the default output directory."""
        self.user_preferences.default_output_dir = path
        self.save_settings()
    
    def is_auto_save_enabled(self) -> bool:
        """Check if auto-save is enabled."""
        return self.user_preferences.auto_save_enabled
    
    def get_auto_save_interval(self) -> int:
        """Get the auto-save interval in seconds."""
        return self.user_preferences.auto_save_interval
    
    def get_theme(self) -> str:
        """Get the current theme."""
        return self.user_preferences.theme
    
    def set_theme(self, theme: str) -> None:
        """Set the current theme."""
        self.user_preferences.theme = theme
        self.save_settings()
    
    def get_language(self) -> str:
        """Get the current language."""
        return self.user_preferences.language
    
    def set_language(self, language: str) -> None:
        """Set the current language."""
        self.user_preferences.language = language
        self.save_settings()
    
    def should_show_welcome_screen(self) -> bool:
        """Check if welcome screen should be shown."""
        return self.user_preferences.show_welcome_screen
    
    def set_show_welcome_screen(self, show: bool) -> None:
        """Set whether to show welcome screen."""
        self.user_preferences.show_welcome_screen = show
        self.save_settings()
    
    def should_check_for_updates(self) -> bool:
        """Check if update checking is enabled."""
        return self.user_preferences.check_for_updates
    
    def set_check_for_updates(self, check: bool) -> None:
        """Set whether to check for updates."""
        self.user_preferences.check_for_updates = check
        self.save_settings()
    
    def get_window_geometry(self) -> Optional[str]:
        """Get the saved window geometry."""
        return self.user_preferences.window_geometry
    
    def set_window_geometry(self, geometry: str) -> None:
        """Set the window geometry."""
        self.user_preferences.window_geometry = geometry
        self.save_settings()
    
    def get_window_state(self) -> Optional[str]:
        """Get the saved window state."""
        return self.user_preferences.window_state
    
    def set_window_state(self, state: str) -> None:
        """Set the window state."""
        self.user_preferences.window_state = state
        self.save_settings()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        logger.info("Resetting application settings to defaults")
        
        self.user_preferences = UserPreferences()
        self.recent_projects.clear()
        self.custom_settings.clear()
        
        self.save_settings()
        logger.info("Settings reset to defaults")
    
    def export_settings(self, export_path: Path) -> None:
        """Export settings to a file."""
        logger.info(f"Exporting settings to: {export_path}")
        
        try:
            export_data = {
                'user_preferences': asdict(self.user_preferences),
                'recent_projects': [asdict(project) for project in self.recent_projects],
                'custom_settings': self.custom_settings,
                'export_timestamp': self._get_timestamp()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Settings exported successfully")
            
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
    
    def import_settings(self, import_path: Path) -> None:
        """Import settings from a file."""
        logger.info(f"Importing settings from: {import_path}")
        
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Import user preferences
            if 'user_preferences' in import_data:
                prefs_data = import_data['user_preferences']
                self.user_preferences = UserPreferences(
                    default_project_path=prefs_data.get('default_project_path', ''),
                    default_output_dir=prefs_data.get('default_output_dir', ''),
                    auto_save_enabled=prefs_data.get('auto_save_enabled', True),
                    auto_save_interval=prefs_data.get('auto_save_interval', 300),
                    show_welcome_screen=prefs_data.get('show_welcome_screen', True),
                    check_for_updates=prefs_data.get('check_for_updates', True),
                    theme=prefs_data.get('theme', 'default'),
                    language=prefs_data.get('language', 'en'),
                    max_recent_projects=prefs_data.get('max_recent_projects', 10),
                    window_geometry=prefs_data.get('window_geometry'),
                    window_state=prefs_data.get('window_state')
                )
            
            # Import recent projects
            if 'recent_projects' in import_data:
                self.recent_projects = []
                for project_data in import_data['recent_projects']:
                    project = RecentProject(
                        path=project_data['path'],
                        name=project_data['name'],
                        last_opened=project_data['last_opened'],
                        description=project_data.get('description')
                    )
                    self.recent_projects.append(project)
            
            # Import custom settings
            if 'custom_settings' in import_data:
                self.custom_settings = import_data['custom_settings']
            
            # Save imported settings
            self.save_settings()
            
            logger.info("Settings imported successfully")
            
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_settings_summary(self) -> Dict[str, Any]:
        """Get a summary of current settings."""
        return {
            'user_preferences': asdict(self.user_preferences),
            'recent_projects_count': len(self.recent_projects),
            'custom_settings_count': len(self.custom_settings),
            'settings_file': str(self.settings_file),
            'last_modified': self._get_last_modified_time()
        }
    
    def _get_last_modified_time(self) -> Optional[str]:
        """Get the last modified time of the settings file."""
        try:
            if self.settings_file.exists():
                timestamp = self.settings_file.stat().st_mtime
                from datetime import datetime
                return datetime.fromtimestamp(timestamp).isoformat()
        except Exception:
            pass
        return None
