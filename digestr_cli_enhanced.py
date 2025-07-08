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
from digestr.config.manager import get_enhanced_config_manager as get_config_manager
from digestr.sources.source_manager import SourceManager
from digestr.core.strategic_prioritizer import enhance_article_prioritization

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

async def generate_tiered_briefing(self, tiered_articles: dict[str, list[dict]], 
                                 briefing_type: str = "comprehensive") -> str:
    """
    Generate a briefing using strategically tiered articles
    """
    if not any(tiered_articles.values()):
        return "No articles available for briefing."
    
    # Create tiered prompt
    prompt = self._create_tiered_prompt(tiered_articles, briefing_type)
    
    # Use the conversational model for better flow
    model = self.models.get("conversational", self.models["default"])
    
    logger.info(f"Generating tiered {briefing_type} briefing with {model}")
    
    # Generate the briefing
    briefing = await self.generate_summary(prompt, model)
    
    return briefing

def _create_tiered_prompt(self, tiered_articles: dict[str, list[dict]], 
                        briefing_type: str = "comprehensive") -> str:
    """
    Create a conversational prompt that handles tiered content strategically
    """
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Count articles and sources
    top_count = len(tiered_articles.get('top', []))
    mid_count = len(tiered_articles.get('mid', []))
    quick_count = len(tiered_articles.get('quick', []))
    total_count = top_count + mid_count + quick_count
    
    # Build content sections
    content_sections = self._build_content_sections(tiered_articles)
    
    # Conversational style configurations
    style_configs = {
        "comprehensive": {
            "greeting": "Good afternoon! I've been following the news and have quite a bit to catch you up on.",
            "approach": "Let's dive deep into what's really happening and why it matters.",
            "tone": "conversational but thorough"
        },
        "quick": {
            "greeting": "Hey there! Quick update on what's making headlines.",
            "approach": "I'll hit the highlights and key developments you should know about.",
            "tone": "brisk and efficient"
        },
        "analytical": {
            "greeting": "I've been analyzing today's developments and there are some interesting patterns emerging.",
            "approach": "Let me walk you through the implications and connections I'm seeing.",
            "tone": "thoughtful and insight-focused"
        }
    }
    
    style = style_configs.get(briefing_type, style_configs["comprehensive"])
    
    # Create the enhanced conversational prompt
    prompt = f"""You are my trusted news analyst and friend. It's {current_time}, and I'm catching up on what's been happening. {style['greeting']}

I've analyzed {total_count} articles from various sources and organized them by importance. {style['approach']}

{content_sections}

CONVERSATIONAL BRIEFING STYLE:
- Tone: {style['tone']}
- Flow: Natural conversation, not bullet points or formal sections
- Connection: Weave related stories together naturally
- Context: Explain why things matter, don't just report what happened
- Engagement: Keep it interesting and insightful

BRIEFING STRUCTURE:
1. Start with a warm, natural greeting that acknowledges the current time
2. Lead with the most significant developments from the TOP PRIORITY stories
3. Naturally flow into the NOTABLE DEVELOPMENTS, connecting related themes
4. Weave in QUICK MENTIONS of other interesting stories where relevant
5. Throughout, explain connections between stories and their broader significance
6. End with thoughtful insights about what these developments mean going forward

IMPORTANT GUIDELINES:
- Write in flowing paragraphs, not bullet points
- Connect stories across categories when they relate
- Use phrases like "Speaking of..." "This connects to..." "What's particularly interesting is..."
- Include specific details and examples to make it engaging
- Explain implications and why readers should care
- Maintain a conversational, friendly tone throughout
- Naturally mention source variety when relevant

Begin your conversational briefing now:"""

    return prompt

def _build_content_sections(self, tiered_articles: dict[str, list[dict]]) -> str:
    """
    Build organized content sections for the prompt
    """
    sections = []
    
    # Top Priority Stories (detailed treatment)
    top_articles = tiered_articles.get('top', [])
    if top_articles:
        sections.append("TOP PRIORITY STORIES (for detailed discussion):")
        for i, article in enumerate(top_articles[:15], 1):  # Limit to avoid overwhelming
            score = article.get('calculated_priority_score', 0)
            sections.append(f"\n{i}. **{article['title']}**")
            sections.append(f"   Source: {article.get('source', 'Unknown')} | Priority Score: {score:.1f}")
            
            # Use content if available, otherwise summary
            content = article.get('content') or article.get('summary', '')
            if len(content) > 400:
                content = content[:400] + "..."
            sections.append(f"   {content}")
            
            # Add category context
            category = article.get('category', 'unknown')
            sections.append(f"   Category: {category}")
    
    # Notable Developments (moderate treatment)
    mid_articles = tiered_articles.get('mid', [])
    if mid_articles:
        sections.append(f"\n\nNOTABLE DEVELOPMENTS (for moderate coverage):")
        for i, article in enumerate(mid_articles[:20], 1):  # Limit for brevity
            score = article.get('calculated_priority_score', 0)
            sections.append(f"\n{i}. **{article['title']}** ({article.get('source', 'Unknown')})")
            
            # Shorter content for mid-tier
            content = article.get('content') or article.get('summary', '')
            if len(content) > 200:
                content = content[:200] + "..."
            sections.append(f"   {content}")
    
    # Quick Mentions (brief treatment)
    quick_articles = tiered_articles.get('quick', [])
    if quick_articles:
        sections.append(f"\n\nQUICK MENTIONS (brief notes on other stories):")
        
        # Group quick mentions by category for better organization
        quick_by_category = {}
        for article in quick_articles[:25]:  # Limit to top 25 quick mentions
            category = article.get('category', 'other')
            if category not in quick_by_category:
                quick_by_category[category] = []
            quick_by_category[category].append(article)
        
        for category, cat_articles in quick_by_category.items():
            sections.append(f"\n{category.upper().replace('_', ' ')}:")
            for article in cat_articles[:8]:  # Max 8 per category
                sections.append(f"• {article['title']} ({article.get('source', 'Unknown')})")
    
    return "\n".join(sections)


async def handle_enhanced_briefing(args):
    """Handle enhanced briefing with professional/social options"""
    print(f"🐛 DEBUG: handle_enhanced_briefing called")
    print(f"🐛 DEBUG: args = {args}")
    # Determine briefing type
    professional_only = getattr(args, 'professional', False)
    social_only = getattr(args, 'social', False)
    

    print(f"🐛 DEBUG: professional_only = {professional_only}")
    print(f"🐛 DEBUG: social_only = {social_only}")


    if professional_only and social_only:
        print("❌ Cannot specify both --professional and --social")
        return
    
    if social_only:
        print("🎯 Generating social briefing from your personal Reddit feed...")
        
        # Test direct personal Reddit access
        import praw
        import os
        
        try:
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                refresh_token=os.getenv('REDDIT_REFRESH_TOKEN'),
                user_agent='Digestr.ai Personal Feed'
            )
            
            # Get personal feed posts
            home_posts = list(reddit.front.hot(limit=20))
            print(f"📱 Found {len(home_posts)} posts from your personal feed")
            
            # Convert to article format for LLM
            article_dicts = []
            for post in home_posts:
                article_dicts.append({
                    'title': post.title,
                    'summary': post.selftext or f"Post from r/{post.subreddit.display_name}",
                    'content': post.selftext or f"Shared in r/{post.subreddit.display_name} with {post.score} upvotes",
                    'source': f"r/{post.subreddit.display_name}",
                    'category': 'social',
                    'score': post.score,
                    'comments': post.num_comments,
                    'source_type': 'social'
                })
            
            # Create casual social prompt
            prompt = create_social_briefing_prompt(article_dicts)
            
            # Generate briefing
            llm = OllamaProvider()
            briefing = await llm.generate_summary(prompt)
            
            # Display social briefing
            print("\n" + "="*80)
            print("🎯 YOUR PERSONAL SOCIAL BRIEFING")
            print("="*80)
            print(briefing)
            print("\n" + "="*80)
            
        except Exception as e:
            print(f"❌ Error generating social briefing: {e}")
            print("💡 Make sure your Reddit credentials are set correctly")
            
    else:
        # Combined briefing (both professional and social)
        print("📊 Generating comprehensive briefing with both professional and social content...")
        
        # Professional content (existing logic)
        print("📰 Fetching professional news...")
        db = DatabaseManager()
        articles = db.get_recent_articles(hours=24, limit=25, unprocessed_only=True)
        
        if articles:
            print(f"📈 Found {len(articles)} professional articles")
            
            article_dicts = []
            for article in articles:
                article_dicts.append({
                    'title': article.title,
                    'summary': article.summary,
                    'content': article.content,
                    'source': article.source,
                    'category': article.category,
                    'importance_score': article.importance_score,
                    'source_type': 'professional'
                })
            
            # Generate professional section
            llm = OllamaProvider()
            professional_briefing = await llm.generate_briefing(article_dicts, briefing_type=args.style)
            
            print("\n" + "="*80)
            print("📋 YOUR COMPREHENSIVE DIGESTR.AI BRIEFING")
            print("="*80)
            print("## 📰 Professional News")
            print(professional_briefing)
            
            # Mark as processed
            article_urls = [article.url for article in articles]
            db.mark_articles_processed(article_urls)
        
        # Social content (your personal Reddit)
        print("\n🎯 Adding personal social content...")
        try:
            import praw
            import os
            
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                refresh_token=os.getenv('REDDIT_REFRESH_TOKEN'),
                user_agent='Digestr.ai Personal Feed'
            )
            
            home_posts = list(reddit.front.hot(limit=15))
            print(f"📱 Found {len(home_posts)} posts from personal feed")
            
            if home_posts:
                # Create social prompt and generate
                prompt = create_social_briefing_prompt([{
                    'title': post.title,
                    'source': f"r/{post.subreddit.display_name}",
                    'score': post.score,
                    'comments': post.num_comments,
                    'summary': post.selftext or f"Post from r/{post.subreddit.display_name}"
                } for post in home_posts])
                
                social_briefing = await llm.generate_summary(prompt)
                
                print("\n## 🎯 Personal Social Highlights")
                print(social_briefing)
            
        except Exception as e:
            print(f"⚠️ Could not fetch personal social content: {e}")
        
        print("\n" + "="*80)


def create_social_briefing_prompt(articles):
    """Create casual prompt for social content"""
    from datetime import datetime
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Group by subreddit
    subreddits = {}
    for article in articles:
        sub = article['source']
        if sub not in subreddits:
            subreddits[sub] = []
        subreddits[sub].append(article)
    
    content = ""
    for sub, posts in subreddits.items():
        content += f"\n**{sub}:**\n"
        for post in posts[:3]:  # Top 3 per subreddit
            score = post.get('score', 0)
            comments = post.get('comments', 0)
            content += f"• {post['title']} ({score} ⬆️, {comments} 💬)\n"
            if post.get('summary'):
                content += f"  {post['summary'][:150]}...\n"
    
    prompt = f"""Hey! Here's what's happening in your corner of Reddit today ({current_time}).

Your Personal Reddit Feed:
{content}

Give me a casual, friendly rundown of the interesting stuff from my personal Reddit feed. Keep it conversational and focus on what makes each post worth my attention. Don't just list things - tell me why they caught your eye and what makes them interesting or entertaining.

Use a friendly, casual tone like you're telling a friend about cool stuff you found online. Group related posts together and highlight the most engaging or surprising content.

Start with a warm greeting and give me the social media highlights:"""

    return prompt



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










async def enhanced_fetch_with_sources(source_types=None):
    """Enhanced fetch supporting multiple sources"""
    config_manager = get_config_manager()
    db_manager = DatabaseManager()
    
    # Initialize source manager
    source_manager = SourceManager(config_manager, db_manager)
    await source_manager.initialize_sources()
    
    if source_types:
        results = await source_manager.fetch_specific_sources(source_types)
    else:
        results = await source_manager.fetch_all_sources()
    
    total_articles = 0
    for source_type, articles in results.items():
        count = len(articles)
        total_articles += count
        source_icon = "🌐" if source_type == "rss" else "🔴" if source_type == "reddit" else "📡"
        print(f"  {source_icon} {source_type}: {count} articles")
    
    print(f"✅ Total: {total_articles} new articles fetched")
    return total_articles


async def sources_status_command():
    """Show source status"""
    config_manager = get_config_manager()
    db_manager = DatabaseManager()
    
    source_manager = SourceManager(config_manager, db_manager)
    await source_manager.initialize_sources()
    
    sources = source_manager.get_available_sources()
    status = source_manager.get_source_status()
    
    print(f"📡 Available Content Sources ({len(sources)}):")
    for source in sources:
        info = status[source]
        status_icon = "✅" if info['validated'] else "❌"
        type_icon = "🌐" if source == "rss" else "🔴" if source == "reddit" else "📡"
        print(f"  {status_icon} {type_icon} {source.upper()}: {'Connected' if info['validated'] else 'Failed'}")






def create_multi_source_briefing_prompt(articles):
    """Create enhanced prompt that highlights Reddit sentiment data"""
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Separate Reddit and RSS articles
    reddit_articles = [a for a in articles if a['source_type'] == 'reddit']
    rss_articles = [a for a in articles if a['source_type'] == 'rss']
    
    prompt = f"""You are an expert news analyst providing a comprehensive briefing. Current time: {current_time}

MULTI-SOURCE INTELLIGENCE BRIEF:

RSS NEWS SOURCES ({len(rss_articles)} articles):
"""
    
    # Add RSS articles
    for article in rss_articles[:15]:  # Limit for prompt size
        prompt += f"\n• **{article['title']}** ({article['source']})\n"
        prompt += f"  {article['summary'][:200]}...\n"
    
    if reddit_articles:
        prompt += f"\nREDDIT COMMUNITY DISCUSSIONS ({len(reddit_articles)} articles with sentiment analysis):\n"
        
        # Add Reddit articles with sentiment highlighting
        for article in reddit_articles[:10]:  # Limit for prompt size
            prompt += f"\n• **{article['title']}** ({article['source']})\n"
            prompt += f"  {article['summary']}\n"
            
            # Highlight if this article has sentiment analysis
            if 'community sentiment' in article['summary'].lower():
                prompt += f"  📊 Community reaction analyzed from Reddit discussions\n"
    
    prompt += f"""

BRIEFING INSTRUCTIONS:
- Provide a comprehensive analysis that synthesizes information from both traditional news sources and community discussions
- When Reddit sentiment data is available, incorporate community perspectives and reactions
- Highlight any notable differences between official reporting and community sentiment
- Use phrases like "Reddit users are expressing..." or "Community reaction shows..." when referencing sentiment data
- Connect related stories across different sources
- Maintain a professional yet conversational tone

Generate your comprehensive briefing:"""
    
    return prompt



async def main():


    
    parser = argparse.ArgumentParser(description="Digestr.ai v2.1 - Multi-Source News Intelligence Platform")


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
    subparsers.add_parser('articles', help='Show recent articles')
    subparsers.add_parser('clear-db', help='Clear processed article status')




    fetch_parser = subparsers.add_parser('fetch', help='Fetch latest articles')
    fetch_parser.add_argument('--sources', nargs='+', 
                             choices=['rss', 'reddit'],
                             help='Specific sources to fetch from (default: all enabled)')
    # Briefing command
    briefing_parser = subparsers.add_parser('briefing', help='Generate AI news briefing')
    briefing_parser.add_argument('--style', choices=['comprehensive', 'quick', 'analytical'], 
                                default='comprehensive', help='Briefing style')
    briefing_parser.add_argument('--interactive', '-i', action='store_true',
                                help='Start interactive Q&A session after briefing')
    briefing_parser.add_argument('--sources', nargs='+',
                                choices=['rss', 'reddit'],
                                help='Include specific sources in briefing')
    briefing_parser.add_argument('--professional', action='store_true',
                            help='Professional briefing only (news sources)')
    briefing_parser.add_argument('--social', action='store_true',
                                help='Social briefing only (personal feeds)')
    briefing_parser.add_argument('--categories', nargs='+',
                                help='Filter by specific categories')

    sources_parser = subparsers.add_parser('sources', help='Manage content sources')
    sources_subparsers = sources_parser.add_subparsers(dest='sources_command', help='Source commands')
    sources_subparsers.add_parser('status', help='Show source status and connections')
    sources_subparsers.add_parser('list', help='List available sources')

    args = parser.parse_args()
    

    



    if args.command == 'status':
        print("🔍 Digestr.ai System Status")
        print("✅ Version: 2.0.0")
        print("✅ Database: Ready")
        print("✅ Ollama: Ready (assumed)")
        print("🎯 Ready for news intelligence!")
        
    elif args.command == 'fetch':
        if hasattr(args, 'sources') and args.sources:
            await enhanced_fetch_with_sources(args.sources)
        else:
            # Use existing fetch or enhanced fetch
            await enhanced_fetch_with_sources()
        
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
        await handle_enhanced_briefing(args)
        
        # Filter by source type if specified
        if hasattr(args, 'sources') and args.sources:
            filtered_articles = []
            for article in articles:
                article_source = 'reddit' if article.title.startswith('[Reddit]') else 'rss'
                if article_source in args.sources:
                    filtered_articles.append(article)
            articles = filtered_articles
        
        if not articles:
            print("📰 No recent articles found. Try running fetch first.")
            return
        
        print(f"📈 Analyzing {len(articles)} articles for briefing")
        
        # Show source breakdown
        reddit_count = len([a for a in articles if a.title.startswith('[Reddit]')])
        rss_count = len(articles) - reddit_count
        if reddit_count > 0:
            print(f"  🔴 Reddit: {reddit_count} articles (with sentiment analysis)")
        if rss_count > 0:
            print(f"  🌐 RSS: {rss_count} articles")
        
        # Convert to format expected by LLM (PRESERVE Reddit sentiment and source info)
        article_dicts = []
        for article in articles:
            # Determine source type and preserve Reddit source info
            if article.title.startswith('[Reddit]'):
                source_type = 'reddit'
                # Keep the r/subreddit source info
                clean_title = article.title.replace('[Reddit] ', '')
            else:
                source_type = 'rss'
                clean_title = article.title
            
            article_dicts.append({
                'title': clean_title,  # Clean title for LLM
                'summary': article.summary,  # This includes sentiment info for Reddit
                'content': article.content,  # This includes full sentiment analysis for Reddit
                'url': article.url,
                'category': article.category,
                'source': article.source,  # This preserves r/subreddit info
                'published_date': article.published_date,
                'importance_score': article.importance_score,
                'source_type': source_type,  # Add source type for LLM context
                'original_title': article.title  # Keep original for reference
            })
        
        # Generate AI briefing with enhanced prompt
        print("🤖 Generating enhanced multi-source briefing...")
        try:
            llm = OllamaProvider()
            
            # Create enhanced prompt that tells LLM about Reddit sentiment
            briefing_prompt = create_multi_source_briefing_prompt(article_dicts)
            briefing = await llm.generate_summary(briefing_prompt)
            
            # Display briefing
            print("\n" + "="*80)
            print("📋 YOUR MULTI-SOURCE DIGESTR.AI BRIEFING")
            print("="*80)
            print(briefing)
            print("\n" + "="*80)
            
            # Mark articles as processed
            article_urls = [article.url for article in articles]
            db.mark_articles_processed(article_urls)
            
        except Exception as e:
            print(f"❌ Error generating briefing: {e}")
            print("💡 Make sure Ollama is running and accessible")
        
        # Interactive mode handling (existing code)
        if hasattr(args, 'interactive') and args.interactive:
            print("\n🎯 Starting interactive session...")
            
            # Get articles for interactive session
            db = DatabaseManager()
            articles = db.get_recent_articles(hours=24, limit=50, unprocessed_only=False)
            
            if not articles:
                print("📰 No articles available for interactive session.")
                return
            
            # Convert to dict format
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
            
            # Start interactive session
            llm = OllamaProvider()
            session = InteractiveSession(article_dicts, llm, plugin_manager)
            await session.start()



    elif args.command == 'sources':
        if args.sources_command == 'status':
            await sources_status_command()
        elif args.sources_command == 'list':
            config_manager = get_config_manager()
            db_manager = DatabaseManager()
            source_manager = SourceManager(config_manager, db_manager)
            await source_manager.initialize_sources()
            
            sources = source_manager.get_available_sources()
            print(f"📡 Available sources: {', '.join(sources)}")

        
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
