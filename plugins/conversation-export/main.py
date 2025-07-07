"""
Conversation Export Plugin for Digestr.ai
Email Scheduler & Export functionality for news briefings
"""

import sys
import os
import asyncio
from datetime import datetime
from pathlib import Path

# Add the src directory to the path
src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'news-summarizer', 'src')
if os.path.exists(src_path):
    sys.path.insert(0, src_path)

try:
    from digestr.core.plugin_base import DigestrPlugin
    from digestr.core.plugin_system import PluginHooks
    from digestr.core.database import DatabaseManager
    from digestr.llm_providers.ollama import OllamaProvider
except ImportError as e:
    print(f"Warning: Could not import Digestr modules: {e}")
    # Fallback classes for testing
    class DigestrPlugin:
        def __init__(self, plugin_manager, config):
            self.plugin_manager = plugin_manager
            self.config = config
        def register_hook(self, hook_name, callback):
            pass
        def register_command(self, command_name, callback, description=""):
            pass
        def get_config(self, key, default=None):
            return self.config.get(key, default)
    
    class PluginHooks:
        BRIEFING_GENERATED = "core.briefing_generated"
        INTERACTIVE_SESSION_END = "interactive.session_end"

# Import plugin modules with absolute imports
import os
import importlib.util

def import_module_from_path(module_name, file_path):
    """Import a module from a specific file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Get the plugin directory
plugin_dir = Path(__file__).parent

# Import modules dynamically
markdown_module = import_module_from_path("markdown_exporter", plugin_dir / "exporters" / "markdown.py")
html_module = import_module_from_path("html_exporter", plugin_dir / "exporters" / "html.py") 
email_module = import_module_from_path("email_sender", plugin_dir / "email" / "sender.py")
scheduler_module = import_module_from_path("scheduler", plugin_dir / "schedulers" / "scheduler.py")

MarkdownExporter = markdown_module.MarkdownExporter
HtmlExporter = html_module.HtmlExporter
EmailSender = email_module.EmailSender
BriefingScheduler = scheduler_module.BriefingScheduler


class ConversationExportPlugin(DigestrPlugin):
    """
    Main plugin class for email scheduling and export functionality
    """
    
    def __init__(self, plugin_manager, config):
        super().__init__(plugin_manager, config)
        print(f"ConversationExportPlugin initializing...")
        
        # Initialize components
        self.markdown_exporter = MarkdownExporter(config)
        self.html_exporter = HtmlExporter(config)
        self.email_sender = EmailSender(config)
        self.scheduler = BriefingScheduler(config, self.email_sender)
        
        # Setup hooks and commands
        self.setup_hooks()
        self.setup_commands()
        
        # Initialize scheduler if enabled
        if self.get_config("scheduling", {}).get("enabled", False):
            self.scheduler.initialize()
        
        print(f"ConversationExportPlugin initialized successfully")
    
    def setup_hooks(self):
        """Register for relevant hooks"""
        self.register_hook(PluginHooks.BRIEFING_GENERATED, self.on_briefing_generated)
        self.register_hook(PluginHooks.INTERACTIVE_SESSION_END, self.on_session_end)
    
    def setup_commands(self):
        """Register interactive commands"""
        self.register_command("export", self.export_command, 
                            "Export current session or briefing")
        self.register_command("email", self.email_command,
                            "Email briefing to recipients")
        self.register_command("schedule", self.schedule_command,
                            "Manage email schedules")
    
    async def export_command(self, args, session):
        """Handle /export command"""
        try:
            # Parse arguments
            export_format = args[0] if args else "markdown"
            filename = args[1] if len(args) > 1 else None
            
            if export_format not in ["markdown", "html"]:
                return "❌ Supported formats: markdown, html"
            
            # Get current session content
            if hasattr(session, 'conversation_history') and session.conversation_history:
                # Export conversation
                content = self._format_conversation_for_export(session)
                title = "Interactive Session"
            else:
                # Export recent briefing
                content = await self._get_recent_briefing()
                title = "Recent Briefing"
                
                if not content:
                    return "❌ No briefing content found to export"
            
            # Export using appropriate exporter
            if export_format == "markdown":
                file_path = self.markdown_exporter.export(content, title, filename)
            else:
                file_path = self.html_exporter.export(content, title, filename)
            
            return f"✅ Exported to: {file_path}"
            
        except Exception as e:
            return f"❌ Export failed: {str(e)}"
    
    async def email_command(self, args, session):
        """Handle /email command"""
        try:
            # Check if email is configured
            email_config = self.get_config("email", {})
            if not email_config.get("enabled", False):
                return "❌ Email not configured. Please setup email in plugin config."
            
            # Parse recipient
            recipient = args[0] if args else email_config.get("sender_email")
            if not recipient:
                return "❌ No recipient specified and no default configured"
            
            # Get content to email
            if hasattr(session, 'conversation_history') and session.conversation_history:
                content = self._format_conversation_for_export(session)
                subject = f"Digestr Interactive Session - {datetime.now().strftime('%Y-%m-%d')}"
            else:
                content = await self._get_recent_briefing()
                subject = f"Digestr Briefing - {datetime.now().strftime('%Y-%m-%d')}"
                
                if not content:
                    return "❌ No content found to email"
            
            # Send email
            success = await self.email_sender.send_briefing(
                recipients=[recipient],
                subject=subject,
                content=content
            )
            
            if success:
                return f"✅ Email sent to {recipient}"
            else:
                return f"❌ Failed to send email to {recipient}"
                
        except Exception as e:
            return f"❌ Email failed: {str(e)}"
    
    async def schedule_command(self, args, session):
        """Handle /schedule command"""
        try:
            if not args:
                return self._show_schedule_status()
            
            action = args[0].lower()
            
            if action == "list":
                return self._list_schedules()
            elif action == "test":
                schedule_name = args[1] if len(args) > 1 else "morning"
                return await self._test_schedule(schedule_name)
            elif action == "enable":
                schedule_name = args[1] if len(args) > 1 else None
                if not schedule_name:
                    return "❌ Please specify schedule name: morning, midday, evening"
                return self._enable_schedule(schedule_name)
            elif action == "disable":
                schedule_name = args[1] if len(args) > 1 else None
                if not schedule_name:
                    return "❌ Please specify schedule name: morning, midday, evening"
                return self._disable_schedule(schedule_name)
            else:
                return "❌ Available actions: list, test, enable, disable"
                
        except Exception as e:
            return f"❌ Schedule command failed: {str(e)}"
    
    def on_briefing_generated(self, briefing_content, articles, style="comprehensive"):
        """Called when a briefing is generated"""
        if self.get_config("export", {}).get("auto_export", False):
            try:
                # Auto-export briefing
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"auto_briefing_{style}_{timestamp}"
                self.markdown_exporter.export(briefing_content, f"{style.title()} Briefing", filename)
                print(f"📄 Auto-exported briefing: {filename}")
            except Exception as e:
                print(f"❌ Auto-export failed: {e}")
    
    def on_session_end(self, session):
        """Called when interactive session ends"""
        print("📋 Conversation export plugin: Session ended")
    
    def _format_conversation_for_export(self, session):
        """Format conversation history for export"""
        if not hasattr(session, 'conversation_history') or not session.conversation_history:
            return "No conversation history available."
        
        content = f"# Interactive Session - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for i, exchange in enumerate(session.conversation_history, 1):
            content += f"## Question {i}\n"
            content += f"**User:** {exchange['question']}\n\n"
            content += f"**Assistant:** {exchange['response']}\n\n"
            content += "---\n\n"
        
        return content
    
    async def _get_recent_briefing(self):
        """Get the most recent briefing content"""
        try:
            # Get recent articles and generate a briefing
            db = DatabaseManager()
            articles = db.get_recent_articles(hours=24, limit=15, unprocessed_only=False)
            
            if not articles:
                return None
            
            # Convert to dict format for LLM
            article_dicts = []
            for article in articles:
                article_dicts.append({
                    'title': article.title,
                    'summary': article.summary,
                    'content': article.content,
                    'url': article.url,
                    'category': article.category,
                    'source': article.source,
                    'published_date': article.published_date,
                    'importance_score': article.importance_score
                })
            
            # Generate briefing
            llm = OllamaProvider()
            briefing = await llm.generate_briefing(article_dicts, briefing_type="comprehensive")
            return briefing
            
        except Exception as e:
            print(f"Error getting recent briefing: {e}")
            return None
    
    def _show_schedule_status(self):
        """Show current schedule configuration"""
        scheduling_config = self.get_config("scheduling", {})
        if not scheduling_config.get("enabled", False):
            return "📅 Scheduling is disabled"
        
        briefings = scheduling_config.get("briefings", {})
        status = "📅 **Current Schedules:**\n\n"
        
        for name, config in briefings.items():
            enabled = "✅" if config.get("enabled", False) else "⚪"
            recipients = ", ".join(config.get("recipients", []))
            status += f"{enabled} **{name.title()}**: {config.get('time')} ({config.get('style')}) → {recipients}\n"
        
        return status
    
    def _list_schedules(self):
        """List all configured schedules"""
        return self._show_schedule_status()
    
    async def _test_schedule(self, schedule_name):
        """Test a specific schedule"""
        scheduling_config = self.get_config("scheduling", {})
        briefings = scheduling_config.get("briefings", {})
        
        if schedule_name not in briefings:
            return f"❌ Schedule '{schedule_name}' not found"
        
        schedule_config = briefings[schedule_name]
        recipients = schedule_config.get("recipients", [])
        
        if not recipients:
            return f"❌ No recipients configured for {schedule_name}"
        
        try:
            # Generate test briefing
            content = await self._get_recent_briefing()
            if not content:
                content = f"Test briefing for {schedule_name} schedule - {datetime.now()}"
            
            # Send test email
            success = await self.email_sender.send_briefing(
                recipients=recipients,
                subject=f"TEST: {schedule_name.title()} Briefing",
                content=content
            )
            
            if success:
                return f"✅ Test email sent to {', '.join(recipients)}"
            else:
                return f"❌ Failed to send test email"
                
        except Exception as e:
            return f"❌ Test failed: {str(e)}"
    
    def _enable_schedule(self, schedule_name):
        """Enable a specific schedule"""
        # This would update the config file
        return f"✅ Schedule '{schedule_name}' enabled (config update needed)"
    
    def _disable_schedule(self, schedule_name):
        """Disable a specific schedule"""
        # This would update the config file
        return f"⚪ Schedule '{schedule_name}' disabled (config update needed)"


def create_plugin(plugin_manager, config):
    """Plugin factory function (required)"""
    return ConversationExportPlugin(plugin_manager, config)