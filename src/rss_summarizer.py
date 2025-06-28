#!/usr/bin/env python3
"""
Advanced RSS Feed Summarizer with Ollama Integration
Optimized for high-speed connections with async fetching and comprehensive sources
"""

import asyncio
import aiohttp
import feedparser
import sqlite3
import requests
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import time
import os
from urllib.parse import urljoin, urlparse
import re
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedRSSummarizer:
    def __init__(self, db_path: str = "rss_feeds.db", ollama_url: str = "http://localhost:11434"):
        self.db_path = db_path
        self.ollama_url = ollama_url
        self.init_database()

        # Comprehensive RSS feeds organized by category
        self.feeds = {
            "tech": [
                "https://feeds.arstechnica.com/arstechnica/index",
                "https://feeds.feedburner.com/techcrunch/startups",
                "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
                "https://www.theverge.com/rss/index.xml",
                "https://techcrunch.com/feed/",
                "https://www.wired.com/feed/rss",
                "https://feeds.feedburner.com/venturebeat/SZYF",
                "https://www.engadget.com/rss.xml",
                "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
                "https://rss.slashdot.org/Slashdot/slashdotMain",
                "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
                "https://moxie.foxnews.com/google-publisher/tech.xml",
                "https://moxie.foxnews.com/google-publisher/health.xml",
            ],
            "world_news": [

                "https://feeds.bbci.co.uk/news/world/rss.xml",
                "https://moxie.foxnews.com/google-publisher/world.xml",
                "https://feeds.npr.org/1001/rss.xml",
                "https://feeds.simplecast.com/54nAGcIl",
                "https://www.theguardian.com/world/rss",
                "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",

                "https://feeds.skynews.com/feeds/rss/world.xml",
                "https://rss.dw.com/xml/rss-en-world",
            ],
            "sports": [
                "https://www.espn.com/espn/rss/news",
                "https://sports.yahoo.com/rss/",

                "https://www.reutersagency.com/feed/?best-topics=sports&post_type=best",
                "https://www.cbssports.com/rss/headlines",
                "https://bleacherreport.com/articles/feed",

            ],
            "cutting_edge": [
                "https://rss.arxiv.org/rss/cs.AI",  # AI papers
                "https://rss.arxiv.org/rss/cs.LG",  # Machine Learning papers
                "https://rss.arxiv.org/rss/cs.CL",  # Computational Linguistics
                "https://rss.arxiv.org/rss/cs.CV",  # Computer Vision
                "https://feeds.nature.com/nature/rss/current",
                "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
                "https://feeds.aps.org/rss/recent/physics.rss",
                "https://feeds.feedburner.com/oreilly/radar",
                "https://distill.pub/rss.xml",
            ],
            "business": [
                "https://feeds.bloomberg.com/markets/news.rss",
                "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
                "https://www.reutersagency.com/en/reutersbest/reuters-best-rss-feeds/",
                "https://feeds.feedburner.com/entrepreneur/latest",


            ],
            "security": [
                "https://feeds.feedburner.com/TheHackersNews",
                "https://krebsonsecurity.com/feed/",
                "https://feeds.feedburner.com/securityweek",
                "https://threatpost.com/feed/",
                "https://feeds.feedburner.com/darkreading/blog",
            ]
        }

        # Model configuration with more specialized options
        self.models = {
            "default": "llama3.1:8b",
            "technical": "deepseek-coder:6.7b",
            "conversational": "llama3.1:8b",
            "academic": "qwen2.5:14b",
            "fast": "llama3.1:8b",
            "detailed": "llama3.1:70b"
        }

        # Session for connection pooling
        self.session = None

    def init_database(self):
        """Initialize SQLite database with enhanced schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_hash TEXT UNIQUE,
                title TEXT,
                summary TEXT,
                content TEXT,
                url TEXT,
                category TEXT,
                source TEXT,
                published_date TEXT,
                fetched_date TEXT,
                processed BOOLEAN DEFAULT FALSE,
                importance_score REAL DEFAULT 0.0,
                word_count INTEGER DEFAULT 0,
                language TEXT DEFAULT 'en'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_date TEXT,
                category TEXT,
                content TEXT,
                model_used TEXT,
                article_count INTEGER,
                processing_time REAL,
                quality_score REAL DEFAULT 0.0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feed_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_url TEXT,
                category TEXT,
                last_fetch TEXT,
                article_count INTEGER,
                success_rate REAL,
                avg_response_time REAL
            )
        ''')

        # Add indexes for better performance
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(fetched_date)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed)')

        conn.commit()
        conn.close()

    async def fetch_single_feed(self, session: aiohttp.ClientSession, feed_url: str, category: str) -> Tuple[str, List[Dict], float]:
        """Fetch a single RSS feed asynchronously"""
        start_time = time.time()
        articles = []

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(feed_url, timeout=timeout) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    source = feed.feed.get('title', urlparse(feed_url).netloc)

                    for entry in feed.entries:
                        article = {
                            'title': entry.get('title', ''),
                            'summary': entry.get('summary', entry.get('description', '')),
                            'url': entry.get('link', ''),
                            'category': category,
                            'source': source,
                            'published_date': entry.get('published', ''),
                            'content': self.extract_content_from_entry(entry),
                            'word_count': len(entry.get('summary', '').split()),
                            'importance_score': self.calculate_importance_score(entry)
                        }
                        articles.append(article)

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {feed_url}")
        except Exception as e:
            logger.error(f"Error fetching {feed_url}: {e}")

        fetch_time = time.time() - start_time
        return feed_url, articles, fetch_time

    def extract_content_from_entry(self, entry) -> str:
        """Extract meaningful content from RSS entry"""
        content = ""

        # Try different content fields
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value if isinstance(
                entry.content, list) else str(entry.content)
        elif hasattr(entry, 'summary_detail') and entry.summary_detail:
            content = entry.summary_detail.value
        elif hasattr(entry, 'summary'):
            content = entry.summary
        elif hasattr(entry, 'description'):
            content = entry.description

        # Clean HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content).strip()

        return content

    def calculate_importance_score(self, entry) -> float:
        """Calculate importance score based on various factors"""
        score = 0.0
        title = entry.get('title', '').lower()
        summary = entry.get('summary', '').lower()

        # Keywords that indicate importance
        important_keywords = [
            'breaking', 'urgent', 'major', 'significant', 'critical', 'emergency',
            'breakthrough', 'discovery', 'announcement', 'launch', 'release',
            'acquisition', 'merger', 'funding', 'ipo', 'election', 'crisis'
        ]

        for keyword in important_keywords:
            if keyword in title:
                score += 2.0
            if keyword in summary:
                score += 1.0

        # Length bonus (longer articles might be more substantial)
        word_count = len(summary.split())
        if word_count > 100:
            score += 1.0
        elif word_count > 200:
            score += 2.0

        return min(score, 10.0)  # Cap at 10.0

    async def fetch_all_feeds(self) -> Dict[str, int]:
        """Fetch all RSS feeds concurrently"""
        start_time = time.time()

        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []

            for category, feed_urls in self.feeds.items():
                for feed_url in feed_urls:
                    task = self.fetch_single_feed(session, feed_url, category)
                    tasks.append(task)

            logger.info(f"Fetching {len(tasks)} feeds concurrently...")
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and store in database
        category_counts = {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Feed fetch failed: {result}")
                continue

            feed_url, articles, fetch_time = result
            category = None
            new_articles = 0

            for article in articles:
                category = article['category']
                url_hash = self.hash_url(article['url'])

                # Check if article already exists
                cursor.execute(
                    'SELECT id FROM articles WHERE url_hash = ?', (url_hash,))
                if cursor.fetchone():
                    continue

                # Insert new article
                cursor.execute('''
                    INSERT INTO articles 
                    (url_hash, title, summary, content, url, category, source, 
                     published_date, fetched_date, importance_score, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    url_hash, article['title'], article['summary'], article['content'],
                    article['url'], article['category'], article['source'],
                    article['published_date'], datetime.now().isoformat(),
                    article['importance_score'], article['word_count']
                ))
                new_articles += 1

            if category:
                category_counts[category] = category_counts.get(
                    category, 0) + new_articles

            # Update feed statistics
            self.update_feed_stats(
                cursor, feed_url, category or 'unknown', new_articles, fetch_time)

        conn.commit()
        conn.close()

        total_time = time.time() - start_time
        total_articles = sum(category_counts.values())

        logger.info(
            f"Fetched {total_articles} new articles in {total_time:.2f} seconds")
        logger.info(f"Articles by category: {category_counts}")

        return category_counts

    def update_feed_stats(self, cursor, feed_url: str, category: str, article_count: int, response_time: float):
        """Update feed statistics"""
        cursor.execute('''
            INSERT OR REPLACE INTO feed_stats 
            (feed_url, category, last_fetch, article_count, avg_response_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (feed_url, category, datetime.now().isoformat(), article_count, response_time))

    def hash_url(self, url: str) -> str:
        """Create a hash of the URL for deduplication"""
        return hashlib.md5(url.encode()).hexdigest()

    def get_recent_articles(self, hours: int = 24, category: Optional[str] = None,
                            limit: int = 50, min_importance: float = 0.0) -> List[Dict]:
        """Get recent articles with enhanced filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(hours=hours)

        query = '''
            SELECT title, summary, content, url, category, source, published_date, importance_score
            FROM articles 
            WHERE fetched_date > ? AND processed = FALSE AND importance_score >= ?
        '''
        params = [cutoff_date.isoformat(), min_importance]

        if category:
            query += ' AND category = ?'
            params.append(category)

        query += ' ORDER BY importance_score DESC, fetched_date DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        articles = []

        for row in cursor.fetchall():
            articles.append({
                'title': row[0],
                'summary': row[1],
                'content': row[2],
                'url': row[3],
                'category': row[4],
                'source': row[5],
                'published_date': row[6],
                'importance_score': row[7]
            })

        conn.close()
        return articles

    def create_enhanced_summary_prompt(self, articles: List[Dict], briefing_type: str = "comprehensive") -> str:
        """Create an enhanced prompt for summarizing articles"""
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

        # Group articles by category
        categorized = {}
        for article in articles:
            cat = article['category']
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(article)

        article_text = ""
        for category, cat_articles in categorized.items():
            article_text += f"\n## {category.upper()} NEWS\n"
            for i, article in enumerate(cat_articles, 1):
                importance = "🔥" if article['importance_score'] > 5 else "📌" if article['importance_score'] > 2 else "📄"
                article_text += f"\n{importance} **{article['title']}** ({article['source']})\n"
                # Use content if available, otherwise summary
                content = article['content'] if article['content'] else article['summary']
                if len(content) > 300:
                    content = content[:300] + "..."
                article_text += f"   {content}\n"

        briefing_styles = {
            "comprehensive": "Give me a thorough but conversational briefing. Connect related stories and provide context.",
            "quick": "Give me a quick, punchy summary hitting the main points.",
            "analytical": "Focus on the implications and deeper meaning of these stories.",
            "casual": "Chat with me like a knowledgeable friend over coffee."
        }

        style_instruction = briefing_styles.get(
            briefing_type, briefing_styles["comprehensive"])

        prompt = f"""You are my personal news analyst and friend. It's {current_time}, and I'm catching up on the latest developments.

Here are the most important stories from my feeds:
{article_text}

{style_instruction}

Key points to cover:
- Start with a warm, natural greeting
- Highlight the most significant or surprising developments
- Connect related stories across categories when relevant
- Share insights on why certain stories matter for the bigger picture
- Keep it engaging and conversational
- End with a thoughtful closing that ties things together

Remember: You're not just reporting - you're helping me understand what's happening in the world and why it matters."""

        return prompt

    async def call_ollama_async(self, prompt: str, model: str = None) -> str:
        """Make an async request to Ollama API"""
        if model is None:
            model = self.models["default"]

        try:
            # Use ThreadPoolExecutor for blocking requests call
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(
                    executor,
                    lambda: requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.7,
                                "top_p": 0.9,
                                "num_ctx": 4096
                            }
                        },
                        timeout=120
                    )
                )

            response.raise_for_status()
            return response.json()["response"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama: {e}")
            return f"Error generating summary: {e}"

    async def generate_summary_async(self, category: Optional[str] = None, hours: int = 24,
                                     model: str = None, briefing_type: str = "comprehensive") -> str:
        """Generate a conversational summary asynchronously"""
        start_time = time.time()

        articles = self.get_recent_articles(
            hours=hours, category=category, limit=30)

        if not articles:
            return f"No new articles found in the last {hours} hours" + (f" for {category}" if category else "") + "."

        prompt = self.create_enhanced_summary_prompt(articles, briefing_type)
        summary = await self.call_ollama_async(prompt, model)

        processing_time = time.time() - start_time

        # Mark articles as processed
        self.mark_articles_processed(articles)

        # Save summary to database
        self.save_summary(summary, category or "all", len(articles),
                          model or self.models["default"], processing_time)

        return summary

    def mark_articles_processed(self, articles: List[Dict]):
        """Mark articles as processed to avoid re-summarizing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for article in articles:
            url_hash = self.hash_url(article['url'])
            cursor.execute(
                'UPDATE articles SET processed = TRUE WHERE url_hash = ?', (url_hash,))

        conn.commit()
        conn.close()

    def save_summary(self, summary: str, category: str, article_count: int,
                     model: str, processing_time: float):
        """Save generated summary to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO summaries (summary_date, category, content, model_used, 
                                 article_count, processing_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().isoformat(), category, summary, model,
              article_count, processing_time))

        conn.commit()
        conn.close()

    def get_feed_statistics(self) -> Dict:
        """Get comprehensive feed statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Article counts by category
        cursor.execute('''
            SELECT category, COUNT(*) as count, AVG(importance_score) as avg_importance
            FROM articles 
            WHERE fetched_date > datetime('now', '-7 days')
            GROUP BY category
            ORDER BY count DESC
        ''')
        category_stats = {row[0]: {"count": row[1], "avg_importance": row[2]}
                          for row in cursor.fetchall()}

        # Feed performance
        cursor.execute('''
            SELECT category, AVG(avg_response_time) as avg_time, SUM(article_count) as total_articles
            FROM feed_stats
            WHERE last_fetch > datetime('now', '-24 hours')
            GROUP BY category
        ''')
        performance_stats = {row[0]: {"avg_response_time": row[1], "total_articles": row[2]}
                             for row in cursor.fetchall()}

        conn.close()

        return {
            "categories": category_stats,
            "performance": performance_stats,
            "total_feeds": sum(len(feeds) for feeds in self.feeds.values())
        }

    async def run_comprehensive_briefing(self, category: Optional[str] = None,
                                         hours: int = 24, model: str = None,
                                         briefing_type: str = "comprehensive"):
        """Run a complete briefing cycle with enhanced features"""
        logger.info("🚀 Starting comprehensive news briefing...")

        # Fetch all feeds concurrently
        category_counts = await self.fetch_all_feeds()

        total_new = sum(category_counts.values())
        if total_new == 0:
            print("📰 No new articles found since last check.")
            return

        print(
            f"📈 Fetched {total_new} new articles across {len(category_counts)} categories")

        # Generate summary
        print(
            f"🤖 Generating {briefing_type} summary with {model or 'default model'}...")
        summary = await self.generate_summary_async(
            category=category,
            hours=hours,
            model=model,
            briefing_type=briefing_type
        )

        # Display results
        print("\n" + "="*80)
        print("📋 YOUR ENHANCED NEWS BRIEFING")
        print("="*80)
        print(summary)
        print("\n" + "="*80)

        # Show statistics
        stats = self.get_feed_statistics()
        print(
            f"📊 Feed Statistics: {stats['total_feeds']} total feeds monitored")
        print("📈 Top categories:",
              ", ".join([f"{cat}: {info['count']}" for cat, info in stats['categories'].items()]))


def main():
    """Enhanced main function"""
    summarizer = AdvancedRSSummarizer()

    print("🤖 Advanced RSS Summarizer with Ollama")
    print("🔥 Optimized for high-speed connections with async processing")

    # Run comprehensive briefing
    asyncio.run(summarizer.run_comprehensive_briefing(
        briefing_type="comprehensive",
        hours=24
    ))


if __name__ == "__main__":
    main()
