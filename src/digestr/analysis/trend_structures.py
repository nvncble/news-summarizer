#!/usr/bin/env python3
"""
Trend Analysis Data Structures
Core data classes for trending topic analysis and correlation
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
import json


@dataclass
class TrendingTopic:
    """A trending topic detected from any source"""
    keyword: str
    aliases: List[str] = field(default_factory=list)
    category: str = "general"
    source: str = ""  # trends24, twitter, youtube, etc.
    region: str = "worldwide"
    
    # Trend metrics
    velocity: float = 0.0      # How fast it's trending (0-1)
    reach: int = 0             # How many sources mention it
    momentum: str = "emerging" # emerging, peak, declining
    rank: int = 0             # Position in trending list
    
    # Timeline
    first_detected: Optional[datetime] = None
    peak_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    # Correlation data
    correlation_score: float = 0.0     # Overall correlation across sources
    geographic_relevance: float = 0.0  # Relevance to user's location
    is_active: bool = True
    
    # Related content
    related_articles: List[str] = field(default_factory=list)  # URLs
    related_posts: List[str] = field(default_factory=list)     # Post IDs
    
    def __post_init__(self):
        if self.first_detected is None:
            self.first_detected = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'keyword': self.keyword,
            'aliases': json.dumps(self.aliases),
            'category': self.category,
            'source': self.source,
            'region': self.region,
            'velocity': self.velocity,
            'reach': self.reach,
            'momentum': self.momentum,
            'first_detected': self.first_detected.isoformat() if self.first_detected else None,
            'peak_time': self.peak_time.isoformat() if self.peak_time else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'correlation_score': self.correlation_score,
            'geographic_relevance': self.geographic_relevance,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrendingTopic':
        """Create from dictionary/database row"""
        return cls(
            keyword=data['keyword'],
            aliases=json.loads(data.get('aliases', '[]')),
            category=data.get('category', 'general'),
            source=data.get('source', ''),
            region=data.get('region', 'worldwide'),
            velocity=data.get('velocity', 0.0),
            reach=data.get('reach', 0),
            momentum=data.get('momentum', 'emerging'),
            first_detected=datetime.fromisoformat(data['first_detected']) if data.get('first_detected') else None,
            peak_time=datetime.fromisoformat(data['peak_time']) if data.get('peak_time') else None,
            last_updated=datetime.fromisoformat(data['last_updated']) if data.get('last_updated') else None,
            correlation_score=data.get('correlation_score', 0.0),
            geographic_relevance=data.get('geographic_relevance', 0.0),
            is_active=data.get('is_active', True)
        )


@dataclass
class TrendCorrelation:
    """Correlation between trending topic and content"""
    trend_keyword: str
    content_id: str           # Article URL or post ID
    content_source: str       # rss, reddit, etc.
    correlation_strength: float  # 0-1
    correlation_type: str     # exact, semantic, contextual, etc.
    match_types: List[str] = field(default_factory=list)  # Which methods found the match
    detected_at: Optional[datetime] = None
    is_cross_source: bool = False  # True if trend appears in multiple sources
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'trend_keyword': self.trend_keyword,
            'content_id': self.content_id,
            'content_source': self.content_source,
            'correlation_strength': self.correlation_strength,
            'correlation_type': self.correlation_type,
            'match_types': json.dumps(self.match_types),
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'is_cross_source': self.is_cross_source
        }


@dataclass
class GeographicConfig:
    """Geographic configuration for trend filtering"""
    country: str = "United States"
    state: Optional[str] = None
    city: Optional[str] = None
    include_national: bool = True
    
    def get_location_keywords(self) -> List[str]:
        """Get location-based keywords for trend filtering"""
        keywords = []
        if self.country == "United States":
            keywords.extend(["United States", "US", "USA", "America", "American"])
        if self.state:
            keywords.extend([self.state, self.get_state_abbreviation()])
        if self.city:
            keywords.append(self.city)
        return keywords
    
    def get_state_abbreviation(self) -> Optional[str]:
        """Get state abbreviation from full name"""
        state_abbrevs = {
            "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
            "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
            "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
            "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
            "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
            "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
            "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
            "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
            "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
            "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
            "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
            "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
            "Wisconsin": "WI", "Wyoming": "WY"
        }
        return state_abbrevs.get(self.state)


@dataclass
class CrossSourceTrendAnalysis:
    """Results of cross-source trend analysis"""
    triple_coverage: List[Dict] = field(default_factory=list)    # trends24 + rss + reddit
    double_coverage: List[Dict] = field(default_factory=list)    # 2 sources
    single_coverage: List[Dict] = field(default_factory=list)    # just trends24
    geographic_trends: List[Dict] = field(default_factory=list)  # location-specific
    emerging_signals: List[Dict] = field(default_factory=list)   # weak but potentially important
    
    total_trends: int = 0
    correlation_count: int = 0
    analysis_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.analysis_timestamp is None:
            self.analysis_timestamp = datetime.now()
        
        self.total_trends = (
            len(self.triple_coverage) + 
            len(self.double_coverage) + 
            len(self.single_coverage) + 
            len(self.geographic_trends) + 
            len(self.emerging_signals)
        )
    
    def get_significant_trends(self) -> List[Dict]:
        """Get most significant trends (triple and strong double coverage)"""
        significant = self.triple_coverage.copy()
        significant.extend([t for t in self.double_coverage if self._is_significant_double(t)])
        return sorted(significant, key=lambda x: x.get('total_strength', 0), reverse=True)
    
    def _is_significant_double(self, trend_data: Dict) -> bool:
        """Determine if double coverage trend is significant enough"""
        return (
            trend_data.get('total_strength', 0) > 0.7 or
            len(trend_data.get('rss_matches', [])) > 2 or
            len(trend_data.get('reddit_matches', [])) > 3
        )