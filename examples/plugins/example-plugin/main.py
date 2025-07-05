"""
Example Digestr.ai Plugin - Fixed Version
This demonstrates the basic plugin structure and capabilities
"""

import sys
import os

# Add the src directory to the path so we can import digestr modules
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'news-summarizer', 'src')
if os.path.exists(src_path):
    sys.path.insert(0, src_path)

try:
    from digestr.core.plugin_base import DigestrPlugin
    from digestr.core.plugin_system import PluginHooks
except ImportError as e:
    print(f"Warning: Could not import Digestr modules: {e}")
    # Define minimal fallback classes for testing
    class DigestrPlugin:
        def __init__(self, plugin_manager, config):
            self.plugin_manager = plugin_manager
            self.config = config
        
        def register_hook(self, hook_name, callback):
            if self.plugin_manager:
                self.plugin_manager.register_hook(hook_name, callback, "example-plugin")
        
        def register_command(self, command_name, callback, description=""):
            if self.plugin_manager:
                self.plugin_manager.register_command(command_name, callback, description, "example-plugin")
        
        def get_config(self, key, default=None):
            return self.config.get(key, default)
    
    class PluginHooks:
        INTERACTIVE_SESSION_END = "interactive.session_end"


class ExamplePlugin(DigestrPlugin):
    def __init__(self, plugin_manager, config):
        super().__init__(plugin_manager, config)
        print(f"ExamplePlugin initializing with plugin_manager: {plugin_manager}")
        print(f"ExamplePlugin config: {config}")
        self.setup_hooks()
        self.setup_commands()
    
    def setup_hooks(self):
        """Register for relevant hooks"""
        print("ExamplePlugin: Registering hooks...")
        self.register_hook(PluginHooks.INTERACTIVE_SESSION_END, self.on_session_end)
    
    def setup_commands(self):
        """Register interactive commands"""
        print("ExamplePlugin: Registering commands...")
        self.register_command("example", self.example_command, 
                            "Example command that shows plugin capabilities")
        print("ExamplePlugin: Command registration complete")
    
    async def example_command(self, args, session):
        """Handle /example command"""
        print(f"ExamplePlugin: example_command called with args: {args}")
        message = self.get_config("message", "Hello from plugin!")
        arg_text = " ".join(args) if args else "no arguments"
        return f"🔌 {message} (You said: {arg_text})"
    
    def on_session_end(self, session):
        """Called when interactive session ends"""
        if self.get_config("enabled", True):
            print("👋 Example plugin says goodbye!")


# Plugin factory function (required)
def create_plugin(plugin_manager, config):
    print(f"create_plugin called with plugin_manager: {plugin_manager}, config: {config}")
    plugin = ExamplePlugin(plugin_manager, config)
    print(f"Created plugin instance: {plugin}")
    return plugin