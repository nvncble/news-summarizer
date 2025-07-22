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
from typing import List, Dict, Optional, Any


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
from digestr.analysis.trend_aware_briefing_generator import TrendAwareBriefingGenerator
from digestr.core.reliable_link_processor import ReliableLinkProcessor

def make_links_clickable_in_briefing(briefing_content: str, content_data: Dict) -> str:
    """Convert [→] format to clickable HTML links"""
    from digestr.core.link_processor import ReliableLinkProcessor
    
    # Collect all articles and posts
    all_items = []
    
    # Professional articles
    for source_name, articles in content_data.get('professional', {}).items():
        for article in articles:
            # Handle both dict and Article objects
            if isinstance(article, dict):
                all_items.append({
                    'title': article.get('title', ''),
                    'url': article.get('url', '')
                })
            else:
                # Article object - use getattr
                all_items.append({
                    'title': getattr(article, 'title', ''),
                    'url': getattr(article, 'url', '')
                })
    
    # Social posts
    for source_name, feed in content_data.get('social', {}).items():
        if hasattr(feed, 'posts'):
            for post in feed.posts:
                all_items.append({
                    'title': post.title,
                    'url': post.url or post.source_url
                })
    
    # Process content
    processor = ReliableLinkProcessor()
    processed = processor.process_briefing_content(briefing_content, all_items)
    
    
    
    return processed
    
    # def replace_arrow_link(match):
    #     title_text = match.group(1).strip()
        
    #     # Simple keyword matching to find URLs
    #     matching_url = None
    #     title_words = title_text.lower().split()
        
    #     for stored_title, url in article_urls.items():
    #         # Check if any significant words from the title appear in stored title
    #         if len(title_words) >= 2:
    #             key_words = title_words[-3:]  # Last 3 words usually most specific
    #             if any(word in stored_title.lower() for word in key_words if len(word) > 3):
    #                 matching_url = url
    #                 break
        
    #     if matching_url:
    #         return f'<a href="{matching_url}" style="color: #007bff; text-decoration: none;">{title_text}</a>'
    #     else:
    #         return title_text
    
    # return re.sub(arrow_pattern, replace_arrow_link, briefing_content)


def safe_article_access(obj, attr_name, default=''):
    """Safe access for Article objects and dictionaries"""
    if obj is None:
        return default
    if hasattr(obj, attr_name):
        value = getattr(obj, attr_name, default)
        return value if value is not None else default
    elif isinstance(obj, dict):
        return obj.get(attr_name, default)
    else:
        return default

def convert_articles_to_dicts(articles):
    """Convert Article objects to dictionaries"""
    if not articles:
        return []
    
    converted = []
    for article in articles:
        if isinstance(article, dict):
            converted.append(article)
        else:
            # Convert Article object to dict
            article_dict = {
                'title': safe_article_access(article, 'title', ''),
                'summary': safe_article_access(article, 'summary', ''),
                'content': safe_article_access(article, 'content', ''),
                'url': safe_article_access(article, 'url', ''),
                'category': safe_article_access(article, 'category', ''),
                'source': safe_article_access(article, 'source', ''),
                'published_date': safe_article_access(article, 'published_date', ''),
                'importance_score': safe_article_access(article, 'importance_score', 0.0),
                'source_type': 'professional'
            }
            converted.append(article_dict)
    return converted











# Email Configuration
SMTP_SERVER = os.getenv('DIGESTR_SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('DIGESTR_SMTP_PORT', '465'))
SENDER_EMAIL = os.getenv('DIGESTR_SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('DIGESTR_SENDER_PASSWORD', '')

RECIPIENTS = []
i = 1
while True:
    recipient = os.getenv(f'DIGESTR_RECIPIENT_{i}')
    if recipient:
        RECIPIENTS.append(recipient)
        i += 1
    else:
        break

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

    async def generate_and_send_enhanced_briefing_with_reliable_links(self, style="comprehensive", force_fresh=True):
        """Generate briefing with guaranteed clickable links"""
        
        try:
            print(f"🚀 Starting enhanced {style} briefing with reliable linking...")
            
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
                # Use standard briefing generator - try different method names
                from digestr.llm_providers.ollama import OllamaProvider
                llm_provider = OllamaProvider()
                briefing_generator = EnhancedBriefingGenerator(llm_provider, self.config_manager)
                
                # Try these methods in order until one works:
                # Use the method that exists (per Python's suggestion)
                structured_briefing = await briefing_generator.generate_structured_briefing(
                    professional_content, social_content, style, "default"
                )
                briefing = structured_briefing.get_full_content()
            
            if not briefing or len(briefing.strip()) < 100:
                print(f"❌ Briefing generation failed or too short: {len(briefing)} chars")
                await self.send_email("❌ Digestr Briefing Error", 
                                    "Briefing generation failed - content too short.")
                return
            
            print("✅ Enhanced briefing generated successfully")
            all_articles = []

            for source_name, articles in professional_content.items():
                if isinstance(articles, list):
                    for article in articles:
                        if isinstance(article, dict):
                            all_articles.append(article)
                        else:
                            # Convert Article object to dict
                            all_articles.append({
                                'title': getattr(article, 'title', ''),
                                'url': getattr(article, 'url', ''),
                                'source': getattr(article, 'source', ''),
                                'summary': getattr(article, 'summary', ''),
                                'content': getattr(article, 'content', ''),
                            })
        
            # Collect social posts
            for source_name, feed in social_content.items():
                if hasattr(feed, 'posts'):
                    for post in feed.posts:
                        all_articles.append({
                            'title': post.title,
                            'url': post.url or post.source_url,
                            'source': f"r/{post.subreddit}" if post.subreddit else post.platform,
                            'content': post.content,
                        })
            
            print("🔗 Processing links in briefing...")
            content_data = {
                'professional': professional_content,
                'social': social_content
            }
            final_briefing = make_links_clickable_in_briefing(briefing, content_data)

            print("✅ Enhanced briefing with reliable links generated successfully")
            
           


            # Send email
            current_time = datetime.now()
            time_period = self.get_time_period(current_time.hour)
            
            trend_indicator = "🔥 Trend-Enhanced" if trend_analysis else "📰"
            subject = f"{trend_indicator} {time_period} Digestr Briefing - {current_time.strftime('%B %d, %Y')}"
            
            await self.send_email(subject, final_briefing, all_articles)
            
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
    
    async def send_email(self, subject, body, articles=None):
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
                
                html_body = self.create_enhanced_html_email(body, subject, articles or [])

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
    
    def create_enhanced_html_email(self, content, subject, articles):
        """Create HTML email with reliable clickable links"""
        
        # Process content to ensure all links are clickable
        link_processor = ReliableLinkProcessor()
        html_content = content
        
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Convert newlines to proper HTML
        formatted_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
                    line-height: 1.6; 
                    color: #333; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px; 
                }}
                .header {{ 
                    text-align: center; 
                    border-bottom: 3px solid #007bff; 
                    padding-bottom: 20px; 
                    margin-bottom: 30px; 
                }}
                .content {{ 
                    font-size: 16px; 
                    line-height: 1.8; 
                }}
                .content p {{ 
                    margin-bottom: 16px; 
                }}
                a {{ 
                    color: #007bff; 
                    text-decoration: none; 
                    font-weight: bold;
                }}
                a:hover {{ 
                    text-decoration: underline; 
                }}
                .footer {{ 
                    margin-top: 40px; 
                    padding-top: 20px; 
                    border-top: 2px solid #eee; 
                    text-align: center; 
                    color: #666; 
                }}
                .stats {{ 
                    font-size: 12px; 
                    color: #999; 
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="color: #007bff; margin: 0;">{subject}</h1>
                <p style="color: #666; margin: 10px 0;">{timestamp}</p>
                <p style="color: #28a745; font-size: 14px;">🔗 All Sources Linked • 🤖 AI Enhanced</p>
            </div>
            
            <div class="content">
                <p>{formatted_content}</p>
            </div>
            
            <div class="footer">
                <p><strong>🤖 Digestr.ai Enhanced Briefing</strong></p>
                <p class="stats">
                    📊 {len(articles)} articles analyzed • 🔗 All sources linked for deep-dive reading
                </p>
                <p style="font-size: 12px;">
                    Multi-Source Intelligence: RSS • Reddit • Trending Topics
                </p>
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
            force_fresh = "--cached" not in sys.argv  # Default to fresh
            await briefer.generate_and_send_enhanced_briefing_with_reliable_links(command, force_fresh)
        else:
            print("Usage: python enhanced_email_briefing.py [comprehensive|quick|analytical|test] [--fresh]")
            print("Enhanced briefing with trend analysis and multi-source intelligence.")
    else:
        await briefer.generate_and_send_enhanced_briefing_with_reliable_links("comprehensive")


if __name__ == "__main__":
    asyncio.run(main())