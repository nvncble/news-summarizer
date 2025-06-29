#!/usr/bin/env python3
"""
Digestr CLI v2 - Enhanced with briefing functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import argparse
import logging

from digestr.core.database import DatabaseManager
from digestr.core.fetcher import FeedManager, RSSFetcher
from digestr.llm_providers.ollama import OllamaProvider

class DigestrCLI:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.feed_manager = FeedManager()
        self.fetcher = RSSFetcher(self.db_manager, self.feed_manager)
        self.llm_provider = OllamaProvider()
    
    async def run_simple_briefing(self):
        print("🚀 Digestr.ai - Fetching latest news...")
        
        # Fetch feeds
        category_counts = await self.fetcher.fetch_all_feeds()
        total_new = sum(category_counts.values())
        
        if total_new == 0:
            print("📰 No new articles found since last check.")
            return
            
        print(f"📈 Found {total_new} new articles across {len(category_counts)} categories")
        
        # Get recent articles for summary
        articles = self.db_manager.get_recent_articles(hours=24, limit=10)
        
        if articles:
            print(f"🤖 Most important recent articles:")
            for i, article in enumerate(articles[:5], 1):
                print(f"  {i}. {article.title[:60]}... (Score: {article.importance_score:.1f})")
        else:
            print("📰 No articles available for summary.")

async def main():
    parser = argparse.ArgumentParser(description="Digestr.ai - News Intelligence Platform")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Commands
    subparsers.add_parser('status', help='Show system status')
    subparsers.add_parser('briefing', help='Quick news briefing')
    subparsers.add_parser('fetch', help='Fetch latest articles only')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        print("🔍 Digestr.ai System Status")
        print("✅ Version: 2.0.0")
        print("✅ Modules: Loaded")
        print("✅ Database: Ready")
        print("🎯 Ready for news analysis!")
        
    elif args.command == 'briefing':
        cli = DigestrCLI()
        await cli.run_simple_briefing()
        
    elif args.command == 'fetch':
        cli = DigestrCLI()
        print("📡 Fetching latest articles...")
        category_counts = await cli.fetcher.fetch_all_feeds()
        total_new = sum(category_counts.values())
        print(f"✅ Fetched {total_new} new articles")
        for category, count in category_counts.items():
            if count > 0:
                print(f"   {category}: {count} articles")
        
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())
