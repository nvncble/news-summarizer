#!/usr/bin/env python3
"""
Enhanced Strategic Article Prioritization System
Implements sophisticated cross-source prioritization and tiered inclusion
"""

from typing import List, Dict, Tuple
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class StrategicPrioritizer:
    """
    Handles sophisticated article prioritization across multiple sources
    with tiered inclusion strategy
    """
    
    def __init__(self):
        # Tier allocation strategy for 100 articles
        self.tier_allocations = {
            'top': 20,      # Detailed coverage - highest priority
            'mid': 35,      # Moderate coverage - good importance
            'quick': 45     # Quick mentions - still worth noting
        }
        
        # Category diversity targets (ensure balanced coverage)
        self.category_targets = {
            'world_news': 0.25,
            'tech': 0.20,
            'business': 0.15,
            'cutting_edge': 0.15,
            'security': 0.10,
            'sports': 0.10,
            'other': 0.05
        }
    
    def prioritize_articles(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Strategic prioritization of articles into tiers
        Returns dict with 'top', 'mid', 'quick' tiers
        """
        if not articles:
            return {'top': [], 'mid': [], 'quick': []}
        
        # Step 1: Calculate enhanced priority scores
        scored_articles = self._calculate_priority_scores(articles)
        
        # Step 2: Ensure category diversity
        diversified_articles = self._ensure_category_diversity(scored_articles)
        
        # Step 3: Allocate to tiers
        tiered_articles = self._allocate_to_tiers(diversified_articles)
        
        logger.info(f"Strategic allocation: Top: {len(tiered_articles['top'])}, "
                   f"Mid: {len(tiered_articles['mid'])}, Quick: {len(tiered_articles['quick'])}")
        
        return tiered_articles
    
    def _calculate_priority_scores(self, articles: List[Dict]) -> List[Tuple[Dict, float]]:
        """
        Calculate enhanced priority scores considering multiple factors
        """
        scored = []
        
        # Group articles by story (for cross-source detection)
        story_groups = self._group_similar_stories(articles)
        
        for article in articles:
            score = 0.0
            
            # Base importance score from RSS or initial processing
            base_score = article.get('importance_score', 0.0)
            score += base_score * 2.0  # Weight base importance heavily
            
            # Reddit engagement boost
            if article.get('source_type') == 'reddit':
                upvotes = article.get('upvotes', 0)
                comments = article.get('comments', 0)
                
                # Logarithmic scaling for engagement
                if upvotes > 0:
                    upvote_score = min(5.0, (upvotes / 1000) * 3.0)  # Cap at 5.0
                    score += upvote_score
                
                if comments > 0:
                    comment_score = min(2.0, (comments / 100) * 1.0)  # Cap at 2.0
                    score += comment_score
                
                # High engagement exponential boost
                if upvotes > 5000:
                    score += 3.0  # Major story boost
                elif upvotes > 2000:
                    score += 1.5  # Notable story boost
            
            # Cross-source correlation bonus
            story_group = story_groups.get(self._get_story_key(article), [])
            if len(story_group) > 1:  # Story appears in multiple sources
                cross_source_bonus = min(4.0, len(story_group) * 1.5)
                score += cross_source_bonus
                logger.debug(f"Cross-source bonus {cross_source_bonus} for: {article['title'][:50]}")
            
            # Recency boost (prefer newer stories)
            if article.get('published_date'):
                # This would need actual date parsing - simplified for now
                score += 0.5  # Small recency boost
            
            # Category importance modifiers
            category = article.get('category', 'other')
            category_modifiers = {
                'world_news': 1.2,     # World events are important
                'cutting_edge': 1.1,   # Innovation matters
                'security': 1.3,       # Security is critical
                'business': 1.0,       # Standard weight
                'tech': 1.0,           # Standard weight
                'sports': 0.8          # Lower priority unless very engaging
            }
            score *= category_modifiers.get(category, 1.0)
            
            # Quality indicators
            title_length = len(article.get('title', ''))
            content_length = len(article.get('content', '') or article.get('summary', ''))
            
            # Prefer substantial content
            if content_length > 200:
                score += 0.5
            if content_length > 500:
                score += 0.5
            
            # Avoid very short or very long titles
            if 10 <= title_length <= 100:
                score += 0.3
            
            scored.append((article, max(0.0, score)))  # Ensure non-negative
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def _group_similar_stories(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group articles that are likely about the same story
        """
        groups = defaultdict(list)
        
        for article in articles:
            story_key = self._get_story_key(article)
            groups[story_key].append(article)
        
        return dict(groups)
    
    def _get_story_key(self, article: Dict) -> str:
        """
        Generate a key to identify similar stories across sources
        """
        title = article.get('title', '').lower()
        
        # Extract key terms (simplified approach)
        # Remove common words and take first few significant words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'says', 'after'}
        words = [w for w in title.split() if w not in common_words and len(w) > 2]
        
        # Take first 3-4 significant words as story key
        key_words = words[:4] if words else ['unknown']
        return '_'.join(key_words)
    
    def _ensure_category_diversity(self, scored_articles: List[Tuple[Dict, float]]) -> List[Tuple[Dict, float]]:
        """
        Ensure category diversity in top articles while maintaining overall scoring
        """
        if not scored_articles:
            return scored_articles
        
        # Count articles by category
        category_counts = defaultdict(int)
        total_articles = len(scored_articles)
        
        # Calculate target counts per category
        category_limits = {}
        for category, target_ratio in self.category_targets.items():
            category_limits[category] = int(total_articles * target_ratio)
        
        # Reorder to ensure diversity in top positions
        diversified = []
        remaining = list(scored_articles)
        category_used = defaultdict(int)
        
        # First pass: ensure each major category gets representation in top tier
        for article, score in remaining[:]:
            category = article.get('category', 'other')
            limit = category_limits.get(category, float('inf'))
            
            if category_used[category] < limit:
                diversified.append((article, score))
                remaining.remove((article, score))
                category_used[category] += 1
                
                # Stop when we have enough diverse articles for top tier
                if len(diversified) >= self.tier_allocations['top']:
                    break
        
        # Second pass: add remaining articles in score order
        diversified.extend(remaining)
        
        return diversified
    
    def _allocate_to_tiers(self, scored_articles: List[Tuple[Dict, float]]) -> Dict[str, List[Dict]]:
        """
        Allocate articles to tiers based on scores and allocation strategy
        """
        result = {'top': [], 'mid': [], 'quick': []}
        
        if not scored_articles:
            return result
        
        # Calculate tier boundaries
        top_end = self.tier_allocations['top']
        mid_end = top_end + self.tier_allocations['mid']
        quick_end = mid_end + self.tier_allocations['quick']
        
        for i, (article, score) in enumerate(scored_articles):
            # Add tier info to article
            article_with_tier = article.copy()
            article_with_tier['calculated_priority_score'] = score
            
            if i < top_end:
                article_with_tier['tier'] = 'top'
                result['top'].append(article_with_tier)
            elif i < mid_end:
                article_with_tier['tier'] = 'mid'
                result['mid'].append(article_with_tier)
            elif i < quick_end:
                article_with_tier['tier'] = 'quick'
                result['quick'].append(article_with_tier)
            else:
                break  # We have enough articles
        
        return result
    
    def get_prioritization_summary(self, tiered_articles: Dict[str, List[Dict]]) -> Dict[str, any]:
        """
        Generate summary statistics about the prioritization
        """
        total_articles = sum(len(tier) for tier in tiered_articles.values())
        
        # Category breakdown
        category_breakdown = defaultdict(lambda: {'top': 0, 'mid': 0, 'quick': 0})
        source_breakdown = defaultdict(lambda: {'top': 0, 'mid': 0, 'quick': 0})
        
        for tier_name, articles in tiered_articles.items():
            for article in articles:
                category = article.get('category', 'unknown')
                source_type = article.get('source_type', 'unknown')
                category_breakdown[category][tier_name] += 1
                source_breakdown[source_type][tier_name] += 1
        
        # Calculate average scores per tier
        avg_scores = {}
        for tier_name, articles in tiered_articles.items():
            if articles:
                scores = [a.get('calculated_priority_score', 0) for a in articles]
                avg_scores[tier_name] = sum(scores) / len(scores)
            else:
                avg_scores[tier_name] = 0.0
        
        return {
            'total_articles': total_articles,
            'tier_counts': {tier: len(articles) for tier, articles in tiered_articles.items()},
            'category_breakdown': dict(category_breakdown),
            'source_breakdown': dict(source_breakdown),
            'average_scores': avg_scores
        }

    def prioritize_with_trends(self, articles: List[Dict], trend_analysis) -> Dict[str, List[Dict]]:
        """Enhanced prioritization with trend correlation data"""
        
        if not articles:
            return {'top': [], 'mid': [], 'quick': []}
        
        # Apply trend boost to articles
        articles_with_trend_boost = self._apply_trend_boost(articles, trend_analysis)
        
        # Use existing prioritization with enhanced scores
        return self.prioritize_articles(articles_with_trend_boost)
    
    def _apply_trend_boost(self, articles: List[Dict], trend_analysis) -> List[Dict]:
        """Apply boost to articles that correlate with trends"""
        
        if not trend_analysis:
            return articles
        
        enhanced_articles = []
        all_correlations = (
            trend_analysis.triple_coverage + 
            trend_analysis.double_coverage + 
            trend_analysis.geographic_trends
        )
        
        for article in articles:
            enhanced_article = article.copy()
            trend_boost = 0.0
            
            # Check for trend correlations
            for correlation_data in all_correlations:
                for match in correlation_data.get('rss_matches', []):
                    if match['article'].get('url') == article.get('url'):
                        # Boost based on correlation strength and source coverage
                        base_boost = match['score'] * 2.0
                        source_multiplier = len(correlation_data['sources']) * 0.5
                        trend_boost += base_boost * source_multiplier
            
            # Apply trend boost to importance score
            enhanced_article['importance_score'] = article.get('importance_score', 0) + trend_boost
            enhanced_article['trend_boost_applied'] = trend_boost
            
            enhanced_articles.append(enhanced_article)
        
        return enhanced_articles

        
# Integration function for the main CLI
def enhance_article_prioritization(articles: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Main function to integrate strategic prioritization into existing system
    """
    prioritizer = StrategicPrioritizer()
    tiered_articles = prioritizer.prioritize_articles(articles)
    
    # Log prioritization summary
    summary = prioritizer.get_prioritization_summary(tiered_articles)
    logger.info(f"Prioritization summary: {summary}")
    
    return tiered_articles