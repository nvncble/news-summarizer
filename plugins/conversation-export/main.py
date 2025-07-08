#!/usr/bin/env python3
"""
Production Email Briefing Plugin for Digestr.ai
Simplified and optimized for reliable email delivery
"""

import os
import yaml
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Import Digestr core modules for efficient integration
try:
    from digestr.core.plugin_base import DigestrPlugin
    from digestr.core.plugin_system import PluginHooks
    from digestr.core.database import DatabaseManager
    from digestr.llm_providers.ollama import OllamaProvider
    from digestr.sources.source_manager import SourceManager
except ImportError as e:
    print(f"Warning: Could not import Digestr modules: {e}")
    # Fallback classes for testing
    class DigestrPlugin:
        def __init__(self, plugin_manager, config):
            self.plugin_manager = plugin_manager
            self.config = config
        def register_hook(self, hook_name, callback): pass
        def register_command(self, command_name, callback, description=""): pass
        def get_config(self, key, default=None): return self.config.get(key, default)
    
    class PluginHooks:
        BRIEFING_GENERATED = "core.briefing_generated"
        INTERACTIVE_SESSION_END = "interactive.session_end"

# Import plugin modules (simplified imports)
from .sender import EmailSender
from .exporters import MarkdownExporter, HtmlExporter

logger = logging.getLogger(__name__)


class EmailBriefingPlugin(DigestrPlugin):
    """Production email briefing plugin with simplified commands"""
    
    def __init__(self, plugin_manager, config):
        super().__init__(plugin_manager, config)
        
        # Load environment variables for email config
        self.email_config = self._load_email_config()
        
        # Initialize components
        self.email_sender = EmailSender(self.email_config)
        self.markdown_exporter = MarkdownExporter(config)
        self.html_exporter = HtmlExporter(config)
        
        # Setup hooks and commands
        self.setup_hooks()
        self.setup_commands()
        
        logger.info("Email briefing plugin initialized")
    
    def _load_email_config(self) -> Dict[str, Any]:
        """Load email configuration from environment variables"""
        return {
            'enabled': self.get_config('email', {}).get('enabled', False),
            'smtp_server': os.getenv('DIGESTR_SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('DIGESTR_SMTP_PORT', '587')),
            'sender_email': os.getenv('DIGESTR_SENDER_EMAIL', ''),
            'sender_password': os.getenv('DIGESTR_SENDER_PASSWORD', ''),
            'use_tls': os.getenv('DIGESTR_SMTP_TLS', 'true').lower() == 'true',
            'subject_template': '📰 {style} Briefing - {date}'
        }
    
    def setup_hooks(self):
        """Register plugin hooks"""
        self.register_hook(PluginHooks.BRIEFING_GENERATED, self.on_briefing_generated)
        self.register_hook(PluginHooks.INTERACTIVE_SESSION_END, self.on_session_end)
    
    def setup_commands(self):
        """Register plugin commands"""
        self.register_command("email-brief", self.email_brief_command,
                            "Send briefing via email: /email-brief [style] [sources] [recipient]")
        self.register_command("schedule", self.schedule_command,
                            "Manage email schedules: /schedule [list|test|status]")
        self.register_command("status", self.status_command,
                            "Show plugin status")
        self.register_command("save", self.save_command,
                            "Save briefing to file: /save [markdown|html]")
    
    async def email_brief_command(self, args: List[str], session=None) -> str:
        """Send a briefing via email on demand"""
        try:
            # Parse arguments
            style = args[0] if len(args) > 0 else "comprehensive"
            sources = args[1].split(',') if len(args) > 1 else ["professional"] 
            recipient = args[2] if len(args) > 2 else self.email_config.get('sender_email')
            
            if not recipient:
                return "❌ No recipient specified. Usage: /email-brief [style] [sources] [recipient]"
            
            # Validate style
            valid_styles = ["comprehensive", "quick", "analytical"]
            if style not in valid_styles:
                return f"❌ Invalid style. Choose from: {', '.join(valid_styles)}"
            
            # Generate briefing
            print(f"📧 Generating {style} briefing...")
            briefing_content = await self._generate_briefing(style, sources)
            
            if not briefing_content or briefing_content.startswith("Error"):
                return f"❌ Failed to generate briefing: {briefing_content}"
            
            # Send email
            success = self.email_sender.send_briefing(
                recipients=[recipient],
                briefing_content=briefing_content,
                briefing_style=style
            )
            
            if success:
                return f"✅ {style.title()} briefing sent to {recipient}"
            else:
                return f"❌ Failed to send email to {recipient}"
                
        except Exception as e:
            logger.error(f"Error in email-brief command: {e}")
            return f"❌ Error: {str(e)}"
    
    async def schedule_command(self, args: List[str], session=None) -> str:
        """Manage email schedules"""
        try:
            action = args[0] if args else "list"
            
            if action == "list":
                return self._show_schedule_config()
            elif action == "test":
                return await self._test_email_sending()
            elif action == "status":
                return self._show_email_status()
            else:
                return "❌ Available actions: list, test, status"
                
        except Exception as e:
            return f"❌ Schedule command error: {str(e)}"
    
    async def status_command(self, args: List[str], session=None) -> str:
        """Show overall plugin status"""
        status_parts = []
        
        # Email configuration status
        email_status = self.email_sender.get_status()
        status_parts.append("📧 **Email Configuration:**")
        status_parts.append(f"  • Enabled: {'✅' if email_status['enabled'] else '❌'}")
        status_parts.append(f"  • SMTP Server: {email_status.get('smtp_server', 'Not set')}")
        status_parts.append(f"  • Sender Email: {email_status.get('sender_email', 'Not set')}")
        status_parts.append(f"  • Configuration Valid: {'✅' if email_status['config_valid'] else '❌'}")
        
        # Scheduling configuration
        scheduling_config = self.get_config('scheduling', {}).get('briefings', {})
        status_parts.append("\n📅 **Scheduled Briefings:**")
        
        if not scheduling_config:
            status_parts.append("  • No briefings configured")
        else:
            for name, config in scheduling_config.items():
                enabled = "✅" if config.get('enabled', False) else "⚪"
                recipients = len(config.get('recipients', []))
                status_parts.append(f"  • {enabled} {name}: {config.get('time')} ({config.get('style')}) → {recipients} recipients")
        
        return "\n".join(status_parts)
    
    async def save_command(self, args: List[str], session=None) -> str:
        """Save current briefing to file"""
        try:
            file_format = args[0] if args else "markdown"
            
            if file_format not in ["markdown", "html"]:
                return "❌ Supported formats: markdown, html"
            
            # Generate current briefing
            briefing_content = await self._generate_briefing("comprehensive", ["professional"])
            
            if not briefing_content:
                return "❌ No briefing content to save"
            
            # Save using appropriate exporter
            if file_format == "markdown":
                file_path = self.markdown_exporter.export(briefing_content, "Current Briefing")
            else:
                file_path = self.html_exporter.export(briefing_content, "Current Briefing")
            
            return f"✅ Briefing saved to: {file_path}"
            
        except Exception as e:
            return f"❌ Save failed: {str(e)}"
    
    async def _generate_briefing(self, style: str, sources: List[str]) -> str:
        """Generate briefing using Digestr core functionality"""
        try:
            # Import config manager here to avoid circular imports
            from digestr.config.manager import get_enhanced_config_manager
            
            # Initialize components
            config_manager = get_enhanced_config_manager()
            db_manager = DatabaseManager()
            source_manager = SourceManager(config_manager, db_manager)
            
            # Determine source types
            if "professional" in sources:
                fetch_sources = ["rss"]
                if "reddit" in source_manager.get_available_sources():
                    fetch_sources.append("reddit")
            elif "social" in sources:
                fetch_sources = ["reddit_personal"] if "reddit_personal" in source_manager.get_available_sources() else []
            else:
                # Use specific sources
                fetch_sources = [s for s in sources if s in source_manager.get_available_sources()]
            
            if not fetch_sources:
                return "Error: No valid sources available"
            
            # Get recent articles from database (don't re-fetch)
            articles = db_manager.get_recent_articles(hours=24, limit=20, unprocessed_only=False)
            
            if not articles:
                return "No recent articles found for briefing"
            
            # Convert articles to dict format for LLM
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
            
            # Generate briefing using Ollama provider
            config = config_manager.get_config()
            llm_provider = OllamaProvider(config.llm.ollama_url, config.llm.models)
            
            briefing = await llm_provider.generate_briefing(
                article_dicts,
                briefing_type=style
            )
            
            return briefing
            
        except Exception as e:
            logger.error(f"Error generating briefing: {e}")
            return f"Error generating briefing: {str(e)}"
    
    def _show_schedule_config(self) -> str:
        """Show current schedule configuration"""
        scheduling_config = self.get_config('scheduling', {})
        
        if not scheduling_config.get('enabled', False):
            return "📅 Scheduling is disabled"
        
        briefings = scheduling_config.get('briefings', {})
        if not briefings:
            return "📅 No briefings configured"
        
        result = ["📅 **Configured Briefings:**"]
        
        for name, config in briefings.items():
            enabled = "✅" if config.get('enabled', False) else "⚪"
            recipients = config.get('recipients', [])
            
            # Load actual recipient emails from environment
            actual_recipients = []
            for recipient in recipients:
                if recipient.startswith('${') and recipient.endswith('}'):
                    env_var = recipient[2:-1]  # Remove ${ and }
                    actual_email = os.getenv(env_var, recipient)
                    actual_recipients.append(actual_email)
                else:
                    actual_recipients.append(recipient)
            
            result.append(f"  {enabled} **{name.title()}**: {config.get('time')} ({config.get('style')})")
            result.append(f"      Sources: {', '.join(config.get('sources', []))}")
            result.append(f"      Recipients: {', '.join(actual_recipients)}")
        
        return "\n".join(result)
    
    async def _test_email_sending(self) -> str:
        """Test email sending functionality"""
        if not self.email_config.get('enabled'):
            return "❌ Email is disabled in configuration"
        
        # Test SMTP connection
        if not self.email_sender.test_connection():
            return "❌ SMTP connection failed. Check your email configuration."
        
        # Try to send a test email
        test_recipient = self.email_config.get('sender_email')
        if not test_recipient:
            return "❌ No test recipient available"
        
        test_content = f"Test email from Digestr.ai plugin\nSent at: {datetime.now()}"
        
        success = self.email_sender.send_email(
            recipients=[test_recipient],
            subject="Digestr.ai Test Email",
            body=test_content
        )
        
        if success:
            return f"✅ Test email sent successfully to {test_recipient}"
        else:
            return f"❌ Failed to send test email to {test_recipient}"
    
    def _show_email_status(self) -> str:
        """Show email configuration status"""
        status = self.email_sender.get_status()
        
        result = ["📧 **Email Status:**"]
        result.append(f"  • Enabled: {'✅' if status['enabled'] else '❌'}")
        result.append(f"  • SMTP Server: {status.get('smtp_server', 'Not configured')}")
        result.append(f"  • SMTP Port: {status.get('smtp_port', 'Not configured')}")
        result.append(f"  • Sender Email: {status.get('sender_email', 'Not configured')}")
        result.append(f"  • Configuration Valid: {'✅' if status['config_valid'] else '❌'}")
        
        # Environment variable status
        result.append("\n🔐 **Environment Variables:**")
        required_vars = ['DIGESTR_SMTP_SERVER', 'DIGESTR_SENDER_EMAIL', 'DIGESTR_SENDER_PASSWORD']
        
        for var in required_vars:
            value = os.getenv(var)
            status_icon = "✅" if value else "❌"
            display_value = "***" if value and 'password' in var.lower() else (value or "Not set")
            result.append(f"  • {var}: {status_icon} {display_value}")
        
        return "\n".join(result)
    
    # Hook handlers
    def on_briefing_generated(self, briefing_content, articles, style="comprehensive"):
        """Called when a briefing is generated"""
        # Could implement auto-emailing here if desired
        pass
    
    def on_session_end(self, session):
        """Called when interactive session ends"""
        logger.debug("Email briefing plugin: Session ended")


def create_plugin(plugin_manager, config):
    """Plugin factory function (required)"""
    return EmailBriefingPlugin(plugin_manager, config)