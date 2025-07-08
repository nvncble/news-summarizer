#!/usr/bin/env python3
"""
Digestr Core Fetcher Module
Handles async RSS fetching, feed management, and article processing
"""

import asyncio
import aiohttp
import feedparser
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
import logging

from .database import DatabaseManager, Article

logger = logging.getLogger(__name__)


class FeedManager:
    """Manages RSS feed configurations and categories"""
    
    def __init__(self):
        # Updated RSS feeds with working URLs only
        self.feeds = {
            "tech": [
                "https://feeds.arstechnica.com/arstechnica/index",
                "https://www.theverge.com/rss/index.xml",
                "https://techcrunch.com/feed/",
                "https://www.wired.com/feed/rss",
                "https://www.engadget.com/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
                "https://moxie.foxnews.com/google-publisher/tech.xml",
                "https://moxie.foxnews.com/google-publisher/health.xml",
            ],
            "world_news": [
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://moxie.foxnews.com/google-publisher/world.xml",
                "https://feeds.npr.org/1001/rss.xml",
                "https://www.theguardian.com/world/rss",
                "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
                "https://feeds.skynews.com/feeds/rss/world.xml",
                "https://rss.dw.com/xml/rss-en-world",
            ],
            "sports": [
                "https://www.espn.com/espn/rss/news",
                "https://sports.yahoo.com/rss/",
                "https://www.cbssports.com/rss/headlines",
            ],
            "cutting_edge": [
                "https://rss.arxiv.org/rss/cs.AI",  # AI papers
                "https://rss.arxiv.org/rss/cs.LG",  # Machine Learning papers
                "https://rss.arxiv.org/rss/cs.CL",  # Computational Linguistics
                "https://rss.arxiv.org/rss/cs.CV",  # Computer Vision
                "https://feeds.nature.com/nature/rss/current",
                "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
                # Removed broken feeds: oreilly/radar, distill.pub
            ],
            "business": [
                "https://feeds.bloomberg.com/markets/news.rss",
                "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
                "https://feeds.feedburner.com/entrepreneur/latest",
            ],
            "security": [
                "https://feeds.feedburner.com/TheHackersNews",
                "https://krebsonsecurity.com/feed/",
                "https://threatpost.com/feed/",
                # Removed broken feeds: securityweek, darkreading
            ]
        }
    
    def get_feeds_for_category(self, category: str) -> List[str]:
        """Get feed URLs for a specific category"""
        return self.feeds.get(category, [])
    
    def get_all_feeds(self) -> Dict[str, List[str]]:
        """Get all feeds organized by category"""
        return self.feeds.copy()
    
    def get_categories(self) -> List[str]:
        """Get list of available categories"""
        return list(self.feeds.keys())
    
    def add_custom_feed(self, category: str, feed_url: str):
        """Add a custom feed to a category"""
        if category not in self.feeds:
            self.feeds[category] = []
        if feed_url not in self.feeds[category]:
            self.feeds[category].append(feed_url)
            logger.info(f"Added custom feed to {category}: {feed_url}")
    
    def remove_feed(self, category: str, feed_url: str) -> bool:
        """Remove a feed from a category"""
        if category in self.feeds and feed_url in self.feeds[category]:
            self.feeds[category].remove(feed_url)
            logger.info(f"Removed feed from {category}: {feed_url}")
            return True
        return False


class ArticleProcessor:
    """Processes individual articles and calculates importance scores"""
    
    @staticmethod
    def extract_content_from_entry(entry) -> str:
        """Extract meaningful content from RSS entry"""
        content = ""
        
        # Try different content fields in order of preference
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value if isinstance(
                entry.content, list) else str(entry.content)
        elif hasattr(entry, 'summary_detail') and entry.summary_detail:
            content = entry.summary_detail.value
        elif hasattr(entry, 'summary'):
            content = entry.summary
        elif hasattr(entry, 'description'):
            content = entry.description
        
        # Clean HTML tags and normalize whitespace
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    @staticmethod
    def calculate_importance_score(entry) -> float:
        """Calculate importance score based on various factors"""
        score = 0.0
        title = entry.get('title', '').lower()
        summary = entry.get('summary', '').lower()
        
        # Keywords that indicate importance
        critical_keywords = ['breaking', 'urgent', 'emergency', 'crisis', 'alert']
        major_keywords = ['major', 'significant', 'critical', 'important']
        business_keywords = ['acquisition', 'merger', 'funding', 'ipo', 'earnings']
        tech_keywords = ['breakthrough', 'discovery', 'announcement', 'launch', 'release']
        
        # Score based on keyword presence
        for keyword in critical_keywords:
            if keyword in title:
                score += 3.0
            if keyword in summary:
                score += 2.0
        
        for keyword in major_keywords:
            if keyword in title:
                score += 2.0
            if keyword in summary:
                score += 1.0
        
        for keyword in business_keywords + tech_keywords:
            if keyword in title:
                score += 1.5
            if keyword in summary:
                score += 0.5
        
        # Length bonus (longer articles might be more substantial)
        word_count = len(summary.split())
        if word_count > 50:
            score += 0.5
        if word_count > 100:
            score += 1.0
        if word_count > 200:
            score += 1.5
        
        # Title length consideration (very short titles might be less informative)
        title_words = len(title.split())
        if title_words < 3:
            score -= 0.5
        elif title_words > 8:
            score += 0.5
        
        return min(score, 10.0)  # Cap at 10.0
    
    @staticmethod
    def create_article_from_entry(entry, category: str, source: str) -> Article:
        """Create an Article object from a feedparser entry"""
        content = ArticleProcessor.extract_content_from_entry(entry)
        importance_score = ArticleProcessor.calculate_importance_score(entry)
        
        return Article(
            title=entry.get('title', ''),
            summary=entry.get('summary', entry.get('description', '')),
            content=content,
            url=entry.get('link', ''),
            category=category,
            source=source,
            published_date=entry.get('published', ''),
            importance_score=importance_score,
            word_count=len(content.split()) if content else 0
        )


class RSSFetcher:
    """Handles async RSS fetching with enhanced error handling and performance"""
    
    def __init__(self, db_manager: DatabaseManager, feed_manager: FeedManager):
        self.db_manager = db_manager
        self.feed_manager = feed_manager
    
    async def fetch_single_feed(self, session: aiohttp.ClientSession, 
                               feed_url: str, category: str) -> Tuple[str, List[Article], float, bool]:
        """
        Fetch a single RSS feed asynchronously
        Returns: (feed_url, articles, fetch_time, success)
        """
        start_time = time.time()
        articles = []
        success = False
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(feed_url, timeout=timeout) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    # Handle potential parsing errors
                    if feed.bozo and hasattr(feed, 'bozo_exception'):
                        logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
                    
                    source = feed.feed.get('title', urlparse(feed_url).netloc)
                    
                    for entry in feed.entries:
                        try:
                            article = ArticleProcessor.create_article_from_entry(
                                entry, category, source
                            )
                            articles.append(article)
                        except Exception as e:
                            logger.warning(f"Error processing entry from {feed_url}: {e}")
                            continue
                    
                    success = True
                    logger.debug(f"Fetched {len(articles)} articles from {feed_url}")
                    
                else:
                    logger.warning(f"HTTP {response.status} for {feed_url}")
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {feed_url}")
        except aiohttp.ClientError as e:
            logger.warning(f"Client error fetching {feed_url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {feed_url}: {e}")
        
        fetch_time = time.time() - start_time
        return feed_url, articles, fetch_time, success
    
    async def fetch_feeds_for_category(self, category: str) -> Tuple[List[Article], Dict[str, float]]:
        """
        Fetch all feeds for a specific category
        Returns: (articles, feed_stats)
        """
        feed_urls = self.feed_manager.get_feeds_for_category(category)
        if not feed_urls:
            logger.warning(f"No feeds configured for category: {category}")
            return [], {}
        
        return await self._fetch_feed_batch(feed_urls, category)
    
    async def fetch_all_feeds(self) -> Tuple[Dict[str, int], Dict[str, Dict[str, float]]]:
        """
        Fetch all RSS feeds concurrently
        Returns: (category_counts, detailed_stats)
        """
        start_time = time.time()
        all_feeds = self.feed_manager.get_all_feeds()
        
        # Create tasks for all categories
        tasks = []
        for category, feed_urls in all_feeds.items():
            if feed_urls:  # Only process categories with feeds
                task = self._fetch_feed_batch(feed_urls, category)
                tasks.append((category, task))
        
        if not tasks:
            logger.warning("No feeds configured")
            return {}, {}
        
        logger.info(f"Fetching feeds for {len(tasks)} categories...")
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Process results
        category_counts = {}
        detailed_stats = {}
        
        for i, result in enumerate(results):
            category = tasks[i][0]
            
            if isinstance(result, Exception):
                logger.error(f"Category {category} fetch failed: {result}")
                continue
            
            articles, feed_stats = result
            
            # Insert articles into database
            if articles:
                inserted_count = self.db_manager.bulk_insert_articles(articles)
                category_counts[category] = inserted_count
                
                # Update feed statistics
                for feed_url, stats in feed_stats.items():
                    self.db_manager.update_feed_stats(
                        feed_url, category, stats['article_count'], 
                        stats['response_time'], stats['success']
                    )
                
                detailed_stats[category] = feed_stats
            else:
                category_counts[category] = 0
        
        total_time = time.time() - start_time
        total_articles = sum(category_counts.values())
        
        logger.info(f"Fetched {total_articles} new articles across {len(category_counts)} categories in {total_time:.2f}s")
        logger.info(f"Articles by category: {category_counts}")
        
        return category_counts, detailed_stats
    
    async def _fetch_feed_batch(self, feed_urls: List[str], category: str) -> Tuple[List[Article], Dict[str, float]]:
        """
        Fetch a batch of feeds for a single category
        Returns: (articles, feed_stats)
        """
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = [
                self.fetch_single_feed(session, feed_url, category)
                for feed_url in feed_urls
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect articles and statistics
        all_articles = []
        feed_stats = {}
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Feed fetch exception: {result}")
                continue
            
            feed_url, articles, fetch_time, success = result
            all_articles.extend(articles)
            
            feed_stats[feed_url] = {
                'article_count': len(articles),
                'response_time': fetch_time,
                'success': success
            }
        
        return all_articles, feed_stats
    
    async def fetch_feeds_incremental(self, categories: Optional[List[str]] = None, 
                                    max_concurrent: int = 20) -> Dict[str, int]:
        """
        Fetch feeds with incremental processing and rate limiting
        Useful for large feed lists or when system resources are limited
        """
        if categories is None:
            categories = self.feed_manager.get_categories()
        
        category_counts = {}
        
        for category in categories:
            feed_urls = self.feed_manager.get_feeds_for_category(category)
            if not feed_urls:
                continue
            
            # Process feeds in batches to control concurrency
            batch_size = max_concurrent
            for i in range(0, len(feed_urls), batch_size):
                batch_urls = feed_urls[i:i + batch_size]
                articles, feed_stats = await self._fetch_feed_batch(batch_urls, category)
                
                if articles:
                    inserted_count = self.db_manager.bulk_insert_articles(articles)
                    category_counts[category] = category_counts.get(category, 0) + inserted_count
                    
                    # Update feed statistics
                    for feed_url, stats in feed_stats.items():
                        self.db_manager.update_feed_stats(
                            feed_url, category, stats['article_count'], 
                            stats['response_time'], stats['success']
                        )
                
                # Small delay between batches to be respectful to servers
                if i + batch_size < len(feed_urls):
                    await asyncio.sleep(0.5)
        
        return category_counts


class EnhancedRSSFetcher(RSSFetcher):
    """
    Enhanced RSS fetcher with additional features for advanced use cases
    This will be the foundation for future interactive and community features
    """
    
    def __init__(self, db_manager: DatabaseManager, feed_manager: FeedManager):
        super().__init__(db_manager, feed_manager)
        self.fetch_history = []  # Track recent fetch operations
        self.custom_headers = {
            'User-Agent': 'Digestr.ai/2.0 (+https://github.com/nvncble/digestr)'
        }
    
    async def fetch_with_custom_feeds(self, custom_feeds: Dict[str, List[str]]) -> Dict[str, int]:
        """
        Fetch using custom feed configuration
        Useful for community shared feed collections
        """
        original_feeds = self.feed_manager.feeds.copy()
        
        try:
            # Temporarily update feed configuration
            self.feed_manager.feeds.update(custom_feeds)
            
            # Perform the fetch
            category_counts, _ = await self.fetch_all_feeds()
            
            return category_counts
            
        finally:
            # Restore original configuration
            self.feed_manager.feeds = original_feeds
    
    async def validate_feed_health(self, feed_url: str) -> Dict[str, any]:
        """
        Validate a single feed's health and characteristics
        Useful for community feed curation
        """
        start_time = time.time()
        health_info = {
            'url': feed_url,
            'accessible': False,
            'response_time': 0.0,
            'article_count': 0,
            'avg_importance': 0.0,
            'last_updated': None,
            'feed_title': '',
            'errors': []
        }
        
        try:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout, 
                                           headers=self.custom_headers) as session:
                async with session.get(feed_url) as response:
                    health_info['response_time'] = time.time() - start_time
                    
                    if response.status == 200:
                        content = await response.text()
                        feed = feedparser.parse(content)
                        
                        if feed.bozo and hasattr(feed, 'bozo_exception'):
                            health_info['errors'].append(f"Parsing warning: {feed.bozo_exception}")
                        
                        health_info['accessible'] = True
                        health_info['feed_title'] = feed.feed.get('title', 'Unknown')
                        health_info['article_count'] = len(feed.entries)
                        health_info['last_updated'] = feed.feed.get('updated', 'Unknown')
                        
                        # Calculate average importance for this feed
                        if feed.entries:
                            importance_scores = [
                                ArticleProcessor.calculate_importance_score(entry)
                                for entry in feed.entries
                            ]
                            health_info['avg_importance'] = sum(importance_scores) / len(importance_scores)
                    
                    else:
                        health_info['errors'].append(f"HTTP {response.status}")
        
        except asyncio.TimeoutError:
            health_info['errors'].append("Timeout")
        except Exception as e:
            health_info['errors'].append(str(e))
        
        return health_info
    
    async def batch_validate_feeds(self, feed_urls: List[str]) -> List[Dict[str, any]]:
        """
        Validate multiple feeds concurrently
        Returns health information for all feeds
        """
        tasks = [self.validate_feed_health(url) for url in feed_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_reports = []
        for result in results:
            if isinstance(result, Exception):
                health_reports.append({
                    'accessible': False,
                    'errors': [str(result)]
                })
            else:
                health_reports.append(result)
        
        return health_reports
    
    def get_fetch_statistics(self) -> Dict[str, any]:
        """Get detailed statistics about recent fetch operations"""
        stats = self.db_manager.get_feed_statistics()
        
        # Add fetcher-specific statistics
        stats['fetcher_info'] = {
            'total_configured_feeds': sum(len(feeds) for feeds in self.feed_manager.feeds.values()),
            'categories_configured': len(self.feed_manager.feeds),
            'recent_fetch_history': len(self.fetch_history)
        }
        
        return stats
    
    async def smart_fetch(self, priority_categories: Optional[List[str]] = None,
                         importance_threshold: float = 2.0) -> Dict[str, int]:
        """
        Intelligent fetching that prioritizes high-value sources
        Future enhancement for resource optimization
        """
        # Get feed statistics to identify high-performing feeds
        stats = self.db_manager.get_feed_statistics()
        
        if priority_categories:
            # Focus on specific categories
            target_feeds = {}
            for category in priority_categories:
                target_feeds[category] = self.feed_manager.get_feeds_for_category(category)
        else:
            # Use all feeds but prioritize based on historical performance
            target_feeds = self.feed_manager.get_all_feeds()
        
        # For now, use standard fetch - this is a placeholder for future ML-based optimization
        category_counts, _ = await self.fetch_all_feeds()
        
        # Filter results by importance threshold if specified
        if importance_threshold > 0:
            # This would be implemented as a post-processing filter
            # For now, return all results
            pass
        
        return category_counts
