#!/usr/bin/env python3
"""
Enhanced Link Processing System for Digestr
Ensures every article gets a clickable link with reliable matching
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ReliableLinkProcessor:
    """Processes briefing content to ensure all articles have clickable links"""
    
    def __init__(self):
        self.link_marker = "🔗"
        self.article_registry = {}  # Maps normalized titles to URLs
        self.title_variations = {}  # Maps variations to canonical titles
        
    def register_articles(self, articles: List[Dict]):
        """Register all articles with multiple matching strategies"""
        self.article_registry.clear()
        self.title_variations.clear()
        
        for article in articles:
            title = article.get('title', '').strip()
            url = article.get('url', '').strip()
            
            if not title or not url:
                continue
                
            # Store the main title -> URL mapping
            self.article_registry[title] = url
            
            # Create variations for better matching
            variations = self._create_title_variations(title)
            for variation in variations:
                self.title_variations[variation] = title
        
        logger.info(f"Registered {len(self.article_registry)} articles with {len(self.title_variations)} variations")
    
    def _create_title_variations(self, title: str) -> List[str]:
        """Create multiple variations of title for fuzzy matching"""
        variations = []
        
        # Original title
        variations.append(title)
        variations.append(title.lower())
        
        # Remove common prefixes
        cleaned_title = title
        prefixes_to_remove = ['[Reddit]', '[Twitter]', '[Breaking]', '[Update]']
        for prefix in prefixes_to_remove:
            if cleaned_title.startswith(prefix):
                cleaned_title = cleaned_title[len(prefix):].strip()
                variations.append(cleaned_title)
                variations.append(cleaned_title.lower())
        
        # Truncated versions (for when LLM shortens titles)
        if len(title) > 50:
            variations.append(title[:50])
            variations.append(title[:40])
            variations.append(title[:30])
        
        # Remove punctuation version
        no_punct = re.sub(r'[^\w\s]', '', title)
        variations.append(no_punct)
        variations.append(no_punct.lower())
        
        # First few words (for when LLM paraphrases)
        words = title.split()
        if len(words) >= 3:
            variations.append(' '.join(words[:3]))
            variations.append(' '.join(words[:4]))
            variations.append(' '.join(words[:5]))
        
        return list(set(variations))  # Remove duplicates
    
    def process_briefing_content(self, content: str, articles: List[Dict]) -> str:
        """Process briefing to add missing links and convert markers to HTML"""
        
        # Step 1: Register all articles
        self.register_articles(articles)
        
        # Step 2: Add link markers where missing
        content_with_markers = self._add_missing_link_markers(content)
        
        # Step 3: Convert markers to HTML links
        html_content = self._convert_markers_to_html_links(content_with_markers)
        
        # Step 4: Validate and report
        self._validate_link_coverage(html_content, articles)
        
        return html_content
    
    def _add_missing_link_markers(self, content: str) -> str:
        """Add 🔗 markers to article mentions that don't have them"""
        
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip if line already has link markers or HTML links
            if self.link_marker in line or 'href=' in line:
                processed_lines.append(line)
                continue
            
            # Look for article title mentions
            modified_line = line
            best_match = None
            best_score = 0
            
            # Check against all title variations
            for variation, canonical_title in self.title_variations.items():
                if len(variation) < 10:  # Skip very short variations
                    continue
                    
                # Case-insensitive search
                if variation.lower() in line.lower():
                    score = len(variation) / len(canonical_title)  # Prefer longer matches
                    if score > best_score:
                        best_match = canonical_title
                        best_score = score
            
            # If we found a good match, add the link marker
            if best_match and best_score > 0.6:  # 60% similarity threshold
                # Find the position and add marker
                # Look for the title mention and add marker after it
                pattern = re.escape(best_match)
                match = re.search(pattern, modified_line, re.IGNORECASE)
                if match:
                    insert_pos = match.end()
                    modified_line = modified_line[:insert_pos] + f" {self.link_marker}" + modified_line[insert_pos:]
                else:
                    # Fallback: add at end of sentence
                    if line.strip().endswith('.'):
                        modified_line = line[:-1] + f" {self.link_marker}."
                    else:
                        modified_line = line + f" {self.link_marker}"
            
            processed_lines.append(modified_line)
        
        return '\n'.join(processed_lines)
    
    def _convert_markers_to_html_links(self, content: str) -> str:
        """Convert 🔗 markers to actual HTML links"""
        
        def replace_marker(match):
            """Replace a single marker with HTML link"""
            full_match = match.group(0)
            
            # Extract the sentence/phrase containing the marker
            sentence_start = max(0, match.start() - 100)
            sentence_end = min(len(content), match.end() + 50)
            context = content[sentence_start:sentence_end]
            
            # Find the best matching article for this context
            url = self._find_best_url_for_context(context)
            
            if url:
                # Replace the marker with HTML link
                link_html = f'<a href="{url}" style="color: #007bff; text-decoration: none; font-weight: bold;">🔗</a>'
                return full_match.replace(self.link_marker, link_html)
            else:
                # Fallback: keep marker but make it visible
                return full_match.replace(self.link_marker, f'<span style="color: #666;">🔗</span>')
        
        # Replace all markers
        pattern = rf'[^.!?\n]*{re.escape(self.link_marker)}[^.!?\n]*'
        result = re.sub(pattern, replace_marker, content)
        
        return result
    
    def _find_best_url_for_context(self, context: str) -> Optional[str]:
        """Find the best matching URL for a given context"""
        best_url = None
        best_score = 0
        
        for title, url in self.article_registry.items():
            # Calculate similarity between context and title
            score = self._calculate_context_similarity(context, title)
            
            if score > best_score and score > 0.4:  # Minimum threshold
                best_score = score
                best_url = url
        
        return best_url
    
    def _calculate_context_similarity(self, context: str, title: str) -> float:
        """Calculate similarity between context and article title"""
        context_lower = context.lower()
        title_lower = title.lower()
        
        # Method 1: Direct substring match
        if title_lower in context_lower:
            return 1.0
        
        # Method 2: Word overlap
        context_words = set(re.findall(r'\b\w+\b', context_lower))
        title_words = set(re.findall(r'\b\w+\b', title_lower))
        
        if not title_words:
            return 0.0
        
        overlap = len(context_words.intersection(title_words))
        word_score = overlap / len(title_words)
        
        # Method 3: Sequence matching
        sequence_score = SequenceMatcher(None, context_lower, title_lower).ratio()
        
        # Combine scores
        final_score = max(word_score, sequence_score * 0.8)
        
        return final_score
    
    def _validate_link_coverage(self, content: str, articles: List[Dict]):
        """Validate that we have good link coverage"""
        
        link_count = content.count('href=')
        marker_count = content.count(self.link_marker)
        total_articles = len(articles)
        
        coverage = (link_count / total_articles * 100) if total_articles > 0 else 0
        
        logger.info(f"Link coverage: {link_count}/{total_articles} articles ({coverage:.1f}%)")
        
        if coverage < 70:
            logger.warning(f"Low link coverage: only {coverage:.1f}% of articles have links")
        
        if marker_count > 0:
            logger.warning(f"{marker_count} unprocessed link markers remain")


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
            
            # Truncate summary for prompt efficiency
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
2. Format: "Article Title {self.link_marker}" or "According to the report {self.link_marker}..."
3. EVERY article mention must have {self.link_marker} - no exceptions
4. Use {self.link_marker} for both direct quotes and paraphrased content
5. If you reference multiple articles in one sentence, add {self.link_marker} after each reference

EXAMPLES:
✅ "Apple's new iPhone features {self.link_marker} show significant improvements..."
✅ "The study {self.link_marker} reveals that 70% of users prefer..."
✅ "Both the tech report {self.link_marker} and market analysis {self.link_marker} indicate..."
❌ "Several articles mentioned improvements" (missing {self.link_marker})

Remember: Every piece of information comes from somewhere - always mark the source!
"""
    
    def create_enhanced_prompt(self, articles: List[Dict], briefing_type: str, sections: str) -> str:
        """Create prompt with enhanced linking instructions"""
        
        current_time = "Monday, July 21, 2025 at 2:30 PM"  # Would be dynamic
        article_section = self.create_article_section(articles)
        linking_instructions = self.create_linking_instructions()
        
        prompt = f"""You are providing a news briefing on {current_time}.

{article_section}

{linking_instructions}

BRIEFING TYPE: {briefing_type}

YOUR TASK:
- Provide an engaging, informative briefing
- Connect related stories and provide context
- Use a conversational but professional tone
- MOST IMPORTANT: Add {self.link_marker} after EVERY article reference

{sections}

Begin your briefing (remember to include {self.link_marker} for every article mention):"""

        return prompt


# Integration functions for existing codebase

def enhance_existing_briefing_generator():
    """Enhance the existing briefing generator with reliable linking"""
    
    # This would be added to the existing enhanced_briefing_generator.py
    
    def _create_professional_prompt_with_reliable_links(self, articles, briefing_type, tone, focus):
        """Enhanced prompt creation with reliable linking"""
        
        prompt_builder = EnhancedPromptBuilder()
        
        # Build the core content
        article_section = prompt_builder.create_article_section(articles)
        linking_instructions = prompt_builder.create_linking_instructions()
        
        prompt = f"""You are a professional news analyst providing a {briefing_type} briefing.

{article_section}

{linking_instructions}

BRIEFING REQUIREMENTS:
- Type: {briefing_type}
- Tone: {tone}
- Focus: {focus}

STRUCTURE:
1. Start with current situation overview
2. Highlight most significant developments
3. Connect related stories across categories
4. Provide analysis and implications
5. End with key takeaways

Remember: Add 🔗 after EVERY article reference!

Begin your analysis:"""
        
        return prompt
    
    def _post_process_briefing_with_links(self, briefing_content, articles):
        """Post-process briefing to ensure all links are clickable"""
        
        link_processor = ReliableLinkProcessor()
        enhanced_content = link_processor.process_briefing_content(briefing_content, articles)
        
        return enhanced_content


def create_email_html_with_reliable_links(briefing_content: str, articles: List[Dict]) -> str:
    """Create HTML email with reliable links"""
    
    # Process the briefing to add links
    link_processor = ReliableLinkProcessor()
    html_content = link_processor.process_briefing_content(briefing_content, articles)
    
    # Wrap in email template
    html_email = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .content {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .header {{ border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }}
            .footer {{ border-top: 1px solid #eee; padding-top: 20px; margin-top: 40px; }}
        </style>
    </head>
    <body>
        <div class="content">
            <div class="header">
                <h1 style="color: #007bff;">🔥 Your Enhanced Digestr Briefing</h1>
            </div>
            
            <div class="briefing-content">
                {html_content.replace(chr(10), '<br>')}
            </div>
            
            <div class="footer">
                <p style="color: #666; font-size: 12px;">
                    📊 Analyzed {len(articles)} articles • 🤖 Enhanced with AI • 🔗 All sources linked
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_email


# Testing function
def test_link_processor():
    """Test the link processor with sample data"""
    
    sample_articles = [
        {
            'title': 'Apple Announces Revolutionary iPhone 16 with AI Features',
            'url': 'https://example.com/apple-iphone-16',
            'source': 'TechNews'
        },
        {
            'title': '[Reddit] Discussion: Is the new iPhone worth upgrading?',
            'url': 'https://reddit.com/r/technology/post123',
            'source': 'r/technology'
        }
    ]
    
    sample_briefing = """
    Good morning! Here's your tech briefing.
    
    Apple's latest announcement about the iPhone 16 shows major improvements in AI capabilities. 
    The community is already discussing whether it's worth upgrading, with mixed reactions on Reddit.
    
    The new features include enhanced Siri and better camera processing.
    """
    
    processor = ReliableLinkProcessor()
    result = processor.process_briefing_content(sample_briefing, sample_articles)
    
    print("ORIGINAL:")
    print(sample_briefing)
    print("\nPROCESSED:")
    print(result)
    
    return result


if __name__ == "__main__":
    test_link_processor()