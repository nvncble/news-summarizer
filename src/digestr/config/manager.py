#!/usr/bin/env python3
"""
Updated Digestr Configuration Management
Handles all new features including personal Reddit and briefing structure
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Base source configuration"""
    enabled: bool = False


@dataclass
class RSSSourceConfig(SourceConfig):
    """RSS source configuration"""
    enabled: bool = True


@dataclass
class RedditSourceConfig(SourceConfig):
    """Reddit news source configuration"""
    enabled: bool = True
    client_id: str = ""
    client_secret: str = ""
    user_agent: str = "Digestr.ai/2.1"
    subreddits: List[Dict] = None
    quality_control: Dict = None
    
    def __post_init__(self):
        if self.subreddits is None:
            self.subreddits = []
        if self.quality_control is None:
            self.quality_control = {
                "min_comment_karma": 50,
                "min_account_age_days": 30,
                "bot_detection": True
            }


@dataclass 
class RedditPersonalConfig(SourceConfig):
    """Personal Reddit source configuration"""
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    user_agent: str = "Digestr.ai/2.1"
    filtering: Dict = None
    content_types: List[str] = None
    cache_duration_minutes: int = 45
    
    def __post_init__(self):
        if self.filtering is None:
            self.filtering = {
                "time_window_hours": 24,
                "min_upvotes": 10,
                "max_posts": 25,
                "exclude_nsfw": True,
                "exclude_subreddits": [],
                "include_only": []
            }
        if self.content_types is None:
            self.content_types = ["hot", "new"]


@dataclass
class BriefingConfig:
    """Briefing structure and style configuration"""
    structure: Dict = None
    styles: Dict = None
    content: Dict = None
    
    def __post_init__(self):
        if self.structure is None:
            self.structure = {
                "default_order": ["professional", "social"],
                "professional_sources": ["rss", "reddit"],
                "social_sources": ["reddit_personal"]
            }
        if self.styles is None:
            self.styles = {
                "professional": {
                    "tone": "analytical and informative",
                    "focus": "implications and significance",
                    "greeting": "Here's your professional briefing"
                },
                "social": {
                    "tone": "casual and conversational",
                    "focus": "interesting highlights from your personal feeds", 
                    "greeting": "And here's what's happening in your corner of Reddit"
                }
            }
        if self.content is None:
            self.content = {
                "skip_if_no_new_articles": True,
                "max_articles_per_briefing": 50,
                "minimum_importance": 1.0,
                "include_article_links": True
            }


@dataclass
class SourcesConfig:
    """All sources configuration"""
    rss: RSSSourceConfig = None
    reddit: RedditSourceConfig = None  
    reddit_personal: RedditPersonalConfig = None
    
    def __post_init__(self):
        if self.rss is None:
            self.rss = RSSSourceConfig()
        if self.reddit is None:
            self.reddit = RedditSourceConfig()
        if self.reddit_personal is None:
            self.reddit_personal = RedditPersonalConfig()


@dataclass
class FeatureFlags:
    """Feature flag configuration with new features"""
    # Stable features (enabled by default)
    enhanced_summarization: bool = True
    concurrent_processing: bool = True
    importance_scoring: bool = True
    
    # New features (opt-in initially)
    interactive_mode: bool = True
    multi_model_support: bool = False
    community_sharing: bool = False
    
    # Experimental features (disabled by default)
    web_search_context: bool = False
    conversation_export: bool = False
    sentiment_analysis: bool = True
    
    # Provider-specific features
    openai_support: bool = False
    anthropic_support: bool = False


@dataclass
class LLMConfig:
    """Enhanced LLM provider configuration"""
    default_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    fallback_enabled: bool = True
    models: Dict[str, str] = None
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
    connection_timeout: int = 30
    max_connections: int = 10


@dataclass
class FetchConfig:
    """RSS fetching configuration"""
    concurrent_limit: int = 50
    per_host_limit: int = 10
    request_timeout: int = 30
    retry_attempts: int = 3
    delay_between_batches: float = 0.5
    respect_robots_txt: bool = True
    user_agent: str = "Digestr.ai/2.1 (+https://github.com/nvncble/digestr)"


@dataclass
class InteractiveConfig:
    """Interactive mode configuration"""
    max_context_length: int = 4000
    conversation_history_limit: int = 10
    enable_plugins: bool = True


@dataclass
class PreferencesConfig:
    """User preferences"""
    default_category: Optional[str] = None
    default_hours: int = 24
    default_briefing_style: str = "comprehensive"


@dataclass
class PluginConfig:
    """Plugin system configuration"""
    enabled: bool = True
    auto_load: bool = True
    directory: str = "~/.config/digestr/plugins"



@dataclass
class TrendingConfig:
    """Trending analysis configuration"""
    enabled: bool = True
    geographic: Dict = None
    correlation: Dict = None
    sources: Dict = None
    briefing_integration: Dict = None
    
    def __post_init__(self):
        if self.geographic is None:
            self.geographic = {
                'country': 'United States',
                'state': None,
                'city': None,
                'include_national': True
            }
        if self.correlation is None:
            self.correlation = {
                'min_threshold': 0.4,
                'strong_threshold': 0.7,
                'semantic_matching': True,
                'entity_extraction': True,
                'geographic_boost': True
            }
        if self.sources is None:
            self.sources = {
                'trends24': {'enabled': True, 'regions': ['united-states']},
                'twitter': {'enabled': False},
                'youtube': {'enabled': False}
            }
        if self.briefing_integration is None:
            self.briefing_integration = {
                'show_trend_alerts': True,
                'integrate_with_articles': True,
                'dedicated_trends_section': True
            }



@dataclass
class DigestrConfig:
    """Main configuration container with all new features"""
    features: FeatureFlags = None
    llm: LLMConfig = None
    database: DatabaseConfig = None
    fetching: FetchConfig = None
    sources: SourcesConfig = None
    briefing: BriefingConfig = None
    interactive: InteractiveConfig = None
    preferences: PreferencesConfig = None
    plugins: PluginConfig = None
    trending: TrendingConfig = None
    
    def __post_init__(self):
        if self.trending is None:
            self.trending = TrendingConfig()
        if self.features is None:
            self.features = FeatureFlags()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.database is None:
            self.database = DatabaseConfig()
        if self.fetching is None:
            self.fetching = FetchConfig()
        if self.sources is None:
            self.sources = SourcesConfig()
        if self.briefing is None:
            self.briefing = BriefingConfig()
        if self.interactive is None:
            self.interactive = InteractiveConfig()
        if self.preferences is None:
            self.preferences = PreferencesConfig()
        if self.plugins is None:
            self.plugins = PluginConfig()


class EnhancedConfigurationManager:
    """Enhanced configuration manager with support for all new features"""
    
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
        """Apply environment variable overrides for new fields"""
        env_mappings = {
            'DIGESTR_OLLAMA_URL': ['llm', 'ollama_url'],
            'DIGESTR_DB_PATH': ['database', 'path'],
            'DIGESTR_DEFAULT_CATEGORY': ['preferences', 'default_category'],
            'DIGESTR_OPENAI_API_KEY': ['llm', 'openai_api_key'],
            'DIGESTR_ANTHROPIC_API_KEY': ['llm', 'anthropic_api_key'],
            'REDDIT_CLIENT_ID': ['sources', 'reddit', 'client_id'],
            'REDDIT_CLIENT_SECRET': ['sources', 'reddit', 'client_secret'],
            'REDDIT_REFRESH_TOKEN': ['sources', 'reddit_personal', 'refresh_token'],
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
        # Handle sources configuration
        sources_data = data.get('sources', {})
        sources_config = SourcesConfig()
        
        # RSS config
        if 'rss' in sources_data:
            rss_data = sources_data['rss']
            sources_config.rss = RSSSourceConfig(**{k: v for k, v in rss_data.items() if hasattr(RSSSourceConfig, k)})
        
        # Reddit config  
        if 'reddit' in sources_data:
            reddit_data = sources_data['reddit']
            sources_config.reddit = RedditSourceConfig(**{k: v for k, v in reddit_data.items() if hasattr(RedditSourceConfig, k)})
        
        # Personal Reddit config
        if 'reddit_personal' in sources_data:
            reddit_personal_data = sources_data['reddit_personal'] 
            sources_config.reddit_personal = RedditPersonalConfig(**{k: v for k, v in reddit_personal_data.items() if hasattr(RedditPersonalConfig, k)})
        
        # Handle other configs
        features_data = data.get('features', {})
        features = FeatureFlags(**{k: v for k, v in features_data.items() if hasattr(FeatureFlags, k)})
        
        llm_data = data.get('llm', {})
        llm = LLMConfig(**{k: v for k, v in llm_data.items() if hasattr(LLMConfig, k)})
        
        database_data = data.get('database', {})
        database = DatabaseConfig(**{k: v for k, v in database_data.items() if hasattr(DatabaseConfig, k)})
        
        fetching_data = data.get('fetching', {})
        fetching = FetchConfig(**{k: v for k, v in fetching_data.items() if hasattr(FetchConfig, k)})
        
        briefing_data = data.get('briefing', {})
        briefing = BriefingConfig(**{k: v for k, v in briefing_data.items() if hasattr(BriefingConfig, k)})
        
        interactive_data = data.get('interactive', {})
        interactive = InteractiveConfig(**{k: v for k, v in interactive_data.items() if hasattr(InteractiveConfig, k)})
        
        preferences_data = data.get('preferences', {})
        preferences = PreferencesConfig(**{k: v for k, v in preferences_data.items() if hasattr(PreferencesConfig, k)})
        
        plugins_data = data.get('plugins', {})
        plugins = PluginConfig(**{k: v for k, v in plugins_data.items() if hasattr(PluginConfig, k)})
        
        return DigestrConfig(
            features=features,
            llm=llm,
            database=database,
            fetching=fetching,
            sources=sources_config,
            briefing=briefing,
            interactive=interactive,
            preferences=preferences,
            plugins=plugins
        )
    
    def _validate_config(self):
        """Validate configuration and feature dependencies"""
        if not self._config:
            return
        
        validation_errors = []
        
        # Validate Reddit configurations
        reddit_config = self._config.sources.reddit
        if reddit_config.enabled and not (reddit_config.client_id and reddit_config.client_secret):
            validation_errors.append("Reddit enabled but missing client_id/client_secret")
        
        reddit_personal_config = self._config.sources.reddit_personal
        if reddit_personal_config.enabled:
            if not (reddit_personal_config.client_id and reddit_personal_config.client_secret and reddit_personal_config.refresh_token):
                validation_errors.append("Personal Reddit enabled but missing credentials")
        
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
    
    def get_config(self) -> DigestrConfig:
        """Get current configuration"""
        return self._config
    
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
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled"""
        return getattr(self._config.features, feature_name, False)
    
    def get_source_config(self, source_name: str):
        """Get configuration for a specific source"""
        return getattr(self._config.sources, source_name, None)
    
    def get_briefing_config(self) -> BriefingConfig:
        """Get briefing configuration"""
        return self._config.briefing
    
    def create_example_config(self, file_path: Optional[str] = None):
        """Create an example configuration file"""
        if file_path is None:
            file_path = self.config_dir / "config.example.yaml"
        
        example_config = DigestrConfig()
        config_dict = asdict(example_config)
        
        try:
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            logger.info(f"Example configuration created at {file_path}")
        except Exception as e:
            logger.error(f"Error creating example config: {e}")


# Global configuration manager
_global_enhanced_config_manager: Optional[EnhancedConfigurationManager] = None

def get_enhanced_config_manager() -> EnhancedConfigurationManager:
    """Get global enhanced configuration manager instance"""
    global _global_enhanced_config_manager
    if _global_enhanced_config_manager is None:
        _global_enhanced_config_manager = EnhancedConfigurationManager()
    return _global_enhanced_config_manager

def get_enhanced_config() -> DigestrConfig:
    """Get current enhanced configuration"""
    return get_enhanced_config_manager().get_config()