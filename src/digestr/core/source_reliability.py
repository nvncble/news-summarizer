"""
Source Reliability Scoring System
Tracks and scores news source reliability
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SourceReliabilityScorer:
    """Score news sources based on reliability factors"""
    
    def __init__(self):
        # Base reliability scores (0-10 scale)
        self.base_scores = {
            # Top tier sources
            "Reuters": 9.5,
            "Associated Press": 9.5,
            "BBC": 9.0,
            "NPR": 9.0,
            "The Guardian": 8.5,
            "The New York Times": 8.5,
            "Nature": 9.5,
            "Science": 9.5,
            "ArXiv": 8.0,  # Pre-print, so slightly lower
            
            # Tech sources
            "Ars Technica": 8.5,
            "The Verge": 7.5,
            "TechCrunch": 7.0,
            "Wired": 8.0,
            "Engadget": 7.0,
            "VentureBeat": 6.5,
            
            # Business sources
            "Bloomberg": 8.5,
            "Financial Times": 9.0,
            "The Economist": 9.0,
            "Wall Street Journal": 8.5,
            
            # Other sources
            "Fox News": 6.0,
            "Breitbart": 4.0,
            "InfoWars": 2.0,
            
            # Reddit (varies by subreddit)
            "r/science": 7.5,
            "r/technology": 6.0,
            "r/worldnews": 6.5,
            "r/MachineLearning": 7.0,
            "r/artificial": 6.0,
            
            # Default scores by domain
            "arxiv.org": 8.0,
            "nature.com": 9.5,
            "sciencemag.org": 9.5,
            "ieee.org": 8.5,
            "acm.org": 8.5,
        }
        
        # Category modifiers
        self.category_modifiers = {
            "cutting_edge": 0.5,  # Boost for scientific sources
            "security": 0.3,      # Boost for security news
            "tech": 0.0,
            "business": 0.0,
            "world_news": 0.0,
            "sports": -0.5,       # Less critical for sports
        }
    
    def get_source_reliability(self, source: str, category: str = None, url: str = None) -> float:
        """Get reliability score for a source"""
        
        # Direct match
        if source in self.base_scores:
            score = self.base_scores[source]
        else:
            # Try domain matching
            score = self._score_by_domain(source, url)
        
        # Apply category modifier
        if category and category in self.category_modifiers:
            score += self.category_modifiers[category]
        
        # Ensure score is between 0 and 10
        return max(0.0, min(10.0, score))
    
    def _score_by_domain(self, source: str, url: str = None) -> float:
        """Score based on domain patterns"""
        
        # Check domain from URL
        if url:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            
            # Check known domains
            for known_domain, score in self.base_scores.items():
                if known_domain.lower() in domain:
                    return score
        
        # Default scores by type
        source_lower = source.lower()
        
        if 'university' in source_lower or '.edu' in source_lower:
            return 8.0
        elif 'institute' in source_lower or 'laboratory' in source_lower:
            return 7.5
        elif 'journal' in source_lower:
            return 7.0
        elif 'blog' in source_lower:
            return 5.0
        else:
            return 6.0  # Default middle score
    
    def adjust_importance_score(self, article: Dict, boost_factor: float = 0.3) -> float:
        """Adjust article importance based on source reliability"""
        
        source = article.get('source', '')
        category = article.get('category', '')
        url = article.get('url', '')
        current_score = article.get('importance_score', 0.0)
        
        reliability = self.get_source_reliability(source, category, url)
        
        # Boost importance for highly reliable sources
        if reliability >= 8.0:
            boost = (reliability - 7.0) * boost_factor
            return current_score + boost
        # Penalize unreliable sources
        elif reliability < 5.0:
            penalty = (5.0 - reliability) * boost_factor
            return max(0.0, current_score - penalty)
        else:
            return current_score