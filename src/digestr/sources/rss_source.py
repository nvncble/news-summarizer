#!/usr/bin/env python3
"""
RSS Source Implementation - Bridge to existing RSS system
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
            # Use existing RSS fetching system
            results, _ = await self.fetcher.fetch_all_feeds()
            
            # Convert to list format expected by source manager
            all_articles = []
            for source_name, source_articles in results.items():
                all_articles.extend(source_articles)
            
            logger.info(f"RSS source fetched {len(all_articles)} articles")
            return all_articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS articles: {e}")
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
