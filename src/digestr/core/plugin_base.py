class DigestrPlugin:
    """Base class for all Digestr plugins"""
    
    def __init__(self, plugin_manager, config):
        self.plugin_manager = plugin_manager
        self.config = config
        self.hooks = {}
    
    def register_hook(self, hook_name, callback):
        """Register a callback for a specific hook"""
        if self.plugin_manager:
            self.plugin_manager.register_hook(hook_name, callback, "plugin")

        
    def register_command(self, command_name, callback, description=""):
        """Register a new interactive command"""
        if self.plugin_manager:
            self.plugin_manager.register_command(command_name, callback, description, "plugin")
    
    def get_config(self, key, default=None):
        """Get plugin-specific configuration"""
        pass
    
    def log(self, message, level="info"):
        """Plugin logging"""
        pass