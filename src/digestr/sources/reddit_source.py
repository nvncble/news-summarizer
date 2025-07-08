"""
Reddit Source Implementation for Digestr.ai
"""

import asyncio
import praw
import prawcore
import time
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import re
import statistics
from digestr.core.database import Article, DatabaseManager
from digestr.sources.base import ContentSource
import warnings
import logging

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", message="It appears that you are using PRAW in an asynchronous environment")

praw_logger = logging.getLogger('praw')
praw_logger.setLevel(logging.ERROR)






@dataclass
class RedditPost:
    """Reddit post data structure"""
    id: str
    title: str
    selftext: str
    url: str
    subreddit: str
    author: str
    score: int
    upvote_ratio: float
    num_comments: int
    awards_received: int
    created_utc: float
    permalink: str
    is_self: bool



@dataclass
class CommentSentiment:
    """Individual comment sentiment data"""
    sentiment_score: float  # -1 to 1 (negative to positive)
    confidence: float      # 0 to 1 (how confident we are)
    upvotes: int          # Comment upvotes for weighting
    quality_score: float  # Overall comment quality (0-1)


@dataclass  
class PostSentiment:
    """Aggregated sentiment for a Reddit post"""
    consensus_score: float     # Overall community sentiment (-1 to 1)
    confidence: float         # Confidence in consensus (0 to 1)
    outlier_scores: List[float]  # Dissenting opinions
    engagement_weight: float  # How much engagement supports this sentiment
    total_comments: int      # Number of comments analyzed
    quality_score: float     # Overall sentiment quality (0 to 1)


class RedditSentimentAnalyzer:
    """Analyzes sentiment from Reddit comments"""
    
    def __init__(self):
        # Positive sentiment indicators
        self.positive_keywords = [
            'great', 'amazing', 'excellent', 'fantastic', 'wonderful', 'brilliant',
            'impressive', 'outstanding', 'awesome', 'perfect', 'love', 'best',
            'incredible', 'revolutionary', 'breakthrough', 'game-changer', 'excited',
            'promising', 'hopeful', 'optimistic', 'beneficial', 'valuable', 'useful'
        ]
        
        # Negative sentiment indicators  
        self.negative_keywords = [
            'terrible', 'awful', 'horrible', 'bad', 'worst', 'hate', 'disgusting',
            'disappointing', 'failure', 'disaster', 'concerning', 'worried', 'dangerous',
            'problematic', 'useless', 'waste', 'ridiculous', 'stupid', 'broken',
            'flawed', 'misleading', 'scam', 'overrated', 'hyped', 'skeptical'
        ]
        
        # Neutral/uncertainty indicators
        self.neutral_keywords = [
            'maybe', 'perhaps', 'possibly', 'might', 'could', 'uncertain',
            'unclear', 'mixed', 'complicated', 'depends', 'varies', 'interesting'
        ]
    
    def analyze_comment_sentiment(self, comment_text: str, upvotes: int) -> CommentSentiment:
        """Analyze sentiment of individual comment"""
        text_lower = comment_text.lower()
        
        # Count sentiment indicators
        positive_count = sum(1 for word in self.positive_keywords if word in text_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in text_lower)
        neutral_count = sum(1 for word in self.neutral_keywords if word in text_lower)
        
        # Calculate base sentiment score
        if positive_count + negative_count == 0:
            sentiment_score = 0.0  # Neutral
            confidence = 0.3      # Low confidence for neutral
        else:
            sentiment_score = (positive_count - negative_count) / (positive_count + negative_count + 1)
            confidence = min(0.9, (positive_count + negative_count) / 10)  # Higher word count = higher confidence
        
        # Adjust for neutral indicators  
        if neutral_count > 0:
            sentiment_score *= 0.7  # Reduce strength
            confidence *= 0.8       # Reduce confidence
        
        # Quality scoring based on comment characteristics
        quality_score = 0.5  # Base quality
        
        # Length indicates thoughtfulness (to a point)
        word_count = len(comment_text.split())
        if 10 <= word_count <= 100:
            quality_score += 0.2
        elif word_count > 100:
            quality_score += 0.1
        
        # Upvotes indicate community agreement
        if upvotes > 10:
            quality_score += 0.2
        elif upvotes > 50:
            quality_score += 0.3
        
        # Penalize very short or very long comments
        if word_count < 5:
            quality_score -= 0.3
        elif word_count > 200:
            quality_score -= 0.2
        
        quality_score = max(0.0, min(1.0, quality_score))
        
        return CommentSentiment(
            sentiment_score=sentiment_score,
            confidence=confidence,
            upvotes=upvotes,
            quality_score=quality_score
        )
    
    def analyze_post_sentiment(self, comments: List[Dict]) -> PostSentiment:
        """Analyze overall sentiment from all comments"""
        if not comments:
            return PostSentiment(0.0, 0.0, [], 0.0, 0, 0.0)
        
        comment_sentiments = []
        
        # Analyze each comment
        for comment in comments:
            sentiment = self.analyze_comment_sentiment(
                comment['body'], 
                comment['score']
            )
            comment_sentiments.append(sentiment)
        
        # Filter for quality comments only
        quality_sentiments = [s for s in comment_sentiments if s.quality_score > 0.4]
        
        if not quality_sentiments:
            return PostSentiment(0.0, 0.0, [], 0.0, len(comments), 0.0)
        
        # Calculate weighted consensus
        total_weight = 0
        weighted_sentiment = 0
        
        for sentiment in quality_sentiments:
            # Weight by upvotes and quality
            weight = (sentiment.upvotes + 1) * sentiment.quality_score * sentiment.confidence
            weighted_sentiment += sentiment.sentiment_score * weight
            total_weight += weight
        
        consensus_score = weighted_sentiment / total_weight if total_weight > 0 else 0.0
        
        # Find outliers (comments that significantly disagree with consensus)
        outliers = []
        consensus_threshold = 0.4  # How far from consensus to be considered outlier
        
        for sentiment in quality_sentiments:
            if abs(sentiment.sentiment_score - consensus_score) > consensus_threshold:
                outliers.append(sentiment.sentiment_score)
        
        # Calculate overall confidence
        sentiment_scores = [s.sentiment_score for s in quality_sentiments]
        if len(sentiment_scores) > 1:
            std_dev = statistics.stdev(sentiment_scores)
            confidence = max(0.0, 1.0 - std_dev)  # Lower std dev = higher confidence
        else:
            confidence = 0.5
        
        # Engagement weight (how much the upvotes support the sentiment)
        total_upvotes = sum(s.upvotes for s in quality_sentiments)
        engagement_weight = min(1.0, total_upvotes / 100)  # Normalize to 0-1
        
        # Overall quality score
        avg_quality = sum(s.quality_score for s in quality_sentiments) / len(quality_sentiments)
        
        return PostSentiment(
            consensus_score=consensus_score,
            confidence=confidence,
            outlier_scores=outliers[:5],  # Limit to top 5 outliers
            engagement_weight=engagement_weight,
            total_comments=len(comments),
            quality_score=avg_quality
        )


class RedditQualityFilter:
    """Filters low-quality Reddit content"""
    
    def __init__(self, config: Dict):
        self.min_comment_karma = config.get('min_comment_karma', 50)
        self.exclude_joke_keywords = config.get('exclude_joke_keywords', [
            'lmao', '/s', 'this is a joke', 'shitpost', 'lol', 'meme'
        ])
    
    def is_quality_post(self, post: RedditPost) -> bool:
        """Determine if a post meets quality standards"""
        if post.score < 10 or post.upvote_ratio < 0.3:
            return False
        
        title_lower = post.title.lower()
        spam_indicators = ['upvote if', 'like if', 'click here']
        if any(indicator in title_lower for indicator in spam_indicators):
            return False
        
        return True



class RedditSentimentAnalyzer:
    """Analyzes sentiment from Reddit comments"""
    
    def __init__(self):
        # Positive sentiment indicators
        self.positive_keywords = [
            'great', 'amazing', 'excellent', 'fantastic', 'wonderful', 'brilliant',
            'impressive', 'outstanding', 'awesome', 'perfect', 'love', 'best',
            'incredible', 'revolutionary', 'breakthrough', 'game-changer', 'excited',
            'promising', 'hopeful', 'optimistic', 'beneficial', 'valuable', 'useful'
        ]
        
        # Negative sentiment indicators  
        self.negative_keywords = [
            'terrible', 'awful', 'horrible', 'bad', 'worst', 'hate', 'disgusting',
            'disappointing', 'failure', 'disaster', 'concerning', 'worried', 'dangerous',
            'problematic', 'useless', 'waste', 'ridiculous', 'stupid', 'broken',
            'flawed', 'misleading', 'scam', 'overrated', 'hyped', 'skeptical'
        ]
        
        # Neutral/uncertainty indicators
        self.neutral_keywords = [
            'maybe', 'perhaps', 'possibly', 'might', 'could', 'uncertain',
            'unclear', 'mixed', 'complicated', 'depends', 'varies', 'interesting'
        ]
    
    def analyze_comment_sentiment(self, comment_text: str, upvotes: int) -> CommentSentiment:
        """Analyze sentiment of individual comment"""
        text_lower = comment_text.lower()
        
        # Count sentiment indicators
        positive_count = sum(1 for word in self.positive_keywords if word in text_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in text_lower)
        neutral_count = sum(1 for word in self.neutral_keywords if word in text_lower)
        
        # Calculate base sentiment score
        if positive_count + negative_count == 0:
            sentiment_score = 0.0  # Neutral
            confidence = 0.3      # Low confidence for neutral
        else:
            sentiment_score = (positive_count - negative_count) / (positive_count + negative_count + 1)
            confidence = min(0.9, (positive_count + negative_count) / 10)
        
        # Adjust for neutral indicators  
        if neutral_count > 0:
            sentiment_score *= 0.7  # Reduce strength
            confidence *= 0.8       # Reduce confidence
        
        # Quality scoring based on comment characteristics
        quality_score = 0.5  # Base quality
        
        # Length indicates thoughtfulness (to a point)
        word_count = len(comment_text.split())
        if 10 <= word_count <= 100:
            quality_score += 0.2
        elif word_count > 100:
            quality_score += 0.1
        
        # Upvotes indicate community agreement
        if upvotes > 10:
            quality_score += 0.2
        elif upvotes > 50:
            quality_score += 0.3
        
        # Penalize very short or very long comments
        if word_count < 5:
            quality_score -= 0.3
        elif word_count > 200:
            quality_score -= 0.2
        
        quality_score = max(0.0, min(1.0, quality_score))
        
        return CommentSentiment(
            sentiment_score=sentiment_score,
            confidence=confidence,
            upvotes=upvotes,
            quality_score=quality_score
        )
    
    def analyze_post_sentiment(self, comments: List[Dict]) -> PostSentiment:
        """Analyze overall sentiment from all comments"""
        if not comments:
            return PostSentiment(0.0, 0.0, [], 0.0, 0, 0.0)
        
        comment_sentiments = []
        
        # Analyze each comment
        for comment in comments:
            sentiment = self.analyze_comment_sentiment(
                comment['body'], 
                comment['score']
            )
            comment_sentiments.append(sentiment)
        
        # Filter for quality comments only
        quality_sentiments = [s for s in comment_sentiments if s.quality_score > 0.4]
        
        if not quality_sentiments:
            return PostSentiment(0.0, 0.0, [], 0.0, len(comments), 0.0)
        
        # Calculate weighted consensus
        total_weight = 0
        weighted_sentiment = 0
        
        for sentiment in quality_sentiments:
            # Weight by upvotes and quality
            weight = (sentiment.upvotes + 1) * sentiment.quality_score * sentiment.confidence
            weighted_sentiment += sentiment.sentiment_score * weight
            total_weight += weight
        
        consensus_score = weighted_sentiment / total_weight if total_weight > 0 else 0.0
        
        # Find outliers (comments that significantly disagree with consensus)
        outliers = []
        consensus_threshold = 0.4
        
        for sentiment in quality_sentiments:
            if abs(sentiment.sentiment_score - consensus_score) > consensus_threshold:
                outliers.append(sentiment.sentiment_score)
        
        # Calculate overall confidence
        sentiment_scores = [s.sentiment_score for s in quality_sentiments]
        if len(sentiment_scores) > 1:
            std_dev = statistics.stdev(sentiment_scores)
            confidence = max(0.0, 1.0 - std_dev)
        else:
            confidence = 0.5
        
        # Engagement weight
        total_upvotes = sum(s.upvotes for s in quality_sentiments)
        engagement_weight = min(1.0, total_upvotes / 100)
        
        # Overall quality score
        avg_quality = sum(s.quality_score for s in quality_sentiments) / len(quality_sentiments)
        
        return PostSentiment(
            consensus_score=consensus_score,
            confidence=confidence,
            outlier_scores=outliers[:5],
            engagement_weight=engagement_weight,
            total_comments=len(comments),
            quality_score=avg_quality
        )



class RedditRateLimiter:
    """Rate limiting for Reddit API"""
    
    def __init__(self, requests_per_minute: int = 80):
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    async def acquire(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.1f} seconds")
                await asyncio.sleep(sleep_time)
        
        self.request_times.append(current_time)


class RedditClient:
    """Reddit API client with rate limiting"""
    
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            ratelimit_seconds=300
        )
        self.rate_limiter = RedditRateLimiter()
        self.quality_filter = None
    
    async def get_subreddit_posts(self, subreddit_name: str, 
                                 time_filter: str = "day",
                                 limit: int = 25,
                                 min_upvotes: int = 100) -> List[RedditPost]:
        """Get quality posts from a subreddit"""
        posts = []
        
        try:
            await self.rate_limiter.acquire()
            
            subreddit = self.reddit.subreddit(subreddit_name)
            submissions = subreddit.top(time_filter=time_filter, limit=limit * 2)
            
            for submission in submissions:
                if submission.score < min_upvotes:
                    continue
                
                post = RedditPost(
                    id=submission.id,
                    title=submission.title,
                    selftext=submission.selftext,
                    url=submission.url,
                    subreddit=subreddit_name,
                    author=str(submission.author) if submission.author else '[deleted]',
                    score=submission.score,
                    upvote_ratio=submission.upvote_ratio,
                    num_comments=submission.num_comments,
                    awards_received=submission.total_awards_received,
                    created_utc=submission.created_utc,
                    permalink=f"https://reddit.com{submission.permalink}",
                    is_self=submission.is_self
                )
                
                if self.quality_filter and self.quality_filter.is_quality_post(post):
                    posts.append(post)
                    if len(posts) >= limit:
                        break
            
            logger.info(f"Retrieved {len(posts)} quality posts from r/{subreddit_name}")
            return posts
            
        except prawcore.exceptions.Forbidden:
            logger.error(f"Access forbidden to r/{subreddit_name}")
            return []
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            return []

    # ADD THIS NEW METHOD HERE:
    async def get_post_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """Get quality comments for sentiment analysis"""
        comments = []
        
        try:
            await self.rate_limiter.acquire()
            
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=3)  # Load more comments
            
            # Flatten comment tree and sort by score
            all_comments = submission.comments.list()
            all_comments.sort(key=lambda c: c.score, reverse=True)
            
            for comment in all_comments[:limit]:
                if hasattr(comment, 'body') and comment.body and comment.body not in ['[deleted]', '[removed]']:
                    comment_dict = {
                        'id': comment.id,
                        'body': comment.body,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'score': comment.score,
                        'created_utc': comment.created_utc,
                        'awards_received': getattr(comment, 'total_awards_received', 0),
                        'is_submitter': comment.is_submitter
                    }
                    
                    # Basic quality filtering for sentiment analysis
                    if len(comment.body.strip()) >= 20 and comment.score >= -2:
                        comments.append(comment_dict)
            
            logger.debug(f"Retrieved {len(comments)} comments for sentiment analysis")
            return comments
            
        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []


class RedditSource(ContentSource):
    """Reddit content source"""
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        
        # Initialize Reddit client
        self.client = RedditClient(
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            user_agent=config['user_agent']
        )
        
        # Initialize quality filter
        self.quality_filter = RedditQualityFilter(config.get('quality_control', {}))
        self.client.quality_filter = self.quality_filter
        
        # Subreddit configuration
        self.subreddit_configs = {
            sub['name']: sub for sub in config.get('subreddits', [])
        }
        
        # Default high-quality subreddits
        self.default_subreddits = [
            {'name': 'technology', 'min_upvotes': 200, 'category': 'tech'},
            {'name': 'science', 'min_upvotes': 300, 'category': 'cutting_edge'},
            {'name': 'worldnews', 'min_upvotes': 500, 'category': 'world_news'},
            {'name': 'futurology', 'min_upvotes': 200, 'category': 'cutting_edge'},
            {'name': 'artificial', 'min_upvotes': 100, 'category': 'tech'},
            {'name': 'MachineLearning', 'min_upvotes': 100, 'category': 'cutting_edge'},
        ]
    
    async def fetch_content(self, hours: int = 24) -> List[Article]:
        """Fetch Reddit content and convert to Article format"""
        articles = []
        
        # Use configured subreddits or defaults
        subreddits_to_fetch = self.subreddit_configs if self.subreddit_configs else {
            sub['name']: sub for sub in self.default_subreddits
        }
        
        for subreddit_name, config in subreddits_to_fetch.items():
            logger.info(f"Fetching from r/{subreddit_name}")
            
            posts = await self.client.get_subreddit_posts(
                subreddit_name=subreddit_name,
                time_filter="day",
                limit=config.get('limit', 25),
                min_upvotes=config.get('min_upvotes', 100)
            )
            
            for post in posts:
                article = self._convert_post_to_article(post, config)
                if article:
                    articles.append(article)
        
        logger.info(f"Fetched {len(articles)} articles from Reddit")
        return articles
    
    async def _convert_post_to_article(self, post: RedditPost, config: Dict) -> Optional[Article]:
        """Convert a Reddit post to an Article with sentiment analysis"""
        importance_score = self._calculate_reddit_importance(post)
        
        # Build content
        content = post.selftext
        if not post.is_self and post.url:
            content += f"\n\nLinked URL: {post.url}"
        
        # Add sentiment analysis if enabled and enough comments
        sentiment_summary = ""
        sentiment = None
        
        if config.get('sentiment_analysis', True) and post.num_comments >= 5:
            try:
                print(f"🔍 Analyzing sentiment for post with {post.num_comments} comments: {post.title[:50]}...")
                
                # FIX: Properly await the async function
                comments = await self.client.get_post_comments(post.id, limit=15)  # Reduced from 20 to 15
                
                if comments:
                    print(f"📊 Retrieved {len(comments)} comments for analysis")
                    
                    # Analyze sentiment
                    analyzer = RedditSentimentAnalyzer()
                    sentiment = analyzer.analyze_post_sentiment(comments)
                    
                    # Add sentiment to content
                    sentiment_summary = self._build_sentiment_summary(sentiment)
                    content += sentiment_summary
                    
                    # Boost importance for posts with strong community engagement
                    if sentiment.engagement_weight > 0.5 and sentiment.quality_score > 0.6:
                        importance_score += 0.5
                        print(f"✨ Boosted importance score due to high engagement")
                        
                else:
                    print(f"⚠️ No quality comments found for analysis")
                    
            except Exception as e:
                print(f"❌ Error analyzing sentiment for post {post.id}: {e}")
                logger.warning(f"Error analyzing sentiment for post {post.id}: {e}")
        
        # Create enhanced summary with sentiment
        summary = self._create_reddit_summary(post)
        if sentiment:
            sentiment_brief = self._format_sentiment_brief(sentiment)
            summary += f" Community sentiment: {sentiment_brief}"
        
        # Create Article object
        article = Article(
            title=f"[Reddit] {post.title}",
            summary=summary,
            content=content,
            url=post.permalink,
            category=config.get('category', 'reddit'),
            source=f"r/{post.subreddit}",
            published_date=datetime.fromtimestamp(post.created_utc).isoformat(),
            importance_score=importance_score,
            word_count=len(content.split()),
            language='en',
            url_hash=self._generate_reddit_hash(post),
            processed=False
        )
        
        return article


    # Also need to update the calling method in fetch_content:
    async def fetch_content(self, hours: int = 24) -> List[Article]:
        """Fetch Reddit content and convert to Article format"""
        articles = []
        
        # Use configured subreddits or defaults
        subreddits_to_fetch = self.subreddit_configs if self.subreddit_configs else {
            sub['name']: sub for sub in self.default_subreddits
        }
        
        for subreddit_name, config in subreddits_to_fetch.items():
            logger.info(f"Fetching from r/{subreddit_name}")
            
            posts = await self.client.get_subreddit_posts(
                subreddit_name=subreddit_name,
                time_filter="day",
                limit=config.get('limit', 25),
                min_upvotes=config.get('min_upvotes', 100)
            )
            
            for post in posts:
                # FIX: Await the async method
                article = await self._convert_post_to_article(post, config)
                if article:
                    articles.append(article)
        
        logger.info(f"Fetched {len(articles)} articles from Reddit")
        return articles

    def _build_sentiment_summary(self, sentiment: PostSentiment) -> str:
        """Build detailed sentiment summary for article content"""
        if sentiment.total_comments == 0:
            return ""
        
        summary = f"\n\n--- Community Sentiment Analysis ---"
        summary += f"\nAnalyzed {sentiment.total_comments} comments:"
        
        # Consensus sentiment
        if sentiment.consensus_score > 0.3:
            consensus = "positive"
        elif sentiment.consensus_score < -0.3:
            consensus = "negative"
        else:
            consensus = "mixed/neutral"
        
        summary += f"\n• Overall sentiment: {consensus} (score: {sentiment.consensus_score:.2f})"
        summary += f"\n• Community confidence: {sentiment.confidence:.0%}"
        summary += f"\n• Engagement level: {sentiment.engagement_weight:.0%}"
        
        # Outliers
        if sentiment.outlier_scores:
            summary += f"\n• Dissenting opinions detected: {len(sentiment.outlier_scores)} comments"
            
        summary += f"\n• Discussion quality: {sentiment.quality_score:.0%}"
        
        return summary

    def _format_sentiment_brief(self, sentiment: PostSentiment) -> str:
        """Format brief sentiment for article summary"""
        if sentiment.consensus_score > 0.3:
            return f"generally positive ({sentiment.confidence:.0%} confidence)"
        elif sentiment.consensus_score < -0.3:
            return f"generally negative ({sentiment.confidence:.0%} confidence)"
        else:
            return f"mixed reactions ({sentiment.total_comments} comments)"
    
    def _calculate_reddit_importance(self, post: RedditPost) -> float:
        """Calculate importance score based on Reddit engagement"""
        score = 0.0
        
        # Base score from upvotes
        if post.score > 0:
            score += min(3.0, (post.score / 1000) * 2)
        
        # Comment engagement bonus
        if post.num_comments > 0:
            score += min(2.0, (post.num_comments / 100) * 1.5)
        
        # Awards indicate quality
        if post.awards_received > 0:
            score += min(2.0, post.awards_received * 0.5)
        
        # Upvote ratio indicates consensus
        if post.upvote_ratio > 0.8:
            score += 1.0
        elif post.upvote_ratio < 0.6:
            score -= 1.0
        
        # Time decay
        hours_old = (time.time() - post.created_utc) / 3600
        if hours_old < 6:
            score += 0.5
        elif hours_old > 24:
            score -= 0.5
        
        return min(score, 10.0)
    
    def _create_reddit_summary(self, post: RedditPost) -> str:
        """Create a summary for Reddit posts"""
        summary = f"Reddit discussion in r/{post.subreddit}"
        
        if post.score > 1000:
            summary += f" with {post.score:,} upvotes"
        
        if post.num_comments > 50:
            summary += f" and {post.num_comments} comments"
        
        if post.awards_received > 0:
            summary += f" ({post.awards_received} awards)"
        
        if post.selftext:
            snippet = post.selftext[:200] + "..." if len(post.selftext) > 200 else post.selftext
            summary += f". {snippet}"
        
        return summary
    
    def _generate_reddit_hash(self, post: RedditPost) -> str:
        """Generate unique hash for Reddit post"""
        return hashlib.md5(f"reddit_{post.id}".encode()).hexdigest()
    
    def get_source_type(self) -> str:
        return "reddit"
    
    def validate_config(self) -> bool:
        """Validate Reddit configuration"""
        required_keys = ['client_id', 'client_secret', 'user_agent']
        for key in required_keys:
            if key not in self.config:
                logger.error(f"Missing required Reddit config key: {key}")
                return False
        
        try:
            # Test Reddit connection
            self.client.reddit.user.me()
            return True
        except Exception as e:
            logger.error(f"Reddit authentication failed: {e}")
            return False
        


