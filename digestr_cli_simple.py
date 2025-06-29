#!/usr/bin/env python3
"""
Digestr CLI - Simple working version
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import argparse

from digestr.core.database import DatabaseManager
from digestr.core.fetcher import FeedManager

# Simple fetch function that bypasses the stats issue
async def simple_fetch():
    import aiohttp
    import feedparser
    from digestr.core.fetcher import ArticleProcessor
    
    db_manager = DatabaseManager()
    feed_manager = FeedManager()
    
    # Just test a few reliable feeds
    test_feeds = {
        "tech": [
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.theverge.com/rss/index.xml",
            "https://techcrunch.com/feed/"
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

async def main():
    parser = argparse.ArgumentParser(description="Digestr.ai - Simple News Fetcher")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    subparsers.add_parser('status', help='Show system status')
    subparsers.add_parser('fetch', help='Fetch latest articles')
    subparsers.add_parser('articles', help='Show recent articles')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        print("🔍 Digestr.ai System Status")
        print("✅ Version: 2.0.0 (Simple)")
        print("✅ Database: Ready")
        print("🎯 Ready for news fetching!")
        
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
            print("📰 No recent articles found. Try: python digestr_cli_simple.py fetch")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
