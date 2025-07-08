#!/usr/bin/env python3
"""
Email Sender for Digestr.ai Conversation Export Plugin
Simplified and reliable email delivery
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    """Email sender with SSL/TLS support for conversation export plugin"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('enabled', False)
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.sender_email = config.get('sender_email', '')
        self.sender_password = config.get('sender_password', '')
        self.use_tls = config.get('use_tls', True)
        self.subject_template = config.get('subject_template', '📰 {style} Briefing - {date}')
        
        if not self.enabled:
            logger.info("EmailSender initialized in disabled mode")
    
    def validate_config(self) -> bool:
        """Validate email configuration"""
        if not self.enabled:
            return False
            
        required_fields = ['smtp_server', 'sender_email', 'sender_password']
        missing = [field for field in required_fields if not getattr(self, field)]
        
        if missing:
            logger.warning(f"Missing email config fields: {missing}")
            return False
        
        return True
    
    def send_email(self, recipients: List[str], subject: str, body: str, 
                   html_body: Optional[str] = None) -> bool:
        """Send basic email to recipients"""
        
        if not self.enabled:
            print(f"[EMAIL DISABLED] Would send to {recipients}: {subject}")
            return True
        
        if not self.validate_config():
            logger.error("Email configuration invalid - cannot send email")
            return False
        
        try:
            # Create message
            if html_body:
                message = MIMEMultipart("alternative")
                text_part = MIMEText(body, "plain", "utf-8")
                html_part = MIMEText(html_body, "html", "utf-8")
                message.attach(text_part)
                message.attach(html_part)
            else:
                message = MIMEText(body, "plain", "utf-8")
            
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            
            # Connect and send
            if self.smtp_port == 465:  # SSL
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
            else:  # TLS (port 587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
            
            logger.info(f"Email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_briefing(self, recipients: List[str], briefing_content: str, 
                     briefing_style: str = "comprehensive") -> bool:
        """Send a news briefing via email with enhanced formatting"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Format subject using template
        subject = self.subject_template.format(
            style=briefing_style.title(),
            date=current_date
        )
        
        # Create enhanced HTML version
        html_body = self._create_html_briefing(briefing_content, briefing_style)
        
        return self.send_email(recipients, subject, briefing_content, html_body)
    
    def _create_html_briefing(self, content: str, style: str) -> str:
        """Create HTML version of briefing email"""
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Convert markdown-style formatting to HTML
        html_content = content
        
        # Basic markdown conversions
        import re
        
        # Headers
        html_content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
        
        # Bold and italic
        html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
        html_content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html_content)
        
        # Line breaks
        html_content = html_content.replace('\n\n', '</p><p>')
        html_content = html_content.replace('\n', '<br>')
        
        # Wrap in paragraphs
        if not html_content.startswith('<'):
            html_content = f'<p>{html_content}</p>'
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{style.title()} News Briefing</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
            
            <div style="text-align: center; border-bottom: 3px solid #007bff; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #007bff; margin: 0; font-size: 2.2em;">📰 {style.title()} News Briefing</h1>
                <p style="color: #666; font-size: 1.1em; margin: 10px 0;">Digestr.ai Intelligence Report</p>
                <p style="color: #888; font-size: 0.9em;">{timestamp}</p>
            </div>
            
            <div style="font-size: 1.05em; line-height: 1.7;">
                {html_content}
            </div>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; text-align: center;">
                <p style="color: #007bff; font-size: 1.1em; font-weight: 600;">🤖 Digestr.ai</p>
                <p style="color: #666; font-size: 0.9em; font-style: italic;">Your Personal News Intelligence Platform</p>
                <p style="color: #888; font-size: 0.8em;">
                    Automated briefing delivered by Conversation Export Plugin
                </p>
            </div>
            
        </body>
        </html>
        """
        
        return html_template
    
    def test_connection(self) -> bool:
        """Test SMTP connection without sending email"""
        if not self.enabled:
            print("[EMAIL DISABLED] Connection test skipped")
            return True
            
        if not self.validate_config():
            return False
        
        try:
            if self.smtp_port == 465:  # SSL
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.sender_email, self.sender_password)
            else:  # TLS
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.sender_email, self.sender_password)
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, any]:
        """Get email sender status"""
        return {
            "enabled": self.enabled,
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "sender_email": self.sender_email if self.sender_email else "Not configured",
            "config_valid": self.validate_config(),
            "use_tls": self.use_tls
        }