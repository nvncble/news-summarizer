#!/usr/bin/env python3
"""
Enhanced Email Briefing Script with Trend Analysis
Combines advanced CLI features with email delivery
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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import enhanced components
from digestr.config.manager import get_enhanced_config_manager
from digestr.sources.source_manager import SourceManager
from digestr.llm_providers.enhanced_briefing_generator import EnhancedBriefingGenerator
from digestr.analysis.trend_correlation_engine import TrendCorrelationEngine
from digestr.analysis.trend_structures import GeographicConfig
from digestr.sources.enhanced_trends24_scraper import EnhancedTrends24Scraper

# Email Configuration
SMTP_SERVER = os.getenv('DIGESTR_SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('DIGESTR_SMTP_PORT', '465'))
SENDER_EMAIL = os.getenv('DIGESTR_SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('DIGESTR_SENDER_PASSWORD', '')

RECIPIENTS = []
for i in range(1, 6):
    recipient = os.getenv(f'DIGESTR_RECIPIENT_{i}')
    if recipient:
        RECIPIENTS.append(recipient)

if not RECIPIENTS:
    print("❌ No recipients configured. Set DIGESTR_RECIPIENT_1 environment variable.")
    sys.exit(1)
    
if not SENDER_EMAIL or not SENDER_PASSWORD:
    print("❌ Email credentials not configured.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedEmailBriefer:
    """Enhanced email briefing with trend analysis and multi-source content"""
    
    def __init__(self):
        self.config_manager = get_enhanced_config_manager()
        self.config = self.config_manager.get_config()
    
    def get_time_period(self, hour):
        """Determine time period based on hour"""
        if 5 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon" 
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"

    async def generate_and_send_enhanced_briefing(self, style="comprehensive", force_fresh=True):
        """Generate enhanced briefing with trend analysis and send email"""
        try:
            print(f"🚀 Starting enhanced {style} briefing...")
            
            # Initialize source manager
            from digestr.core.database import DatabaseManager
            db_manager = DatabaseManager()
            source_manager = SourceManager(self.config_manager, db_manager)
            await source_manager.initialize_sources()
            
            # Fetch content (with or without fresh fetch)
            if force_fresh:
                print("📡 Fetching fresh content from all sources...")
                
                # Check if trends are enabled
                if self.config.trending.enabled:
                    print("📈 Trend analysis enabled - fetching with trend correlation...")
                    results = await source_manager.fetch_with_trend_analysis()
                    trend_analysis = results.get('trend_analysis')
                else:
                    print("📰 Fetching professional and social content...")
                    results = await source_manager.fetch_all_sources()
                    trend_analysis = None
            else:
                print("📚 Using cached content from database...")
                results = await source_manager.fetch_all_sources()
                trend_analysis = results.get('trend_analysis')
            
            professional_content = results.get('professional', {})
            social_content = results.get('social', {})
            
            # Count content
            total_professional = sum(len(content) for content in professional_content.values() if isinstance(content, list))
            total_social = sum(len(feed.posts) for feed in social_content.values() if hasattr(feed, 'posts'))
            
            print(f"📊 Content summary: {total_professional} professional articles, {total_social} social posts")
            
            if trend_analysis:
                significant_trends = trend_analysis.get_significant_trends()
                print(f"📈 Found {len(significant_trends)} significant cross-source trends")
            
            if total_professional == 0 and total_social == 0:
                print("📰 No content found - sending notification email")
                await self.send_email("📰 Digestr Briefing - No New Content", 
                                    f"No new content found during fetch at {datetime.now().strftime('%H:%M:%S')}.")
                return
            
            # Generate enhanced briefing
            print("🤖 Generating enhanced briefing...")
            briefing_generator = EnhancedBriefingGenerator(None, self.config_manager)
            
            if trend_analysis:
                # Use trend-aware briefing generator
                from digestr.analysis.trend_aware_briefing_generator import TrendAwareBriefingGenerator
                from digestr.llm_providers.ollama import OllamaProvider
                
                llm = OllamaProvider()
                trend_briefing_generator = TrendAwareBriefingGenerator(llm)
                
                content_data = {
                    'professional': professional_content,
                    'social': social_content
                }
                
                briefing = await trend_briefing_generator.generate_comprehensive_briefing(
                    content_data, trend_analysis, style
                )
            else:
                # Use standard enhanced briefing
                briefing = await briefing_generator.generate_combined_briefing(
                    professional_content, social_content, style
                )
            
            if not briefing or len(briefing.strip()) < 100:
                print(f"❌ Briefing generation failed or too short: {len(briefing)} chars")
                await self.send_email("❌ Digestr Briefing Error", 
                                    "Briefing generation failed - content too short.")
                return
            
            print("✅ Enhanced briefing generated successfully")
            
            # Send email
            current_time = datetime.now()
            time_period = self.get_time_period(current_time.hour)
            
            trend_indicator = "🔥 Trend-Enhanced" if trend_analysis else "📰"
            subject = f"{trend_indicator} {time_period} Digestr Briefing - {current_time.strftime('%B %d, %Y')}"
            
            await self.send_email(subject, briefing)
            
            # Mark articles as processed
            if total_professional > 0:
                from digestr.core.database import DatabaseManager
                db = DatabaseManager()
                recent_articles = db.get_recent_articles(hours=24, limit=100, unprocessed_only=True)
                if recent_articles:
                    urls = [article.url for article in recent_articles]
                    db.mark_articles_processed(urls)
            
            print(f"🎉 Enhanced {style} briefing completed and sent!")
            
        except Exception as e:
            logger.error(f"Error in enhanced briefing process: {e}")
            import traceback
            traceback.print_exc()
            await self.send_email("❌ Digestr Enhanced Briefing Error", 
                                f"An error occurred while generating your enhanced briefing:\n\n{str(e)}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def send_email(self, subject, body):
        """Send email via SMTP with SSL (known working config)"""
        smtp_configs = [
            {"server": "smtp.gmail.com", "port": 465, "method": "SSL"},
            {"server": "smtp.gmail.com", "port": 587, "method": "TLS"},
        ]
        
        for config in smtp_configs:
            try:
                print(f"🔄 Trying {config['server']}:{config['port']} with {config['method']}...")
                
                message = MIMEMultipart("alternative")
                message["From"] = SENDER_EMAIL
                message["To"] = ", ".join(RECIPIENTS)
                message["Subject"] = subject
                
                text_part = MIMEText(body, "plain", "utf-8")
                message.attach(text_part)
                
                html_body = self.create_html_email(body, subject)
                html_part = MIMEText(html_body, "html", "utf-8")
                message.attach(html_part)
                
                if config["method"] == "SSL":
                    context = ssl.create_default_context()
                    server = smtplib.SMTP_SSL(config["server"], config["port"], context=context)
                else:
                    server = smtplib.SMTP(config["server"], config["port"], timeout=30)
                    server.starttls()
                
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(message)
                server.quit()
                
                print(f"✅ Email sent successfully to {RECIPIENTS}")
                return
                
            except Exception as e:
                print(f"❌ Failed with {config['server']}:{config['port']} - {e}")
                continue
        
        logger.error(f"Failed to send email with all SMTP configurations")
    
    def create_html_email(self, content, subject):
        """Create enhanced HTML email"""
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
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
                <p style="color: #28a745; font-size: 14px;">Enhanced with Multi-Source Intelligence & Trend Analysis</p>
            </div>
            
            <div style="font-size: 16px; line-height: 1.8;">
                <p>{html_content}</p>
            </div>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666;">
                <p><strong>🤖 Digestr.ai Enhanced</strong><br>
                Multi-Source News Intelligence with Trend Analysis</p>
                <p style="font-size: 12px;">RSS • Reddit • Trending Topics • AI Analysis</p>
            </div>
            
        </body>
        </html>
        """
        return html
    
    async def test_email(self):
        """Test enhanced email functionality"""
        test_subject = "🧪 Digestr Enhanced Email Test"
        test_body = f"""This is a test email from Digestr.ai Enhanced sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

✅ If you received this, the enhanced email delivery is working correctly!

Enhanced Features Available:
🔥 Trend Analysis - Cross-source trend correlation
📰 Multi-Source - RSS feeds + Reddit + Trending topics  
🎯 Smart Prioritization - AI-powered content ranking
📊 Sentiment Analysis - Community reaction insights
🌍 Geographic Relevance - Location-based filtering

Your enhanced briefings will include all these features automatically!"""
        
        await self.send_email(test_subject, test_body)


async def main():
    """Main function for enhanced briefing"""
    briefer = EnhancedEmailBriefer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            print("🧪 Testing enhanced email functionality...")
            await briefer.test_email()
        elif command in ["comprehensive", "quick", "analytical"]:
            force_fresh = "--fresh" in sys.argv or True  # Default to fresh
            await briefer.generate_and_send_enhanced_briefing(command, force_fresh)
        else:
            print("Usage: python enhanced_email_briefing.py [comprehensive|quick|analytical|test] [--fresh]")
            print("Enhanced briefing with trend analysis and multi-source intelligence.")
    else:
        await briefer.generate_and_send_enhanced_briefing("comprehensive")


if __name__ == "__main__":
    asyncio.run(main())