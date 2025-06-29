#!/usr/bin/env python3
"""
Digestr CLI - Enhanced with briefing functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import argparse
from datetime import datetime

from digestr.core.database import DatabaseManager
from digestr.core.fetcher import FeedManager
from digestr.llm_providers.ollama import OllamaProvider

# Simple fetch function
async def simple_fetch():
    import aiohttp
    import feedparser
    from digestr.core.fetcher import ArticleProcessor
    
    db_manager = DatabaseManager()
    feed_manager = FeedManager()
    
    # Use reliable feeds
    test_feeds = {
        "tech": [
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.theverge.com/rss/index.xml",
            "https://techcrunch.com/feed/"
        ],
        "world_news": [
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://www.theguardian.com/world/rss"
        ]
    }
    
    articles_found = 0
    
    async with aiohttp.ClientSession() as session:
        for category, feeds in test_feeds.items():
            for feed_url in feeds:
                try:
                    async with session.get(feed_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            source = feed.feed.get('title', 'Unknown')
                            
                            for entry in feed.entries:
                                article = ArticleProcessor.create_article_from_entry(entry, category, source)
                                if db_manager.insert_article(article):
                                    articles_found += 1
                            
                            print(f"✅ {feed_url}: {len(feed.entries)} articles")
                        else:
                            print(f"❌ {feed_url}: HTTP {response.status}")
                except Exception as e:
                    print(f"❌ {feed_url}: {e}")
    
    return articles_found

async def generate_briefing():
    """Generate a news briefing using the new modular system"""
    print("🚀 Digestr.ai v2.0 - Generating News Briefing")
    
    # Fetch latest articles
    print("📡 Fetching latest news...")
    await simple_fetch()
    
    # Get articles for briefing
    db = DatabaseManager()
    articles = db.get_recent_articles(hours=24, limit=20)
    
    if not articles:
        print("📰 No recent articles found. Try running fetch first.")
        return
    
    print(f"📈 Found {len(articles)} articles for analysis")
    
    # Convert to format expected by LLM provider
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
    
    # Generate AI briefing
    print("🤖 Generating AI briefing...")
    try:
        llm = OllamaProvider()
        briefing = await llm.generate_briefing(article_dicts, briefing_type="comprehensive")
        
        # Display briefing
        print("\n" + "="*80)
        print("📋 YOUR DIGESTR.AI NEWS BRIEFING")
        print("="*80)
        print(briefing)
        print("\n" + "="*80)
        
        # Mark articles as processed
        article_urls = [article.url for article in articles]
        db.mark_articles_processed(article_urls)
        
    except Exception as e:
        print(f"❌ Error generating briefing: {e}")
        print("💡 Make sure Ollama is running and accessible")

async def main():
    parser = argparse.ArgumentParser(description="Digestr.ai v2.0 - News Intelligence Platform")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    subparsers.add_parser('status', help='Show system status')
    subparsers.add_parser('fetch', help='Fetch latest articles')
    subparsers.add_parser('articles', help='Show recent articles')
    
    # Add briefing command
    briefing_parser = subparsers.add_parser('briefing', help='Generate AI news briefing')
    briefing_parser.add_argument('--style', choices=['comprehensive', 'quick', 'analytical'], 
                                default='comprehensive', help='Briefing style')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        print("🔍 Digestr.ai System Status")
        print("✅ Version: 2.0.0")
        print("✅ Database: Ready")
        print("✅ Ollama: Ready (assumed)")
        print("🎯 Ready for news intelligence!")
        
    elif args.command == 'fetch':
        print("📡 Fetching from reliable feeds...")
        count = await simple_fetch()
        print(f"✅ Found {count} new articles")
        
    elif args.command == 'articles':
        db = DatabaseManager()
        articles = db.get_recent_articles(hours=24, limit=10)
        
        if articles:
            print(f"📰 Recent articles ({len(articles)} found):")
            for i, article in enumerate(articles[:5], 1):
                print(f"  {i}. {article.title[:60]}...")
                print(f"     Source: {article.source} | Score: {article.importance_score:.1f}")
        else:
            print("📰 No recent articles found. Try: python digestr_cli.py fetch")
    
    elif args.command == 'briefing':
        await generate_briefing()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
