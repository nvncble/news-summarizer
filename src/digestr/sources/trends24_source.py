#!/usr/bin/env python3
"""
Trends24.in Source Implementation
Scrapes trending topics from Trends24.in with geographic filtering
"""

import asyncio
import aiohttp
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin
import logging

from digestr.analysis.trend_structures import TrendingTopic, GeographicConfig

logger = logging.getLogger(__name__)


class Trends24Source:
    """Scrape trending topics from Trends24.in"""
    
    def __init__(self, geo_config: GeographicConfig):
        self.geo_config = geo_config
        self.base_url = "https://trends24.in"
        self.last_fetch_time = None
        self.cache_duration = 300  # 5 minutes cache
        self.cached_trends = {}
        
        # Rate limiting
        self.request_delay = 2  # seconds between requests
        self.last_request_time = 0
        
        # Headers to appear more like a regular browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def fetch_trending_topics(self, regions: List[str] = None) -> List[TrendingTopic]:
        """Fetch current trending topics with geographic filtering"""
        
        if regions is None:
            regions = self.get_default_regions()
        
        all_trends = []
        
        for region in regions:
            try:
                regional_trends = await self._scrape_region_trends(region)
                all_trends.extend(regional_trends)
                
                # Rate limiting between regions
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error fetching trends for region {region}: {e}")
                continue
        
        # Deduplicate and score
        unique_trends = self._deduplicate_and_score(all_trends)
        
        # Apply geographic relevance scoring
        for trend in unique_trends:
            trend.geographic_relevance = self._score_geographic_relevance(trend)
        
        logger.info(f"Fetched {len(unique_trends)} unique trending topics from {len(regions)} regions")
        return unique_trends
    
    def get_default_regions(self) -> List[str]:
        """Get default regions based on geographic config"""
        regions = []
        
        if self.geo_config.include_national:
            regions.append("united-states")
        
        # Add state-specific if configured
        if self.geo_config.state:
            state_slug = self.geo_config.state.lower().replace(' ', '-')
            regions.append(f"us-{state_slug}")
        
        # Add major cities if configured
        if self.geo_config.city:
            city_mappings = {
                "New York": "new-york",
                "Los Angeles": "los-angeles", 
                "Chicago": "chicago",
                "Houston": "houston",
                "Phoenix": "phoenix",
                "Philadelphia": "philadelphia",
                "San Antonio": "san-antonio",
                "San Diego": "san-diego",
                "Dallas": "dallas",
                "San Jose": "san-jose"
            }
            city_slug = city_mappings.get(self.geo_config.city)
            if city_slug:
                regions.append(f"us-{city_slug}")
        
        return regions
    
    async def _scrape_region_trends(self, region: str) -> List[TrendingTopic]:
        """Scrape trends for specific region"""
        
        # Check cache first
        if self._is_cache_valid(region):
            logger.debug(f"Using cached trends for {region}")
            return self.cached_trends[region]
        
        await self._respect_rate_limit()
        
        url = f"{self.base_url}/{region}/"
        trends = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return []
                    
                    html = await response.text()
                    trends = self._parse_trends_from_html(html, region)
                    
                    # Cache the results
                    self.cached_trends[region] = trends
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return []
        
        return trends
    
    def _parse_trends_from_html(self, html: str, region: str) -> List[TrendingTopic]:
        """Parse trending topics from HTML"""
        
        trends = []
        
        try:
            # Multiple parsing strategies since website structure may vary
            trends.extend(self._parse_twitter_trends(html, region))
            trends.extend(self._parse_general_trends(html, region))
            
        except Exception as e:
            logger.error(f"Error parsing HTML for {region}: {e}")
        
        return trends
    
    def _parse_twitter_trends(self, html: str, region: str) -> List[TrendingTopic]:
        """Parse Twitter trends section"""
        
        trends = []
        
        # Look for Twitter trends section
        twitter_section_pattern = r'<div[^>]*twitter[^>]*>.*?</div>'
        twitter_matches = re.findall(twitter_section_pattern, html, re.DOTALL | re.IGNORECASE)
        
        for section in twitter_matches:
            # Extract trending hashtags and terms
            trend_patterns = [
                r'#(\w+)',  # Hashtags
                r'<a[^>]*>([^<]+)</a>',  # Links
                r'<span[^>]*trend[^>]*>([^<]+)</span>',  # Trend spans
            ]
            
            for pattern in trend_patterns:
                matches = re.findall(pattern, section, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match[0] else match[1]
                    
                    trend_text = self._clean_trend_text(match)
                    if self._is_valid_trend(trend_text):
                        trend = TrendingTopic(
                            keyword=trend_text,
                            source="trends24",
                            region=region,
                            category=self._categorize_trend(trend_text),
                            velocity=0.5,  # Default velocity
                            momentum="emerging"
                        )
                        trends.append(trend)
        
        return trends
    
    def _parse_general_trends(self, html: str, region: str) -> List[TrendingTopic]:
        """Parse general trends from various sections"""
        
        trends = []
        
        # Look for trend containers
        trend_patterns = [
            r'<li[^>]*>.*?<a[^>]*>([^<]+)</a>.*?</li>',
            r'<div[^>]*trend[^>]*>.*?<span[^>]*>([^<]+)</span>.*?</div>',
            r'<tr[^>]*>.*?<td[^>]*>([^<]+)</td>.*?</tr>',
        ]
        
        for pattern in trend_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                trend_text = self._clean_trend_text(match)
                if self._is_valid_trend(trend_text):
                    # Try to extract rank/position
                    rank = self._extract_rank_from_context(html, trend_text)
                    
                    trend = TrendingTopic(
                        keyword=trend_text,
                        source="trends24",
                        region=region,
                        category=self._categorize_trend(trend_text),
                        rank=rank,
                        velocity=max(0.3, 1.0 - (rank * 0.05)) if rank else 0.5,
                        momentum="emerging"
                    )
                    trends.append(trend)
        
        return trends
    
    def _clean_trend_text(self, text: str) -> str:
        """Clean and normalize trend text"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep hashtags
        if not text.startswith('#'):
            text = re.sub(r'[^\w\s\-\']', '', text)
        
        return text.strip()
    
    def _is_valid_trend(self, trend_text: str) -> bool:
        """Validate if trend text is worth including"""
        if not trend_text or len(trend_text) < 2:
            return False
        
        # Skip very long trends (likely not real trends)
        if len(trend_text) > 100:
            return False
        
        # Skip if it's just numbers
        if trend_text.isdigit():
            return False
        
        # Skip common non-trend words
        skip_words = {
            'trending', 'trends', 'twitter', 'hashtag', 'follow', 'like', 
            'share', 'click', 'here', 'more', 'news', 'today'
        }
        if trend_text.lower() in skip_words:
            return False
        
        return True
    
    def _categorize_trend(self, trend_text: str) -> str:
        """Basic categorization of trend"""
        trend_lower = trend_text.lower()
        
        # Political keywords
        if any(word in trend_lower for word in ['election', 'president', 'congress', 'senate', 'vote', 'politics', 'biden', 'trump']):
            return 'politics'
        
        # Technology keywords
        if any(word in trend_lower for word in ['ai', 'tech', 'apple', 'google', 'microsoft', 'iphone', 'android', 'crypto']):
            return 'tech'
        
        # Sports keywords
        if any(word in trend_lower for word in ['nfl', 'nba', 'mlb', 'nhl', 'soccer', 'football', 'basketball', 'game']):
            return 'sports'
        
        # Entertainment keywords
        if any(word in trend_lower for word in ['movie', 'tv', 'netflix', 'celebrity', 'music', 'album', 'concert']):
            return 'entertainment'
        
        # Business keywords
        if any(word in trend_lower for word in ['stock', 'market', 'business', 'economy', 'earnings', 'company']):
            return 'business'
        
        return 'general'
    
    def _extract_rank_from_context(self, html: str, trend_text: str) -> Optional[int]:
        """Try to extract ranking/position of trend"""
        # Look for numbered lists or ranking indicators
        rank_patterns = [
            rf'(\d+)\.?\s*{re.escape(trend_text)}',
            rf'{re.escape(trend_text)}.*?#(\d+)',
            rf'rank.*?(\d+).*?{re.escape(trend_text)}',
        ]
        
        for pattern in rank_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _deduplicate_and_score(self, trends: List[TrendingTopic]) -> List[TrendingTopic]:
        """Remove duplicates and enhance scoring"""
        
        unique_trends = {}
        
        for trend in trends:
            key = trend.keyword.lower().strip()
            
            if key in unique_trends:
                # Merge with existing trend
                existing = unique_trends[key]
                
                # Keep best rank
                if trend.rank and (not existing.rank or trend.rank < existing.rank):
                    existing.rank = trend.rank
                    existing.velocity = trend.velocity
                
                # Increase reach for multiple regions
                existing.reach += 1
                
                # Update aliases
                if trend.keyword not in existing.aliases:
                    existing.aliases.append(trend.keyword)
                
            else:
                # New trend
                trend.reach = 1
                unique_trends[key] = trend
        
        return list(unique_trends.values())
    
    def _score_geographic_relevance(self, trend: TrendingTopic) -> float:
        """Score geographic relevance to user's location"""
        
        location_keywords = self.geo_config.get_location_keywords()
        trend_text = (trend.keyword + ' ' + trend.region).lower()
        
        relevance = 0.0
        
        # Direct location mentions
        for keyword in location_keywords:
            if keyword.lower() in trend_text:
                relevance += 0.3
        
        # Region-based relevance
        if 'united-states' in trend.region or 'us-' in trend.region:
            relevance += 0.4
        
        # State-specific boost
        if self.geo_config.state and self.geo_config.state.lower().replace(' ', '-') in trend.region:
            relevance += 0.5
        
        # Category-based geographic relevance
        if trend.category in ['politics', 'economy'] and 'us' in trend.region:
            relevance += 0.3
        
        return min(1.0, relevance)
    
    async def _respect_rate_limit(self):
        """Ensure we don't make requests too quickly"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _is_cache_valid(self, region: str) -> bool:
        """Check if cached data is still valid"""
        if region not in self.cached_trends:
            return False
        
        if not self.last_fetch_time:
            return False
        
        age = (datetime.now() - self.last_fetch_time).total_seconds()
        return age < self.cache_duration
    
    async def test_connection(self) -> Dict[str, any]:
        """Test connection to Trends24.in"""
        try:
            trends = await self.fetch_trending_topics(["united-states"])
            return {
                'success': True,
                'trends_found': len(trends),
                'message': f'Successfully scraped {len(trends)} trends'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_source_status(self) -> Dict[str, any]:
        """Get source status information"""
        return {
            'enabled': True,
            'type': 'trends',
            'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            'cached_regions': list(self.cached_trends.keys()),
            'geographic_config': {
                'country': self.geo_config.country,
                'state': self.geo_config.state,
                'city': self.geo_config.city
            }
        }