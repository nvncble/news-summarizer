#!/usr/bin/env python3
"""
FIXED: Enhanced Link Processing System for Digestr
Ensures every article gets a clickable link with reliable matching
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ReliableLinkProcessor:
    """FIXED: Processes briefing content to ensure all articles have clickable links"""
    
    def __init__(self):
        self.link_marker = "🔗"
        self.article_registry = {}  # Maps normalized titles to URLs
        
    def register_articles(self, articles: List[Dict]):
        """Register all articles with multiple matching strategies"""
        self.article_registry.clear()
        
        logger.info(f"Registering {len(articles)} articles for link processing")
        
        for article in articles:
            title = article.get('title', '').strip()
            url = article.get('url', '').strip()
            
            if not title or not url:
                continue
                
            # Store the main title -> URL mapping
            self.article_registry[title] = url
            
            # Add variations for better matching
            variations = self._create_title_variations(title)
            for variation in variations:
                self.article_registry[variation] = url
        
        logger.info(f"Registered {len(self.article_registry)} title variations")
    
    def _create_title_variations(self, title: str) -> List[str]:
        """Create multiple variations of title for fuzzy matching"""
        variations = []
        
        # Remove common prefixes
        cleaned_title = title
        prefixes = ['[Reddit]', '[Twitter]', '[Breaking]', 'Breaking:', 'Update:']
        for prefix in prefixes:
            if cleaned_title.startswith(prefix):
                cleaned_title = cleaned_title[len(prefix):].strip()
                variations.append(cleaned_title)
        
        # Truncated versions
        if len(title) > 20:
            variations.extend([title[:50], title[:40], title[:30], title[:20]])
        
        # First few words
        words = title.split()
        if len(words) >= 2:
            variations.append(' '.join(words[:2]))
        if len(words) >= 3:
            variations.append(' '.join(words[:3]))
        
        return variations
    
    def process_briefing_content(self, content: str, articles: List[Dict]) -> str:
        """Process briefing to add missing links and convert markers to HTML"""
        
        # Step 1: Register all articles
        self.register_articles(articles)
        
        if not self.article_registry:
            return content
        
        # Step 2: Add link markers where missing
        content_with_markers = self._add_link_markers(content)
        
        # Step 3: Convert markers to HTML links
        html_content = self._convert_markers_to_html(content_with_markers)
        
        return html_content
    
    def _add_link_markers(self, content: str) -> str:
        """Add link markers to article mentions"""
        
        modified_content = content
        
        for title_or_variation, url in self.article_registry.items():
            if len(title_or_variation) < 5:
                continue
            
            # Case-insensitive search
            if title_or_variation.lower() in modified_content.lower():
                # Find the position and add marker
                pattern = re.escape(title_or_variation)
                
                def add_marker(match):
                    return match.group(0) + f" {self.link_marker}"
                
                # Only add if not already there
                context_start = modified_content.lower().find(title_or_variation.lower())
                context_end = context_start + len(title_or_variation) + 10
                context = modified_content[context_start:context_end] if context_start >= 0 else ""
                
                if self.link_marker not in context:
                    modified_content = re.sub(pattern, add_marker, modified_content, count=1, flags=re.IGNORECASE)
                    break  # Only add one marker per article
        
        return modified_content
    
    def _convert_markers_to_html(self, content: str) -> str:
        """Convert markers to HTML links"""
        
        def replace_marker(match):
            sentence = match.group(0)
            
            # Find best matching URL for this sentence
            best_url = self._find_url_for_sentence(sentence)
            
            if best_url:
                link_html = f'<a href="{best_url}" style="color: #007bff; text-decoration: none; font-weight: bold;">🔗</a>'
                return sentence.replace(self.link_marker, link_html)
            else:
                return sentence.replace(self.link_marker, '<span style="color: #666;">🔗</span>')
        
        # Find sentences with markers
        pattern = rf'[^.!?\n]*{re.escape(self.link_marker)}[^.!?\n]*'
        return re.sub(pattern, replace_marker, content)
    
    def _find_url_for_sentence(self, sentence: str) -> Optional[str]:
        """Find the best URL for a sentence"""
        
        sentence_lower = sentence.lower()
        
        for title_or_variation, url in self.article_registry.items():
            if title_or_variation.lower() in sentence_lower:
                return url
        
        return None


class EnhancedPromptBuilder:
    """Builds prompts that encourage consistent link marker usage"""
    
    def __init__(self):
        self.link_marker = "🔗"
    
    def create_article_section(self, articles: List[Dict], max_articles: int = 20) -> str:
        """Create article section with embedded URLs for reference"""
        
        content = ""
        
        for i, article in enumerate(articles[:max_articles], 1):
            title = article.get('title', 'Untitled')
            url = article.get('url', '')
            source = article.get('source', 'Unknown')
            summary = article.get('content') or article.get('summary', '')
            
            if len(summary) > 300:
                summary = summary[:300] + "..."
            
            content += f"\n--- ARTICLE {i} ---\n"
            content += f"TITLE: {title}\n"
            content += f"SOURCE: {source}\n"
            content += f"URL: {url}\n"
            content += f"CONTENT: {summary}\n"
        
        return content
    
    def create_linking_instructions(self) -> str:
        """Create clear instructions for link marker usage"""
        
        return f"""
CRITICAL LINKING REQUIREMENTS:
1. When mentioning ANY article, immediately add {self.link_marker} after the title/reference
2. EVERY article mention must have {self.link_marker} - no exceptions
3. Format: "Article Title {self.link_marker}" or "According to the report {self.link_marker}..."

EXAMPLES:
✅ "Apple's iPhone announcement {self.link_marker} shows major improvements..."
✅ "The study {self.link_marker} reveals concerning trends..."
❌ "Several articles mentioned" (missing {self.link_marker})

Remember: Always add {self.link_marker} after mentioning any article!
"""
