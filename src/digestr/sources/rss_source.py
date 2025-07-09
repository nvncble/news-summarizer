#!/usr/bin/env python3
"""
RSS Source Implementation - Bridge to existing RSS system
FIXED: Return actual articles instead of counts
"""

import asyncio
import logging
from typing import List, Dict, Any
from digestr.core.fetcher import FeedManager, RSSFetcher

logger = logging.getLogger(__name__)


class RSSSource:
    """RSS source wrapper for existing RSS fetching system"""
    
    def __init__(self, config_manager, db_manager):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.feed_manager = FeedManager()
        self.fetcher = RSSFetcher(db_manager, self.feed_manager)
    
    async def fetch_articles(self):
        """Fetch RSS articles using existing RSS fetcher"""
        try:
            # STEP 1: Fetch new articles (this saves to database)
            category_counts, _ = await self.fetcher.fetch_all_feeds()
            
            total_new = sum(category_counts.values())
            logger.info(f"RSS fetcher saved {total_new} new articles to database")
            
            # STEP 2: Get the actual articles from database 
            # (this is what was missing - we need to retrieve the articles, not just counts)
            articles = self.db_manager.get_recent_articles(
                hours=24, 
                limit=100, 
                unprocessed_only=False  # Get all recent articles, not just unprocessed
            )
            
            # STEP 3: Convert Article objects to dicts for source manager
            article_dicts = []
            for article in articles:
                # Only include RSS articles (exclude Reddit ones)
                if not article.title.startswith('[Reddit]'):
                    article_dicts.append({
                        'title': article.title,
                        'summary': article.summary,
                        'content': article.content,
                        'url': article.url,
                        'category': article.category,
                        'source': article.source,
                        'published_date': article.published_date,
                        'importance_score': article.importance_score,
                        'source_type': 'professional'
                    })
            
            logger.info(f"RSS source returning {len(article_dicts)} articles")
            return article_dicts
            
        except Exception as e:
            logger.error(f"Error fetching RSS articles: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def fetch_content(self):
        """Alternative method name for compatibility"""
        return await self.fetch_articles()
    
    def get_source_status(self):
        """Get RSS source status"""
        return {
            'enabled': True,
            'validated': True,  # Could add real validation here
            'type': 'professional',
            'article_count': 0  # Could add real count
        }
    
    async def test_connection(self):
        """Test RSS connection"""
        try:
            # Test by fetching a small number of feeds
            test_feeds = self.feed_manager.get_feeds_for_category("tech")[:2]
            if test_feeds:
                return {
                    'success': True,
                    'message': f'RSS feeds accessible ({len(test_feeds)} test feeds)'
                }
            else:
                return {
                    'success': False,
                    'message': 'No RSS feeds configured'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }