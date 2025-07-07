#!/usr/bin/env python3
"""
Fixed Email Sender Module for Digestr.ai Plugin
Addresses the import and method issues found in testing
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    """Multi-provider email sender with SSL/TLS support"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.provider = config.get('provider', 'gmail')
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 465)
        self.sender_email = config.get('sender_email', '')
        self.sender_password = config.get('sender_password', '')
        self.use_tls = config.get('use_tls', False)
        self.subject_template = config.get('subject_template', '{style} Briefing - {date}')
        
        # For devspace/testing, allow empty credentials
        self.enabled = config.get('enabled', False)
        if not self.enabled:
            logger.info("EmailSender initialized in disabled mode (devspace)")
    
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
        """Send email to recipients"""
        
        # For devspace/testing mode
        if not self.enabled:
            print(f"[DEVSPACE] Would send email to {recipients}")
            print(f"[DEVSPACE] Subject: {subject}")
            print(f"[DEVSPACE] Body preview: {body[:100]}...")
            return True
        
        if not self.validate_config():
            logger.error("Email configuration invalid - cannot send email")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = self.sender_email
            message["To"] = ", ".join(recipients)
            message["Subject"] = subject
            
            # Add text part
            text_part = MIMEText(body, "plain", "utf-8")
            message.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                message.attach(html_part)
            
            # Connect and send
            if self.smtp_port == 465:  # SSL
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, recipients, message.as_string())
            else:  # TLS
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.sendmail(self.sender_email, recipients, message.as_string())
            
            logger.info(f"Email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_briefing(self, recipients: List[str], briefing_content: str, 
                     briefing_style: str = "comprehensive") -> bool:
        """Send a news briefing via email"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Format subject using template
        subject = self.subject_template.format(
            style=briefing_style.title(),
            date=current_date
        )
        
        # Create HTML version (avoiding problematic unicode in code)
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    Your {briefing_style.title()} News Briefing
                </h2>
                <p style="color: #7f8c8d; font-size: 14px;">
                    Generated on {datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")}
                </p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    {briefing_content.replace(chr(10), '<br>')}
                </div>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #95a5a6; font-size: 12px; text-align: center;">
                    Powered by Digestr.ai | Automated News Intelligence
                </p>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(recipients, subject, briefing_content, html_body)
    
    def test_connection(self) -> bool:
        """Test SMTP connection without sending email"""
        if not self.enabled:
            print("[DEVSPACE] Email testing skipped - disabled mode")
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
            "provider": self.provider,
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "sender_email": self.sender_email if self.sender_email else "Not configured",
            "config_valid": self.validate_config(),
            "devspace_mode": not self.enabled
        }


# Test function for development
def test_email_sender():
    """Test the EmailSender in devspace mode"""
    config = {
        'enabled': False,  # Devspace mode
        'provider': 'gmail',
        'smtp_server': '',
        'smtp_port': 465,
        'sender_email': '',
        'sender_password': '',
        'use_tls': False,
        'subject_template': '{style} Briefing - {date}'
    }
    
    sender = EmailSender(config)
    print("Email Sender Status:")
    status = sender.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Test sending (in devspace mode)
    result = sender.send_briefing(
        ['test@example.com'], 
        'This is a test briefing content for devspace testing.',
        'test'
    )
    print(f"Send test result: {result}")


if __name__ == "__main__":
    test_email_sender()
