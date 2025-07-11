"""
Link Processor - Ensures all article references have clickable links
"""

import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class LinkProcessor:
    """Process briefing content to ensure all articles have links"""
    
    def __init__(self):
        self.link_format = "[→]"  # Can be easily changed
        self.article_registry = {}
        
    def register_articles(self, articles: List[Dict]):
        """Register all articles for link matching"""
        self.article_registry.clear()
        
        for article in articles:
            # Multiple keys for better matching
            title = article.get('title', '')
            url = article.get('url', '')
            
            if title and url:
                # Store multiple variations for matching
                self.article_registry[title] = url
                
                # Also store shortened versions
                if len(title) > 50:
                    self.article_registry[title[:50]] = url
                    self.article_registry[title[:40]] = url
                
                # Remove common prefixes for Reddit
                if title.startswith('[Reddit]'):
                    clean_title = title[8:].strip()
                    self.article_registry[clean_title] = url
    
    def process_briefing_content(self, content: str, articles: List[Dict]) -> str:
        """Process briefing to add links where missing"""
        self.register_articles(articles)
        
        # Find article mentions and add links
        processed = self._add_missing_links(content)
        
        # Convert any arrow markers to links if found
        processed = self._convert_arrow_markers(processed)
        
        return processed
    
    def _add_missing_links(self, content: str) -> str:
        """Add [→] links to article titles that don't have them"""
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip if line already has a link marker
            if self.link_format in line or '](http' in line:
                processed_lines.append(line)
                continue
            
            # Check if line contains an article title
            line_processed = False
            for title, url in self.article_registry.items():
                # Look for title mentions (case insensitive)
                pattern = re.escape(title)
                match = re.search(pattern, line, re.IGNORECASE)
                
                if match and url:
                    # Add link after the title
                    start, end = match.span()
                    new_line = line[:end] + f" {self.link_format}" + line[end:]
                    processed_lines.append(new_line)
                    line_processed = True
                    break
            
            if not line_processed:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _convert_arrow_markers(self, content: str) -> str:
        """Convert [→] markers to actual links for terminal/email"""
        for title, url in self.article_registry.items():
            # Pattern: "title [→]" (with possible formatting)
            patterns = [
                f"{re.escape(title)} {re.escape(self.link_format)}",
                f"{re.escape(title)}{re.escape(self.link_format)}",
                f"**{re.escape(title)}** {re.escape(self.link_format)}",
            ]
            
            for pattern in patterns:
                # For terminal: Create ANSI escape sequence for clickable link
                if self._is_terminal_output():
                    return f"\033]8;;{url}\033\\{title} {self.link_format}\033]8;;\033\\"
                else:
                    return f"{title} {self.link_format}|{url}|"

            content = re.sub(pattern, make_replacement, content, flags=re.IGNORECASE)
        
        return content
    
    def _is_terminal_output(self) -> bool:
        """Detect if output is going to terminal"""
        import sys
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def format_for_html_email(self, content: str) -> str:
        """Convert link markers to HTML links for email"""
        # Pattern: "text [→]|url|"
        pattern = r'([^|]+)\s*\[→\]\|([^|]+)\|'
        
        def replace_with_html(match):
            text = match.group(1).strip()
            url = match.group(2).strip()
            return f'<a href="{url}" style="color: #007bff; text-decoration: none;">{text} →</a>'
        
        return re.sub(pattern, replace_with_html, content)


# CLI formatting helper
def format_article_with_link(title: str, url: str, use_ansi: bool = True) -> str:
    """Format article title with clickable link for CLI"""
    if use_ansi and url:
        # ANSI escape sequence for hyperlink
        return f"\033]8;;{url}\033\\{title} [→]\033]8;;\033\\"
    else:
        return f"{title} [→]"