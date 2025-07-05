#!/usr/bin/env python3
"""
Digestr Plugin Manager - Full Implementation
Manages plugin lifecycle: discovery, loading, validation, and execution
"""

import os
import json
import yaml
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass

from .plugin_base import DigestrPlugin
from .plugin_system import PluginHooks

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    """Plugin manifest data structure"""
    name: str
    display_name: str
    version: str
    author: str
    description: str
    digestr_version: str
    entry_point: str
    hooks: List[str]
    commands: List[Dict[str, str]]
    config_schema: Dict[str, Any]
    dependencies: List[str]
    tags: List[str]
    plugin_dir: Path


class PluginManager:
    """Manages plugin lifecycle and hook execution"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.plugins: Dict[str, DigestrPlugin] = {}  # Active plugin instances
        self.manifests: Dict[str, PluginManifest] = {}  # Loaded manifests
        self.hooks: Dict[str, List[callable]] = {}  # Hook callbacks
        self.commands: Dict[str, callable] = {}  # Registered commands
        
        self.plugin_dir = self._get_plugin_directory()
        self.enabled_plugins = self._load_enabled_plugins()
        
        # Initialize hooks registry
        self._initialize_hooks()
    
    def _get_plugin_directory(self) -> Path:
        """Get the plugin directory path"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '~/.config')) / 'digestr'
        else:  # Unix-like systems
            config_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')) / 'digestr'
        
        plugin_dir = config_dir.expanduser() / 'plugins'
        plugin_dir.mkdir(parents=True, exist_ok=True)
        return plugin_dir
    
    def _load_enabled_plugins(self) -> Dict[str, Dict]:
        """Load the enabled plugins configuration"""
        enabled_file = self.plugin_dir.parent / 'plugins' / 'enabled.yaml'
        
        if not enabled_file.exists():
            # Create default enabled.yaml
            default_config = {
                'plugins': {},
                'auto_update': False,
                'load_order': []
            }
            enabled_file.parent.mkdir(exist_ok=True)
            with open(enabled_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
            return default_config
        
        try:
            with open(enabled_file, 'r') as f:
                return yaml.safe_load(f) or {'plugins': {}, 'auto_update': False, 'load_order': []}
        except Exception as e:
            logger.error(f"Error loading enabled plugins config: {e}")
            return {'plugins': {}, 'auto_update': False, 'load_order': []}
    
    def _initialize_hooks(self):
        """Initialize the hooks registry with all available hooks"""
        # Get all hook constants from PluginHooks
        for attr_name in dir(PluginHooks):
            if not attr_name.startswith('_'):
                hook_name = getattr(PluginHooks, attr_name)
                if isinstance(hook_name, str):
                    self.hooks[hook_name] = []
    
    def discover_plugins(self) -> List[str]:
        """
        Scan plugin directory and discover all available plugins
        Returns list of plugin names found
        """
        discovered = []
        
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {self.plugin_dir}")
            return discovered
        
        # Scan for plugin directories
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                manifest_file = item / 'plugin.json'
                
                if manifest_file.exists():
                    try:
                        manifest = self._load_plugin_manifest(manifest_file)
                        if manifest:
                            self.manifests[manifest.name] = manifest
                            discovered.append(manifest.name)
                            logger.debug(f"Discovered plugin: {manifest.name}")
                    except Exception as e:
                        logger.error(f"Error loading plugin manifest {manifest_file}: {e}")
                else:
                    logger.warning(f"Plugin directory missing manifest: {item}")
        
        logger.info(f"Discovered {len(discovered)} plugins: {discovered}")
        return discovered
    
    def _load_plugin_manifest(self, manifest_file: Path) -> Optional[PluginManifest]:
        """Load and validate a plugin manifest"""
        try:
            with open(manifest_file, 'r') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ['name', 'version', 'author', 'description', 'entry_point']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create manifest object
            manifest = PluginManifest(
                name=data['name'],
                display_name=data.get('display_name', data['name']),
                version=data['version'],
                author=data['author'],
                description=data['description'],
                digestr_version=data.get('digestr_version', '>=2.1.0'),
                entry_point=data['entry_point'],
                hooks=data.get('hooks', []),
                commands=data.get('commands', []),
                config_schema=data.get('config_schema', {}),
                dependencies=data.get('dependencies', []),
                tags=data.get('tags', []),
                plugin_dir=manifest_file.parent
            )
            
            # Validate the manifest
            if self._validate_plugin_manifest(manifest):
                return manifest
            else:
                logger.error(f"Plugin manifest validation failed: {manifest.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing plugin manifest {manifest_file}: {e}")
            return None
    
    def _validate_plugin_manifest(self, manifest: PluginManifest) -> bool:
        """Validate plugin manifest for correctness"""
        try:
            # Check entry point file exists
            entry_file = manifest.plugin_dir / manifest.entry_point
            if not entry_file.exists():
                logger.error(f"Plugin entry point not found: {entry_file}")
                return False
            
            # Validate hooks are known
            unknown_hooks = [hook for hook in manifest.hooks if hook not in self.hooks]
            if unknown_hooks:
                logger.warning(f"Plugin {manifest.name} uses unknown hooks: {unknown_hooks}")
            
            # Validate version format (basic check)
            if not manifest.version.replace('.', '').replace('-', '').replace('_', '').isalnum():
                logger.error(f"Invalid version format: {manifest.version}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating plugin manifest: {e}")
            return False
    
    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load and instantiate a specific plugin
        Returns True if successful, False otherwise
        """
        try:
            # Check if plugin is already loaded
            if plugin_name in self.plugins:
                logger.warning(f"Plugin {plugin_name} is already loaded")
                return True
            
            # Get plugin manifest
            if plugin_name not in self.manifests:
                logger.error(f"Plugin manifest not found: {plugin_name}")
                return False
            
            manifest = self.manifests[plugin_name]
            
            # Load plugin configuration
            plugin_config = self._load_plugin_config(manifest)
            
            # Dynamically import the plugin module
            plugin_instance = self._import_and_instantiate_plugin(manifest, plugin_config)
            
            if plugin_instance:
                self.plugins[plugin_name] = plugin_instance
                logger.info(f"Successfully loaded plugin: {plugin_name}")
                return True
            else:
                logger.error(f"Failed to instantiate plugin: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
    
    def _load_plugin_config(self, manifest: PluginManifest) -> Dict[str, Any]:
        """Load plugin-specific configuration"""
        config_file = manifest.plugin_dir / 'config.yaml'
        
        # Start with default values from schema
        config = {}
        for key, schema in manifest.config_schema.items():
            config[key] = schema.get('default')
        
        # Override with user configuration if it exists
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                config.update(user_config)
            except Exception as e:
                logger.error(f"Error loading plugin config {config_file}: {e}")
        
        return config
    
    def _import_and_instantiate_plugin(self, manifest: PluginManifest, config: Dict[str, Any]) -> Optional[DigestrPlugin]:
        """Dynamically import and instantiate a plugin"""
        try:
            # Construct module path
            entry_file = manifest.plugin_dir / manifest.entry_point
            module_name = f"digestr_plugin_{manifest.name.replace('-', '_')}"
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, entry_file)
            if not spec or not spec.loader:
                logger.error(f"Could not load module spec for {entry_file}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get the plugin factory function
            if hasattr(module, 'create_plugin'):
                plugin_instance = module.create_plugin(self, config)
                
                if isinstance(plugin_instance, DigestrPlugin):
                    return plugin_instance
                else:
                    logger.error(f"Plugin factory returned invalid type: {type(plugin_instance)}")
                    return None
            else:
                logger.error(f"Plugin {manifest.name} missing create_plugin function")
                return None
                
        except Exception as e:
            logger.error(f"Error importing plugin {manifest.name}: {e}")
            return None
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin and clean up its resources"""
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} is not loaded")
                return True
            
            plugin = self.plugins[plugin_name]
            
            # Clean up hooks registered by this plugin
            self._cleanup_plugin_hooks(plugin_name)
            
            # Clean up commands registered by this plugin
            self._cleanup_plugin_commands(plugin_name)
            
            # Remove from loaded plugins
            del self.plugins[plugin_name]
            
            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def _cleanup_plugin_hooks(self, plugin_name: str):
        """Remove all hooks registered by a specific plugin"""
        # This is a simplified cleanup - in a full implementation,
        # we'd track which plugin registered which callback
        pass
    
    def _cleanup_plugin_commands(self, plugin_name: str):
        """Remove all commands registered by a specific plugin"""
        # This is a simplified cleanup - in a full implementation,
        # we'd track which plugin registered which command
        pass
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin (add to enabled list and load it)"""
        try:
            # Update enabled plugins config
            self.enabled_plugins['plugins'][plugin_name] = {
                'enabled': True,
                'auto_update': True
            }
            
            # Save the configuration
            self._save_enabled_plugins()
            
            # Load the plugin
            return self.load_plugin(plugin_name)
            
        except Exception as e:
            logger.error(f"Error enabling plugin {plugin_name}: {e}")
            return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin (remove from enabled list and unload it)"""
        try:
            # Update enabled plugins config
            if plugin_name in self.enabled_plugins['plugins']:
                self.enabled_plugins['plugins'][plugin_name]['enabled'] = False
            
            # Save the configuration
            self._save_enabled_plugins()
            
            # Unload the plugin
            return self.unload_plugin(plugin_name)
            
        except Exception as e:
            logger.error(f"Error disabling plugin {plugin_name}: {e}")
            return False
    
    def _save_enabled_plugins(self):
        """Save the enabled plugins configuration"""
        enabled_file = self.plugin_dir.parent / 'plugins' / 'enabled.yaml'
        try:
            with open(enabled_file, 'w') as f:
                yaml.dump(self.enabled_plugins, f, default_flow_style=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving enabled plugins config: {e}")
    
    def load_enabled_plugins(self):
        """Load all enabled plugins on startup"""
        for plugin_name, plugin_config in self.enabled_plugins.get('plugins', {}).items():
            if plugin_config.get('enabled', False):
                logger.info(f"Auto-loading enabled plugin: {plugin_name}")
                self.load_plugin(plugin_name)
    
    def register_hook(self, hook_name: str, callback: callable, plugin_name: str = None):
        """Register a callback for a specific hook"""
        if hook_name not in self.hooks:
            logger.warning(f"Unknown hook: {hook_name}")
            self.hooks[hook_name] = []
        
        self.hooks[hook_name].append(callback)
        logger.debug(f"Registered hook {hook_name} for plugin {plugin_name}")
    
    def register_command(self, command_name: str, callback: callable, description: str = "", plugin_name: str = None):
        """Register a new interactive command"""
        if command_name in self.commands:
            logger.warning(f"Command {command_name} already registered, overriding")
        
        self.commands[command_name] = {
            'callback': callback,
            'description': description,
            'plugin': plugin_name
        }
        logger.debug(f"Registered command /{command_name} for plugin {plugin_name}")
    
    async def execute_hook(self, hook_name: str, *args, **kwargs):
        """Execute all callbacks registered for a hook"""
        if hook_name not in self.hooks:
            logger.debug(f"No callbacks registered for hook: {hook_name}")
            return
        
        callbacks = self.hooks[hook_name]
        logger.debug(f"Executing {len(callbacks)} callbacks for hook: {hook_name}")
        
        for callback in callbacks:
            try:
                # Handle both sync and async callbacks
                if hasattr(callback, '__await__'):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing hook callback {callback}: {e}")
    
    async def handle_command(self, command: str, args: List[str] = None, session_context=None):
        """Route plugin commands to appropriate handlers"""
        if not command.startswith('/'):
            return False
        
        command_name = command[1:]  # Remove the '/' prefix
        
        if command_name not in self.commands:
            return False
        
        command_info = self.commands[command_name]
        callback = command_info['callback']
        
        try:
            # Handle both sync and async command callbacks
            if hasattr(callback, '__await__'):
                result = await callback(args or [], session_context)
            else:
                result = callback(args or [], session_context)
            
            # Print the result if it's a string
            if isinstance(result, str):
                print(result)
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            print(f"❌ Error executing command: {e}")
            return True  # We handled it, even if it failed
    
    def get_available_plugins(self) -> List[Dict[str, Any]]:
        """Get list of all available plugins with their status"""
        plugins = []
        
        for name, manifest in self.manifests.items():
            is_enabled = self.enabled_plugins.get('plugins', {}).get(name, {}).get('enabled', False)
            is_loaded = name in self.plugins
            
            plugins.append({
                'name': name,
                'display_name': manifest.display_name,
                'version': manifest.version,
                'author': manifest.author,
                'description': manifest.description,
                'enabled': is_enabled,
                'loaded': is_loaded,
                'hooks': manifest.hooks,
                'commands': [cmd.get('name') for cmd in manifest.commands],
                'tags': manifest.tags
            })
        
        return plugins
    
    def get_plugin_status(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a specific plugin"""
        if plugin_name not in self.manifests:
            return None
        
        manifest = self.manifests[plugin_name]
        is_enabled = self.enabled_plugins.get('plugins', {}).get(plugin_name, {}).get('enabled', False)
        is_loaded = plugin_name in self.plugins
        
        status = {
            'name': plugin_name,
            'display_name': manifest.display_name,
            'version': manifest.version,
            'author': manifest.author,
            'description': manifest.description,
            'enabled': is_enabled,
            'loaded': is_loaded,
            'plugin_dir': str(manifest.plugin_dir),
            'entry_point': manifest.entry_point,
            'hooks': manifest.hooks,
            'commands': manifest.commands,
            'config_schema': manifest.config_schema,
            'dependencies': manifest.dependencies,
            'tags': manifest.tags
        }
        
        if is_loaded:
            plugin_instance = self.plugins[plugin_name]
            status['instance'] = str(type(plugin_instance))
        
        return status
    
    def initialize(self):
        """Initialize the plugin manager - discover and load enabled plugins"""
        logger.info("Initializing plugin manager...")
        
        # Discover all available plugins
        discovered = self.discover_plugins()
        logger.info(f"Discovered {len(discovered)} plugins")
        
        # Load enabled plugins
        self.load_enabled_plugins()
        
        logger.info(f"Plugin manager initialized with {len(self.plugins)} active plugins")