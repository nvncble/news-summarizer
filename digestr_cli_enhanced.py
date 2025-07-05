#!/usr/bin/env python3
"""
Digestr CLI - Enhanced with briefing functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
import sqlite3
import asyncio
import argparse
from datetime import datetime
from digestr.features.interactive import InteractiveSession
from digestr.core.database import DatabaseManager
from digestr.core.fetcher import FeedManager
from digestr.llm_providers.ollama import OllamaProvider
from digestr.core.plugin_manager import PluginManager
from digestr.core.plugin_manager import PluginManager
from digestr.config.manager import get_config_manager

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
    articles = db.get_recent_articles(hours=24, limit=30, unprocessed_only=False)

    
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






async def handle_plugin_commands(args):
    """Handle all plugin-related commands"""
    
    # Initialize plugin manager
    config_manager = get_config_manager()
    plugin_manager = PluginManager(config_manager)
    
    # Initialize the plugin system (discover and load enabled plugins)
    plugin_manager.initialize()
    
    if args.plugin_command == 'list':
        print("📦 Available Plugins:")
        print("=" * 50)
        
        plugins = plugin_manager.get_available_plugins()
        
        if not plugins:
            print("  No plugins found.")
            print(f"  Check plugin directory: {plugin_manager.plugin_dir}")
            print("  Create plugins with: python digestr_cli_enhanced.py plugin create [name]")
            return
        
        for plugin in plugins:
            status_icon = "✅" if plugin['enabled'] else "⚪"
            loaded_icon = "🔄" if plugin['loaded'] else "💤"
            
            print(f"  {status_icon} {loaded_icon} {plugin['display_name']}")
            print(f"      Name: {plugin['name']}")
            print(f"      Version: {plugin['version']} by {plugin['author']}")
            print(f"      Description: {plugin['description']}")
            
            if plugin['commands']:
                commands = [f"/{cmd}" for cmd in plugin['commands']]
                print(f"      Commands: {', '.join(commands)}")
            
            if plugin['tags']:
                print(f"      Tags: {', '.join(plugin['tags'])}")
            
            print()
        
        print("Legend: ✅ Enabled  ⚪ Disabled  🔄 Loaded  💤 Not Loaded")
    
    elif args.plugin_command == 'install':
        plugin_name = args.name
        print(f"📦 Installing plugin: {plugin_name}")
        
        # For now, this is a placeholder for future implementation
        # In the future, this would download from the plugin registry
        print("❌ Plugin installation from registry not yet implemented")
        print("💡 To install a plugin manually:")
        print(f"   1. Create directory: {plugin_manager.plugin_dir}/{plugin_name}")
        print(f"   2. Add plugin.json, main.py, and config.yaml")
        print(f"   3. Enable with: python digestr_cli_enhanced.py plugin enable {plugin_name}")
    
    elif args.plugin_command == 'enable':
        plugin_name = args.name
        print(f"✅ Enabling plugin: {plugin_name}")
        
        # First, make sure we've discovered plugins
        discovered = plugin_manager.discover_plugins()
        
        if plugin_name not in plugin_manager.manifests:
            print(f"❌ Plugin '{plugin_name}' not found")
            print(f"Available plugins: {list(plugin_manager.manifests.keys())}")
            return
        
        success = plugin_manager.enable_plugin(plugin_name)
        if success:
            print(f"✅ Plugin '{plugin_name}' enabled and loaded successfully")
        else:
            print(f"❌ Failed to enable plugin '{plugin_name}'")
            print("💡 Check logs for error details")
    
    elif args.plugin_command == 'disable':
        plugin_name = args.name
        print(f"❌ Disabling plugin: {plugin_name}")
        
        if plugin_name not in plugin_manager.manifests:
            print(f"❌ Plugin '{plugin_name}' not found")
            return
        
        success = plugin_manager.disable_plugin(plugin_name)
        if success:
            print(f"✅ Plugin '{plugin_name}' disabled successfully")
        else:
            print(f"❌ Failed to disable plugin '{plugin_name}'")
    
    elif args.plugin_command == 'config':
        plugin_name = args.name
        print(f"⚙️ Plugin Configuration: {plugin_name}")
        
        status = plugin_manager.get_plugin_status(plugin_name)
        if not status:
            print(f"❌ Plugin '{plugin_name}' not found")
            return
        
        print(f"Plugin: {status['display_name']} v{status['version']}")
        print(f"Author: {status['author']}")
        print(f"Status: {'Enabled' if status['enabled'] else 'Disabled'}")
        print(f"Loaded: {'Yes' if status['loaded'] else 'No'}")
        print(f"Directory: {status['plugin_dir']}")
        
        # Show configuration schema
        if status['config_schema']:
            print("\n📝 Configuration Options:")
            for key, schema in status['config_schema'].items():
                default = schema.get('default', 'None')
                description = schema.get('description', 'No description')
                print(f"  {key}: {description} (default: {default})")
        
        # Show configuration file location
        config_file = f"{status['plugin_dir']}/config.yaml"
        print(f"\n🔧 Edit configuration: {config_file}")
    
    elif args.plugin_command == 'status':
        print("🔌 Plugin System Status:")
        print("=" * 50)
        
        print(f"Plugin Directory: {plugin_manager.plugin_dir}")
        print(f"Discovered Plugins: {len(plugin_manager.manifests)}")
        print(f"Loaded Plugins: {len(plugin_manager.plugins)}")
        print(f"Registered Hooks: {len(plugin_manager.hooks)}")
        print(f"Registered Commands: {len(plugin_manager.commands)}")
        
        if plugin_manager.commands:
            print("\n💬 Available Plugin Commands:")
            for cmd_name, cmd_info in plugin_manager.commands.items():
                plugin_name = cmd_info.get('plugin', 'unknown')
                description = cmd_info.get('description', 'No description')
                print(f"  /{cmd_name}: {description} (from {plugin_name})")
    
    else:
        print("❌ Unknown plugin command")
        print("Available commands: list, install, enable, disable, config, status")





















async def main():


    
    parser = argparse.ArgumentParser(description="Digestr.ai v2.0 - News Intelligence Platform")

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Plugin commands
    plugin_parser = subparsers.add_parser('plugin', help='Manage plugins')
    plugin_subparsers = plugin_parser.add_subparsers(dest='plugin_command', help='Plugin commands')
    plugin_subparsers.add_parser('list', help='List available plugins')
    plugin_subparsers.add_parser('install', help='Install a plugin').add_argument('name', help='Plugin name')
    plugin_subparsers.add_parser('enable', help='Enable a plugin').add_argument('name', help='Plugin name')
    plugin_subparsers.add_parser('disable', help='Disable a plugin').add_argument('name', help='Plugin name')
    plugin_subparsers.add_parser('config', help='Configure a plugin').add_argument('name', help='Plugin name')
    plugin_subparsers.add_parser('status', help='Show plugin system status')

    # Existing commands  
    subparsers.add_parser('status', help='Show system status')
    subparsers.add_parser('fetch', help='Fetch latest articles')
    subparsers.add_parser('articles', help='Show recent articles')
    subparsers.add_parser('clear-db', help='Clear processed article status')

    # Briefing command
    briefing_parser = subparsers.add_parser('briefing', help='Generate AI news briefing')
    briefing_parser.add_argument('--style', choices=['comprehensive', 'quick', 'analytical'], 
                            default='comprehensive', help='Briefing style')
    briefing_parser.add_argument('--interactive', '-i', action='store_true',
                            help='Start interactive Q&A session after briefing')
    
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


    elif args.command == 'plugin':
        await handle_plugin_commands(args)


    elif args.command == 'clear-db':
        print("🧹 Clearing processed article status...")
        db = DatabaseManager()
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE articles SET processed = FALSE')
        conn.commit()
        conn.close()
        print("✅ All articles marked as unprocessed")



    elif args.command == 'briefing':
        # Get articles BEFORE generating briefing (so they're available for interactive)
        db = DatabaseManager()
        articles = db.get_recent_articles(hours=24, limit=30, unprocessed_only=True)
        
        if not articles:
            print("📰 No recent articles found. Try running fetch first.")
            if hasattr(args, 'interactive') and args.interactive:
                print("No articles available for interactive session.")
            return
        
        # Generate the briefing (this will mark articles as processed)
        await generate_briefing()
        
        # Then optionally start interactive mode using the SAME articles we got earlier
        if hasattr(args, 'interactive') and args.interactive:
            print("\n🎯 Starting interactive session...")
            print("💡 You can now ask follow-up questions about the news!")
            
            # Convert to dict format (using the articles we got BEFORE they were marked processed)
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
            
            # Initialize plugin manager
            config_manager = get_config_manager()
            plugin_manager = PluginManager(config_manager)
            plugin_manager.initialize()
            
            # Start interactive session with plugin support
            llm = OllamaProvider()
            session = InteractiveSession(article_dicts, llm, plugin_manager)
            await session.start()
        
    else:
        parser.print_help()


    

if __name__ == "__main__":
    asyncio.run(main())
