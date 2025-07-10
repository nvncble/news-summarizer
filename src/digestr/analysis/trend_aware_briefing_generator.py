#!/usr/bin/env python3
"""
Trend-Aware Briefing Generator
Enhanced briefing generation with comprehensive trend integration
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from digestr.analysis.trend_structures import CrossSourceTrendAnalysis
from digestr.llm_providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)


class TrendAwareBriefingGenerator:
    """Generate briefings with comprehensive trend integration"""
    
    def __init__(self, llm_provider: OllamaProvider):
        self.llm_provider = llm_provider


    def _safe_get(self, obj, attr_name, default=''):
        """Safely get attribute from Article object or dictionary"""
        if hasattr(obj, attr_name):
            # Article object - use getattr
            value = getattr(obj, attr_name, default)
            return value if value is not None else default
        elif isinstance(obj, dict):
            # Dictionary - use get
            return obj.get(attr_name, default)
        else:
            return default
    
    async def generate_comprehensive_briefing(self, content_data: Dict, 
                                            trend_analysis: CrossSourceTrendAnalysis,
                                            briefing_type: str = "comprehensive") -> str:
        """Generate briefing with both integrated and dedicated trend sections"""
        
        sections = []
        
        # 1. TREND ALERT (if significant cross-source trends)
        if self._has_significant_trends(trend_analysis):
            trend_alert = await self.generate_trend_alert_section(trend_analysis)
            sections.append(trend_alert)
        
        # 2. ENHANCED PROFESSIONAL SECTION (with trend indicators)
        if content_data.get('professional'):
            professional_section = await self.generate_professional_with_trends(
                content_data['professional'], trend_analysis, briefing_type
            )
            sections.append(professional_section)
        
        # 3. ENHANCED SOCIAL SECTION (with trend indicators)
        if content_data.get('social'):
            social_section = await self.generate_social_with_trends(
                content_data['social'], trend_analysis, briefing_type
            )
            sections.append(social_section)
        
        # 4. COMPREHENSIVE TRENDS ANALYSIS SECTION
        if trend_analysis.total_trends > 0:
            trends_section = await self.generate_comprehensive_trends_section(trend_analysis)
            sections.append(trends_section)
        
        return self.combine_sections(sections)
    
    def _has_significant_trends(self, trend_analysis: CrossSourceTrendAnalysis) -> bool:
        """Check if there are significant cross-source trends worth alerting about"""
        return (
            len(trend_analysis.triple_coverage) > 0 or 
            len(trend_analysis.double_coverage) > 2 or
            len([t for t in trend_analysis.get_significant_trends()]) > 1
        )
    
    async def generate_trend_alert_section(self, trend_analysis: CrossSourceTrendAnalysis) -> str:
        """Generate opening trend alert for significant cross-source trends"""
        
        significant_trends = trend_analysis.get_significant_trends()[:3]  # Top 3
        
        if not significant_trends:
            return ""
        
        alert_content = self._build_trend_alert_content(significant_trends)
        
        prompt = f"""You are a breaking news analyst detecting significant cross-source trends.

{alert_content}

Create a compelling trend alert that:
- Opens with urgency: "🚨 CROSS-SOURCE TREND ALERT"
- Explains why these multi-source trends are significant news
- Highlights the most important trend that appears across news, social media, and trending platforms
- Connects trends to broader implications for readers
- Sets the stage for the detailed briefing that follows
- Uses an urgent but professional tone
- Keep it concise (2-3 paragraphs max)

Generate the trend alert now:"""
        
        return await self.llm_provider.generate_summary(prompt)
    
    def _build_trend_alert_content(self, significant_trends: List[Dict]) -> str:
        """Build structured content for trend alert"""
        
        content_parts = []
        
        for i, trend_data in enumerate(significant_trends, 1):
            trend = trend_data['trend']
            source_count = len(trend_data['sources'])
            rss_count = len(trend_data.get('rss_matches', []))
            reddit_count = len(trend_data.get('reddit_matches', []))
            total_strength = trend_data.get('total_strength', 0)
            
            content_parts.append(f"TREND #{i}: **{trend.keyword}**")
            content_parts.append(f"  Sources: {', '.join(trend_data['sources'])}")
            content_parts.append(f"  Coverage: {rss_count} news articles, {reddit_count} social discussions")
            content_parts.append(f"  Strength: {total_strength:.2f}")
            
            # Add best correlated headline if available
            if trend_data.get('rss_matches'):
                best_match = max(trend_data['rss_matches'], key=lambda x: x['score'])
                content_parts.append(f"  Key story: \"{best_match['article']['title']}\"")
            
            content_parts.append("")  # Empty line
        
        return "\n".join(content_parts)
    
    async def generate_professional_with_trends(self, professional_content: Dict, 
                                              trend_analysis: CrossSourceTrendAnalysis,
                                              briefing_type: str) -> str:
        """Generate professional section with trend indicators"""
        
        # Enhance articles with trend indicators
        enhanced_articles = self._enhance_articles_with_trends(
            professional_content, trend_analysis
        )
        
        # Build professional content with trend integration
        prompt = self._create_professional_with_trends_prompt(
            enhanced_articles, trend_analysis, briefing_type
        )
        
        return await self.llm_provider.generate_summary(prompt)
    
    async def generate_social_with_trends(self, social_content: Dict,
                                        trend_analysis: CrossSourceTrendAnalysis,
                                        briefing_type: str) -> str:
        """Generate social section with trend indicators"""
        
        # Enhance social posts with trend indicators
        enhanced_posts = self._enhance_social_posts_with_trends(
            social_content, trend_analysis
        )
        
        prompt = self._create_social_with_trends_prompt(
            enhanced_posts, trend_analysis, briefing_type
        )
        
        return await self.llm_provider.generate_summary(prompt)
    
    def _enhance_articles_with_trends(self, professional_content: Dict,
                                    trend_analysis: CrossSourceTrendAnalysis) -> List[Dict]:
        """Add trend indicators to professional articles"""
        
        enhanced = []
        all_correlations = (
            trend_analysis.triple_coverage + 
            trend_analysis.double_coverage + 
            trend_analysis.geographic_trends
        )
        
        for source_name, articles in professional_content.items():
            for article in articles:
                if hasattr(article, 'title'):  # Article object
                    enhanced_article = {
                        'title': getattr(article, 'title', ''),
                        'summary': getattr(article, 'summary', ''),
                        'content': getattr(article, 'content', ''),
                        'source': getattr(article, 'source', ''),
                        'category': getattr(article, 'category', ''),
                        'url': getattr(article, 'url', ''),
                        'importance_score': getattr(article, 'importance_score', 0.0),
                        'published_date': getattr(article, 'published_date', None)
                    }
                else:  # Dictionary
                    enhanced_article = article.copy()
                trend_indicators = []
                
                # Find correlations for this article
                for correlation_data in all_correlations:
                    trend = correlation_data['trend']
                    
                    # Check RSS matches
                    for match in correlation_data.get('rss_matches', []):
                        if match['article'].get('url') == self._safe_get(article, 'url'):
                            indicator = self._create_trend_indicator(
                                trend, correlation_data, match['score']
                            )
                            if indicator:
                                trend_indicators.append(indicator)
                
                # Apply trend indicators to article
                if trend_indicators:
                    enhanced_article['trend_indicators'] = trend_indicators[:2]  # Limit to 2
                    enhanced_article['has_trends'] = True
                    # Boost importance for trending articles
                    enhanced_article['importance_score'] = enhanced_article.get('importance_score', 0) + 1.0
                
                enhanced.append(enhanced_article)
        
        # Sort by importance (trending articles will be higher)
        enhanced.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
        
        return enhanced
    
    def _enhance_social_posts_with_trends(self, social_content: Dict,
                                        trend_analysis: CrossSourceTrendAnalysis) -> List[Dict]:
        """Add trend indicators to social posts"""
        
        enhanced = []
        all_correlations = (
            trend_analysis.triple_coverage + 
            trend_analysis.double_coverage + 
            trend_analysis.geographic_trends
        )
        
        for source_name, feed in social_content.items():
            if hasattr(feed, 'posts'):
                for post in feed.posts:
                    enhanced_post = post.to_dict()
                    trend_indicators = []
                    
                    # Find correlations for this post
                    for correlation_data in all_correlations:
                        trend = correlation_data['trend']
                        
                        # Check Reddit matches
                        for match in correlation_data.get('reddit_matches', []):
                            post_url = self._safe_get(match['post'], 'url') if hasattr(match['post'], 'url') else match['post'].get('url', '')
                            post_id = self._safe_get(match['post'], 'id') if hasattr(match['post'], 'id') else match['post'].get('id', '')

                            if (post_url == enhanced_post.get('url') or
                                post_id == enhanced_post.get('id')):
                                indicator = self._create_trend_indicator(
                                    trend, correlation_data, match['score']
                                )
                                if indicator:
                                    trend_indicators.append(indicator)
                    
                    if trend_indicators:
                        enhanced_post['trend_indicators'] = trend_indicators[:2]
                        enhanced_post['has_trends'] = True
                        enhanced_post['interest_score'] = enhanced_post.get('interest_score', 0) + 1.0
                    
                    enhanced.append(enhanced_post)
        
        # Sort by interest score (trending posts higher)
        enhanced.sort(key=lambda x: x.get('interest_score', 0), reverse=True)
        
        return enhanced
    
    def _create_trend_indicator(self, trend, correlation_data: Dict, match_score: float) -> Optional[str]:
        """Create trend indicator text for article/post"""
        
        source_count = len(correlation_data['sources'])
        
        if source_count >= 3 and match_score > 0.7:
            return f"🔥🔥🔥 TRIPLE-SOURCE TREND: {trend.keyword}"
        elif source_count >= 2 and match_score > 0.6:
            return f"🔥🔥 CROSS-SOURCE: {trend.keyword}"
        elif match_score > 0.8:
            return f"🔥 TRENDING: {trend.keyword}"
        elif trend.geographic_relevance > 0.7:
            return f"📍 LOCAL TREND: {trend.keyword}"
        
        return None
    
    def _create_professional_with_trends_prompt(self, enhanced_articles: List[Dict],
                                              trend_analysis: CrossSourceTrendAnalysis,
                                              briefing_type: str) -> str:
        """Create prompt for professional section with trend integration"""
        
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Build article content with trend highlighting
        article_content = ""
        trending_count = 0
        
        for article in enhanced_articles[:20]:  # Limit for prompt size
            has_trends = ('has_trends', False)
            if has_trends:
                trending_count += 1
                indicators = " | ".join(article.get('trend_indicators', []))
                article_content += f"\n🔥 **{article['title']}** | {indicators}\n"
            else:
                article_content += f"\n📰 **{article['title']}**\n"
            
            article_content += f"Source: {article.get('source', 'Unknown')}\n"
            
            content = article.get('content') or article.get('summary', '')
            if len(content) > 300:
                content = content[:300] + "..."
            article_content += f"{content}\n---\n"
        
        prompt = f"""You are a professional news analyst providing a briefing. Current time: {current_time}

PROFESSIONAL NEWS CONTENT ({len(enhanced_articles)} articles, {trending_count} with cross-source trends):
{article_content}

CROSS-SOURCE TREND CONTEXT:
- {len(trend_analysis.triple_coverage)} topics trending across ALL sources (news + social + trending)
- {len(trend_analysis.double_coverage)} topics trending across TWO sources
- Articles marked with 🔥 indicators correlate with these trending topics

BRIEFING INSTRUCTIONS:
- Provide a {briefing_type} analysis of the most significant professional news
- HIGHLIGHT articles that have trend indicators as they represent cross-source validation
- When an article has trend indicators, mention that it's "trending across multiple sources"
- Connect related stories and explain their broader implications
- Explain why cross-source trending makes certain stories more significant
- Use a professional but engaging tone
- Structure as flowing narrative, not bullet points
- Prioritize trending content but include important non-trending stories too

Begin your professional briefing with trend integration:"""
        
        return prompt
    
    def _create_social_with_trends_prompt(self, enhanced_posts: List[Dict],
                                        trend_analysis: CrossSourceTrendAnalysis,
                                        briefing_type: str) -> str:
        """Create prompt for social section with trend integration"""
        
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Build social content with trend highlighting
        social_content = ""
        trending_social_count = 0
        
        for post in enhanced_posts[:15]:  # Limit for prompt size
            has_trends = post.get('has_trends', False)
            if has_trends:
                trending_social_count += 1
                indicators = " | ".join(post.get('trend_indicators', []))
                social_content += f"\n🔥 **{post['title']}** | {indicators}\n"
            else:
                social_content += f"\n💬 **{post['title']}**\n"
            
            social_content += f"Community: {post.get('community', 'Unknown')} | "
            social_content += f"{post.get('score', 0)} ⬆️, {post.get('comments', 0)} 💬\n"
            
            content = post.get('content', '')[:200]
            if content:
                social_content += f"{content}...\n"
            social_content += "---\n"
        
        prompt = f"""You are a friendly social media curator sharing highlights. Current time: {current_time}

SOCIAL CONTENT HIGHLIGHTS ({len(enhanced_posts)} posts, {trending_social_count} with cross-source trends):
{social_content}

SOCIAL TREND CONTEXT:
- Posts marked with 🔥 indicators are trending across news, social media, and trending platforms
- These represent topics that have broken out of social media into mainstream attention
- {trending_social_count} social posts correlate with broader trending topics

SOCIAL BRIEFING INSTRUCTIONS:
- Share the most interesting and engaging social media highlights
- EMPHASIZE posts with trend indicators as they show topics gaining mainstream traction
- When a post has trend indicators, mention it's "trending beyond social media"
- Use a casual, friendly tone like chatting with a friend
- Highlight what makes each post interesting or worth noting
- Connect posts that relate to similar themes, especially trending ones
- Keep it light and engaging - this is the "social pulse" section

Begin your social highlights with trend awareness:"""
        
        return prompt
    
    async def generate_comprehensive_trends_section(self, trend_analysis: CrossSourceTrendAnalysis) -> str:
        """Generate dedicated comprehensive trends analysis section"""
        
        section_content = self._build_comprehensive_trends_content(trend_analysis)
        
        prompt = f"""You are a trend analyst providing comprehensive cross-source trend analysis.

{section_content}

Create a comprehensive trends analysis that:
- Starts with "📈 COMPREHENSIVE CROSS-SOURCE TREND ANALYSIS"
- Explains what it means when topics trend across multiple platforms simultaneously
- Highlights the most significant multi-source trends and their implications
- Discusses how social media trends correlate with mainstream news coverage
- Identifies emerging signals and geographic trends worth monitoring
- Connects trends to broader societal, political, or industry patterns
- Ends with "Trends to Watch" recommendations for what might develop next
- Uses an analytical but accessible tone
- Structure as flowing analysis with clear sections, not just lists

Generate your comprehensive trends analysis:"""
        
        return await self.llm_provider.generate_summary(prompt)
    
    def _build_comprehensive_trends_content(self, trend_analysis: CrossSourceTrendAnalysis) -> str:
        """Build structured content for comprehensive trends section"""
        
        content_parts = []
        
        # Summary statistics
        content_parts.append(f"ANALYSIS SUMMARY:")
        content_parts.append(f"- Total trends analyzed: {trend_analysis.total_trends}")
        content_parts.append(f"- Cross-source correlations found: {trend_analysis.correlation_count}")
        content_parts.append(f"- Triple-source trends: {len(trend_analysis.triple_coverage)}")
        content_parts.append(f"- Double-source trends: {len(trend_analysis.double_coverage)}")
        content_parts.append("")
        
        # Triple coverage trends (highest priority)
        if trend_analysis.triple_coverage:
            content_parts.append("🔥🔥🔥 TRIPLE-SOURCE TRENDS (News + Social + Trending Platforms):")
            for i, trend_data in enumerate(trend_analysis.triple_coverage[:5], 1):
                trend = trend_data['trend']
                rss_count = len(trend_data.get('rss_matches', []))
                reddit_count = len(trend_data.get('reddit_matches', []))
                strength = trend_data.get('total_strength', 0)
                
                content_parts.append(f"{i}. **{trend.keyword}** (Strength: {strength:.2f})")
                content_parts.append(f"   📰 {rss_count} news articles | 🔴 {reddit_count} social discussions | 📈 Trending nationally")
                content_parts.append(f"   Category: {trend.category} | Geographic relevance: {trend.geographic_relevance:.0%}")
                content_parts.append("")
        
        # Double coverage trends
        if trend_analysis.double_coverage:
            content_parts.append("🔥🔥 DOUBLE-SOURCE TRENDS:")
            for trend_data in trend_analysis.double_coverage[:8]:
                trend = trend_data['trend']
                sources = " + ".join(trend_data['sources'])
                strength = trend_data.get('total_strength', 0)
                content_parts.append(f"• **{trend.keyword}** | Sources: {sources} | Strength: {strength:.2f}")
        
        # Geographic trends
        if trend_analysis.geographic_trends:
            content_parts.append("\n🇺🇸 GEOGRAPHIC & REGIONAL TRENDS:")
            for trend_data in trend_analysis.geographic_trends[:5]:
                trend = trend_data['trend']
                content_parts.append(f"• **{trend.keyword}** | Region: {trend.region} | Relevance: {trend.geographic_relevance:.0%}")
        
        # Emerging signals
        if trend_analysis.emerging_signals:
            content_parts.append("\n📡 EMERGING SIGNALS TO MONITOR:")
            for trend_data in trend_analysis.emerging_signals[:5]:
                trend = trend_data['trend']
                content_parts.append(f"• **{trend.keyword}** | Velocity: {trend.velocity:.2f} | Early indicator")
        
        return "\n".join(content_parts)
    
    def combine_sections(self, sections: List[str]) -> str:
        """Combine briefing sections into final output"""
        
        # Filter out empty sections
        non_empty_sections = [section.strip() for section in sections if section.strip()]
        
        if not non_empty_sections:
            return "No content available for briefing."
        
        # Add header
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        header = f"""
📋 YOUR TREND-ENHANCED DIGESTR.AI BRIEFING
Generated on {timestamp}
{"="*80}"""
        
        # Combine with section separators
        combined = header + "\n\n" + "\n\n" + "="*60 + "\n\n".join(non_empty_sections)
        
        # Add footer
        footer = f"""
{"="*80}
🤖 Enhanced with cross-source trend analysis
💡 Articles marked with 🔥 indicators are trending across multiple platforms
"""
        
        return combined + "\n" + footer