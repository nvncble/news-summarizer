"""
Simple Email Briefing Script for Digestr.ai
NOW USES IDENTICAL LOGIC AS CLI COMMAND
"""

import asyncio
import smtplib
import ssl
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from argparse import Namespace

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import CLI functions to reuse exact same logic
from digestr_cli_enhanced import enhanced_fetch_with_sources, handle_enhanced_briefing

# Email Configuration
SMTP_SERVER = os.getenv('DIGESTR_SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('DIGESTR_SMTP_PORT', '465'))
SENDER_EMAIL = os.getenv('DIGESTR_SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('DIGESTR_SENDER_PASSWORD', '')

RECIPIENTS = []
for i in range(1, 6):  # Support up to 5 recipients
    recipient = os.getenv(f'DIGESTR_RECIPIENT_{i}')
    if recipient:
        RECIPIENTS.append(recipient)

if not RECIPIENTS:
    print("❌ No recipients configured. Set DIGESTR_RECIPIENT_1 environment variable.")
    
if not SENDER_EMAIL or not SENDER_PASSWORD:
    print("❌ Email credentials not configured. Set DIGESTR_SENDER_EMAIL and DIGESTR_SENDER_PASSWORD environment variables.")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IdenticalEmailBriefer:
    """Email briefing that uses IDENTICAL logic as CLI"""
    
    def __init__(self):
        pass
    
    def get_time_period(self, hour):
        """Determine time period based on hour for email subject"""
        if 5 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon" 
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"

    async def generate_and_send_identical_briefing(self, style="comprehensive"):
        """Generate briefing using EXACT SAME CLI logic and send email"""
        try:
            print(f"🚀 Starting {style} briefing with CLI-identical logic...")
            
            # Step 1: FETCH using exact same CLI fetch logic
            print("📡 FETCHING using CLI fetch logic...")
            print(f"🕐 Fetch started at: {datetime.now().strftime('%H:%M:%S')}")
            
            # Use the exact same fetch function as CLI
            total_new_articles = await enhanced_fetch_with_sources(['rss', 'reddit'])
            
            print(f"🕐 Fetch completed at: {datetime.now().strftime('%H:%M:%S')}")
            print(f"📊 SUCCESS: {total_new_articles} articles fetched from CLI logic")
            
            if total_new_articles == 0:
                print("📰 No new articles found from CLI fetch")
                await self.send_email("📰 Digestr Briefing - No New Articles", 
                                    f"No new articles were found during fetch at {datetime.now().strftime('%H:%M:%S')}.")
                return
            
            # Step 2: BRIEFING using exact same CLI briefing logic
            print("🤖 Generating briefing using CLI briefing logic...")
            
            # Create args object identical to CLI command
            args = Namespace(
                command='briefing',
                style=style, 
                interactive=False,
                sources=['rss', 'reddit'],
                professional=False,
                social=False,
                categories=None
            )
            
            # Capture the briefing output by redirecting stdout
            import io
            from contextlib import redirect_stdout
            
            captured_output = io.StringIO()
            
            # Run the exact same CLI briefing function
            with redirect_stdout(captured_output):
                await handle_enhanced_briefing(args)
            
            # Get the captured briefing content
            full_cli_output = captured_output.getvalue()
            
            # Extract just the briefing content (remove debug output)
            lines = full_cli_output.split('\n')
            briefing_start = -1
            briefing_end = -1
            
            for i, line in enumerate(lines):
                if "YOUR COMPREHENSIVE DIGESTR.AI BRIEFING" in line:
                    briefing_start = i
                elif briefing_start > -1 and line.strip() == "=" * 80:
                    briefing_end = i + 1
                    break
            
            if briefing_start > -1 and briefing_end > -1:
                briefing_content = '\n'.join(lines[briefing_start:briefing_end])
            else:
                # Fallback: use all content after the header
                briefing_content = full_cli_output
            
            if not briefing_content or len(briefing_content.strip()) < 100:
                print(f"❌ Briefing generation failed or too short: {len(briefing_content)} chars")
                return
            
            print("✅ CLI-identical briefing generated successfully")
            
            # Step 3: EMAIL the identical briefing
            current_time = datetime.now()
            time_period = self.get_time_period(current_time.hour)
            
            # Create subject with CLI-style fetch info
            subject = f"📰 {time_period} CLI-Identical Briefing - {current_time.strftime('%B %d, %Y')}"
            
            await self.send_email(subject, briefing_content)
            
            print(f"🎉 CLI-identical {style} briefing completed and sent!")
            
        except Exception as e:
            logger.error(f"Error in CLI-identical briefing process: {e}")
            await self.send_email("❌ Digestr CLI-Identical Briefing Error", 
                                f"An error occurred while generating your CLI-identical briefing:\n\n{str(e)}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def send_email(self, subject, body):
        """Send email via Gmail SMTP"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = SENDER_EMAIL
            message["To"] = ", ".join(RECIPIENTS)
            message["Subject"] = subject
            
            # Add text content
            text_part = MIMEText(body, "plain", "utf-8")
            message.attach(text_part)
            
            # Create HTML version
            html_body = self.create_html_email(body, subject)
            html_part = MIMEText(html_body, "html", "utf-8")
            message.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(message)
            
            print(f"✅ Email sent successfully to {RECIPIENTS}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            print(f"❌ Email failed: {e}")
    
    def create_html_email(self, content, subject):
        """Create nice HTML email"""
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Convert line breaks to HTML
        html_content = content.replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
            
            <div style="text-align: center; border-bottom: 3px solid #007bff; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #007bff; margin: 0;">{subject}</h1>
                <p style="color: #666; margin: 10px 0;">{timestamp}</p>
                <p style="color: #28a745; font-size: 14px;">Generated using CLI-identical logic</p>
            </div>
            
            <div style="font-size: 16px; line-height: 1.8;">
                <p>{html_content}</p>
            </div>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666;">
                <p><strong>🤖 Digestr.ai</strong><br>
                Your Personal News Intelligence Platform</p>
                <p style="font-size: 12px;">CLI-Identical Automated Briefing • Generated with ❤️</p>
            </div>
            
        </body>
        </html>
        """
        return html
    
    async def test_email(self):
        """Test email functionality"""
        test_subject = "🧪 Digestr CLI-Identical Email Test"
        test_body = f"""This is a test email from Digestr.ai sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

✅ If you received this, email delivery is working correctly!

This system now uses IDENTICAL logic as the CLI command:
- Same fetch operation as 'digestr_cli_enhanced.py fetch --sources rss reddit'
- Same briefing generation as 'digestr_cli_enhanced.py briefing --sources rss reddit'
- Identical content and formatting

Your scheduled briefings will be exactly the same as running the CLI commands manually!"""
        
        await self.send_email(test_subject, test_body)


async def main():
    """Main function with CLI-identical briefing generation"""
    briefer = IdenticalEmailBriefer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            print("🧪 Testing CLI-identical email functionality...")
            await briefer.test_email()
        elif command in ["comprehensive", "quick", "analytical"]:
            await briefer.generate_and_send_identical_briefing(command)
        else:
            print("Usage: python simple_email_briefing.py [comprehensive|quick|analytical|test]")
            print("This will generate briefings using IDENTICAL CLI logic.")
    else:
        # Default: comprehensive briefing
        await briefer.generate_and_send_identical_briefing("comprehensive")


if __name__ == "__main__":
    asyncio.run(main())