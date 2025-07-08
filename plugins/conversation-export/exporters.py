#!/usr/bin/env python3
"""
Simplified Exporters for Digestr.ai Plugin
Markdown and HTML export functionality
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class BaseExporter:
    """Base class for exporters"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.export_config = config.get("export", {})
        
        # Ensure export directory exists
        export_dir = self.export_config.get("save_directory", "~/Downloads/digestr-exports")
        self.export_dir = Path(export_dir).expanduser()
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, title: str, extension: str) -> str:
        """Generate filename with timestamp"""
        timestamp = datetime.now()
        
        # Clean title for filename
        clean_title = re.sub(r'[^\w\s-]', '', title)
        clean_title = re.sub(r'[-\s]+', '-', clean_title)
        clean_title = clean_title[:50]  # Limit length
        
        filename = f"{clean_title}-{timestamp.strftime('%Y%m%d_%H%M%S')}.{extension}"
        return filename


class MarkdownExporter(BaseExporter):
    """Export briefings and conversations to Markdown format"""
    
    def export(self, content: str, title: str = "Digestr Export", filename: str = None) -> str:
        """Export content to Markdown file"""
        
        if not filename:
            filename = self._generate_filename(title, "md")
        elif not filename.endswith('.md'):
            filename += '.md'
        
        file_path = self.export_dir / filename
        
        # Create markdown document with metadata
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        markdown_content = f"""# {title}

*Generated on {timestamp}*

---

{content}

---

*Exported from Digestr.ai - Your Personal News Intelligence Platform*
"""
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return str(file_path)
            
        except Exception as e:
            raise Exception(f"Failed to write markdown file: {e}")


class HtmlExporter(BaseExporter):
    """Export briefings and conversations to HTML format"""
    
    def export(self, content: str, title: str = "Digestr Export", filename: str = None) -> str:
        """Export content to HTML file"""
        
        if not filename:
            filename = self._generate_filename(title, "html")
        elif not filename.endswith('.html'):
            filename += '.html'
        
        file_path = self.export_dir / filename
        
        # Create HTML document
        html_content = self._create_html_document(content, title)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return str(file_path)
            
        except Exception as e:
            raise Exception(f"Failed to write HTML file: {e}")
    
    def _create_html_document(self, content: str, title: str) -> str:
        """Create a complete HTML document"""
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        # Convert markdown-like content to HTML
        html_body = self._markdown_to_html(content)
        
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Digestr.ai</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
        
        .content blockquote {{
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 15px 20px;
            margin: 20px 0;
            font-style: italic;
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
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📰 {title}</h1>
            <div class="subtitle">Digestr.ai Export</div>
            <div class="timestamp">Generated on {timestamp}</div>
        </div>
        
        <div class="content">
            {html_body}
        </div>
        
        <div class="footer">
            <div class="logo">🤖 Digestr.ai</div>
            <div>Your Personal News Intelligence Platform</div>
        </div>
    </div>
</body>
</html>"""
        
        return html_document
    
    def _markdown_to_html(self, content: str) -> str:
        """Convert basic markdown to HTML"""
        # Escape HTML special characters first
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Convert headers
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
        
        # Convert line breaks and paragraphs
        paragraphs = content.split('\n\n')
        html_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # Check if it's already an HTML element
                if para.startswith('<'):
                    html_paragraphs.append(para)
                else:
                    # Convert single line breaks to <br> within paragraphs
                    para = para.replace('\n', '<br>')
                    html_paragraphs.append(f'<p>{para}</p>')
        
        return '\n'.join(html_paragraphs)