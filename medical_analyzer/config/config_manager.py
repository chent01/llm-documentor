"""
Configuration management for the Medical Software Analysis Tool.

This module provides configuration loading, validation, and management
for application settings, LLM backends, and user preferences.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM backend settings."""
    backend_type: str  # 'mock', 'llama_cpp', 'local_server', 'openai', 'anthropic'
    model_path: Optional[str] = None
    server_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.1
    timeout: int = 30
    retry_attempts: int = 3
    batch_size: int = 8
    context_window: int = 4096
    embedding_model: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate the LLM configuration."""
        if self.backend_type not in ['mock', 'llama_cpp', 'local_server', 'openai', 'anthropic']:
            logger.error(f"Invalid backend type: {self.backend_type}")
            return False
            
        if self.backend_type == 'llama_cpp' and not self.model_path:
            logger.error("Model path is required for llama_cpp backend")
            return False
            
        if self.backend_type == 'local_server' and not self.server_url:
            logger.error("Server URL is required for local_server backend")
            return False
            
        if self.backend_type in ['openai', 'anthropic'] and not self.api_key:
            logger.error(f"API key is required for {self.backend_type} backend")
            return False
            
        return True


@dataclass
class DatabaseConfig:
    """Configuration for database settings."""
    db_path: str = ":memory:"
    backup_enabled: bool = True
    backup_interval: int = 3600  # seconds
    max_backups: int = 10


@dataclass
class ExportConfig:
    """Configuration for export settings."""
    default_format: str = "zip"
    include_audit_log: bool = True
    include_metadata: bool = True
    compression_level: int = 6
    max_file_size: int = 100 * 1024 * 1024  # 100MB


@dataclass
class UIConfig:
    """Configuration for UI settings."""
    theme: str = "default"
    window_width: int = 1200
    window_height: int = 800
    auto_save: bool = True
    auto_save_interval: int = 300  # seconds
    show_tooltips: bool = True
    confirm_exit: bool = True


@dataclass
class AnalysisConfig:
    """Configuration for analysis settings."""
    max_chunk_size: int = 1000
    min_confidence: float = 0.5
    max_files_per_analysis: int = 1000
    supported_extensions: List[str] = None
    enable_parallel_processing: bool = True
    max_workers: int = 4
    
    def __post_init__(self):
        if self.supported_extensions is None:
            self.supported_extensions = ['.c', '.h', '.js', '.ts', '.jsx', '.tsx']


@dataclass
class LoggingConfig:
    """Configuration for logging settings."""
    level: str = "INFO"
    file_enabled: bool = True
    console_enabled: bool = True
    log_file: str = "medical_analyzer.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ConfigManager:
    """Manages application configuration loading, validation, and access."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Optional path to a configuration file. If provided,
                         this file will be loaded instead of the default.
        """
        self.config_dir = self._get_config_dir()
        self.config_file = Path(config_path) if config_path else self.config_dir / "config.json"
        self.user_config_file = self.config_dir / "user_config.json"
        
        # Default configurations
        self.llm_config = LLMConfig(backend_type="mock")
        self.database_config = DatabaseConfig()
        self.export_config = ExportConfig()
        self.ui_config = UIConfig()
        self.analysis_config = AnalysisConfig()
        self.logging_config = LoggingConfig()
        
        # Version information
        self.version = self._get_version()
        
        # Custom settings
        self.custom_settings: Dict[str, Any] = {}
        
        # Load default configuration
        self.load_default_config()
    
    def _get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        # Try user-specific config directory first
        if os.name == 'nt':  # Windows
            config_dir = Path.home() / "AppData" / "Local" / "MedicalAnalyzer"
        else:  # Unix-like
            config_dir = Path.home() / ".config" / "medical_analyzer"
        
        # Create directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        return config_dir
    
    def _get_version(self) -> str:
        """Get the application version.
        
        Returns:
            The application version string.
        """
        try:
            from medical_analyzer import __version__
            return __version__
        except ImportError:
            return "1.0.0"
    
    def load_default_config(self) -> None:
        """Load default configuration settings."""
        logger.info("Loading default configuration")
        
        # Check if default config exists in package
        default_config_path = Path(__file__).parent / "templates" / "default_config.json"
        
        if default_config_path.exists():
            try:
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._apply_config(config_data)
                logger.info("Loaded default configuration from template")
            except Exception as e:
                logger.error(f"Failed to load default configuration: {e}")
        else:
            logger.info("No default configuration template found, using built-in defaults")
            
            # Set default LLM configuration if no template found
            self.llm_config = LLMConfig(
            backend_type="mock",
            max_tokens=1000,
            temperature=0.1,
            timeout=30,
            retry_attempts=3
        )
        
        # Set default database configuration
        db_path = self.config_dir / "medical_analyzer.db"
        self.database_config = DatabaseConfig(
            db_path=str(db_path),
            backup_enabled=True,
            backup_interval=3600,
            max_backups=10
        )
        
        # Set default export configuration
        self.export_config = ExportConfig(
            default_format="zip",
            include_audit_log=True,
            include_metadata=True,
            compression_level=6,
            max_file_size=100 * 1024 * 1024
        )
        
        # Set default UI configuration
        self.ui_config = UIConfig(
            theme="default",
            window_width=1200,
            window_height=800,
            auto_save=True,
            auto_save_interval=300,
            show_tooltips=True,
            confirm_exit=True
        )
        
        # Set default analysis configuration
        self.analysis_config = AnalysisConfig(
            max_chunk_size=1000,
            min_confidence=0.5,
            max_files_per_analysis=1000,
            enable_parallel_processing=True,
            max_workers=4
        )
        
        # Set default logging configuration
        log_file = self.config_dir / "medical_analyzer.log"
        self.logging_config = LoggingConfig(
            level="INFO",
            file_enabled=True,
            console_enabled=True,
            log_file=str(log_file),
            max_file_size=10 * 1024 * 1024,
            backup_count=5
        )
        
        logger.info("Default configuration loaded successfully")
    
    def load_config(self, config_path: Path) -> None:
        """Load configuration from a JSON file."""
        logger.info(f"Loading configuration from: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Load LLM configuration
            if 'llm' in config_data:
                llm_data = config_data['llm']
                self.llm_config = LLMConfig(
                    backend_type=llm_data.get('backend_type', 'mock'),
                    model_path=llm_data.get('model_path'),
                    server_url=llm_data.get('server_url'),
                    api_key=llm_data.get('api_key'),
                    max_tokens=llm_data.get('max_tokens', 1000),
                    temperature=llm_data.get('temperature', 0.1),
                    timeout=llm_data.get('timeout', 30),
                    retry_attempts=llm_data.get('retry_attempts', 3)
                )
            
            # Load database configuration
            if 'database' in config_data:
                db_data = config_data['database']
                self.database_config = DatabaseConfig(
                    db_path=db_data.get('db_path', str(self.config_dir / "medical_analyzer.db")),
                    backup_enabled=db_data.get('backup_enabled', True),
                    backup_interval=db_data.get('backup_interval', 3600),
                    max_backups=db_data.get('max_backups', 10)
                )
            
            # Load export configuration
            if 'export' in config_data:
                export_data = config_data['export']
                self.export_config = ExportConfig(
                    default_format=export_data.get('default_format', 'zip'),
                    include_audit_log=export_data.get('include_audit_log', True),
                    include_metadata=export_data.get('include_metadata', True),
                    compression_level=export_data.get('compression_level', 6),
                    max_file_size=export_data.get('max_file_size', 100 * 1024 * 1024)
                )
            
            # Load UI configuration
            if 'ui' in config_data:
                ui_data = config_data['ui']
                self.ui_config = UIConfig(
                    theme=ui_data.get('theme', 'default'),
                    window_width=ui_data.get('window_width', 1200),
                    window_height=ui_data.get('window_height', 800),
                    auto_save=ui_data.get('auto_save', True),
                    auto_save_interval=ui_data.get('auto_save_interval', 300),
                    show_tooltips=ui_data.get('show_tooltips', True),
                    confirm_exit=ui_data.get('confirm_exit', True)
                )
            
            # Load analysis configuration
            if 'analysis' in config_data:
                analysis_data = config_data['analysis']
                self.analysis_config = AnalysisConfig(
                    max_chunk_size=analysis_data.get('max_chunk_size', 1000),
                    min_confidence=analysis_data.get('min_confidence', 0.5),
                    max_files_per_analysis=analysis_data.get('max_files_per_analysis', 1000),
                    supported_extensions=analysis_data.get('supported_extensions', ['.c', '.h', '.js', '.ts', '.jsx', '.tsx']),
                    enable_parallel_processing=analysis_data.get('enable_parallel_processing', True),
                    max_workers=analysis_data.get('max_workers', 4)
                )
            
            # Load logging configuration
            if 'logging' in config_data:
                logging_data = config_data['logging']
                log_file = self.config_dir / "medical_analyzer.log"
                self.logging_config = LoggingConfig(
                    level=logging_data.get('level', 'INFO'),
                    file_enabled=logging_data.get('file_enabled', True),
                    console_enabled=logging_data.get('console_enabled', True),
                    log_file=logging_data.get('log_file', str(log_file)),
                    max_file_size=logging_data.get('max_file_size', 10 * 1024 * 1024),
                    backup_count=logging_data.get('backup_count', 5),
                    format_string=logging_data.get('format_string', "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )
            
            # Load custom settings
            if 'custom' in config_data:
                self.custom_settings = config_data['custom']
            
            logger.info("Configuration loaded successfully")
            
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {config_path}")
            self.load_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            self.load_default_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.load_default_config()
    
    def save_config(self, config_path: Optional[Path] = None) -> None:
        """Save current configuration to a JSON file."""
        if config_path is None:
            config_path = self.config_file
        
        logger.info(f"Saving configuration to: {config_path}")
        
        try:
            config_data = {
                'llm': asdict(self.llm_config),
                'database': asdict(self.database_config),
                'export': asdict(self.export_config),
                'ui': asdict(self.ui_config),
                'analysis': asdict(self.analysis_config),
                'logging': asdict(self.logging_config),
                'custom': self.custom_settings
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def _apply_config(self, config_data: Dict[str, Any]) -> None:
        """Apply configuration data to the current configuration.
        
        Args:
            config_data: Configuration data to apply.
        """
        # Apply LLM configuration
        if 'llm' in config_data:
            llm_data = config_data['llm']
            self.llm_config = LLMConfig(
                backend_type=llm_data.get('backend_type', 'mock'),
                model_path=llm_data.get('model_path'),
                server_url=llm_data.get('server_url'),
                api_key=llm_data.get('api_key'),
                model_name=llm_data.get('model_name'),
                max_tokens=llm_data.get('max_tokens', 1000),
                temperature=llm_data.get('temperature', 0.1),
                timeout=llm_data.get('timeout', 30),
                retry_attempts=llm_data.get('retry_attempts', 3),
                batch_size=llm_data.get('batch_size', 8),
                context_window=llm_data.get('context_window', 4096),
                embedding_model=llm_data.get('embedding_model')
            )
        
        # Apply database configuration
        if 'database' in config_data:
            db_data = config_data['database']
            self.database_config = DatabaseConfig(
                db_path=db_data.get('db_path', ':memory:'),
                backup_enabled=db_data.get('backup_enabled', True),
                backup_interval=db_data.get('backup_interval', 3600),
                max_backups=db_data.get('max_backups', 10)
            )
        
        # Apply export configuration
        if 'export' in config_data:
            export_data = config_data['export']
            self.export_config = ExportConfig(
                default_format=export_data.get('default_format', 'zip'),
                include_audit_log=export_data.get('include_audit_log', True),
                include_metadata=export_data.get('include_metadata', True),
                compression_level=export_data.get('compression_level', 6),
                max_file_size=export_data.get('max_file_size', 100 * 1024 * 1024)
            )
        
        # Apply UI configuration
        if 'ui' in config_data:
            ui_data = config_data['ui']
            self.ui_config = UIConfig(
                theme=ui_data.get('theme', 'default'),
                window_width=ui_data.get('window_width', 1200),
                window_height=ui_data.get('window_height', 800),
                auto_save=ui_data.get('auto_save', True),
                auto_save_interval=ui_data.get('auto_save_interval', 300),
                show_tooltips=ui_data.get('show_tooltips', True),
                confirm_exit=ui_data.get('confirm_exit', True)
            )
        
        # Apply analysis configuration
        if 'analysis' in config_data:
            analysis_data = config_data['analysis']
            self.analysis_config = AnalysisConfig(
                max_chunk_size=analysis_data.get('max_chunk_size', 1000),
                min_confidence=analysis_data.get('min_confidence', 0.5),
                max_files_per_analysis=analysis_data.get('max_files_per_analysis', 1000),
                supported_extensions=analysis_data.get('supported_extensions'),
                enable_parallel_processing=analysis_data.get('enable_parallel_processing', True),
                max_workers=analysis_data.get('max_workers', 4)
            )
        
        # Apply logging configuration
        if 'logging' in config_data:
            logging_data = config_data['logging']
            self.logging_config = LoggingConfig(
                level=logging_data.get('level', 'INFO'),
                file_enabled=logging_data.get('file_enabled', True),
                console_enabled=logging_data.get('console_enabled', True),
                log_file=logging_data.get('log_file', 'medical_analyzer.log'),
                max_file_size=logging_data.get('max_file_size', 10 * 1024 * 1024),
                backup_count=logging_data.get('backup_count', 5),
                format_string=logging_data.get('format_string', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        
        # Apply custom settings
        if 'custom' in config_data:
            self.custom_settings = config_data['custom']
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration as a dictionary."""
        return asdict(self.llm_config)
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration as a dictionary."""
        return asdict(self.database_config)
    
    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration as a dictionary."""
        return asdict(self.export_config)
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration as a dictionary."""
        return asdict(self.ui_config)
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration as a dictionary."""
        return asdict(self.analysis_config)
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration as a dictionary."""
        return asdict(self.logging_config)
    
    def update_llm_config(self, **kwargs) -> None:
        """Update LLM configuration."""
        for key, value in kwargs.items():
            if hasattr(self.llm_config, key):
                setattr(self.llm_config, key, value)
            else:
                logger.warning(f"Unknown LLM config key: {key}")
    
    def update_ui_config(self, **kwargs) -> None:
        """Update UI configuration."""
        for key, value in kwargs.items():
            if hasattr(self.ui_config, key):
                setattr(self.ui_config, key, value)
            else:
                logger.warning(f"Unknown UI config key: {key}")
    
    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """Get a custom setting value."""
        return self.custom_settings.get(key, default)
    
    def set_custom_setting(self, key: str, value: Any) -> None:
        """Set a custom setting value."""
        self.custom_settings[key] = value
    
    def validate_config(self) -> bool:
        """Validate the current configuration."""
        logger.info("Validating configuration")
        
        try:
            # Validate LLM configuration
            if not self.llm_config.backend_type:
                logger.error("LLM backend type is required")
                return False
            
            # Validate database configuration
            if not self.database_config.db_path:
                logger.error("Database path is required")
                return False
            
            # Validate analysis configuration
            if self.analysis_config.max_chunk_size <= 0:
                logger.error("Max chunk size must be positive")
                return False
            
            if not (0.0 <= self.analysis_config.min_confidence <= 1.0):
                logger.error("Min confidence must be between 0.0 and 1.0")
                return False
            
            # Validate logging configuration
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if self.logging_config.level not in valid_log_levels:
                logger.error(f"Invalid log level: {self.logging_config.level}")
                return False
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def create_sample_config(self, output_path: Path) -> None:
        """Create a sample configuration file."""
        logger.info(f"Creating sample configuration at: {output_path}")
        
        sample_config = {
            'llm': {
                'backend_type': 'mock',
                'model_path': None,
                'server_url': None,
                'api_key': None,
                'max_tokens': 1000,
                'temperature': 0.1,
                'timeout': 30,
                'retry_attempts': 3
            },
            'database': {
                'db_path': str(self.config_dir / "medical_analyzer.db"),
                'backup_enabled': True,
                'backup_interval': 3600,
                'max_backups': 10
            },
            'export': {
                'default_format': 'zip',
                'include_audit_log': True,
                'include_metadata': True,
                'compression_level': 6,
                'max_file_size': 100 * 1024 * 1024
            },
            'ui': {
                'theme': 'default',
                'window_width': 1200,
                'window_height': 800,
                'auto_save': True,
                'auto_save_interval': 300,
                'show_tooltips': True,
                'confirm_exit': True
            },
            'analysis': {
                'max_chunk_size': 1000,
                'min_confidence': 0.5,
                'max_files_per_analysis': 1000,
                'supported_extensions': ['.c', '.h', '.js', '.ts', '.jsx', '.tsx'],
                'enable_parallel_processing': True,
                'max_workers': 4
            },
            'logging': {
                'level': 'INFO',
                'file_enabled': True,
                'console_enabled': True,
                'log_file': str(self.config_dir / "medical_analyzer.log"),
                'max_file_size': 10 * 1024 * 1024,
                'backup_count': 5,
                'format_string': "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            'custom': {
                'example_setting': 'example_value'
            }
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, indent=2, ensure_ascii=False)
            
            logger.info("Sample configuration created successfully")
            
        except Exception as e:
            logger.error(f"Error creating sample configuration: {e}")
