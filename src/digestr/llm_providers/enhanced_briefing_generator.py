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
from digestr.core.reliable_link_processor import ReliableLinkProcessor, EnhancedPromptBuilder

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
    """Enhanced briefing generator with reliable linking - UPDATED VERSION"""
    
    def __init__(self, llm_provider: OllamaProvider, config_manager):
        self.llm_provider = llm_provider
        self.config_manager = config_manager
        self.briefing_config = config_manager.get_config().briefing
        
        # Add link processor
        self.link_processor = ReliableLinkProcessor()
        self.prompt_builder = EnhancedPromptBuilder()
    
    async def _generate_professional_section(
        self, 
        professional_content: Dict[str, List],
        briefing_type: str
    ) -> Optional[BriefingSection]:
        """Generate professional section with reliable links"""
        
        # Convert to LLM format
        from digestr.sources.source_manager import prepare_professional_content_for_llm
        articles = prepare_professional_content_for_llm(professional_content)
        
        if not articles:
            return None
        
        # Get style configuration
        try:
            # Try accessing as object attributes first
            tone = getattr(self.briefing_config, 'professional_tone', 'analytical and informative')
            focus = getattr(self.briefing_config, 'professional_focus', 'implications and significance')
        except AttributeError:
            # Fallback to defaults
            tone = 'analytical and informative'
            focus = 'implications and significance'
        # Create enhanced prompt with linking instructions
        prompt = self._create_professional_prompt_with_reliable_links(
            articles, briefing_type, tone, focus
        )
        
        # Generate content
        logger.info(f"Generating professional section with {len(articles)} articles")
        raw_content = await self.llm_provider.generate_summary(prompt)
        
        # Post-process to ensure all links are clickable
        final_content = self.link_processor.process_briefing_content(raw_content, articles)
        
        return BriefingSection(
            title="📰 Professional News Analysis",
            content=final_content,
            section_type="professional",
            source_count=len(professional_content),
            item_count=len(articles)
        )
    
    def _create_professional_prompt_with_reliable_links(
        self,
        articles: List[Dict],
        briefing_type: str,
        tone: str,
        focus: str
    ) -> str:
        """Create professional prompt with reliable linking instructions"""
        
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Use the enhanced prompt builder
        article_section = self.prompt_builder.create_article_section(articles, max_articles=15)
        linking_instructions = self.prompt_builder.create_linking_instructions()
        
        prompt = f"""You are a professional news analyst providing an {briefing_type} briefing on {current_time}.

{article_section}

{linking_instructions}

BRIEFING REQUIREMENTS:
- Type: {briefing_type}
- Tone: {tone}
- Focus: {focus}

ANALYSIS STRUCTURE:
1. Lead with the most significant developments
2. Group related stories and explain connections
3. Provide context and implications
4. Highlight what matters most to readers
5. End with key insights

CRITICAL: Add 🔗 after EVERY article reference. No article should be mentioned without 🔗.

Begin your professional analysis:"""

        return prompt
    
    async def _generate_social_section(
        self,
        social_content: Dict[str, SocialFeed],
        briefing_type: str
    ) -> Optional[BriefingSection]:
        """Generate social section with reliable links"""
        
        # Convert to LLM format
        from digestr.sources.source_manager import prepare_social_content_for_llm
        posts = prepare_social_content_for_llm(social_content)
        
        if not posts:
            return None
        
        # Get style configuration  
        try:
            tone = getattr(self.briefing_config, 'social_tone', 'casual and conversational')
            focus = getattr(self.briefing_config, 'social_focus', 'interesting highlights from your personal feeds')
        except AttributeError:
            tone = 'casual and conversational'
            focus = 'interesting highlights from your personal feeds'
        
        # Create enhanced prompt with linking instructions
        prompt = self._create_social_prompt_with_reliable_links(
            posts, briefing_type, tone, focus
        )
        
        # Generate content
        logger.info(f"Generating social section with {len(posts)} posts")
        raw_content = await self.llm_provider.generate_summary(prompt)
        
        # Post-process to ensure all links are clickable
        final_content = self.link_processor.process_briefing_content(raw_content, posts)
        
        return BriefingSection(
            title="🎯 Social Highlights",
            content=final_content,
            section_type="social",
            source_count=len(social_content),
            item_count=len(posts)
        )
    
    def _create_social_prompt_with_reliable_links(
        self,
        posts: List[Dict],
        briefing_type: str,
        tone: str,
        focus: str
    ) -> str:
        """Create social prompt with reliable linking instructions"""
        
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Build social content section with URLs
        social_section = ""
        
        # Group by platform
        platforms = {}
        for post in posts:
            platform = post.get('platform', 'social')
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append(post)
        
        for i, (platform, platform_posts) in enumerate(platforms.items(), 1):
            social_section += f"\n--- {platform.upper()} POSTS ---\n"
            
            for j, post in enumerate(platform_posts[:8], 1):  # Limit per platform
                title = post.get('title', 'Untitled')
                url = post.get('url', '') or post.get('source_url', '')
                community = post.get('community', '') or post.get('subreddit', '')
                score = post.get('score', 0)
                comments = post.get('comments', 0)
                
                social_section += f"\nPOST {i}.{j}: {title}\n"
                social_section += f"COMMUNITY: {community}\n"
                social_section += f"ENGAGEMENT: {score} upvotes, {comments} comments\n"
                social_section += f"URL: {url}\n"
                
                content = post.get('content', '')[:200]
                if content:
                    social_section += f"CONTENT: {content}...\n"
        
        # Enhanced linking instructions
        linking_instructions = self.prompt_builder.create_linking_instructions()
        
        prompt = f"""You are a social media curator sharing highlights on {current_time}.

{social_section}

{linking_instructions}

SOCIAL BRIEFING REQUIREMENTS:
- Type: {briefing_type}
- Tone: {tone}
- Focus: {focus}

SOCIAL CONTENT GUIDELINES:
1. Share the most engaging and interesting posts
2. Explain why each post is worth attention
3. Mention community reactions when relevant
4. Keep it conversational and friendly
5. Connect posts when they relate to similar themes

CRITICAL: Add 🔗 after EVERY post reference. Every post mentioned needs 🔗.

Begin your social highlights:"""

        return prompt
    
    async def generate_structured_briefing(
    self,
    professional_content: Dict[str, List] = None,
    social_content: Dict[str, SocialFeed] = None,
    briefing_type: str = "comprehensive",
    format_type: str = "default"
) -> StructuredBriefing:
        """Generate structured briefing with multiple sections"""
        
        sections = []
        stats = {}
        
        # Generate professional section
        if professional_content:
            prof_section = await self._generate_professional_section(
                professional_content, briefing_type
            )
            if prof_section:
                sections.append(prof_section)
                stats['professional_articles'] = prof_section.item_count
        
        # Generate social section
        if social_content:
            social_section = await self._generate_social_section(
                social_content, briefing_type
            )
            if social_section:
                sections.append(social_section)
                stats['social_posts'] = social_section.item_count
        
        # Create structured briefing
        title = f"{briefing_type.capitalize()} News Briefing"
        timestamp = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        return StructuredBriefing(
            title=title,
            timestamp=timestamp,
            sections=sections,
            summary_stats=stats
        )


# Integration helpers

def create_enhanced_briefing_generator(config_manager) -> EnhancedBriefingGenerator:
    """Factory function to create enhanced briefing generator"""
    from digestr.llm_providers.ollama import OllamaProvider
    
    config = config_manager.get_config()
    llm_provider = OllamaProvider(config.llm.ollama_url, config.llm.models)
    
    return EnhancedBriefingGenerator(llm_provider, config_manager)