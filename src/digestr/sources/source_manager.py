#!/usr/bin/env python3
"""
Updated SourceManager with Personal Reddit Integration
Handles both professional and social content sources
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import existing sources
from digestr.sources.rss_source import RSSSource
from digestr.sources.reddit_source import RedditSource

# Import new personal sources
from digestr.sources.reddit_personal_source import RedditPersonalSource
from digestr.sources.social_post_structure import SocialFeed

logger = logging.getLogger(__name__)


class SourceManager:
    """
    Enhanced SourceManager that handles both professional and social sources
    Supports structured briefings with separate professional and social sections
    """
    
    def __init__(self, config_manager, db_manager):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.config = config_manager.get_config()
        
        # Source instances
        self.sources = {}
        self.professional_sources = []
        self.social_sources = []
        
        # Results cache
        self.last_fetch_results = {}
        self.last_fetch_time = None
    
    async def initialize_sources(self):
        """Initialize all configured sources"""
        logger.info("Initializing enhanced source manager...")
        
        source_configs = self.config.sources

        # Initialize professional sources
        if hasattr(source_configs, 'rss') and source_configs.rss.enabled:
            self.sources['rss'] = RSSSource(self.config_manager, self.db_manager)
            self.professional_sources.append('rss')
            
        if hasattr(source_configs, 'reddit') and source_configs.reddit.enabled:
            # Pass the reddit config, not the whole config manager
            reddit_config = {
                'client_id': source_configs.reddit.client_id,
                'client_secret': source_configs.reddit.client_secret,
                'user_agent': source_configs.reddit.user_agent,
                'subreddits': source_configs.reddit.subreddits,
                'quality_control': source_configs.reddit.quality_control
            }
            self.sources['reddit'] = RedditSource(reddit_config, self.db_manager)  
            self.professional_sources.append('reddit')

        # Initialize social sources
        if hasattr(source_configs, 'reddit_personal') and source_configs.reddit_personal.enabled:
            self.sources['reddit_personal'] = RedditPersonalSource(self.config_manager, self.db_manager)
            self.social_sources.append('reddit_personal')
                
        logger.info(f"Initialized {len(self.sources)} sources: {list(self.sources.keys())}")
        logger.info(f"Professional sources: {self.professional_sources}")
        logger.info(f"Social sources: {self.social_sources}")
    
    async def fetch_all_sources(self) -> Dict[str, Any]:
        """Fetch content from all sources"""
        results = {
            'professional': {},
            'social': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Fetch professional sources
        professional_tasks = []
        for source_name in self.professional_sources:
            if source_name in self.sources:
                task = self._fetch_source_safe(source_name)
                professional_tasks.append((source_name, task))
        
        # Fetch social sources  
        social_tasks = []
        for source_name in self.social_sources:
            if source_name in self.sources:
                task = self._fetch_source_safe(source_name)
                social_tasks.append((source_name, task))
        
        # Execute professional fetches
        if professional_tasks:
            logger.info(f"Fetching {len(professional_tasks)} professional sources...")
            professional_results = await asyncio.gather(*[task for _, task in professional_tasks], return_exceptions=True)
            
            for i, (source_name, _) in enumerate(professional_tasks):
                result = professional_results[i]
                if isinstance(result, Exception):
                    logger.error(f"Professional source {source_name} failed: {result}")
                    results['professional'][source_name] = []
                else:
                    results['professional'][source_name] = result
                    
        # Execute social fetches
        if social_tasks:
            logger.info(f"Fetching {len(social_tasks)} social sources...")
            social_results = await asyncio.gather(*[task for _, task in social_tasks], return_exceptions=True)
            
            for i, (source_name, _) in enumerate(social_tasks):
                result = social_results[i]
                if isinstance(result, Exception):
                    logger.error(f"Social source {source_name} failed: {result}")
                    results['social'][source_name] = SocialFeed(platform=source_name, posts=[])
                else:
                    results['social'][source_name] = result
        
        # Cache results
        self.last_fetch_results = results
        self.last_fetch_time = datetime.now()
        
        # Log summary
        total_professional = sum(len(content) for content in results['professional'].values() if isinstance(content, list))
        total_social = sum(len(feed.posts) for feed in results['social'].values() if isinstance(feed, SocialFeed))
        
        logger.info(f"Fetch complete: {total_professional} professional articles, {total_social} social posts")
        
        return results
    
    async def _fetch_source_safe(self, source_name: str):
        """Safely fetch from a source with error handling"""
        try:
            source = self.sources[source_name]
            
            if hasattr(source, 'fetch_content'):
                # New social sources
                return await source.fetch_content()
            elif hasattr(source, 'fetch_articles'):
                # Existing professional sources
                return await source.fetch_articles()
            else:
                logger.error(f"Source {source_name} has no fetch method")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            raise e
    
    async def fetch_professional_only(self) -> Dict[str, List]:
        """Fetch only professional sources"""
        results = {}
        
        for source_name in self.professional_sources:
            if source_name in self.sources:
                try:
                    content = await self._fetch_source_safe(source_name)
                    results[source_name] = content
                except Exception as e:
                    logger.error(f"Professional source {source_name} failed: {e}")
                    results[source_name] = []
        
        return results
    
    async def fetch_social_only(self) -> Dict[str, SocialFeed]:
        """Fetch only social sources"""
        results = {}
        
        for source_name in self.social_sources:
            if source_name in self.sources:
                try:
                    content = await self._fetch_source_safe(source_name)
                    results[source_name] = content if isinstance(content, SocialFeed) else SocialFeed(platform=source_name, posts=[])
                except Exception as e:
                    logger.error(f"Social source {source_name} failed: {e}")
                    results[source_name] = SocialFeed(platform=source_name, posts=[])
        
        return results
    
    async def fetch_specific_sources(self, source_types: List[str]) -> Dict[str, Any]:
        """Fetch from specific sources"""
        results = {}
        
        for source_type in source_types:
            if source_type in self.sources:
                try:
                    content = await self._fetch_source_safe(source_type)
                    results[source_type] = content
                except Exception as e:
                    logger.error(f"Source {source_type} failed: {e}")
                    results[source_type] = [] if source_type in self.professional_sources else SocialFeed(platform=source_type, posts=[])
        
        return results
    
    def get_available_sources(self) -> List[str]:
        """Get list of all available sources"""
        return list(self.sources.keys())
    
    def get_professional_sources(self) -> List[str]:
        """Get list of professional sources"""
        return self.professional_sources.copy()
    
    def get_social_sources(self) -> List[str]:
        """Get list of social sources"""
        return self.social_sources.copy()
    
    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all sources"""
        status = {}
        
        for source_name, source in self.sources.items():
            try:
                if hasattr(source, 'get_source_status'):
                    status[source_name] = source.get_source_status()
                else:
                    # Basic status for sources without detailed status
                    status[source_name] = {
                        'enabled': True,
                        'validated': True,
                        'type': 'professional' if source_name in self.professional_sources else 'social'
                    }
            except Exception as e:
                status[source_name] = {
                    'enabled': False,
                    'validated': False,
                    'error': str(e)
                }
        
        return status
    
    async def test_all_sources(self) -> Dict[str, Dict[str, Any]]:
        """Test connectivity for all sources"""
        results = {}
        
        for source_name, source in self.sources.items():
            try:
                if hasattr(source, 'test_connection'):
                    results[source_name] = await source.test_connection()
                else:
                    # Basic test - try to initialize
                    results[source_name] = {
                        'success': True,
                        'message': f"{source_name} initialized successfully"
                    }
            except Exception as e:
                results[source_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results
    
    def get_briefing_structure_config(self) -> Dict[str, Any]:
        """Get briefing structure configuration"""
        briefing_config = self.config.briefing
        
        return {
            'default_order': briefing_config.get('structure', {}).get('default_order', ['professional', 'social']),
            'professional_sources': briefing_config.get('structure', {}).get('professional_sources', self.professional_sources),
            'social_sources': briefing_config.get('structure', {}).get('social_sources', self.social_sources),
            'styles': briefing_config.get('styles', {})
        }
    
    def get_fetch_summary(self) -> Dict[str, Any]:
        """Get summary of last fetch operation"""
        if not self.last_fetch_results:
            return {'status': 'no_fetch_performed'}
        
        professional_count = sum(
            len(content) for content in self.last_fetch_results.get('professional', {}).values() 
            if isinstance(content, list)
        )
        
        social_count = sum(
            len(feed.posts) for feed in self.last_fetch_results.get('social', {}).values()
            if isinstance(feed, SocialFeed)
        )
        
        return {
            'timestamp': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            'professional_articles': professional_count,
            'social_posts': social_count,
            'sources_fetched': {
                'professional': list(self.last_fetch_results.get('professional', {}).keys()),
                'social': list(self.last_fetch_results.get('social', {}).keys())
            }
        }
    
    def clear_all_caches(self):
        """Clear all source caches"""
        for source in self.sources.values():
            if hasattr(source, 'clear_cache'):
                source.clear_cache()
        
        self.last_fetch_results = {}
        self.last_fetch_time = None
        
        logger.info("All source caches cleared")


# Utility functions for integration

def prepare_professional_content_for_llm(professional_results: Dict[str, List]) -> List[Dict]:
    """Convert professional source results to LLM-compatible format"""
    articles = []
    
    for source_name, content in professional_results.items():
        for item in content:
            if hasattr(item, 'to_dict'):
                # Article object with to_dict method
                article_dict = item.to_dict()
            elif isinstance(item, dict):
                # Already a dictionary
                article_dict = item.copy()
            else:
                # Try to convert basic attributes
                article_dict = {
                    'title': getattr(item, 'title', ''),
                    'summary': getattr(item, 'summary', ''),
                    'content': getattr(item, 'content', ''),
                    'source': getattr(item, 'source', source_name),
                    'category': getattr(item, 'category', 'unknown'),
                    'importance_score': getattr(item, 'importance_score', 0.0),
                    'source_type': 'professional'
                }
            
            # Ensure source_type is set
            article_dict['source_type'] = 'professional'
            articles.append(article_dict)
    
    return articles


def prepare_social_content_for_llm(social_results: Dict[str, SocialFeed]) -> List[Dict]:
    """Convert social source results to LLM-compatible format"""
    posts = []
    
    for source_name, feed in social_results.items():
        if isinstance(feed, SocialFeed):
            for post in feed.posts:
                post_dict = post.to_dict()
                post_dict['source_type'] = 'social'
                posts.append(post_dict)
    
    return posts