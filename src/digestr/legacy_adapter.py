#!/usr/bin/env python3
"""
Digestr Legacy Compatibility Adapter
Maintains backward compatibility with existing rss_summarizer.py usage
"""

import asyncio
import sys
from typing import Optional
import logging

# Import new modular components
from digestr.core.database import DatabaseManager
from digestr.core.fetcher import FeedManager, RSSFetcher
from digestr.llm_providers.ollama import OllamaProvider
from digestr.config.manager import get_config_manager

logger = logging.getLogger(__name__)


class LegacyRSSummarizer:
    """
    Legacy-compatible wrapper that provides the same interface as AdvancedRSSummarizer
    while using the new modular architecture internally
    """
    
    def __init__(self, db_path: str = "rss_feeds.db", ollama_url: str = "http://localhost:11434"):
        # Load configuration with legacy parameter support
        self.config_manager = get_config_manager()
        config = self.config_manager.get_config()
        
        # Override with legacy parameters if provided
        if db_path != "rss_feeds.db":
            config.database.path = db_path
        if ollama_url != "http://localhost:11434":
            config.llm.ollama_url = ollama_url
        
        # Initialize modular components
        self.db_manager = DatabaseManager(config.database.path)
        self.feed_manager = FeedManager()
        self.fetcher = RSSFetcher(self.db_manager, self.feed_manager)
        self.llm_provider = OllamaProvider(config.llm.ollama_url, config.llm.models)
        
        # Legacy attributes for compatibility
        self.db_path = config.database.path
        self.ollama_url = config.llm.ollama_url
        self.feeds = self.feed_manager.get_all_feeds()
        self.models = config.llm.models
        self.session = None  # Kept for compatibility, not used in new architecture
    
    # Legacy method implementations that delegate to new modular system
    
    def init_database(self):
        """Legacy database initialization - now handled by DatabaseManager"""
        # This is now handled automatically by DatabaseManager.__init__
        pass
    
    async def fetch_all_feeds(self):
        """Legacy fetch method - delegate to new fetcher"""
        category_counts, _ = await self.fetcher.fetch_all_feeds()
        return category_counts
    
    def get_recent_articles(self, hours: int = 24, category: Optional[str] = None,
                           limit: int = 50, min_importance: float = 0.0):
        """Legacy article retrieval - delegate to DatabaseManager"""
        articles = self.db_manager.get_recent_articles(
            hours=hours, 
            category=category, 
            limit=limit, 
            min_importance=min_importance,
            unprocessed_only=True  # Legacy behavior
        )
        
        # Convert to legacy format (list of dicts)
        legacy_articles = []
        for article in articles:
            legacy_articles.append({
                'title': article.title,
                'summary': article.summary,
                'content': article.content,
                'url': article.url,
                'category': article.category,
                'source': article.source,
                'published_date': article.published_date,
                'importance_score': article.importance_score
            })
        
        return legacy_articles
    
    def create_enhanced_summary_prompt(self, articles, briefing_type: str = "comprehensive"):
        """Legacy prompt creation - delegate to LLM provider"""
        return self.llm_provider.create_summary_prompt(articles, briefing_type)
    
    async def call_ollama_async(self, prompt: str, model: str = None):
        """Legacy Ollama call - delegate to LLM provider"""
        if model is None:
            model = self.models["default"]
        return await self.llm_provider.generate_summary(prompt, model)
    
    async def generate_summary_async(self, category: Optional[str] = None, hours: int = 24,
                                   model: str = None, briefing_type: str = "comprehensive"):
        """Legacy summary generation - orchestrate through new components"""
        # Get articles using new system
        articles = self.db_manager.get_recent_articles(
            hours=hours, 
            category=category, 
            limit=30,
            unprocessed_only=True
        )
        
        if not articles:
            return f"No new articles found in the last {hours} hours" + (f" for {category}" if category else "") + "."
        
        # Convert to legacy format for prompt creation
        legacy_articles = []
        for article in articles:
            legacy_articles.append({
                'title': article.title,
                'summary': article.summary,
                'content': article.content,
                'url': article.url,
                'category': article.category,
                'published_date': article.published_date,
                'importance_score': article.importance_score
            })
        
            briefing_type=briefing_type,
            model=model
        )
        
        # Mark articles as processed
        article_urls = [article.url for article in articles]
        self.db_manager.mark_articles_processed(article_urls)
        
        # Save summary (convert back to new format)
        summary_obj = Summary(
            category=category or "all",
            content=summary,
            model_used=model or self.models["default"],
            article_count=len(articles),
            processing_time=0.0  # Legacy - actual timing handled in new system
        )
        self.db_manager.save_summary(summary_obj)
        
        return summary
    
    def mark_articles_processed(self, articles):
        """Legacy article processing - delegate to DatabaseManager"""
        if not articles:
            return
        
        # Extract URLs from legacy article format
        if isinstance(articles[0], dict):
            urls = [article['url'] for article in articles]
        else:
            # Handle case where Article objects are passed
            urls = [article.url for article in articles]
        
        self.db_manager.mark_articles_processed(urls)
    
    def save_summary(self, summary: str, category: str, article_count: int,
                    model: str, processing_time: float):
        """Legacy summary saving - delegate to DatabaseManager"""
        from digestr.core.database import Summary
        
        summary_obj = Summary(
            category=category,
            content=summary,
            model_used=model,
            article_count=article_count,
            processing_time=processing_time
        )
        self.db_manager.save_summary(summary_obj)
    
    def get_feed_statistics(self):
        """Legacy statistics - delegate to DatabaseManager"""
        stats = self.db_manager.get_feed_statistics()
        
        # Convert to legacy format expected by original code
        legacy_stats = {
            "categories": stats["categories"],
            "performance": stats["performance"],
            "total_feeds": sum(len(feeds) for feeds in self.feeds.values())
        }
        
        return legacy_stats
    
    async def run_comprehensive_briefing(self, category: Optional[str] = None,
                                       hours: int = 24, model: str = None,
                                       briefing_type: str = "comprehensive"):
        """Legacy briefing runner - orchestrate through new system"""
        logger.info("🚀 Starting comprehensive news briefing...")
        
        # Fetch all feeds using new system
        category_counts = await self.fetcher.fetch_all_feeds()
        
        total_new = sum(category_counts.values())
        if total_new == 0:
            print("📰 No new articles found since last check.")
            return
        
        print(f"📈 Fetched {total_new} new articles across {len(category_counts)} categories")
        
        # Generate summary
        print(f"🤖 Generating {briefing_type} summary with {model or 'default model'}...")
        from digestr.core.database import Summary
        import time
        
        summary = await self.generate_summary_async(
            category=category,
            hours=hours,
        # Generate summary using new LLM provider
        summary = await self.llm_provider.generate_briefing(
            legacy_articles, 
            model=model,
            briefing_type=briefing_type
        )
        
        # Display results (legacy format)

        print("\n" + "="*80)
        print("📋 YOUR ENHANCED NEWS BRIEFING")
        print("="*80)
        print(summary)
        print("\n" + "="*80)
        

        # Show statistics
        stats = self.get_feed_statistics()
        print(f"📊 Feed Statistics: {stats['total_feeds']} total feeds monitored")
        print("📈 Top categories:", 
              ", ".join([f"{cat}: {info['count']}" for cat, info in stats['categories'].items()]))
    
    # Legacy helper methods
    def hash_url(self, url: str) -> str:
        """Legacy URL hashing - delegate to DatabaseManager"""
        return self.db_manager.hash_url(url)
    
    def extract_content_from_entry(self, entry):
        """Legacy content extraction - delegate to ArticleProcessor"""
        from digestr.core.fetcher import ArticleProcessor
        return ArticleProcessor.extract_content_from_entry(entry)
    
    def calculate_importance_score(self, entry):
        """Legacy importance scoring - delegate to ArticleProcessor"""
        from digestr.core.fetcher import ArticleProcessor
        return ArticleProcessor.calculate_importance_score(entry)


def run_legacy_briefing():
    """
    Entry point that maintains exact v1.x behavior
    This function is called by the legacy rss_summarizer.py
    """
    try:
        # Create legacy-compatible summarizer
        summarizer = LegacyRSSummarizer()
        
        print("🤖 Advanced RSS Summarizer with Ollama")
        print("🔥 Optimized for high-speed connections with async processing")
        print("✨ Now powered by Digestr.ai v2.0 modular architecture")
        
        # Run the same comprehensive briefing as before
        asyncio.run(summarizer.run_comprehensive_briefing(
            briefing_type="comprehensive",
            hours=24
        ))
        
        # Show migration hint
        print("\n💡 Discover new interactive features with: digestr briefing --interactive")
        print("💡 Manage features with: digestr config show")
        
    except KeyboardInterrupt:
        print("\n👋 Briefing cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error in legacy briefing: {e}")
        print(f"❌ Error running briefing: {e}")
        print("💡 Try: digestr config reset  # to reset configuration")
        sys.exit(1)


def create_legacy_compatible_instance(db_path: str = "rss_feeds.db", 
                                    ollama_url: str = "http://localhost:11434"):
    """
    Factory function for creating legacy-compatible instances
    Used by tests and any code that imports the old class directly
    """
    return LegacyRSSummarizer(db_path, ollama_url)
