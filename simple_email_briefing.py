"""
Simple Email Briefing Script for Digestr.ai
Bypasses complex plugin system - just fetches news and emails it
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

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from digestr.core.database import DatabaseManager
from digestr.llm_providers.ollama import OllamaProvider
from digestr.config.manager import get_enhanced_config_manager
from digestr.sources.source_manager import SourceManager

# Email Configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465  # SSL port
SENDER_EMAIL = 'nvncbleyeti@gmail.com'
SENDER_PASSWORD = 'aawo abby cosk tyqg'  # Your app password
RECIPIENTS = ['nvncbleyeti@gmail.com', 'a.jarama@yahoo.com']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleEmailBriefer:
    """Simple email briefing with multi-source support (RSS + Reddit)"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.config_manager = get_enhanced_config_manager()
        self.source_manager = SourceManager(self.config_manager, self.db)
        self.ollama = OllamaProvider()
    



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


    async def generate_and_send_briefing(self, style="comprehensive"):
        """Main function - FORCE fetch fresh content, generate briefing, send email"""
        try:
            print(f"🚀 Starting {style} briefing with FRESH content fetch...")
            
            # Step 1: Initialize sources (RSS + Reddit)
            print("⚙️ Initializing RSS and Reddit sources...")
            await self.source_manager.initialize_sources()
            
            # Step 2: FORCE fetch fresh content from both sources
            print("📡 FETCHING FRESH CONTENT from RSS feeds and Reddit...")
            print(f"🕐 Fetch started at: {datetime.now().strftime('%H:%M:%S')}")
            
            # Clear any caches to ensure fresh content
            if hasattr(self.source_manager, 'clear_all_caches'):
                self.source_manager.clear_all_caches()
            
            results = await self.source_manager.fetch_specific_sources(['rss', 'reddit'])
            
            print(f"🕐 Fetch completed at: {datetime.now().strftime('%H:%M:%S')}")
            
            # Count and validate fresh articles
            total_new_articles = 0
            fetch_details = {}
            
            for source_name, articles in results.items():
                if isinstance(articles, list):
                    count = len(articles)
                    total_new_articles += count
                    fetch_details[source_name] = count
                    print(f"  📊 {source_name}: {count} articles fetched")
                    
                    # Show some article titles to verify freshness
                    if count > 0 and hasattr(articles[0], 'title'):
                        print(f"      Latest: {articles[0].title[:60]}...")
            
            if total_new_articles == 0:
                print("📰 No new articles found from fresh fetch")
                await self.send_email("📰 Digestr Briefing - No New Articles", 
                                    f"No new articles were found from RSS or Reddit sources during fetch at {datetime.now().strftime('%H:%M:%S')}.")
                return
            
            print(f"📈 SUCCESS: {total_new_articles} fresh articles fetched from multiple sources")
            
            # Step 3: Convert FRESH articles for briefing (use fetched results, not database)
            print("🤖 Generating briefing from FRESH content...")
            combined_articles = []
            
            for source_name, articles in results.items():
                if isinstance(articles, list):
                    for article in articles:
                        # Convert fresh Article objects to dict format
                        if hasattr(article, 'title'):
                            article_dict = {
                                'title': article.title,
                                'summary': article.summary,
                                'content': article.content,
                                'url': article.url,
                                'category': article.category,
                                'source': article.source,
                                'published_date': article.published_date,
                                'importance_score': getattr(article, 'importance_score', 0),
                                'source_type': 'reddit' if source_name == 'reddit' else 'professional',
                                'fetched_fresh': True  # Mark as fresh
                            }
                            combined_articles.append(article_dict)
            
            if not combined_articles:
                print("📰 No fresh articles to process for briefing")
                return
            
            print(f"🔄 Processing {len(combined_articles)} fresh articles for briefing...")
            
            # Step 4: Generate enhanced briefing from fresh content
            briefing = await self.generate_multi_source_briefing(combined_articles, style)
            
            if briefing.startswith("Error"):
                print(f"❌ Briefing generation failed: {briefing}")
                return
            
            print("✅ Multi-source briefing generated from fresh content")
            
            # Step 5: Send email with fresh content summary
            current_time = datetime.now()
            time_period = self.get_time_period(current_time.hour)
            
            # Include fetch details in subject
            source_summary = f"({fetch_details.get('rss', 0)} RSS + {fetch_details.get('reddit', 0)} Reddit)"
            subject = f"📰 {time_period} Fresh Briefing {source_summary} - {current_time.strftime('%B %d, %Y')}"
            
            await self.send_email(subject, briefing)
            
            # Step 6: Mark fresh articles as processed (to avoid re-processing)
            article_urls = [article['url'] for article in combined_articles if article.get('url')]
            if article_urls:
                self.db.mark_articles_processed(article_urls)
                print(f"📝 Marked {len(article_urls)} fresh articles as processed")
            
            print(f"🎉 {style.title()} briefing with fresh content completed and sent!")
            print(f"📊 Final stats: {total_new_articles} articles from {len(fetch_details)} sources")
            
        except Exception as e:
            logger.error(f"Error in fresh briefing process: {e}")
            await self.send_email("❌ Digestr Fresh Briefing Error", 
                                f"An error occurred while generating your fresh briefing:\n\n{str(e)}\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def generate_multi_source_briefing(self, articles, style):
        """Generate briefing with RSS + Reddit content (like CLI --sources rss reddit)"""
        
        # Separate RSS and Reddit articles
        rss_articles = [a for a in articles if a.get('source_type') == 'professional' and 'reddit' not in a.get('source', '').lower()]
        reddit_articles = [a for a in articles if a.get('source_type') == 'reddit' or 'reddit' in a.get('source', '').lower()]
        
        print(f"📊 Content breakdown: {len(rss_articles)} RSS articles, {len(reddit_articles)} Reddit articles")
        
        # Create enhanced prompt that highlights both sources
        prompt = self.create_multi_source_prompt(rss_articles, reddit_articles, style)
        
        # Generate briefing using Ollama
        briefing = await self.ollama.generate_summary(prompt)
        
        return briefing
    
    def create_multi_source_prompt(self, rss_articles, reddit_articles, style):
        """Create prompt that combines RSS news + Reddit community sentiment"""
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        prompt = f"""You are a comprehensive news analyst providing a multi-source briefing. Current time: {current_time}

MULTI-SOURCE INTELLIGENCE BRIEF:

RSS NEWS SOURCES ({len(rss_articles)} articles):
"""
        
        # Add RSS articles
        for i, article in enumerate(rss_articles[:12], 1):  # Limit for prompt size
            importance = article.get('importance_score', 0)
            indicator = "🔥" if importance > 5 else "📌" if importance > 2 else "📄"
            prompt += f"\n{indicator} **{article['title']}** ({article.get('source', 'Unknown')})\n"
            content = article.get('content') or article.get('summary', '')
            if len(content) > 250:
                content = content[:250] + "..."
            prompt += f"   {content}\n"
        
        if reddit_articles:
            prompt += f"\nREDDIT COMMUNITY DISCUSSIONS ({len(reddit_articles)} articles with sentiment analysis):\n"
            
            # Add Reddit articles with community context
            for i, article in enumerate(reddit_articles[:8], 1):  # Limit for prompt size
                title = article['title'].replace('[Reddit] ', '')  # Clean title
                prompt += f"\n🔴 **{title}** ({article.get('source', 'Unknown')})\n"
                content = article.get('content') or article.get('summary', '')
                if len(content) > 200:
                    content = content[:200] + "..."
                prompt += f"   {content}\n"
        
        prompt += f"""

BRIEFING STYLE: {style.title()}

INSTRUCTIONS:
- Provide a comprehensive analysis that synthesizes information from both traditional news and community discussions
- When Reddit content is available, incorporate community perspectives and reactions  
- Highlight any notable differences between official reporting and community sentiment
- Use phrases like "Reddit discussions show..." or "Community reaction indicates..." when referencing Reddit content
- Connect related stories across different sources
- Maintain a professional yet engaging tone
- Structure as flowing narrative, not bullet points

Generate your comprehensive multi-source briefing:"""
        
        return prompt
    
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
            </div>
            
            <div style="font-size: 16px; line-height: 1.8;">
                <p>{html_content}</p>
            </div>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; text-align: center; color: #666;">
                <p><strong>🤖 Digestr.ai</strong><br>
                Your Personal News Intelligence Platform</p>
                <p style="font-size: 12px;">Automated briefing • Generated with ❤️</p>
            </div>
            
        </body>
        </html>
        """
        return html
    
    async def test_email(self):
        """Test email functionality with fresh fetch info"""
        test_subject = "🧪 Digestr Fresh Multi-Source Email Test"
        test_body = f"""This is a test email from Digestr.ai sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

✅ If you received this, email delivery is working correctly!

This system will FETCH FRESH CONTENT each time and send you briefings that combine:
📰 Traditional RSS news sources (fetched live)
🔴 Reddit community discussions and sentiment (fetched live)  
🤖 AI-powered analysis and synthesis

Each briefing will:
- Force fresh content fetch from all sources
- Show exact article counts fetched
- Include timestamps of fetch operations
- Process only newly fetched content (not cached articles)

Your scheduled briefings will include both professional news coverage and community reactions for a complete picture of what's happening."""
        
        await self.send_email(test_subject, test_body)
    
    async def force_fresh_briefing(self, style="comprehensive"):
        """Force a completely fresh briefing by clearing all caches first"""
        print("🔄 FORCING completely fresh briefing (clearing all caches)...")
        
        # Clear database processed flags to ensure fresh processing
        print("🧹 Clearing processed article flags...")
        conn = self.db.db_path
        import sqlite3
        with sqlite3.connect(conn) as db_conn:
            cursor = db_conn.cursor()
            cursor.execute('UPDATE articles SET processed = FALSE WHERE fetched_date > datetime("now", "-24 hours")')
            db_conn.commit()
            
        # Now run normal briefing with fresh fetch
        await self.generate_and_send_briefing(style)


async def main():
    """Main function with command line options for multi-source briefings"""
    briefer = SimpleEmailBriefer()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            print("🧪 Testing multi-source email functionality...")
            await briefer.test_email()
        elif command in ["comprehensive", "quick", "analytical"]:
            await briefer.generate_and_send_briefing(command)
        else:
            print("Usage: python simple_email_briefing.py [comprehensive|quick|analytical|test]")
            print("This will generate briefings using both RSS news and Reddit community discussions.")
    else:
        # Default: comprehensive briefing
        await briefer.generate_and_send_briefing("comprehensive")


if __name__ == "__main__":
    asyncio.run(main())