#!/usr/bin/env python3
"""
Reddit Personal Source - Fetches user's personal Reddit feed
Handles authentication, filtering, and caching for personal Reddit content
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

# Import the social post structures we just created
from .social_post_structure import SocialPost, SocialFeed, create_reddit_post_from_submission, calculate_interest_score, categorize_content

logger = logging.getLogger(__name__)

try:
    import praw
    import prawcore
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    logger.warning("PRAW not available. Install with: pip install praw")


class RedditPersonalSource:
    """
    Fetches and processes user's personal Reddit feed
    Supports caching, filtering, and graceful error handling
    """
    
    def __init__(self, config_manager, db_manager):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.config = config_manager.get_config().sources.get('reddit_personal', {})
        
        # Caching
        self.cache_duration = self.config.get('cache_duration_minutes', 45)
        self.last_fetch_time = None
        self.cached_feed = None
        
        # Reddit API client
        self.reddit = None
        self.authenticated = False
        
        # Initialize if enabled
        if self.config.get('enabled', False):
            self._initialize_reddit_client()
    
    def _initialize_reddit_client(self):
        """Initialize Reddit API client with authentication"""
        if not PRAW_AVAILABLE:
            logger.error("PRAW library not available for Reddit personal source")
            return
        
        try:
            # Get credentials from environment variables first, then fall back to config
            import os
            client_id = os.getenv('REDDIT_CLIENT_ID') or self.config.get('client_id', '')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET') or self.config.get('client_secret', '')
            refresh_token = os.getenv('REDDIT_REFRESH_TOKEN') or self.config.get('refresh_token', '')
            user_agent = self.config.get('user_agent', 'Digestr.ai/2.1')
            
            if not all([client_id, client_secret, refresh_token]):
                logger.warning("Reddit personal source: Missing required credentials")
                return
            
            # Initialize PRAW client
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                user_agent=user_agent,
                check_for_async=False  # We'll handle our own async
            )
            
            # Test authentication
            self._test_authentication()
            
        except Exception as e:
            logger.error(f"Failed to initialize Reddit personal source: {e}")
            self.reddit = None
    
    def _test_authentication(self):
        """Test Reddit authentication"""
        try:
            if self.reddit:
                # Try to access user info
                user = self.reddit.user.me()
                if user:
                    self.authenticated = True
                    logger.info(f"Reddit personal source authenticated for user: {user.name}")
                else:
                    logger.error("Reddit personal source: Authentication failed")
        except prawcore.exceptions.ResponseException as e:
            logger.error(f"Reddit personal source authentication error: {e}")
        except Exception as e:
            logger.error(f"Reddit personal source unexpected error: {e}")
    
    async def fetch_content(self) -> Optional[SocialFeed]:
        """
        Fetch user's personal Reddit feed with caching
        """
        # Check if source is enabled and authenticated
        if not self.config.get('enabled', False):
            logger.debug("Reddit personal source is disabled")
            return None
        
        if not self.authenticated:
            logger.warning("Reddit personal source: Not authenticated, skipping")
            return SocialFeed(
                platform="reddit_personal",
                feed_type="error",
                posts=[],
                fetch_time=datetime.now().isoformat()
            )
        
        # Check cache first
        if self._is_cache_valid():
            logger.debug("Using cached Reddit personal feed")
            return self.cached_feed
        
        # Fetch fresh content
        logger.info("Fetching fresh Reddit personal feed")
        try:
            posts = await self._fetch_personal_feed()
            filtered_posts = self._apply_filtering(posts)
            
            # Create feed object
            feed = SocialFeed(
                platform="reddit_personal",
                feed_type="home",
                posts=filtered_posts,
                total_fetched=len(posts),
                filtered_count=len(filtered_posts)
            )
            
            # Cache the results
            self.cached_feed = feed
            self.last_fetch_time = datetime.now()
            
            logger.info(f"Fetched {len(posts)} posts, filtered to {len(filtered_posts)}")
            return feed
            
        except Exception as e:
            logger.error(f"Error fetching Reddit personal feed: {e}")
            return SocialFeed(
                platform="reddit_personal",
                feed_type="error",
                posts=[],
                fetch_time=datetime.now().isoformat()
            )
    
    def _is_cache_valid(self) -> bool:
        """Check if cached content is still valid"""
        if not self.last_fetch_time or not self.cached_feed:
            return False
        
        cache_age = datetime.now() - self.last_fetch_time
        cache_limit = timedelta(minutes=self.cache_duration)
        
        return cache_age < cache_limit
    
    async def _fetch_personal_feed(self) -> List[SocialPost]:
        """Fetch posts from user's personal Reddit feed"""
        if not self.reddit:
            return []
        
        posts = []
        filtering = self.config.get('filtering', {})
        content_types = self.config.get('content_types', ['hot'])
        time_window_hours = filtering.get('time_window_hours', 24)
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        
        try:
            # Run Reddit API calls in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Fetch different content types
            for content_type in content_types:
                if content_type == "hot":
                    submissions = await loop.run_in_executor(
                        None, 
                        lambda: list(self.reddit.front.hot(limit=50))
                    )
                elif content_type == "new":
                    submissions = await loop.run_in_executor(
                        None,
                        lambda: list(self.reddit.front.new(limit=25))
                    )
                else:
                    continue  # Unknown content type
                
                # Convert submissions to SocialPost objects
                for submission in submissions:
                    try:
                        # Check time filter
                        post_time = datetime.fromtimestamp(submission.created_utc)
                        if post_time < cutoff_time:
                            continue
                        
                        # Convert to SocialPost
                        post = create_reddit_post_from_submission(submission, "reddit_personal")
                        
                        # Calculate interest score
                        post.interest_score = calculate_interest_score(post)
                        
                        # Categorize content
                        post.content_category = categorize_content(post)
                        
                        posts.append(post)
                        
                    except Exception as e:
                        logger.warning(f"Error processing Reddit submission {submission.id}: {e}")
                        continue
        
        except prawcore.exceptions.ResponseException as e:
            logger.error(f"Reddit API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching Reddit personal feed: {e}")
        
        return posts
    
    def _apply_filtering(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Apply user-configured filtering to posts"""
        if not posts:
            return []
        
        filtering = self.config.get('filtering', {})
        filtered = []
        
        # Get filter parameters
        min_upvotes = filtering.get('min_upvotes', 10)
        max_posts = filtering.get('max_posts', 25)
        exclude_nsfw = filtering.get('exclude_nsfw', True)
        exclude_subreddits = set(filtering.get('exclude_subreddits', []))
        include_only = set(filtering.get('include_only', []))
        
        for post in posts:
            # NSFW filter
            if exclude_nsfw and post.is_nsfw:
                continue
            
            # Score filter
            if post.score < min_upvotes:
                continue
            
            # Subreddit exclude filter
            if post.subreddit.lower() in {s.lower() for s in exclude_subreddits}:
                continue
            
            # Include only filter (if specified)
            if include_only and post.subreddit.lower() not in {s.lower() for s in include_only}:
                continue
            
            filtered.append(post)
        
        # Sort by interest score (combination of engagement and relevance)
        filtered.sort(key=lambda x: (x.interest_score, x.score), reverse=True)
        
        # Limit to max posts
        return filtered[:max_posts]
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get current status of Reddit personal source"""
        return {
            'enabled': self.config.get('enabled', False),
            'authenticated': self.authenticated,
            'cache_valid': self._is_cache_valid(),
            'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            'cached_posts': len(self.cached_feed.posts) if self.cached_feed else 0,
            'praw_available': PRAW_AVAILABLE,
            'config_valid': self._validate_config()
        }
    
    def _validate_config(self) -> bool:
        """Validate configuration completeness"""
        required_fields = ['client_id', 'client_secret', 'refresh_token']
        return all(self.config.get(field) for field in required_fields)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection and return diagnostic info"""
        result = {
            'success': False,
            'authenticated': False,
            'error': None,
            'user': None,
            'subscriptions_count': 0
        }
        
        try:
            if not self.reddit:
                result['error'] = "Reddit client not initialized"
                return result
            
            # Test authentication
            user = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.reddit.user.me()
            )
            
            if user:
                result['authenticated'] = True
                result['user'] = user.name
                
                # Count subscriptions
                subreddits = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: list(user.subreddits(limit=None))
                )
                result['subscriptions_count'] = len(subreddits)
                result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def clear_cache(self):
        """Clear cached content"""
        self.cached_feed = None
        self.last_fetch_time = None
        logger.info("Reddit personal source cache cleared")


# Integration function for SourceManager
def create_reddit_personal_source(config_manager, db_manager):
    """Factory function to create RedditPersonalSource"""
    return RedditPersonalSource(config_manager, db_manager)


# Setup utility for users
def setup_reddit_personal_auth():
    """
    Guide user through Reddit personal authentication setup
    This would be called from a CLI command
    """
    print("🔑 Reddit Personal Authentication Setup")
    print("=" * 50)
    print()
    print("To access your personal Reddit feed, you need to:")
    print("1. Create a Reddit app at https://www.reddit.com/prefs/apps")
    print("2. Choose 'script' application type")
    print("3. Get your client_id and client_secret")
    print("4. Get a refresh token for your account")
    print()
    print("Add these to your environment variables:")
    print("export REDDIT_CLIENT_ID='your_client_id'")
    print("export REDDIT_CLIENT_SECRET='your_client_secret'") 
    print("export REDDIT_REFRESH_TOKEN='your_refresh_token'")
    print()
    print("Then enable reddit_personal in your config:")
    print("sources.reddit_personal.enabled = true")
    print()
    print("💡 For refresh token help, see: https://github.com/reddit-archive/reddit/wiki/OAuth2")


if __name__ == "__main__":
    # Test the module
    setup_reddit_personal_auth()