#!/usr/bin/env python3
"""
Enhanced Briefing Generator - FIXED VERSION
Added links, removed fluff, condensed prompts
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from digestr.llm_providers.ollama import OllamaProvider
from digestr.sources.social_post_structure import SocialFeed

logger = logging.getLogger(__name__)


@dataclass
class BriefingSection:
    """Individual section of a briefing"""
    title: str
    content: str
    section_type: str  # "professional", "social", "combined"
    source_count: int
    item_count: int


@dataclass
class StructuredBriefing:
    """Complete structured briefing with multiple sections"""
    title: str
    timestamp: str
    sections: List[BriefingSection]
    summary_stats: Dict[str, Any]
    
    def get_full_content(self) -> str:
        """Get complete briefing as single string"""
        content_parts = [f"# {self.title}\n*Generated on {self.timestamp}*\n"]
        
        for section in self.sections:
            content_parts.append(f"\n## {section.title}\n")
            content_parts.append(section.content)
        
        # Add summary stats
        if self.summary_stats:
            content_parts.append("\n---\n")
            content_parts.append("**Sources:** ")
            stats_parts = []
            if 'professional_articles' in self.summary_stats:
                stats_parts.append(f"{self.summary_stats['professional_articles']} professional articles")
            if 'social_posts' in self.summary_stats:
                stats_parts.append(f"{self.summary_stats['social_posts']} social posts")
            content_parts.append(", ".join(stats_parts))
        
        return "\n".join(content_parts)


class EnhancedBriefingGenerator:
    """Enhanced briefing generator - NO FLUFF, WITH LINKS"""
    
    def __init__(self, llm_provider: OllamaProvider, config_manager):
        self.llm_provider = llm_provider
        self.config_manager = config_manager
        self.briefing_config = config_manager.get_config().briefing
    
    async def generate_structured_briefing(
        self, 
        professional_content: Dict[str, List] = None,
        social_content: Dict[str, SocialFeed] = None,
        briefing_type: str = "comprehensive",
        structure: str = "default"
    ) -> StructuredBriefing:
        """Generate a structured briefing with professional and social sections"""
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        sections = []
        
        # Get structure configuration
        structure_config = self.briefing_config.get('structure', {})
        section_order = structure_config.get('default_order', ['professional', 'social'])
        
        if structure == "professional_only":
            section_order = ['professional']
        elif structure == "social_only":
            section_order = ['social']
        
        # Generate sections based on order
        for section_type in section_order:
            if section_type == "professional" and professional_content:
                section = await self._generate_professional_section(
                    professional_content, briefing_type
                )
                if section:
                    sections.append(section)
            
            elif section_type == "social" and social_content:
                section = await self._generate_social_section(
                    social_content, briefing_type
                )
                if section:
                    sections.append(section)
        
        # Calculate summary stats
        prof_count = sum(len(content) for content in (professional_content or {}).values())
        social_count = sum(len(feed.posts) for feed in (social_content or {}).values() if isinstance(feed, SocialFeed))
        
        summary_stats = {
            'professional_articles': prof_count,
            'social_posts': social_count,
            'total_sources': len((professional_content or {}).keys()) + len((social_content or {}).keys()),
            'briefing_type': briefing_type
        }
        
        # Create structured briefing
        briefing_title = f"{briefing_type.title()} Intelligence Briefing"
        
        return StructuredBriefing(
            title=briefing_title,
            timestamp=timestamp,
            sections=sections,
            summary_stats=summary_stats
        )
    
    async def _generate_professional_section(
        self, 
        professional_content: Dict[str, List],
        briefing_type: str
    ) -> Optional[BriefingSection]:
        """Generate the professional news section - WITH LINKS, NO FLUFF"""
        
        # Convert to LLM format
        from digestr.sources.source_manager import prepare_professional_content_for_llm
        articles = prepare_professional_content_for_llm(professional_content)
        
        if not articles:
            return None
        
        # Get style configuration
        style_config = self.briefing_config.get('styles', {}).get('professional', {})
        tone = style_config.get('tone', 'analytical and informative')
        focus = style_config.get('focus', 'implications and significance')
        
        # Create professional briefing prompt - FIXED VERSION
        prompt = self._create_professional_prompt_fixed(articles, briefing_type, tone, focus)
        
        # Generate content
        logger.info(f"Generating professional section with {len(articles)} articles")
        content = await self.llm_provider.generate_summary(prompt)
        
        return BriefingSection(
            title="📰 Professional News Analysis",
            content=content,
            section_type="professional",
            source_count=len(professional_content),
            item_count=len(articles)
        )
    
    async def _generate_social_section(
        self,
        social_content: Dict[str, SocialFeed],
        briefing_type: str
    ) -> Optional[BriefingSection]:
        """Generate the social content section - WITH LINKS, NO FLUFF"""
        
        # Convert to LLM format
        from digestr.sources.source_manager import prepare_social_content_for_llm
        posts = prepare_social_content_for_llm(social_content)
        
        if not posts:
            return None
        
        # Get style configuration  
        style_config = self.briefing_config.get('styles', {}).get('social', {})
        tone = style_config.get('tone', 'casual and conversational')
        focus = style_config.get('focus', 'interesting highlights from your personal feeds')
        
        # Create social briefing prompt - FIXED VERSION
        prompt = self._create_social_prompt_fixed(posts, briefing_type, tone, focus)
        
        # Generate content
        logger.info(f"Generating social section with {len(posts)} posts")
        content = await self.llm_provider.generate_summary(prompt)
        
        return BriefingSection(
            title="🎯 Social Highlights",
            content=content,
            section_type="social",
            source_count=len(social_content),
            item_count=len(posts)
        )
    
    def _create_professional_prompt_fixed(
        self,
        articles: List[Dict],
        briefing_type: str,
        tone: str,
        focus: str
    ) -> str:
        """Create prompt for professional news section - FIXED: NO FLUFF, WITH LINKS"""
        
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Group articles by category
        categorized = {}
        for article in articles:
            cat = article.get('category', 'general')
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(article)
        
        # Build article content WITH URLS
        article_content = ""
        for category, cat_articles in categorized.items():
            article_content += f"\n### {category.upper().replace('_', ' ')} ({len(cat_articles)} articles)\n"
            
            # Sort by importance
            cat_articles.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
            
            for article in cat_articles[:8]:  # Limit per category
                importance = article.get('importance_score', 0)
                indicator = "🔥" if importance > 5 else "📌" if importance > 2 else "📄"
                
                article_content += f"\n{indicator} **{article['title']}**\n"
                article_content += f"Source: {article.get('source', 'Unknown')}\n"
                article_content += f"URL: {article.get('url', '')}\n"  # ADD URL FOR LINKS
                
                # Use content or summary
                content = article.get('content') or article.get('summary', '')
                if len(content) > 300:
                    content = content[:300] + "..."
                article_content += f"{content}\n---\n"
        
        prompt = f"""You are a professional news analyst providing an {briefing_type} briefing.

PROFESSIONAL NEWS CONTENT:
{article_content}

BRIEFING REQUIREMENTS:
- Type: {briefing_type}
- Tone: {tone}
- Focus: {focus}

CRITICAL INSTRUCTIONS:
- INCLUDE CLICKABLE LINKS: Format every story as [title](URL) when mentioning articles
- NO introductory paragraphs or meta-commentary
- NO concluding summaries ("In conclusion..." etc.)
- Jump straight into the analysis
- Connect related stories and explain implications
- Keep it analytical but concise
- Focus on significance and broader context

Begin your analysis immediately:"""

        return prompt
    
    def _create_social_prompt_fixed(
        self,
        posts: List[Dict],
        briefing_type: str,
        tone: str,
        focus: str
    ) -> str:
        """Create prompt for social content section - FIXED: NO FLUFF, WITH LINKS"""
        
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Group posts by platform and community
        grouped_posts = {}
        for post in posts:
            platform = post.get('platform', 'unknown')
            community = post.get('community', 'general')
            
            if platform not in grouped_posts:
                grouped_posts[platform] = {}
            if community not in grouped_posts[platform]:
                grouped_posts[platform][community] = []
            
            grouped_posts[platform][community].append(post)
        
        # Build social content WITH URLS
        social_content = ""
        for platform, communities in grouped_posts.items():
            social_content += f"\n### {platform.upper().replace('_', ' ')} HIGHLIGHTS\n"
            
            for community, community_posts in communities.items():
                # Sort by engagement
                community_posts.sort(key=lambda x: x.get('score', 0), reverse=True)
                
                social_content += f"\n**r/{community}** ({len(community_posts)} posts)\n"
                
                for post in community_posts[:5]:  # Top 5 per community
                    score = post.get('score', 0)
                    comments = post.get('comments', 0)
                    engagement = "🔥" if score > 1000 else "📈" if score > 100 else "💬"
                    
                    social_content += f"\n{engagement} **{post['title']}** ({score} ⬆️, {comments} 💬)\n"
                    social_content += f"URL: {post.get('url', '')}\n"  # ADD URL FOR LINKS
                    
                    content = post.get('content', '')[:200]
                    if content:
                        social_content += f"{content}...\n"
                    social_content += "---\n"
        
        prompt = f"""You are a social media curator sharing highlights.

SOCIAL CONTENT HIGHLIGHTS:
{social_content}

INSTRUCTIONS:
- Type: {briefing_type} (but casual)
- Tone: {tone}
- Focus: {focus}

CRITICAL REQUIREMENTS:
- INCLUDE CLICKABLE LINKS: Format as [post title](URL) when mentioning posts
- NO lengthy introductions or greetings
- NO concluding paragraphs
- Jump straight into the highlights
- Highlight what makes each post interesting
- Keep it engaging but focused
- Mention engagement levels naturally

Begin your social highlights immediately:"""

        return prompt
    
    async def generate_combined_briefing(
        self,
        professional_content: Dict[str, List] = None,
        social_content: Dict[str, SocialFeed] = None,
        briefing_type: str = "comprehensive"
    ) -> str:
        """Generate a traditional combined briefing (legacy format) - FIXED VERSION"""
        
        structured_briefing = await self.generate_structured_briefing(
            professional_content, social_content, briefing_type, "default"
        )
        
        return structured_briefing.get_full_content()
    
    async def generate_professional_only(
        self,
        professional_content: Dict[str, List],
        briefing_type: str = "comprehensive"
    ) -> str:
        """Generate professional-only briefing"""
        
        structured_briefing = await self.generate_structured_briefing(
            professional_content, None, briefing_type, "professional_only"
        )
        
        return structured_briefing.get_full_content()
    
    async def generate_social_only(
        self,
        social_content: Dict[str, SocialFeed],
        briefing_type: str = "casual"
    ) -> str:
        """Generate social-only briefing"""
        
        structured_briefing = await self.generate_structured_briefing(
            None, social_content, briefing_type, "social_only"
        )
        
        return structured_briefing.get_full_content()


# Integration helpers

def create_enhanced_briefing_generator(config_manager) -> EnhancedBriefingGenerator:
    """Factory function to create enhanced briefing generator"""
    from digestr.llm_providers.ollama import OllamaProvider
    
    config = config_manager.get_config()
    llm_provider = OllamaProvider(config.llm.ollama_url, config.llm.models)
    
    return EnhancedBriefingGenerator(llm_provider, config_manager)