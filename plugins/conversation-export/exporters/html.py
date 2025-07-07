"""
HTML Exporter for Digestr briefings and conversations
"""

import os
import re
from datetime import datetime
from pathlib import Path


class HtmlExporter:
    """Export briefings and conversations to HTML format"""
    
    def __init__(self, config):
        self.config = config
        self.export_config = config.get("export", {})
    
    def export(self, content, title="Digestr Export", filename=None):
        """
        Export content to HTML file
        
        Args:
            content: String content to export (markdown format)
            title: Title for the document
            filename: Optional custom filename
            
        Returns:
            str: Path to exported file
        """
        # Ensure export directory exists
        export_dir = Path(self.export_config.get("save_directory", "~/Downloads/digestr-exports")).expanduser()
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now()
            template = self.export_config.get("filename_template", "export-{date}-{time}")
            filename = template.format(
                date=timestamp.strftime("%Y-%m-%d"),
                time=timestamp.strftime("%H%M%S"),
                style="export"
            )
        
        # Ensure .html extension
        if not filename.endswith('.html'):
            filename += '.html'
        
        file_path = export_dir / filename
        
        # Create HTML content
        html_content = self._create_html_document(content, title)
        
        # Write to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return str(file_path)
            
        except Exception as e:
            raise Exception(f"Failed to write HTML file: {e}")
    
    def _create_html_document(self, content, title):
        """Create a complete HTML document"""
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        # Convert markdown content to HTML
        html_body = self._markdown_to_html(content)
        
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Digestr.ai</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }}
        
        .header {{
            text-align: center;
            border-bottom: 3px solid #007bff;
            padding-bottom: 25px;
            margin-bottom: 35px;
        }}
        
        .header h1 {{
            color: #007bff;
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        
        .header .subtitle {{
            color: #6c757d;
            font-size: 1.2em;
            margin-top: 10px;
            font-style: italic;
        }}
        
        .header .timestamp {{
            color: #868e96;
            font-size: 0.95em;
            margin-top: 15px;
        }}
        
        .content {{
            font-size: 1.1em;
            line-height: 1.8;
        }}
        
        .content h1 {{
            color: #007bff;
            font-size: 2.2em;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
        }}
        
        .content h2 {{
            color: #007bff;
            font-size: 1.8em;
            margin-top: 35px;
            margin-bottom: 15px;
            border-left: 4px solid #007bff;
            padding-left: 15px;
        }}
        
        .content h3 {{
            color: #495057;
            font-size: 1.4em;
            margin-top: 25px;
            margin-bottom: 12px;
        }}
        
        .content p {{
            margin-bottom: 16px;
            text-align: justify;
        }}
        
        .content blockquote {{
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px 20px;
            margin: 20px 0;
            font-style: italic;
        }}
        
        .content ul, .content ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        
        .content li {{
            margin-bottom: 8px;
        }}
        
        .content code {{
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9em;
        }}
        
        .content pre {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            border-left: 4px solid #007bff;
        }}
        
        .content a {{
            color: #007bff;
            text-decoration: none;
            border-bottom: 1px dotted #007bff;
        }}
        
        .content a:hover {{
            text-decoration: none;
            border-bottom: 1px solid #007bff;
        }}
        
        .highlight {{
            background-color: #fff3cd;
            padding: 15px 20px;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        
        .important {{
            color: #dc3545;
            font-weight: 600;
        }}
        
        .category-tag {{
            background-color: #e9ecef;
            color: #495057;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            display: inline-block;
            margin: 3px 3px 3px 0;
            font-weight: 500;
        }}
        
        .article-meta {{
            background-color: #f8f9fa;
            padding: 12px 15px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 0.95em;
            color: #6c757d;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 25px;
            border-top: 2px solid #e9ecef;
            color: #6c757d;
        }}
        
        .footer .logo {{
            font-size: 1.3em;
            font-weight: 600;
            color: #007bff;
            margin-bottom: 10px;
        }}
        
        .footer .tagline {{
            font-style: italic;
            margin-bottom: 15px;
        }}
        
        .footer .credits {{
            font-size: 0.9em;
            color: #868e96;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 25px 0;
        }}
        
        .stat-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 1.8em;
            font-weight: 600;
            color: #007bff;
        }}
        
        .stat-label {{
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px;
                margin: 10px;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .content {{
                font-size: 1em;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        @media print {{
            body {{
                background-color: white;
            }}
            
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
            
            .footer {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 {title}</h1>
            <div class="subtitle">Digestr.ai Intelligence Report</div>
            <div class="timestamp">Generated on {timestamp}</div>
        </div>
        
        <div class="content">
            {html_body}
        </div>
        
        <div class="footer">
            <div class="logo">🤖 Digestr.ai</div>
            <div class="tagline">Your Personal News Intelligence Platform</div>
            <div class="credits">
                Export generated by the Email Scheduler & Export Plugin<br>
                <small>Created with ❤️ for staying informed</small>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        return html_document
    
    def _markdown_to_html(self, content):
        """Convert markdown content to HTML"""
        import re
        
        # Escape HTML special characters first
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Convert headers (must be in order from largest to smallest)
        content = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', content, flags=re.MULTILINE)
        content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
        
        # Convert bold and italic
        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
        
        # Convert inline code
        content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
        
        # Convert links
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', content)
        
        # Convert blockquotes
        content = re.sub(r'^> (.*?)$', r'<blockquote>\1</blockquote>', content, flags=re.MULTILINE)
        
        # Convert horizontal rules
        content = re.sub(r'^---+$', r'<hr>', content, flags=re.MULTILINE)
        
        # Convert unordered lists
        lines = content.split('\n')
        in_list = False
        result_lines = []
        
        for line in lines:
            if re.match(r'^\s*[-*+]\s+', line):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                item_text = re.sub(r'^\s*[-*+]\s+', '', line)
                result_lines.append(f'<li>{item_text}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)
        
        if in_list:
            result_lines.append('</ul>')
        
        content = '\n'.join(result_lines)
        
        # Convert paragraphs (split by double newlines)
        paragraphs = content.split('\n\n')
        html_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # Check if it's already an HTML element
                if (para.startswith('<h') or para.startswith('<ul') or 
                    para.startswith('<blockquote') or para.startswith('<hr') or
                    para.startswith('<div')):
                    html_paragraphs.append(para)
                else:
                    # Convert single line breaks to <br> within paragraphs
                    para = para.replace('\n', '<br>')
                    html_paragraphs.append(f'<p>{para}</p>')
        
        return '\n'.join(html_paragraphs)
    
    def export_briefing_with_stats(self, briefing_content, articles, style="comprehensive"):
        """
        Export a briefing with enhanced statistics and formatting
        
        Args:
            briefing_content: The AI-generated briefing text
            articles: List of article dictionaries
            style: Briefing style name
            
        Returns:
            str: Path to exported file
        """
        timestamp = datetime.now()
        
        # Calculate statistics
        categories = {}
        total_importance = 0
        high_importance_count = 0
        
        for article in articles:
            cat = article.get('category', 'general')
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
            
            importance = article.get('importance_score', 0)
            total_importance += importance
            if importance > 5:
                high_importance_count += 1
        
        avg_importance = total_importance / len(articles) if articles else 0
        
        # Create enhanced content with statistics
        enhanced_content = f"""
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-number">{len(articles)}</div>
        <div class="stat-label">Total Articles</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{len(categories)}</div>
        <div class="stat-label">Categories</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{avg_importance:.1f}</div>
        <div class="stat-label">Avg. Importance</div>
    </div>
    <div class="stat-card">
        <div class="stat-number">{high_importance_count}</div>
        <div class="stat-label">High Priority</div>
    </div>
</div>

## AI-Generated Summary

{briefing_content}

## Source Analysis
"""
        
        # Add category breakdown
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            enhanced_content += f"<span class='category-tag'>{category.title().replace('_', ' ')}: {count} articles</span> "
        
        enhanced_content += "\n\n"
        
        # Add article details if requested
        if self.export_config.get("include_article_details", True):
            enhanced_content += "## Featured Articles\n\n"
            
            # Sort articles by importance
            sorted_articles = sorted(articles, key=lambda x: x.get('importance_score', 0), reverse=True)
            
            for i, article in enumerate(sorted_articles[:10], 1):  # Top 10 articles
                importance = article.get('importance_score', 0)
                indicator = "🔥" if importance > 5 else "📌" if importance > 2 else "📄"
                
                enhanced_content += f"### {indicator} {article['title']}\n\n"
                enhanced_content += f'<div class="article-meta">'
                enhanced_content += f"<strong>Source:</strong> {article.get('source', 'Unknown')} | "
                enhanced_content += f"<strong>Category:</strong> {article.get('category', 'Unknown')} | "
                enhanced_content += f"<strong>Importance:</strong> {importance:.1f}/10"
                
                if article.get('published_date'):
                    enhanced_content += f" | <strong>Published:</strong> {article['published_date']}"
                
                enhanced_content += "</div>\n\n"
                
                # Add summary
                summary = article.get('summary') or article.get('content', '')
                if summary:
                    preview = summary[:300] + "..." if len(summary) > 300 else summary
                    enhanced_content += f"{preview}\n\n"
                
                # Add link if available
                if article.get('url') and self.export_config.get("include_article_links", True):
                    enhanced_content += f"[Read full article]({article['url']})\n\n"
                
                enhanced_content += "---\n\n"
        
        # Generate filename for briefing
        filename = self.export_config.get("filename_template", "briefing-{style}-{date}-{time}").format(
            style=style,
            date=timestamp.strftime("%Y-%m-%d"),
            time=timestamp.strftime("%H%M%S")
        )
        
        return self.export(enhanced_content, f"{style.title()} News Briefing", filename)