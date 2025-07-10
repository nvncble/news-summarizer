"""
Trend Correlation Engine
Comprehensive correlation matching across all content sources
"""

import asyncio
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from collections import defaultdict

from .trend_structures import TrendingTopic, TrendCorrelation, CrossSourceTrendAnalysis, GeographicConfig

logger = logging.getLogger(__name__)


class TrendCorrelationEngine:
    """Advanced correlation matching across all sources"""
    
    def __init__(self, geo_config: GeographicConfig, db_manager):
        self.geo_config = geo_config
        self.db_manager = db_manager
        
        # Correlation thresholds
        self.min_correlation_threshold = 0.4
        self.strong_correlation_threshold = 0.7
        
        # Stop words to ignore in matching
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
    
    async def find_cross_source_correlations(self, trends_data: List[TrendingTopic], 
                                           rss_articles: List[Dict], 
                                           reddit_posts: List[Dict]) -> CrossSourceTrendAnalysis:
        """Find comprehensive correlations across all sources"""
        
        logger.info(f"Analyzing {len(trends_data)} trends against {len(rss_articles)} RSS articles and {len(reddit_posts)} Reddit posts")
        
        correlations = {}  # trend_key -> correlation_data
        
        for trend in trends_data:
            trend_key = self.normalize_trend_key(trend.keyword)
            correlations[trend_key] = {
                'trend': trend,
                'sources': ['trends24'],
                'rss_matches': [],
                'reddit_matches': [],
                'total_strength': 0.0,
                'geographic_relevance': self.check_geographic_relevance(trend),
                'cross_source_boost': 0.0
            }
            
            # Check RSS correlations
            for article in rss_articles:
                correlation_score, match_types = await self.calculate_comprehensive_correlation(
                    trend, article, source_type='rss'
                )
                if correlation_score > self.min_correlation_threshold:
                    correlations[trend_key]['rss_matches'].append({
                        'article': article,
                        'score': correlation_score,
                        'match_types': match_types
                    })
                    correlations[trend_key]['total_strength'] += correlation_score
            
            # Check Reddit correlations
            for post in reddit_posts:
                correlation_score, match_types = await self.calculate_comprehensive_correlation(
                    trend, post, source_type='reddit'
                )
                if correlation_score > self.min_correlation_threshold:
                    correlations[trend_key]['reddit_matches'].append({
                        'post': post,
                        'score': correlation_score,
                        'match_types': match_types
                    })
                    correlations[trend_key]['total_strength'] += correlation_score
            
            # Update source coverage and calculate cross-source boost
            if correlations[trend_key]['rss_matches']:
                correlations[trend_key]['sources'].append('rss')
            if correlations[trend_key]['reddit_matches']:
                correlations[trend_key]['sources'].append('reddit')
            
            # Cross-source boost multiplier
            source_count = len(correlations[trend_key]['sources'])
            if source_count >= 3:
                correlations[trend_key]['cross_source_boost'] = 2.0
            elif source_count == 2:
                correlations[trend_key]['cross_source_boost'] = 1.0
        
        # Save correlations to database
        await self.save_correlations_to_db(correlations)
        
        return self.categorize_by_source_coverage(correlations)
    
    async def calculate_comprehensive_correlation(self, trend: TrendingTopic, 
                                                content: Dict, source_type: str) -> Tuple[float, List[str]]:
        """Use multiple methods to find correlations comprehensively"""
        
        scores = []
        successful_methods = []
        
        # Method 1: Exact keyword matching
        exact_score = self.exact_keyword_match(trend, content)
        scores.append(('exact', exact_score, 0.3))  # weight
        if exact_score > 0:
            successful_methods.append('exact')
        
        # Method 2: Semantic similarity (enhanced keyword matching)
        semantic_score = self.semantic_similarity_match(trend, content)
        scores.append(('semantic', semantic_score, 0.25))
        if semantic_score > 0:
            successful_methods.append('semantic')
        
        # Method 3: Entity extraction (names, places, companies)
        entity_score = self.entity_extraction_match(trend, content)
        scores.append(('entity', entity_score, 0.2))
        if entity_score > 0:
            successful_methods.append('entity')
        
        # Method 4: Topic/category contextual matching
        context_score = self.contextual_topic_match(trend, content)
        scores.append(('context', context_score, 0.15))
        if context_score > 0:
            successful_methods.append('context')
        
        # Method 5: Phrase and partial matching
        phrase_score = self.phrase_similarity_match(trend, content)
        scores.append(('phrase', phrase_score, 0.1))
        if phrase_score > 0:
            successful_methods.append('phrase')
        
        # Weighted combination
        final_score = sum(score * weight for _, score, weight in scores)
        
        # Geographic boost
        if self.has_geographic_relevance(trend, content):
            final_score *= 1.2
            successful_methods.append('geographic')
        
        return min(1.0, final_score), successful_methods
    
    def exact_keyword_match(self, trend: TrendingTopic, content: Dict) -> float:
        """Exact keyword matching with aliases"""
        
        content_text = self.get_content_text(content).lower()
        trend_keywords = [trend.keyword.lower()] + [alias.lower() for alias in trend.aliases]
        
        matches = 0
        total_keywords = len(trend_keywords)
        
        for keyword in trend_keywords:
            # Exact phrase matching
            if keyword in content_text:
                matches += 1
            # Word boundary matching for single words
            elif len(keyword.split()) == 1:
                if re.search(r'\b' + re.escape(keyword) + r'\b', content_text):
                    matches += 0.8  # Slightly lower score for word boundary
        
        return min(1.0, matches / total_keywords)
    
    def semantic_similarity_match(self, trend: TrendingTopic, content: Dict) -> float:
        """Enhanced keyword similarity matching"""
        
        content_text = self.get_content_text(content).lower()
        
        # Create expanded keyword set for trend
        trend_words = self.extract_meaningful_words(trend.keyword)
        for alias in trend.aliases:
            trend_words.update(self.extract_meaningful_words(alias))
        
        # Extract meaningful words from content
        content_words = self.extract_meaningful_words(content_text)
        
        if not trend_words or not content_words:
            return 0.0
        
        # Calculate overlap
        overlap = len(trend_words.intersection(content_words))
        union = len(trend_words.union(content_words))
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = overlap / union
        
        # Boost for multiple word matches
        if overlap > 1:
            jaccard_similarity *= 1.2
        
        return min(1.0, jaccard_similarity)
    
    def entity_extraction_match(self, trend: TrendingTopic, content: Dict) -> float:
        """Basic entity extraction and matching"""
        
        content_text = self.get_content_text(content)
        
        # Look for proper nouns and capitalized terms
        content_entities = self.extract_entities(content_text)
        trend_entities = self.extract_entities(trend.keyword + ' ' + ' '.join(trend.aliases))
        
        if not trend_entities:
            return 0.0
        
        matches = 0
        for trend_entity in trend_entities:
            for content_entity in content_entities:
                # Exact match
                if trend_entity.lower() == content_entity.lower():
                    matches += 1.0
                # Partial match
                elif trend_entity.lower() in content_entity.lower() or content_entity.lower() in trend_entity.lower():
                    matches += 0.5
        
        return min(1.0, matches / len(trend_entities))
    
    def contextual_topic_match(self, trend: TrendingTopic, content: Dict) -> float:
        """Topic/category contextual matching"""
        
        if hasattr(content, 'category'):
            content_category = (content.category or '').lower()
        elif isinstance(content, dict):
            content_category = content.get('category', '').lower()
        else:
            content_category = ''
        trend_category = trend.category.lower()
        
        # Direct category match
        if content_category == trend_category:
            return 0.8
        
        # Related category matching
        category_relations = {
            'tech': ['technology', 'cutting_edge', 'artificial', 'ai'],
            'politics': ['world_news', 'government', 'election'],
            'business': ['finance', 'economy', 'market'],
            'entertainment': ['sports', 'celebrity', 'media'],
            'health': ['medical', 'science', 'wellness']
        }
        
        for category, related in category_relations.items():
            if trend_category == category and content_category in related:
                return 0.6
            if content_category == category and trend_category in related:
                return 0.6
        
        return 0.0
    
    def phrase_similarity_match(self, trend: TrendingTopic, content: Dict) -> float:
        """Phrase and partial matching"""
        
        content_text = self.get_content_text(content).lower()
        
        # Split trend into phrases
        trend_phrases = [trend.keyword.lower()]
        trend_phrases.extend([alias.lower() for alias in trend.aliases])
        
        best_match = 0.0
        
        for phrase in trend_phrases:
            words = phrase.split()
            if len(words) > 1:
                # Multi-word phrase - check for partial matches
                matches = sum(1 for word in words if word in content_text)
                partial_score = matches / len(words)
                best_match = max(best_match, partial_score * 0.8)  # Discount for partial
            else:
                # Single word - check for stemmed matches
                word = words[0]
                if self.fuzzy_word_match(word, content_text):
                    best_match = max(best_match, 0.6)
        
        return best_match
    
    def check_geographic_relevance(self, trend: TrendingTopic) -> float:
        """Check how relevant trend is to user's geographic location"""
        
        location_keywords = self.geo_config.get_location_keywords()
        trend_text = (trend.keyword + ' ' + ' '.join(trend.aliases) + ' ' + trend.region).lower()
        
        relevance = 0.0
        
        for keyword in location_keywords:
            if keyword.lower() in trend_text:
                relevance += 0.3
        
        # US-specific boost for certain categories
        if trend.category in ['politics', 'economy', 'government'] and 'us' in trend_text:
            relevance += 0.4
        
        return min(1.0, relevance)
    
    def has_geographic_relevance(self, trend: TrendingTopic, content: Dict) -> bool:
        """Check if content has geographic relevance to trend"""
        
        content_text = self.get_content_text(content).lower()
        location_keywords = self.geo_config.get_location_keywords()
        
        for keyword in location_keywords:
            if keyword.lower() in content_text:
                return True
        
        return False
    
    def categorize_by_source_coverage(self, correlations: Dict) -> CrossSourceTrendAnalysis:
        """Organize trends by how many sources mention them"""
        
        analysis = CrossSourceTrendAnalysis()
        
        for trend_key, data in correlations.items():
            source_count = len(data['sources'])
            has_content_correlation = bool(data['rss_matches'] or data['reddit_matches'])
            geographic_relevance = data['geographic_relevance']
            total_strength = data['total_strength']
            
            # Enhance data with calculated metrics
            data['source_count'] = source_count
            data['has_correlations'] = has_content_correlation
            data['total_strength'] = total_strength + data['cross_source_boost']
            
            if source_count >= 3:
                analysis.triple_coverage.append(data)
            elif source_count == 2 and has_content_correlation:
                analysis.double_coverage.append(data)
            elif geographic_relevance > 0.7:
                analysis.geographic_trends.append(data)
            elif source_count == 1:
                # Check if it's an emerging signal worth watching
                if self.is_emerging_signal(data):
                    analysis.emerging_signals.append(data)
                else:
                    analysis.single_coverage.append(data)
        
        # Sort each category by total correlation strength
        for trend_list in [analysis.triple_coverage, analysis.double_coverage, 
                          analysis.geographic_trends, analysis.emerging_signals]:
            trend_list.sort(key=lambda x: x['total_strength'], reverse=True)
        
        analysis.correlation_count = sum(
            len(data['rss_matches']) + len(data['reddit_matches'])
            for data in correlations.values()
        )
        
        logger.info(f"Trend analysis complete: {analysis.total_trends} trends, {analysis.correlation_count} correlations")
        
        return analysis
    
    def is_emerging_signal(self, trend_data: Dict) -> bool:
        """Determine if single-source trend is worth watching"""
        
        trend = trend_data['trend']
        
        # High velocity trends are worth watching
        if trend.velocity > 0.7:
            return True
        
        # Geographic relevance makes it interesting
        if trend_data['geographic_relevance'] > 0.5:
            return True
        
        # Certain categories are always interesting
        important_categories = ['politics', 'security', 'economy', 'health']
        if trend.category.lower() in important_categories:
            return True
        
        return False
    
    def normalize_trend_key(self, keyword: str) -> str:
        """Normalize trend keyword for deduplication"""
        return re.sub(r'[^\w\s]', '', keyword.lower()).strip()
    
    def get_content_text(self, content) -> str:
        """Extract all text from content item (handles both Dict and Article objects)"""
        text_parts = []
        
        # Handle Article objects (from database/RSS)
        if hasattr(content, 'title'):
            # Get title
            if hasattr(content, 'title') and content.title:
                text_parts.append(content.title)
            
            # Get summary
            if hasattr(content, 'summary') and content.summary:
                text_parts.append(content.summary)
            
            # Get content
            if hasattr(content, 'content') and content.content:
                text_parts.append(content.content)
        
        # Handle dictionary format
        elif isinstance(content, dict):
            # Get title
            if content.get('title'):
                text_parts.append(content['title'])
            
            # Get summary
            if content.get('summary'):
                text_parts.append(content['summary'])
            
            # Get content
            if content.get('content'):
                text_parts.append(content['content'])
        
        return ' '.join(text_parts)
    
    def extract_meaningful_words(self, text: str) -> set:
        """Extract meaningful words, removing stop words"""
        words = re.findall(r'\b\w+\b', text.lower())
        return {word for word in words if word not in self.stop_words and len(word) > 2}
    
    def extract_entities(self, text: str) -> List[str]:
        """Basic entity extraction - capitalized terms"""
        # Find capitalized words/phrases
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        return list(set(entities))
    
    def fuzzy_word_match(self, word: str, text: str) -> bool:
        """Basic fuzzy matching for word variations"""
        # Check for word with common suffixes/prefixes
        variations = [
            word, word + 's', word + 'ing', word + 'ed', word + 'er', word + 'est',
            word[:-1] if word.endswith('s') else word,
            word[:-3] if word.endswith('ing') else word,
            word[:-2] if word.endswith('ed') else word
        ]
        
        for variation in variations:
            if variation in text:
                return True
        
        return False
    
    async def save_correlations_to_db(self, correlations: Dict):
        """Save correlation data to database"""
        
        try:
            # Save trending topics
            for trend_key, data in correlations.items():
                trend = data['trend']
                await self._save_trending_topic(trend)
            
            # Save correlations
            for trend_key, data in correlations.items():
                trend_keyword = data['trend'].keyword
                
                # Save RSS correlations
                for match in data['rss_matches']:
                    correlation = TrendCorrelation(
                        trend_keyword=trend_keyword,
                        content_id=getattr(match['article'], 'url', '') if hasattr(match['article'], 'url') else match['article'].get('url', ''),
                        content_source='rss',
                        correlation_strength=match['score'],
                        correlation_type='multi_method',
                        match_types=match['match_types'],
                        is_cross_source=len(data['sources']) > 1
                    )
                    await self._save_correlation(correlation)
                
                # Save Reddit correlations
                for match in data['reddit_matches']:
                    correlation = TrendCorrelation(
                        trend_keyword=trend_keyword,
                        content_id=(getattr(match['post'], 'url', '') if hasattr(match['post'], 'url') else match['post'].get('url', '')) or (getattr(match['post'], 'id', '') if hasattr(match['post'], 'id') else match['post'].get('id', '')),

                        content_source='reddit',
                        correlation_strength=match['score'],
                        correlation_type='multi_method',
                        match_types=match['match_types'],
                        is_cross_source=len(data['sources']) > 1
                    )
                    await self._save_correlation(correlation)
                    
        except Exception as e:
            logger.error(f"Error saving correlations to database: {e}")
    
    async def _save_trending_topic(self, trend: TrendingTopic):
        """Save or update trending topic in database"""
        # This would use your existing database manager
        # Implementation depends on your database structure
        pass
    
    async def _save_correlation(self, correlation: TrendCorrelation):
        """Save correlation to database"""
        # This would use your existing database manager
        # Implementation depends on your database structure
        pass