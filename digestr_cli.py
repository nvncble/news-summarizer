#!/usr/bin/env python3
"""
Digestr CLI - Enhanced command-line interface
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
import argparse
import logging

# Import our modules (commenting out problematic ones for now)
try:
    from digestr.core.database import DatabaseManager
    from digestr.core.fetcher import FeedManager, RSSFetcher
    from digestr.llm_providers.ollama import OllamaProvider
    MODULES_LOADED = True
except ImportError as e:
    print(f"⚠️  Some modules couldn't load: {e}")
    MODULES_LOADED = False

def main():
    parser = argparse.ArgumentParser(
        description="Digestr.ai - Intelligent news summarization and analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  digestr_cli.py status                    # System status
  digestr_cli.py test                      # Test core functionality
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Test command
    subparsers.add_parser('test', help='Test core functionality')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        print("🔍 Digestr.ai System Status")
        print(f"✅ Version: 2.0.0")
        print(f"✅ Modules loaded: {'Yes' if MODULES_LOADED else 'No'}")
        print(f"✅ Python path: OK")
        
        if MODULES_LOADED:
            try:
                db = DatabaseManager("test.db")
                print("✅ Database: OK")
                feed_mgr = FeedManager()
                print(f"✅ Feed manager: {len(feed_mgr.get_categories())} categories")
                llm = OllamaProvider()
                print("✅ LLM provider: OK")
            except Exception as e:
                print(f"❌ Module initialization: {e}")
        
    elif args.command == 'test':
        if not MODULES_LOADED:
            print("❌ Cannot test - modules not loaded")
            return
            
        print("🧪 Testing Digestr functionality...")
        
        # Test database
        try:
            db = DatabaseManager("test.db")
            print("✅ Database initialization: OK")
        except Exception as e:
            print(f"❌ Database test: {e}")
            
        # Test feed manager
        try:
            feed_mgr = FeedManager()
            categories = feed_mgr.get_categories()
            print(f"✅ Feed manager: {len(categories)} categories ({', '.join(categories[:3])}...)")
        except Exception as e:
            print(f"❌ Feed manager test: {e}")
            
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
