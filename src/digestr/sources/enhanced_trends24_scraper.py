#!/usr/bin/env python3
"""
Enhanced Trends24.in Scraper with BeautifulSoup
More robust HTML parsing and trend extraction
"""

import asyncio
import aiohttp
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
import logging

try:
    from bs4 import BeautifulSoup, Tag
    import lxml
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logging.warning("BeautifulSoup4 not available. Install with: pip install beautifulsoup4 lxml")

from digestr.analysis.trend_structures import TrendingTopic, GeographicConfig

logger = logging.getLogger(__name__)


class EnhancedTrends24Scraper:
    """Enhanced scraper for Trends24.in with robust HTML parsing"""
    
    def __init__(self, geo_config: GeographicConfig):
        self.geo_config = geo_config
        self.base_url = "https://trends24.in"
        
        # Rate limiting and caching
        self.request_delay = 2
        self.last_request_time = 0
        self.cache_duration = 300  # 5 minutes
        self.cached_results = {}
        
        # Enhanced headers for better success rate
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Patterns for trend extraction
        self.trend_selectors = [
            'li[data-trend]',
            '.trend-item',
            '.trending-topic',
            'a[href*="twitter.com"]',
            '.trend',
            '[class*="trend"]',
            'li > a',
            'span.trend-name',
            '.topic'
        ]
        
        # Categories for classification
        self.category_keywords = {
            'politics': [
                'biden', 'trump', 'congress', 'senate', 'election', 'vote', 'politics',
                'republican', 'democrat', 'president', 'white house', 'government',
                'policy', 'legislation', 'campaign', 'poll'
            ],
            'tech': [
                'ai', 'artificial intelligence', 'tech', 'apple', 'google', 'microsoft',
                'meta', 'tesla', 'iphone', 'android', 'crypto', 'bitcoin', 'blockchain',
                'startup', 'innovation', 'software', 'hardware', 'app', 'platform'
            ],
            'entertainment': [
                'movie', 'film', 'tv', 'netflix', 'disney', 'hollywood', 'celebrity',
                'music', 'album', 'concert', 'tour', 'awards', 'oscar', 'grammy',
                'streaming', 'show', 'series', 'actor', 'actress', 'singer'
            ],
            'sports': [
                'nfl', 'nba', 'mlb', 'nhl', 'soccer', 'football', 'basketball',
                'baseball', 'hockey', 'game', 'match', 'playoff', 'championship',
                'olympics', 'world cup', 'super bowl', 'finals', 'draft', 'trade'
            ],
            'business': [
                'stock', 'market', 'business', 'economy', 'earnings', 'company',
                'ceo', 'finance', 'investment', 'merger', 'acquisition', 'ipo',
                'revenue', 'profit', 'loss', 'growth', 'bankruptcy', 'layoffs'
            ],
            'health': [
                'health', 'medical', 'doctor', 'hospital', 'disease', 'vaccine',
                'covid', 'pandemic', 'virus', 'treatment', 'medicine', 'drug',
                'fda', 'research', 'study', 'clinical', 'patient', 'symptoms'
            ],
            'science': [
                'science', 'research', 'study', 'discovery', 'breakthrough',
                'nasa', 'space', 'climate', 'environment', 'energy', 'renewable',
                'solar', 'wind', 'nuclear', 'physics', 'chemistry', 'biology'
            ]
        }
    
    async def fetch_trending_topics(self, regions: List[str] = None) -> List[TrendingTopic]:
        """Fetch trending topics with enhanced parsing"""
        
        if not BS4_AVAILABLE:
            logger.error("BeautifulSoup4 not available. Falling back to basic parsing.")
            return []
        
        if regions is None:
            regions = self._get_default_regions()
        
        all_trends = []
        
        for region in regions:
            try:
                trends = await self._scrape_region_enhanced(region)
                all_trends.extend(trends)
                
                # Rate limiting
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.error(f"Error fetching trends for region {region}: {e}")
                continue
        
        # Process and deduplicate
        processed_trends = self._process_and_deduplicate(all_trends)
        
        logger.info(f"Enhanced scraper found {len(processed_trends)} unique trends from {len(regions)} regions")
        return processed_trends
    
    async def _scrape_region_enhanced(self, region: str) -> List[TrendingTopic]:
        """Enhanced region scraping with BeautifulSoup"""
        
        # Check cache
        cache_key = f"{region}_{int(time.time() // self.cache_duration)}"
        if cache_key in self.cached_results:
            return self.cached_results[cache_key]
        
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
                    trends = self._parse_with_beautifulsoup(html, region)
                    
                    # Cache results
                    self.cached_results[cache_key] = trends
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        
        return trends
    
    def _parse_with_beautifulsoup(self, html: str, region: str) -> List[TrendingTopic]:
        """Parse HTML using BeautifulSoup for better accuracy"""
        
        trends = []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try multiple parsing strategies
            trends.extend(self._parse_twitter_trends_enhanced(soup, region))
            trends.extend(self._parse_general_trends_enhanced(soup, region))
            trends.extend(self._parse_list_trends_enhanced(soup, region))
            trends.extend(self._parse_table_trends_enhanced(soup, region))
            
        except Exception as e:
            logger.error(f"Error parsing HTML with BeautifulSoup: {e}")
        
        return trends
    
    def _parse_twitter_trends_enhanced(self, soup: BeautifulSoup, region: str) -> List[TrendingTopic]:
        """Parse Twitter trends section with enhanced selectors"""
        
        trends = []
        
        # Look for Twitter-specific containers
        twitter_sections = soup.find_all(['div', 'section'], 
                                       class_=re.compile(r'twitter|trend', re.I))
        
        for section in twitter_sections:
            # Find trend links and items
            trend_elements = section.find_all(['a', 'span', 'li'], 
                                            class_=re.compile(r'trend|topic', re.I))
            
            for element in trend_elements:
                trend_text = self._extract_clean_text(element)
                if self._is_valid_trend_text(trend_text):
                    trend = self._create_trending_topic(trend_text, region, element)
                    if trend:
                        trends.append(trend)
        
        return trends
    
    def _parse_general_trends_enhanced(self, soup: BeautifulSoup, region: str) -> List[TrendingTopic]:
        """Parse general trend containers"""
        
        trends = []
        
        # Try multiple selectors
        for selector in self.trend_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    trend_text = self._extract_clean_text(element)
                    if self._is_valid_trend_text(trend_text):
                        trend = self._create_trending_topic(trend_text, region, element)
                        if trend:
                            trends.append(trend)
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        return trends
    
    def _parse_list_trends_enhanced(self, soup: BeautifulSoup, region: str) -> List[TrendingTopic]:
        """Parse ordered and unordered lists of trends"""
        
        trends = []
        
        # Find lists that might contain trends
        lists = soup.find_all(['ol', 'ul'])
        
        for list_element in lists:
            # Check if this list contains trends
            if self._looks_like_trend_list(list_element):
                items = list_element.find_all('li')
                
                for i, item in enumerate(items):
                    trend_text = self._extract_clean_text(item)
                    if self._is_valid_trend_text(trend_text):
                        trend = self._create_trending_topic(trend_text, region, item)
                        if trend:
                            trend.rank = i + 1  # Set rank based on list position
                            trend.velocity = max(0.3, 1.0 - (i * 0.05))  # Higher rank = higher velocity
                            trends.append(trend)
        
        return trends
    
    def _parse_table_trends_enhanced(self, soup: BeautifulSoup, region: str) -> List[TrendingTopic]:
        """Parse table-based trend layouts"""
        
        trends = []
        
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                
                for cell in cells:
                    trend_text = self._extract_clean_text(cell)
                    if self._is_valid_trend_text(trend_text):
                        trend = self._create_trending_topic(trend_text, region, cell)
                        if trend:
                            trend.rank = i + 1
                            trends.append(trend)
        
        return trends
    
    def _extract_clean_text(self, element) -> str:
        """Extract and clean text from HTML element"""
        
        if not element:
            return ""
        
        # Get text content
        if hasattr(element, 'get_text'):
            text = element.get_text(strip=True)
        else:
            text = str(element).strip()
        
        # Clean up the text
        text = self._clean_trend_text(text)
        
        # If text is still not good, try href attribute for links
        if not text and hasattr(element, 'get') and element.get('href'):
            href = element.get('href')
            # Extract trend from Twitter URL
            if 'twitter.com' in href:
                match = re.search(r'/hashtag/([^?]+)', href)
                if match:
                    text = f"#{match.group(1)}"
        
        return text
    
    def _clean_trend_text(self, text: str) -> str:
        """Enhanced text cleaning"""
        
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            'trending:', 'trend:', '#trending', 'hot:', 'popular:',
            'now trending:', 'currently trending:'
        ]
        
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix):
                text = text[len(prefix):].strip()
        
        # Remove numbered list indicators
        text = re.sub(r'^\d+\.\s*', '', text)
        text = re.sub(r'^\d+\)\s*', '', text)
        
        # Clean special characters but preserve hashtags
        if not text.startswith('#'):
            text = re.sub(r'[^\w\s\-\']', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'\.{2,}', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _is_valid_trend_text(self, text: str) -> bool:
        """Enhanced validation of trend text"""
        
        if not text or len(text.strip()) < 2:
            return False
        
        # Length checks
        if len(text) > 150:  # Very long text unlikely to be a trend
            return False
        
        # Skip pure numbers
        if text.replace('#', '').replace(' ', '').isdigit():
            return False
        
        # Skip common non-trend phrases
        skip_phrases = {
            'trending', 'trends', 'twitter', 'hashtag', 'follow', 'like',
            'share', 'click', 'here', 'more', 'news', 'today', 'now',
            'see more', 'view all', 'show more', 'read more', 'continue',
            'loading', 'error', 'retry', 'refresh', 'home', 'about',
            'privacy', 'terms', 'contact', 'help', 'support'
        }
        
        text_lower = text.lower().strip()
        if text_lower in skip_phrases:
            return False
        
        # Skip if it looks like navigation or UI text
        if any(phrase in text_lower for phrase in ['click here', 'read more', 'see all']):
            return False
        
        # Skip very common words
        if text_lower in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']:
            return False
        
        return True
    
    def _looks_like_trend_list(self, list_element) -> bool:
        """Check if a list element contains trends"""
        
        # Check for trend-related classes
        classes = list_element.get('class', [])
        if any('trend' in str(cls).lower() for cls in classes):
            return True
        
        # Check for trend-related IDs
        element_id = list_element.get('id', '')
        if 'trend' in element_id.lower():
            return True
        
        # Check if parent has trend-related attributes
        parent = list_element.parent
        if parent:
            parent_classes = parent.get('class', [])
            if any('trend' in str(cls).lower() for cls in parent_classes):
                return True
        
        # Check if list items look like trends
        items = list_element.find_all('li')[:5]  # Check first 5 items
        trend_like_count = 0
        
        for item in items:
            text = self._extract_clean_text(item)
            if self._is_valid_trend_text(text):
                trend_like_count += 1
        
        # If more than half look like trends, consider it a trend list
        return trend_like_count > len(items) / 2
    
    def _create_trending_topic(self, text: str, region: str, element) -> Optional[TrendingTopic]:
        """Create TrendingTopic from text and context"""
        
        if not self._is_valid_trend_text(text):
            return None
        
        # Categorize the trend
        category = self._categorize_trend_enhanced(text)
        
        # Extract additional context from element
        velocity = self._estimate_velocity_from_context(element)
        
        trend = TrendingTopic(
            keyword=text,
            category=category,
            source="trends24",
            region=region,
            velocity=velocity,
            momentum="emerging",
            reach=1
        )
        
        return trend
    
    def _categorize_trend_enhanced(self, text: str) -> str:
        """Enhanced trend categorization"""
        
        text_lower = text.lower()
        
        # Score each category
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    # Exact match gets higher score
                    if keyword == text_lower:
                        score += 3
                    # Word boundary match
                    elif re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                        score += 2
                    # Partial match
                    else:
                        score += 1
            
            if score > 0:
                category_scores[category] = score
        
        # Return highest scoring category
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return 'general'
    
    def _estimate_velocity_from_context(self, element) -> float:
        """Estimate trend velocity from HTML context"""
        
        velocity = 0.5  # Default
        
        try:
            # Check for ranking indicators
            text = str(element)
            
            # Look for rank indicators
            rank_match = re.search(r'(?:rank|position|#)[\s:]*(\d+)', text, re.I)
            if rank_match:
                rank = int(rank_match.group(1))
                velocity = max(0.3, 1.0 - (rank * 0.05))
            
            # Look for popularity indicators
            if any(word in text.lower() for word in ['hot', 'trending', 'viral', 'popular']):
                velocity += 0.2
            
            # Look for time indicators
            if any(word in text.lower() for word in ['now', 'live', 'breaking', 'urgent']):
                velocity += 0.3
            
        except Exception:
            pass
        
        return min(1.0, velocity)
    
    def _process_and_deduplicate(self, trends: List[TrendingTopic]) -> List[TrendingTopic]:
        """Process and deduplicate trends with enhanced logic"""
        
        if not trends:
            return []
        
        # Group similar trends
        trend_groups = {}
        
        for trend in trends:
            # Create a normalized key for grouping
            key = self._normalize_trend_key(trend.keyword)
            
            if key in trend_groups:
                # Merge with existing trend
                existing = trend_groups[key]
                
                # Keep the better rank
                if trend.rank and (not existing.rank or trend.rank < existing.rank):
                    existing.rank = trend.rank
                    existing.velocity = trend.velocity
                
                # Accumulate reach
                existing.reach += 1
                
                # Add as alias if different
                if trend.keyword != existing.keyword and trend.keyword not in existing.aliases:
                    existing.aliases.append(trend.keyword)
                
                # Keep best category
                if trend.category != 'general' and existing.category == 'general':
                    existing.category = trend.category
                
            else:
                trend_groups[key] = trend
        
        # Convert back to list and sort
        unique_trends = list(trend_groups.values())
        
        # Sort by velocity and reach
        unique_trends.sort(key=lambda t: (t.velocity, t.reach), reverse=True)
        
        # Apply geographic relevance scoring
        for trend in unique_trends:
            trend.geographic_relevance = self._calculate_geographic_relevance(trend)
        
        return unique_trends
    
    def _normalize_trend_key(self, keyword: str) -> str:
        """Create normalized key for deduplication"""
        
        # Remove hashtags and clean
        normalized = keyword.replace('#', '').lower().strip()
        
        # Remove common variations
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _calculate_geographic_relevance(self, trend: TrendingTopic) -> float:
        """Calculate geographic relevance score"""
        
        location_keywords = self.geo_config.get_location_keywords()
        trend_text = (trend.keyword + ' ' + trend.region + ' ' + ' '.join(trend.aliases)).lower()
        
        relevance = 0.0
        
        # Direct location mentions
        for keyword in location_keywords:
            if keyword.lower() in trend_text:
                relevance += 0.3
        
        # Region-based scoring
        if 'united-states' in trend.region or 'us-' in trend.region:
            relevance += 0.4
        
        # State/city specific
        if self.geo_config.state and self.geo_config.state.lower().replace(' ', '-') in trend.region:
            relevance += 0.5
        
        # Category-based geographic relevance
        geographic_categories = ['politics', 'government', 'economy', 'election']
        if trend.category in geographic_categories:
            relevance += 0.2
        
        return min(1.0, relevance)
    
    def _get_default_regions(self) -> List[str]:
        """Get default regions based on configuration"""
        
        regions = []
        
        if self.geo_config.include_national:
            regions.append("united-states")
        
        # Add state if configured
        if self.geo_config.state:
            state_mappings = {
                "California": "california",
                "New York": "new-york",
                "Texas": "texas",
                "Florida": "florida",
                "Illinois": "illinois",
                "Pennsylvania": "pennsylvania",
                "Ohio": "ohio",
                "Georgia": "georgia",
                "North Carolina": "north-carolina",
                "Michigan": "michigan"
            }
            
            state_slug = state_mappings.get(self.geo_config.state)
            if state_slug:
                regions.append(f"us-{state_slug}")
        
        return regions if regions else ["united-states"]
    
    async def _respect_rate_limit(self):
        """Enhanced rate limiting with backoff"""
        
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def test_connection(self) -> Dict[str, any]:
        """Test connection with enhanced error reporting"""
        
        try:
            trends = await self.fetch_trending_topics(["united-states"])
            
            return {
                'success': True,
                'trends_found': len(trends),
                'categories_found': len(set(t.category for t in trends)),
                'sample_trends': [t.keyword for t in trends[:5]],
                'message': f'Successfully scraped {len(trends)} trends'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'bs4_available': BS4_AVAILABLE
            }