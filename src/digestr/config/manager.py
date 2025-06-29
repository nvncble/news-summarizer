#!/usr/bin/env python3
"""
Digestr Configuration Management
Handles feature flags, user preferences, and environment configuration
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlags:
    """Feature flag configuration"""
    # Stable features (enabled by default in v2.0.0)
    enhanced_summarization: bool = True
    concurrent_processing: bool = True
    importance_scoring: bool = True
    
    # New features (opt-in initially)
    interactive_mode: bool = False
    multi_model_support: bool = False
    community_sharing: bool = False
    
    # Experimental features (disabled by default)
    web_search_context: bool = False
    conversation_export: bool = False
    sentiment_analysis: bool = False
    
    # Provider-specific features
    openai_support: bool = False
    anthropic_support: bool = False


@dataclass
class LLMConfig:
    """LLM provider configuration"""
    default_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    fallback_enabled: bool = True
    
    # Model mappings
    models: Dict[str, str] = None
    
    # API configurations (when providers are enabled)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    def __post_init__(self):
        if self.models is None:
            self.models = {
                "default": "llama3.1:8b",
                "technical": "deepseek-coder:6.7b",
                "conversational": "llama3.1:8b",
                "academic": "qwen2.5:14b",
                "fast": "llama3.1:8b",
                "detailed": "llama3.1:70b"
            }

@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "rss_feeds.db"
    cleanup_days: int = 30
    backup_enabled: bool = True
    
    # Performance settings
    connection_timeout: int = 30
    max_connections: int = 10


@dataclass
class FetchConfig:
    """RSS fetching configuration"""
    concurrent_limit: int = 50
    per_host_limit: int = 10
    request_timeout: int = 30
    retry_attempts: int = 3
    
    # Rate limiting
    delay_between_batches: float = 0.5
    respect_robots_txt: bool = True
    
    # Custom headers
    user_agent: str = "Digestr.ai/2.0 (+https://github.com/nvncble/digestr)"


@dataclass
class DigestrConfig:
    """Main configuration container"""
    features: FeatureFlags = None
    llm: LLMConfig = None
    database: DatabaseConfig = None
    fetching: FetchConfig = None
    
    # User preferences
    default_category: Optional[str] = None
    default_hours: int = 24
    default_briefing_style: str = "comprehensive"
    
    def __post_init__(self):
        if self.features is None:
            self.features = FeatureFlags()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.fetching is None:
            self.fetching = FetchConfig()


class ConfigurationManager:
    """Manages configuration loading, validation, and feature flag operations"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else self._get_default_config_dir()
        self.config_file = self.config_dir / "config.yaml"
        self.project_config_file = Path("./digestr.yaml")
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._config: Optional[DigestrConfig] = None
        self._load_config()
    
    def _get_default_config_dir(self) -> Path:
        """Get default configuration directory following XDG specification"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '~/.config')) / 'digestr'
        else:  # Unix-like systems
            config_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')) / 'digestr'
        
        return config_dir.expanduser()
    
    def _load_config(self):
        """Load configuration with hierarchical precedence"""
        # Start with defaults
        config_data = {}
        
        # Load user config if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                config_data.update(user_config)
                logger.debug(f"Loaded user config from {self.config_file}")
            except Exception as e:
                logger.warning(f"Error loading user config: {e}")
        
        # Load project config if it exists (overrides user config)
        if self.project_config_file.exists():
            try:
                with open(self.project_config_file, 'r') as f:
                    project_config = yaml.safe_load(f) or {}
                self._merge_config(config_data, project_config)
                logger.debug(f"Loaded project config from {self.project_config_file}")
            except Exception as e:
                logger.warning(f"Error loading project config: {e}")
        
        # Apply environment variable overrides
        self._apply_env_overrides(config_data)
        
        # Create configuration object
        self._config = self._create_config_from_dict(config_data)
        
        # Validate configuration
        self._validate_config()
    
    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def _apply_env_overrides(self, config_data: Dict):
        """Apply environment variable overrides"""
        env_mappings = {
            'DIGESTR_OLLAMA_URL': ['llm', 'ollama_url'],
            'DIGESTR_DB_PATH': ['database', 'path'],
            'DIGESTR_DEFAULT_CATEGORY': ['default_category'],
            'DIGESTR_OPENAI_API_KEY': ['llm', 'openai_api_key'],
            'DIGESTR_ANTHROPIC_API_KEY': ['llm', 'anthropic_api_key'],
        }
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                self._set_nested_value(config_data, config_path, os.environ[env_var])
    
    def _set_nested_value(self, data: Dict, path: List[str], value: Any):
        """Set a nested dictionary value using a path"""
        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _create_config_from_dict(self, data: Dict) -> DigestrConfig:
        """Create DigestrConfig object from dictionary data"""
        # Extract nested configurations
        features_data = data.get('features', {})
        llm_data = data.get('llm', {})
        database_data = data.get('database', {})
        fetching_data = data.get('fetching', {})
        
        # Create nested configuration objects
        features = FeatureFlags(**{k: v for k, v in features_data.items() 
                                 if hasattr(FeatureFlags, k)})
        llm = LLMConfig(**{k: v for k, v in llm_data.items() 
                         if hasattr(LLMConfig, k)})
        database = DatabaseConfig(**{k: v for k, v in database_data.items() 
                                   if hasattr(DatabaseConfig, k)})
        fetching = FetchConfig(**{k: v for k, v in fetching_data.items() 
                               if hasattr(FetchConfig, k)})
        
        # Create main config with remaining top-level settings
        main_config_data = {k: v for k, v in data.items() 
                           if k not in ['features', 'llm', 'database', 'fetching']}
        
        return DigestrConfig(
            features=features,
            llm=llm,
            database=database,
            fetching=fetching,
            **{k: v for k, v in main_config_data.items() 
               if hasattr(DigestrConfig, k)}
        )
    
    def _validate_config(self):
        """Validate configuration and feature dependencies"""
        if not self._config:
            return
        
        validation_errors = []
        
        # Validate LLM provider configuration
        if self._config.features.openai_support and not self._config.llm.openai_api_key:
            validation_errors.append("OpenAI support enabled but no API key configured")
        
        if self._config.features.anthropic_support and not self._config.llm.anthropic_api_key:
            validation_errors.append("Anthropic support enabled but no API key configured")
        
        # Validate file paths
        db_path = Path(self._config.database.path)
        if not db_path.parent.exists():
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                validation_errors.append(f"Cannot create database directory: {e}")
        
        # Log validation errors
        for error in validation_errors:
            logger.warning(f"Configuration validation: {error}")
    
    def save_config(self):
        """Save current configuration to user config file"""
        if not self._config:
            return
        
        try:
            config_dict = asdict(self._config)
            with open(self.config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get_config(self) -> DigestrConfig:
        """Get current configuration"""
        return self._config
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled"""
        return getattr(self._config.features, feature_name, False)
    
    def enable_feature(self, feature_name: str) -> bool:
        """Enable a specific feature"""
        if hasattr(self._config.features, feature_name):
            setattr(self._config.features, feature_name, True)
            self.save_config()
            logger.info(f"Enabled feature: {feature_name}")
            return True
        return False
    
    def disable_feature(self, feature_name: str) -> bool:
        """Disable a specific feature"""
        if hasattr(self._config.features, feature_name):
            setattr(self._config.features, feature_name, False)
            self.save_config()
            logger.info(f"Disabled feature: {feature_name}")
            return True
        return False
    
    def list_features(self) -> Dict[str, bool]:
        """List all features and their current status"""
        return asdict(self._config.features)
    
    def list_experimental_features(self) -> Dict[str, bool]:
        """List only experimental features"""
        experimental = [
            'web_search_context', 'conversation_export', 'sentiment_analysis'
        ]
        return {name: getattr(self._config.features, name) 
                for name in experimental}
    
    def enable_experimental_mode(self):
        """Enable all experimental features"""
        experimental_features = self.list_experimental_features()
        for feature_name in experimental_features:
            setattr(self._config.features, feature_name, True)
        self.save_config()
        logger.info("Enabled experimental mode")
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration"""
        return self._config.llm
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return self._config.database
    
    def get_fetch_config(self) -> FetchConfig:
        """Get fetching configuration"""
        return self._config.fetching
    
    def update_config(self, **kwargs):
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save_config()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self._config = DigestrConfig()
        self.save_config()
        logger.info("Configuration reset to defaults")
    
    def export_config(self, file_path: str):
        """Export current configuration to a file"""
        try:
            config_dict = asdict(self._config)
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration exported to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
    
    def import_config(self, file_path: str):
        """Import configuration from a file"""
        try:
            with open(file_path, 'r') as f:
                imported_data = yaml.safe_load(f)
            
            self._config = self._create_config_from_dict(imported_data)
            self._validate_config()
            self.save_config()
            logger.info(f"Configuration imported from {file_path}")
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a comprehensive status summary"""
        if not self._config:
            return {"status": "error", "message": "No configuration loaded"}
        
        enabled_features = [name for name, enabled in self.list_features().items() if enabled]
        experimental_features = [name for name, enabled in self.list_experimental_features().items() if enabled]
        
        return {
            "config_file": str(self.config_file),
            "project_config": str(self.project_config_file) if self.project_config_file.exists() else None,
            "features": {
                "total_enabled": len(enabled_features),
                "enabled": enabled_features,
                "experimental_enabled": experimental_features
            },
            "llm": {
                "default_provider": self._config.llm.default_provider,
                "ollama_url": self._config.llm.ollama_url,
                "providers_available": self._get_available_providers()
            },
            "database": {
                "path": self._config.database.path,
                "exists": Path(self._config.database.path).exists()
            }
        }
    
    def _get_available_providers(self) -> List[str]:
        """Get list of available LLM providers based on configuration"""
        providers = ["ollama"]  # Always available
        
        if self._config.features.openai_support and self._config.llm.openai_api_key:
            providers.append("openai")
        
        if self._config.features.anthropic_support and self._config.llm.anthropic_api_key:
            providers.append("anthropic")
        
        return providers


# Convenience function for getting global configuration
_global_config_manager: Optional[ConfigurationManager] = None

def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigurationManager()
    return _global_config_manager

def get_config() -> DigestrConfig:
    """Get current configuration"""
    return get_config_manager().get_config()

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled"""
    return get_config_manager().is_feature_enabled(feature_name)
