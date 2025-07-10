#!/usr/bin/env python3
"""
Social Content Data Structures - FIXED VERSION
Handles social media posts, personal feeds, and social interactions
"""

import math  # ← ADD THIS IMPORT
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class SocialPost:
    """Social media post data structure (Reddit, Twitter, etc.)"""
    id: Optional[str] = None
    platform: str = ""  # "reddit", "twitter", "youtube"
    post_type: str = ""  # "text", "link", "image", "video"
    
    # Core content
    title: str = ""
    content: str = ""
    url: str = ""
    source_url: str = ""  # Original Reddit/Twitter URL
    
    # Author info
    author: str = ""
    author_verified: bool = False
    
    # Location/Context
    subreddit: str = ""  # For Reddit
    community: str = ""  # Generic community/channel name
    
    # Engagement metrics
    upvotes: int = 0
    downvotes: int = 0
    score: int = 0  # Net score
    comments_count: int = 0
    shares_count: int = 0
    
    # Timing
    created_utc: Optional[datetime] = None
    fetched_date: str = ""
    
    # Content analysis
    sentiment_score: float = 0.0
    interest_score: float = 0.0  # AI-calculated relevance to user
    content_category: str = ""  # "entertainment", "news", "discussion", etc.
    
    # Metadata
    is_nsfw: bool = False
    is_spoiler: bool = False
    is_pinned: bool = False
    flair: str = ""
    
    # For link posts
    domain: str = ""
    thumbnail_url: str = ""
    
    def __post_init__(self):
        """Set defaults and calculate derived fields"""
        if not self.fetched_date:
            self.fetched_date = datetime.now().isoformat()
            
        if not self.score and self.upvotes:
            self.score = self.upvotes - self.downvotes
            
        if self.url and not self.domain:
            from urllib.parse import urlparse
            self.domain = urlparse(self.url).netloc
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM processing"""
        return {
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'community': self.community or self.subreddit,
            'score': self.score,
            'comments': self.comments_count,
            'url': self.url,
            'platform': self.platform,
            'interest_score': self.interest_score,
            'content_category': self.content_category,
            'created_utc': self.created_utc.isoformat() if self.created_utc else "",
            'source_type': 'social'  # For compatibility with existing briefing system
        }
    
    def get_engagement_level(self) -> str:
        """Categorize engagement level"""
        if self.platform == "reddit":
            if self.score > 5000:
                return "viral"
            elif self.score > 1000:
                return "high"
            elif self.score > 100:
                return "moderate"
            else:
                return "low"
        else:
            # Default for other platforms
            return "unknown"
    
    def is_worth_including(self, min_score: int = 10) -> bool:
        """Basic filter for inclusion in briefing"""
        if self.is_nsfw and not self._allow_nsfw():
            return False
        if self.score < min_score:
            return False
        return True
    
    def _allow_nsfw(self) -> bool:
        """Check if NSFW content is allowed (from config)"""
        # This would check config, for now default to False
        return False


@dataclass 
class SocialFeed:
    """Collection of social posts from a specific source"""
    platform: str = ""
    feed_type: str = ""  # "home", "trending", "subscriptions"
    posts: List[SocialPost] = None
    fetch_time: str = ""
    total_fetched: int = 0
    filtered_count: int = 0
    
    def __post_init__(self):
        if self.posts is None:
            self.posts = []
        if not self.fetch_time:
            self.fetch_time = datetime.now().isoformat()
        if not self.total_fetched:
            self.total_fetched = len(self.posts)
    
    def get_top_posts(self, limit: int = 10) -> List[SocialPost]:
        """Get top posts by score"""
        return sorted(self.posts, key=lambda x: x.score, reverse=True)[:limit]
    
    def get_posts_by_category(self, category: str) -> List[SocialPost]:
        """Filter posts by content category"""
        return [post for post in self.posts if post.content_category == category]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for this feed"""
        if not self.posts:
            return {"total": 0}
            
        return {
            "total": len(self.posts),
            "avg_score": sum(p.score for p in self.posts) / len(self.posts),
            "top_score": max(p.score for p in self.posts) if self.posts else 0,
            "communities": len(set(p.community or p.subreddit for p in self.posts)),
            "engagement_levels": {
                level: len([p for p in self.posts if p.get_engagement_level() == level])
                for level in ["viral", "high", "moderate", "low"]
            }
        }


# Utility functions for social content processing

def create_reddit_post_from_submission(submission, platform="reddit") -> SocialPost:
    """Convert PRAW submission to SocialPost"""
    return SocialPost(
        id=submission.id,
        platform=platform,
        post_type="link" if submission.url != submission.permalink else "text",
        title=submission.title,
        content=submission.selftext or "",
        url=submission.url if submission.url != submission.permalink else "",
        source_url=f"https://reddit.com{submission.permalink}",
        author=str(submission.author) if submission.author else "[deleted]",
        subreddit=submission.subreddit.display_name,
        community=submission.subreddit.display_name,
        upvotes=submission.ups,
        downvotes=submission.downs if hasattr(submission, 'downs') else 0,
        score=submission.score,
        comments_count=submission.num_comments,
        created_utc=datetime.fromtimestamp(submission.created_utc),
        is_nsfw=submission.over_18,
        is_pinned=submission.pinned,
        flair=submission.link_flair_text or "",
        domain=submission.domain if hasattr(submission, 'domain') else ""
    )


def calculate_interest_score(post: SocialPost, user_preferences: Dict = None) -> float:
    """Calculate AI-based interest score for a post - FIXED VERSION"""
    score = 0.0
    
    # Base engagement score
    if post.platform == "reddit":
        # Logarithmic scaling for Reddit scores - FIXED: Added math import
        score += min(5.0, math.log10(max(1, post.score)) * 2)
    
    # Comment engagement bonus
    if post.comments_count > 10:
        score += min(2.0, math.log10(post.comments_count))
    
    # Community popularity (if we have data)
    # This would be enhanced with user preference learning
    
    # Time recency bonus
    if post.created_utc:
        hours_old = (datetime.now() - post.created_utc).total_seconds() / 3600
        if hours_old < 6:
            score += 1.0  # Fresh content bonus
        elif hours_old > 48:
            score -= 1.0  # Old content penalty
    
    return max(0.0, score)


def categorize_content(post: SocialPost) -> str:
    """Categorize social content type"""
    title_lower = post.title.lower()
    content_lower = (post.content or "").lower()
    full_text = f"{title_lower} {content_lower}"
    
    # Simple keyword-based categorization
    if any(word in full_text for word in ["eli5", "explain", "how does", "what is"]):
        return "educational"
    elif any(word in full_text for word in ["ama", "ask me anything"]):
        return "discussion"
    elif any(word in full_text for word in ["funny", "lol", "meme", "humor"]):
        return "entertainment"
    elif any(word in full_text for word in ["news", "breaking", "update", "announced"]):
        return "news"
    elif any(word in full_text for word in ["tips", "advice", "help", "how to"]):
        return "advice"
    else:
        return "general"