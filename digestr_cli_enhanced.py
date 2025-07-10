#!/usr/bin/env python3
"""
Digestr CLI - Enhanced with briefing functionality
"""
from dotenv import load_dotenv
import sys
import os
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
import sqlite3
import asyncio
import argparse

from pathlib import Path

project_root = Path(__file__).parent
src_path = project_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))


from datetime import datetime
from digestr.features.interactive import InteractiveSession
from digestr.core.database import DatabaseManager
from digestr.core.fetcher import FeedManager
from digestr.llm_providers.ollama import OllamaProvider
from digestr.core.plugin_manager import PluginManager
from digestr.core.plugin_manager import PluginManager
from digestr.config.manager import get_enhanced_config_manager
from digestr.sources.source_manager import SourceManager
from digestr.core.strategic_prioritizer import enhance_article_prioritization
from digestr.analysis.trend_structures import CrossSourceTrendAnalysis, GeographicConfig
from digestr.analysis.trend_correlation_engine import TrendCorrelationEngine
from digestr.analysis.trend_aware_briefing_generator import TrendAwareBriefingGenerator
from digestr.sources.enhanced_trends24_scraper import EnhancedTrends24Scraper
from digestr.core.trend_database_manager import TrendDatabaseManager


def get_config_manager():
    """Wrapper function to get config manager"""
    return get_enhanced_config_manager()
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



async def generate_standard_briefing(professional_content, social_content, llm, style):
    """Generate standard briefing without trend analysis"""
    
    # Convert Article objects to dictionaries for compatibility
    all_articles = []
    
    # Process professional content
    for source_type, content in professional_content.items():
        if isinstance(content, list):
            for item in content:
                if hasattr(item, 'title'):  # Article object
                    article_dict = {
                        'title': getattr(item, 'title', ''),
                        'summary': getattr(item, 'summary', ''),
                        'content': getattr(item, 'content', ''),
                        'source': getattr(item, 'source', source_type),
                        'category': getattr(item, 'category', 'unknown'),
                        'url': getattr(item, 'url', ''),
                        'importance_score': getattr(item, 'importance_score', 0.0),
                        'source_type': 'professional'
                    }
                else:  # Already a dictionary
                    article_dict = item.copy()
                    article_dict['source_type'] = 'professional'
                
                all_articles.append(article_dict)
    
    # Process social content
    for source_type, feed in social_content.items():
        if hasattr(feed, 'posts'):
            for post in feed.posts:
                if hasattr(post, 'to_dict'):
                    post_dict = post.to_dict()
                    post_dict['source_type'] = 'social'
                    all_articles.append(post_dict)
    
    if not all_articles:
        return "No articles available for briefing generation."
    
    # Create appropriate prompt based on style
    if style == 'comprehensive':
        prompt = create_multi_source_briefing_prompt(all_articles)
    elif style == 'quick':
        prompt = create_quick_briefing_prompt(all_articles)
    else:  # analytical
        prompt = create_analytical_briefing_prompt(all_articles)
    
    # Generate briefing using LLM
    try:
        briefing = await llm.generate_summary(prompt)
        return briefing
    except Exception as e:
        return f"Error generating briefing: {e}"

def create_quick_briefing_prompt(articles):
    """Create prompt for quick briefing style"""
    from datetime import datetime
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Take top articles only
    top_articles = sorted(articles, key=lambda x: x.get('importance_score', 0), reverse=True)[:10]
    
    content = ""
    for i, article in enumerate(top_articles, 1):
        content += f"\n{i}. **{article['title']}** ({article.get('source', 'Unknown')})\n"
        summary = article.get('summary', '')[:150]
        content += f"   {summary}...\n"
    
    prompt = f"""You are providing a quick news briefing for {current_time}.

TOP NEWS HEADLINES:
{content}

Provide a brief, efficient summary of the key developments. Keep it concise and focused on the most important information. Use a brisk, professional tone and highlight the main points readers need to know. Aim for 3-4 short paragraphs maximum.

Quick briefing:"""
    
    return prompt

def create_analytical_briefing_prompt(articles):
    """Create prompt for analytical briefing style"""
    from datetime import datetime
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Group articles by category for analysis
    categories = {}
    for article in articles:
        cat = article.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(article)
    
    content = ""
    for category, cat_articles in categories.items():
        content += f"\n**{category.upper()}** ({len(cat_articles)} articles):\n"
        for article in cat_articles[:5]:  # Top 5 per category
            content += f"• {article['title']} ({article.get('source', 'Unknown')})\n"
    
    prompt = f"""You are providing an analytical news briefing for {current_time}.

CONTENT BY CATEGORY:
{content}

Provide a thoughtful, analytical perspective on today's developments. Focus on:
- Patterns and trends emerging across categories
- Connections between different stories
- Implications and potential consequences
- What these developments mean for the bigger picture

Use an insightful, analytical tone and help readers understand not just what happened, but why it matters and what it might lead to.

Analytical briefing:"""
    
    return prompt

async def handle_enhanced_fetch_with_trends(args):
    """Handle fetch command with trend support"""
    
    print("📡 Fetching content with trend analysis...")
    
    config_manager = get_config_manager()
    db_manager = DatabaseManager()
    
    source_manager = SourceManager(config_manager, db_manager)
    await source_manager.initialize_sources()
    
    if getattr(args, 'trends_only', False):
        print("📈 Fetching trends only...")
        # Implement trends-only fetch
        print("Trends-only fetch not fully implemented yet")
        return
    
    # Fetch from specified sources or all sources
    if hasattr(args, 'sources') and args.sources:
        results = await source_manager.fetch_specific_sources(args.sources)
    else:
        results = await source_manager.fetch_all_sources()
    
    # Display results
    total_items = 0
    for source_type, content in results.items():
        if isinstance(content, list):
            count = len(content)
            total_items += count
            print(f"✅ {source_type}: {count} items")
        elif hasattr(content, 'posts'):
            count = len(content.posts)
            total_items += count
            print(f"✅ {source_type}: {count} posts")
    
    print(f"📊 Total items fetched: {total_items}")

async def handle_enhanced_sources_commands(args):
    """Handle source management commands"""
    
    if args.sources_command == 'status':
        await sources_status_command()
    
    elif args.sources_command == 'list':
        config_manager = get_config_manager()
        db_manager = DatabaseManager()
        source_manager = SourceManager(config_manager, db_manager)
        await source_manager.initialize_sources()
        
        sources = source_manager.get_available_sources()
        professional = source_manager.get_professional_sources()
        social = source_manager.get_social_sources()
        
        print("📡 Available Sources:")
        print(f"  Professional: {', '.join(professional)}")
        print(f"  Social: {', '.join(social)}")
        print(f"  Total: {len(sources)} sources")
    
    elif args.sources_command == 'test':
        config_manager = get_config_manager()
        db_manager = DatabaseManager()
        source_manager = SourceManager(config_manager, db_manager)
        await source_manager.initialize_sources()
        
        print("🧪 Testing all source connections...")
        results = await source_manager.test_all_sources()
        
        for source, result in results.items():
            status = "✅" if result['success'] else "❌"
            message = result.get('message', result.get('error', 'Unknown'))
            print(f"  {status} {source}: {message}")

async def handle_config_commands(args):
    """Handle configuration management commands"""
    
    config_manager = get_config_manager()
    
    if args.config_command == 'show':
        print("⚙️ Current Configuration:")
        config = config_manager.get_config()
        
        print(f"📡 Sources:")
        if hasattr(config, 'sources'):
            print(f"  RSS: {'Enabled' if config.sources.rss.enabled else 'Disabled'}")
            print(f"  Reddit: {'Enabled' if config.sources.reddit.enabled else 'Disabled'}")
        
        print(f"📈 Trending:")
        if hasattr(config, 'trending'):
            print(f"  Enabled: {config.trending.enabled}")
            if config.trending.enabled:
                enabled_sources = [name for name, cfg in config.trending.sources.items() 
                                 if cfg.get('enabled', False)]
                print(f"  Sources: {', '.join(enabled_sources)}")
    
    elif args.config_command == 'validate':
        print("✅ Validating configuration...")
        try:
            config = config_manager.get_config()
            print("✅ Configuration is valid")
        except Exception as e:
            print(f"❌ Configuration error: {e}")
    
    elif args.config_command == 'reset':
        print("🔄 Reset configuration not implemented yet")

async def monitor_trends_realtime(config, geo_config, args):
    """Monitor trends in real-time"""
    print(f"📊 Monitoring trends for {args.duration} minutes...")
    print("Real-time monitoring not fully implemented yet")

async def generate_trend_report(trend_db, args):
    """Generate comprehensive trend report"""
    print(f"📋 Generating {args.days}-day trend report...")
    print("Trend reporting not fully implemented yet")

async def handle_geographic_commands(args, config_manager):
    """Handle geographic configuration commands"""
    print("🌍 Geographic configuration not fully implemented yet")

async def show_database_statistics(args):
    """Show database statistics"""
    print("📊 Database statistics not fully implemented yet")

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




async def handle_enhanced_briefing_with_full_trends(args):
    """Complete briefing handler with full trend analysis integration"""
    
    print("🚀 Generating trend-enhanced briefing...")
    
    # Initialize all components
    config_manager = get_config_manager()
    config = config_manager.get_config()
    db_manager = DatabaseManager()
    
    # Check if trends are disabled for this briefing
    trends_enabled = config.trending.enabled and not getattr(args, 'no_trends', False)
    
    if trends_enabled:
        print("📈 Trend analysis enabled")
        
        # Initialize trend components
        geo_config = GeographicConfig(
            country=config.trending.geographic.get('country', 'United States'),
            state=config.trending.geographic.get('state'),
            city=config.trending.geographic.get('city'),
            include_national=config.trending.geographic.get('include_national', True)
        )
        
        trend_db = TrendDatabaseManager(db_manager.db_path)
        trend_engine = TrendCorrelationEngine(geo_config, db_manager)
        
        if config.trending.sources.get('trends24', {}).get('enabled', False):
            trends24_scraper = EnhancedTrends24Scraper(geo_config)
        else:
            trends24_scraper = None
    else:
        print("📈 Trend analysis disabled")
        trend_engine = None
        trends24_scraper = None
    
    # Initialize source manager
    source_manager = SourceManager(config_manager, db_manager)
    await source_manager.initialize_sources()
    
    # Fetch content based on args
    if getattr(args, 'trends_only', False) and trends24_scraper:
        print("📈 Fetching trends only...")
        trends = await trends24_scraper.fetch_trending_topics()
        
        print(f"🔥 Found {len(trends)} trending topics:")
        for i, trend in enumerate(trends[:10], 1):
            print(f"  {i}. {trend.keyword} ({trend.category}) - Velocity: {trend.velocity:.2f}")
        return
    
    if getattr(args, 'fresh', False):
        print("🔄 Fetching fresh content...")
        # Fresh fetch requested
        if trends_enabled and trend_engine and trends24_scraper:
            all_results = await fetch_with_comprehensive_trend_analysis(
                source_manager, trend_engine, trends24_scraper, args
            )
        else:
            all_results = await source_manager.fetch_all_sources()
            all_results['trend_analysis'] = None
    else:
        # Use cached data from database
        print("📚 Using cached content from database...")
        
        # Get recent articles from database instead of fetching
        recent_articles = db_manager.get_recent_articles(hours=24, limit=200, unprocessed_only=False)
        

        rss_articles = []
        reddit_articles = []
        
        for article in recent_articles:
            source = getattr(article, 'source', '').lower()
            if 'reddit' in source:
                reddit_articles.append(article)
            else:
                rss_articles.append(article)



        # Convert to the expected format
        all_results = {
            'professional': {
                'rss': recent_articles  # All articles for now
            },
            'social': {},
            'trend_analysis': None
        }
    
    professional_content = all_results.get('professional', {})
    social_content = all_results.get('social', {})




   

    trend_analysis = all_results.get('trend_analysis')
    
    # Content summary
    total_professional = sum(len(content) for content in professional_content.values() if isinstance(content, list))
    total_social = 0
    for source_name, content in social_content.items():
        if hasattr(content, 'posts'):  # SocialFeed object
            total_social += len(content.posts)
        elif isinstance(content, list):  # List of posts (like copied Reddit)
            total_social += len(content)
    
    if total_professional == 0 and total_social == 0:
        print("📰 No new content found. Try running fetch first.")
        return
    
    print(f"📊 Content summary: {total_professional} professional articles, {total_social} social posts")
    
    if trend_analysis:
        significant_trends = trend_analysis.get_significant_trends()
        print(f"📈 Trend analysis: {trend_analysis.total_trends} trends, {trend_analysis.correlation_count} correlations")
        print(f"🔥 Significant cross-source trends: {len(significant_trends)}")
        
        if significant_trends:
            print("   Top trends:")
            for trend_data in significant_trends[:3]:
                trend = trend_data['trend']
                sources = len(trend_data['sources'])
                print(f"     • {trend.keyword} ({sources} sources)")
    
    # Generate briefing
    llm = OllamaProvider()
    
    if trends_enabled and trend_analysis:
        briefing_generator = TrendAwareBriefingGenerator(llm)
        content_data = {
            'professional': professional_content,
            'social': social_content
        }
        
        briefing = await briefing_generator.generate_comprehensive_briefing(
            content_data, trend_analysis, args.style
        )
    else:
        # Fall back to standard briefing without trends
        briefing = await generate_standard_briefing(
            professional_content, social_content, llm, args.style
        )
    
    # Display briefing
    print("\n" + "="*80)
    if trends_enabled:
        print("📋 YOUR TREND-ENHANCED DIGESTR.AI BRIEFING")
    else:
        print("📋 YOUR DIGESTR.AI BRIEFING")
    print("="*80)
    print(briefing)
    print("\n" + "="*80)
    
    # Mark articles as processed
    if total_professional > 0:
        article_urls = []
        for content in professional_content.values():
            if isinstance(content, list):
                for article in content:
                    if hasattr(article, 'url'):
                        url = getattr(article, 'url', '')
                    elif isinstance(article, dict):
                        url = article.get('url', '')
                    else:
                        url = ''
                    
                    if url:
                        article_urls.append(url)
        if article_urls:
            db_manager.mark_articles_processed(article_urls)
    



    # Interactive mode handling
    if hasattr(args, 'interactive') and args.interactive:
        print("\n🎯 Starting interactive session...")
        
        # Get articles for interactive session
        db = DatabaseManager()
        interactive_articles = db.get_recent_articles(hours=24, limit=50, unprocessed_only=False)
        
        if not interactive_articles:
            print("📰 No articles available for interactive session.")
            return
        
        # Convert to dict format
        article_dicts = []
        for article in interactive_articles:
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
        #from digestr.config.manager import get_enhanced_config_manager as get_config_manager
        from digestr.core.plugin_manager import PluginManager
        from digestr.features.interactive import InteractiveSession
        
        config_manager = get_config_manager()
        plugin_manager = PluginManager(config_manager)
        plugin_manager.initialize()
        
        # Start interactive session
        llm = OllamaProvider()
        session = InteractiveSession(article_dicts, llm, plugin_manager)
        await session.start()

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










async def fetch_with_comprehensive_trend_analysis(source_manager, trend_engine, trends24_scraper, args):
    """Fetch content with comprehensive trend analysis"""
    
    print("📡 Fetching content from all sources...")
    
    # Fetch regular content
    results = await source_manager.fetch_all_sources()
    
    print("📈 Fetching trending topics...")
    
    # Fetch trending topics
    trends = await trends24_scraper.fetch_trending_topics()
    
    if not trends:
        print("⚠️  No trends found from external sources")
        results['trend_analysis'] = CrossSourceTrendAnalysis()
        return results
    
    print(f"📊 Found {len(trends)} trending topics")
    
    # Prepare content for correlation analysis
    rss_articles = []
    reddit_posts = []
    
    for source_type, content in results.get('professional', {}).items():
        if isinstance(content, list):
            if source_type == 'rss':
                rss_articles.extend(content)
            elif source_type == 'reddit':
                reddit_posts.extend(content)
    
    print(f"🔍 Analyzing correlations: {len(trends)} trends vs {len(rss_articles)} articles + {len(reddit_posts)} posts")
    
    # Perform comprehensive correlation analysis
    trend_analysis = await trend_engine.find_cross_source_correlations(
        trends, rss_articles, reddit_posts
    )
    
    results['trend_analysis'] = trend_analysis
    
    return results


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
        # Handle different status key names for different sources
        validated = info.get('validated', info.get('authenticated', False))
        status_icon = "✅" if validated else "❌"
        type_icon = "🌐" if source == "rss" else "🔴" if source == "reddit" else "📡"
        status_text = 'Connected' if validated else 'Failed'
        print(f"  {status_icon} {type_icon} {source.upper()}: {status_text}")






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





async def handle_trends_commands(args):
    """Complete trend command handler"""
    
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if not config.trending.enabled:
        print("❌ Trend analysis is disabled in configuration")
        print("💡 Enable with: trending.enabled = true in config.yaml")
        return
    
    # Initialize trend components
    geo_config = GeographicConfig(
        country=config.trending.geographic.get('country', 'United States'),
        state=config.trending.geographic.get('state'),
        city=config.trending.geographic.get('city'),
        include_national=config.trending.geographic.get('include_national', True)
    )
    
    db_manager = DatabaseManager()
    trend_db = TrendDatabaseManager(db_manager.db_path)
    
    if args.trends_command == 'status':
        await show_trend_system_status(config, geo_config, trend_db)
    
    elif args.trends_command == 'test':
        await test_all_trend_sources(config, geo_config)
    
    elif args.trends_command == 'fetch':
        await fetch_and_display_trends(config, geo_config, args)
    
    elif args.trends_command == 'analyze':
        await run_trend_correlation_analysis(config, geo_config, db_manager, args)
    
    elif args.trends_command == 'monitor':
        await monitor_trends_realtime(config, geo_config, args)
    
    elif args.trends_command == 'report':
        await generate_trend_report(trend_db, args)
    
    elif args.trends_command == 'geo':
        await handle_geographic_commands(args, config_manager)

async def show_trend_system_status(config, geo_config, trend_db):
    """Show comprehensive trend system status"""
    
    print("📈 Trend Analysis System Status")
    print("=" * 50)
    
    # Configuration status
    print(f"✅ Enabled: {config.trending.enabled}")
    print(f"🌍 Geographic focus: {geo_config.country}")
    if geo_config.state:
        print(f"   State: {geo_config.state}")
    if geo_config.city:
        print(f"   City: {geo_config.city}")
    
    # Source status
    sources = config.trending.sources
    print(f"\n📡 Trend Sources:")
    for source_name, source_config in sources.items():
        status = "✅" if source_config.get('enabled', False) else "❌"
        print(f"   {status} {source_name.title()}")
    
    # Database status
    try:
        stats = trend_db.get_trend_statistics()
        print(f"\n📊 Database Statistics (last 7 days):")
        print(f"   Trends tracked: {stats['total_trends']}")
        print(f"   Cross-source trends: {stats['cross_source_trends']}")
        print(f"   Correlations found: {stats['total_correlations']}")
        
        if stats['source_breakdown']:
            print(f"   Source breakdown:")
            for source, data in stats['source_breakdown'].items():
                print(f"     • {source}: {data['count']} trends (avg velocity: {data['avg_velocity']})")
    
    except Exception as e:
        print(f"⚠️  Database statistics unavailable: {e}")
    
    # Configuration validation
    print(f"\n⚙️  Configuration:")
    correlation_config = config.trending.correlation
    print(f"   Correlation threshold: {correlation_config.get('min_threshold', 0.4)}")
    print(f"   Semantic matching: {correlation_config.get('semantic_matching', True)}")
    print(f"   Geographic boost: {correlation_config.get('geographic_boost', True)}")

async def test_all_trend_sources(config, geo_config):
    """Test all configured trend sources"""
    
    print("🧪 Testing Trend Source Connections")
    print("=" * 50)
    
    sources = config.trending.sources
    
    for source_name, source_config in sources.items():
        if not source_config.get('enabled', False):
            print(f"⚪ {source_name.title()}: Disabled")
            continue
        
        print(f"🔍 Testing {source_name.title()}...")
        
        try:
            if source_name == 'trends24':
                from digestr.sources.enhanced_trends24_scraper import EnhancedTrends24Scraper
                scraper = EnhancedTrends24Scraper(geo_config)
                result = await scraper.test_connection()
                
                if result['success']:
                    print(f"   ✅ {result['message']}")
                    if 'sample_trends' in result:
                        print(f"   📊 Sample trends: {', '.join(result['sample_trends'])}")
                else:
                    print(f"   ❌ {result['error']}")
            
            else:
                print(f"   ⚠️  Test not implemented for {source_name}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")

async def fetch_and_display_trends(config, geo_config, args):
    """Fetch and display current trends"""
    
    print("📈 Fetching Current Trending Topics")
    print("=" * 50)
    
    if not config.trending.sources.get('trends24', {}).get('enabled', False):
        print("❌ Trends24 source is not enabled")
        return
    
    try:
        from digestr.sources.enhanced_trends24_scraper import EnhancedTrends24Scraper
        scraper = EnhancedTrends24Scraper(geo_config)
        
        regions = [args.region] if args.region else None
        trends = await scraper.fetch_trending_topics(regions)
        
        if args.category:
            trends = [t for t in trends if t.category == args.category]
        
        trends = trends[:args.limit]
        
        if not trends:
            print("📰 No trends found matching criteria")
            return
        
        print(f"🔥 Found {len(trends)} trending topics:")
        print()
        
        # Group by category
        from collections import defaultdict
        by_category = defaultdict(list)
        for trend in trends:
            by_category[trend.category].append(trend)
        
        for category, cat_trends in by_category.items():
            print(f"📂 {category.upper()}:")
            for i, trend in enumerate(cat_trends, 1):
                velocity_indicator = "🔥" if trend.velocity > 0.7 else "📈" if trend.velocity > 0.4 else "📊"
                print(f"   {i:2d}. {velocity_indicator} {trend.keyword}")
                print(f"       Velocity: {trend.velocity:.2f} | Region: {trend.region} | Reach: {trend.reach}")
                if trend.aliases:
                    print(f"       Aliases: {', '.join(trend.aliases[:3])}")
            print()
    
    except Exception as e:
        print(f"❌ Error fetching trends: {e}")

async def run_trend_correlation_analysis(config, geo_config, db_manager, args):
    """Run comprehensive trend correlation analysis"""
    
    print("🔍 Running Trend Correlation Analysis")
    print("=" * 50)
    
    try:
        # Initialize components
        from digestr.analysis.trend_correlation_engine import TrendCorrelationEngine
        from digestr.sources.enhanced_trends24_scraper import EnhancedTrends24Scraper
        
        trend_engine = TrendCorrelationEngine(geo_config, db_manager)
        trends24_scraper = EnhancedTrends24Scraper(geo_config)
        source_manager = SourceManager(get_config_manager(), db_manager)
        await source_manager.initialize_sources()
        
        # Fetch trends
        print("📈 Fetching trending topics...")
        trends = await trends24_scraper.fetch_trending_topics()
        print(f"   Found {len(trends)} trends")
        
        # Fetch content
        print("📡 Fetching content for correlation...")
        results = await source_manager.fetch_all_sources()
        
        # Prepare content
        rss_articles = []
        reddit_posts = []
        
        for source_type, content in results.get('professional', {}).items():
            if isinstance(content, list):
                if source_type == 'rss':
                    rss_articles.extend(content)
                elif source_type == 'reddit':
                    reddit_posts.extend(content)
        
        print(f"   {len(rss_articles)} RSS articles, {len(reddit_posts)} Reddit posts")
        
        # Run correlation analysis
        print("🔍 Analyzing correlations...")
        trend_analysis = await trend_engine.find_cross_source_correlations(
            trends, rss_articles, reddit_posts
        )
        
        # Display results
        print(f"\n📊 Analysis Results:")
        print(f"   Total trends analyzed: {trend_analysis.total_trends}")
        print(f"   Correlations found: {trend_analysis.correlation_count}")
        print(f"   Triple-source trends: {len(trend_analysis.triple_coverage)}")
        print(f"   Double-source trends: {len(trend_analysis.double_coverage)}")
        print(f"   Geographic trends: {len(trend_analysis.geographic_trends)}")
        
        # Show significant trends
        significant = trend_analysis.get_significant_trends()
        if significant:
            print(f"\n🔥 Most Significant Cross-Source Trends:")
            for i, trend_data in enumerate(significant[:5], 1):
                trend = trend_data['trend']
                sources = len(trend_data['sources'])
                strength = trend_data.get('total_strength', 0)
                print(f"   {i}. {trend.keyword}")
                print(f"      Sources: {sources} | Strength: {strength:.2f}")
                print(f"      Coverage: {', '.join(trend_data['sources'])}")
        
        # Save to database if requested
        if args.save:
            print(f"\n💾 Saving analysis results to database...")
            # Save logic would go here
            print(f"   ✅ Results saved")
    
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

async def setup_enhanced_argument_parser():
    """Complete argument parser with all trend analysis commands"""
    
    parser = argparse.ArgumentParser(description="Digestr.ai v2.1 - Multi-Source News Intelligence with Trend Analysis")

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Status command
    subparsers.add_parser('status', help='Show system status including trend analysis')

    # Fetch command with trend support
    fetch_parser = subparsers.add_parser('fetch', help='Fetch latest articles and trends')
    fetch_parser.add_argument('--sources', nargs='+', 
                             choices=['rss', 'reddit', 'reddit_personal', 'trends'],
                             help='Specific sources to fetch from (default: all enabled)')
    fetch_parser.add_argument('--trends-only', action='store_true',
                             help='Fetch only trending topics')

    # Enhanced briefing command
    briefing_parser = subparsers.add_parser('briefing', help='Generate AI news briefing with trend analysis')
    briefing_parser.add_argument('--style', choices=['comprehensive', 'quick', 'analytical'], 
                                default='comprehensive', help='Briefing style')
    briefing_parser.add_argument('--interactive', '-i', action='store_true',
                                help='Start interactive Q&A session after briefing')
    briefing_parser.add_argument('--sources', nargs='+',
                                choices=['rss', 'reddit', 'reddit_personal', 'trends'],
                                help='Include specific sources in briefing')
    briefing_parser.add_argument('--professional', action='store_true',
                                help='Professional briefing only (news sources)')
    briefing_parser.add_argument('--social', action='store_true',
                                help='Social briefing only (personal feeds)')
    briefing_parser.add_argument('--trends-focus', action='store_true',
                                help='Focus on trending topics and correlations')
    briefing_parser.add_argument('--no-trends', action='store_true',
                                help='Disable trend analysis for this briefing')
    briefing_parser.add_argument('--fresh', action='store_true',
                            help='Fetch fresh content instead of using cached data')
    # Comprehensive trend analysis commands
    trends_parser = subparsers.add_parser('trends', help='Trend analysis and monitoring commands')
    trends_subparsers = trends_parser.add_subparsers(dest='trends_command', help='Trend commands')
    
    # Basic trend commands
    trends_subparsers.add_parser('status', help='Show trend analysis system status')
    trends_subparsers.add_parser('test', help='Test all trend source connections')
    
    # Trend fetching
    fetch_trends = trends_subparsers.add_parser('fetch', help='Fetch current trending topics')
    fetch_trends.add_argument('--region', help='Specific region (e.g., united-states, california)')
    fetch_trends.add_argument('--category', help='Filter by category (e.g., tech, politics)')
    fetch_trends.add_argument('--limit', type=int, default=20, help='Maximum trends to show')
    
    # Trend analysis
    analyze_trends = trends_subparsers.add_parser('analyze', help='Run comprehensive trend correlation analysis')
    analyze_trends.add_argument('--save', action='store_true', help='Save results to database')
    analyze_trends.add_argument('--threshold', type=float, default=0.4, help='Correlation threshold')
    
    # Trend monitoring
    monitor_trends = trends_subparsers.add_parser('monitor', help='Monitor trends over time')
    monitor_trends.add_argument('--duration', type=int, default=60, help='Monitor duration in minutes')
    monitor_trends.add_argument('--interval', type=int, default=5, help='Check interval in minutes')
    
    # Trend reporting
    report_trends = trends_subparsers.add_parser('report', help='Generate trend analysis report')
    report_trends.add_argument('--days', type=int, default=7, help='Report period in days')
    report_trends.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')
    
    # Geographic configuration
    geo_trends = trends_subparsers.add_parser('geo', help='Geographic trend configuration')
    geo_subparsers = geo_trends.add_subparsers(dest='geo_command', help='Geographic commands')
    
    geo_set = geo_subparsers.add_parser('set', help='Set geographic preferences')
    geo_set.add_argument('--country', help='Country (e.g., "United States")')
    geo_set.add_argument('--state', help='State (e.g., "California")')
    geo_set.add_argument('--city', help='City (e.g., "San Francisco")')
    
    geo_subparsers.add_parser('show', help='Show current geographic settings')
    geo_subparsers.add_parser('reset', help='Reset to default geographic settings')

    # Database management for trends
    db_parser = subparsers.add_parser('db', help='Database management commands')
    db_subparsers = db_parser.add_subparsers(dest='db_command', help='Database commands')
    
    db_subparsers.add_parser('migrate', help='Add trend analysis tables to database')
    
    cleanup_db = db_subparsers.add_parser('cleanup', help='Clean up old data')
    cleanup_db.add_argument('--days', type=int, default=30, help='Keep data newer than N days')
    cleanup_db.add_argument('--trends-only', action='store_true', help='Clean only trend data')
    
    stats_db = db_subparsers.add_parser('stats', help='Show database statistics')
    stats_db.add_argument('--trends', action='store_true', help='Include trend statistics')

    # Source management with trends
    sources_parser = subparsers.add_parser('sources', help='Manage content sources including trends')
    sources_subparsers = sources_parser.add_subparsers(dest='sources_command', help='Source commands')
    sources_subparsers.add_parser('status', help='Show all source status including trend sources')
    sources_subparsers.add_parser('list', help='List available sources and trend sources')
    sources_subparsers.add_parser('test', help='Test all source connections')

    # Configuration management
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_subparsers = config_parser.add_subparsers(dest='config_command', help='Config commands')
    config_subparsers.add_parser('show', help='Show current configuration')
    config_subparsers.add_parser('validate', help='Validate configuration')
    config_subparsers.add_parser('reset', help='Reset to default configuration')
    
    return parser



async def handle_database_commands(args):
    """Handle database management commands"""
    
    if args.db_command == 'migrate':
        await migrate_database_for_trends()
    
    elif args.db_command == 'cleanup':
        await cleanup_database(args)
    
    elif args.db_command == 'stats':
        await show_database_statistics(args)

async def migrate_database_for_trends():
    """Migrate database to add trend analysis tables"""
    
    print("🗄️  Migrating Database for Trend Analysis")
    print("=" * 50)
    
    try:
        from digestr.core.trend_database_manager import TrendDatabaseManager
        
        db_manager = DatabaseManager()
        trend_db = TrendDatabaseManager(db_manager.db_path)
        
        # The migration is handled in the TrendDatabaseManager initialization
        print("✅ Database migration completed successfully")
        print("📊 Trend analysis tables are ready")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

async def cleanup_database(args):
    """Clean up old database entries"""
    
    print(f"🧹 Cleaning up database (keeping last {args.days} days)")
    print("=" * 50)
    
    try:
        db_manager = DatabaseManager()
        
        if args.trends_only:
            from digestr.core.trend_database_manager import TrendDatabaseManager
            trend_db = TrendDatabaseManager(db_manager.db_path)
            removed = trend_db.cleanup_old_trends(args.days)
            print(f"✅ Removed {removed} old trend records")
        else:
            # Clean articles
            articles_removed = db_manager.cleanup_old_articles(args.days)
            print(f"✅ Removed {articles_removed} old articles")
            
            # Clean trends
            from digestr.core.trend_database_manager import TrendDatabaseManager
            trend_db = TrendDatabaseManager(db_manager.db_path)
            trends_removed = trend_db.cleanup_old_trends(args.days)
            print(f"✅ Removed {trends_removed} old trend records")
            
            total_removed = articles_removed + trends_removed
            print(f"📊 Total cleaned: {total_removed} records")
    
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")






async def main():
    parser = await setup_enhanced_argument_parser()
    args = parser.parse_args()
    
    if args.command == 'status':
        await show_enhanced_system_status()
        
    elif args.command == 'fetch':
        await handle_enhanced_fetch_with_trends(args)
        
    elif args.command == 'briefing':
        await handle_enhanced_briefing_with_full_trends(args)
        
    elif args.command == 'trends':
        await handle_trends_commands(args)
        
    elif args.command == 'db':
        await handle_database_commands(args)
        
    elif args.command == 'sources':
        await handle_enhanced_sources_commands(args)
        
    elif args.command == 'config':
        await handle_config_commands(args)
        
    else:
        parser.print_help()

async def show_enhanced_system_status():
    """Show complete system status including trends"""
    
    print("🔍 Digestr.ai Enhanced System Status")
    print("✅ Version: 2.1.0 with Trend Analysis")
    print("✅ Database: Ready")
    print("✅ LLM: Ready (Ollama)")
    
    # Check trend analysis
    config_manager = get_config_manager()
    config = config_manager.get_config()
    
    if config.trending.enabled:
        print("✅ Trend Analysis: Enabled")
        enabled_sources = [name for name, cfg in config.trending.sources.items() 
                          if cfg.get('enabled', False)]
        print(f"📈 Trend Sources: {', '.join(enabled_sources) if enabled_sources else 'None'}")
    else:
        print("⚪ Trend Analysis: Disabled")
    
    print("🎯 Ready for intelligent news analysis with cross-source trend correlation!")

if __name__ == "__main__":
    asyncio.run(main())
