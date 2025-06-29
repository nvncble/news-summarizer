#!/usr/bin/env python3
"""
Digestr Core Database Module
Handles all SQLite operations, schema management, and statistics
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Article data structure"""
    id: Optional[int] = None
    url_hash: str = ""
    title: str = ""
    summary: str = ""
    content: str = ""
    url: str = ""
    category: str = ""
    source: str = ""
    published_date: str = ""
    fetched_date: str = ""
    processed: bool = False
    importance_score: float = 0.0
    word_count: int = 0
    language: str = "en"


@dataclass
class Summary:
    """Summary data structure"""
    id: Optional[int] = None
    summary_date: str = ""
    category: str = ""
    content: str = ""
    model_used: str = ""
    article_count: int = 0
    processing_time: float = 0.0
    quality_score: float = 0.0


@dataclass
class FeedStats:
    """Feed statistics data structure"""
    id: Optional[int] = None
    feed_url: str = ""
    category: str = ""
    last_fetch: str = ""
    article_count: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0


class DatabaseManager:
    """Manages all database operations for Digestr"""

    def __init__(self, db_path: str = "rss_feeds.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with enhanced schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Articles table with enhanced schema
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

        # Summaries table
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

        # Feed statistics table
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

        # Performance indexes
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(fetched_date)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_articles_importance ON articles(importance_score)')

        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")

    def hash_url(self, url: str) -> str:
        """Create a hash of the URL for deduplication"""
        return hashlib.md5(url.encode()).hexdigest()

    def insert_article(self, article: Article) -> bool:
        """
        Insert a new article into the database
        Returns True if inserted, False if duplicate
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Generate URL hash if not provided
            if not article.url_hash:
                article.url_hash = self.hash_url(article.url)

            # Set fetched_date if not provided
            if not article.fetched_date:
                article.fetched_date = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO articles 
                (url_hash, title, summary, content, url, category, source, 
                 published_date, fetched_date, processed, importance_score, word_count, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.url_hash, article.title, article.summary, article.content,
                article.url, article.category, article.source, article.published_date,
                article.fetched_date, article.processed, article.importance_score,
                article.word_count, article.language
            ))

            conn.commit()
            logger.debug(f"Inserted article: {article.title[:50]}...")
            return True

        except sqlite3.IntegrityError:
            # Duplicate article (url_hash already exists)
            logger.debug(f"Duplicate article skipped: {article.url}")
            return False
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
            return False
        finally:
            conn.close()

    def bulk_insert_articles(self, articles: List[Article]) -> int:
        """
        Insert multiple articles efficiently
        Returns number of successfully inserted articles
        """
        if not articles:
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        inserted_count = 0

        try:
            for article in articles:
                if not article.url_hash:
                    article.url_hash = self.hash_url(article.url)
                if not article.fetched_date:
                    article.fetched_date = datetime.now().isoformat()

                try:
                    cursor.execute('''
                        INSERT INTO articles 
                        (url_hash, title, summary, content, url, category, source, 
                         published_date, fetched_date, processed, importance_score, word_count, language)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        article.url_hash, article.title, article.summary, article.content,
                        article.url, article.category, article.source, article.published_date,
                        article.fetched_date, article.processed, article.importance_score,
                        article.word_count, article.language
                    ))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    # Skip duplicates
                    continue

            conn.commit()
            logger.info(
                f"Bulk inserted {inserted_count}/{len(articles)} articles")

        except Exception as e:
            logger.error(f"Error in bulk insert: {e}")
            conn.rollback()
        finally:
            conn.close()

        return inserted_count

    def get_recent_articles(self, hours: int = 24, category: Optional[str] = None,
                            limit: int = 50, min_importance: float = 0.0,
                            unprocessed_only: bool = True) -> List[Article]:
        """Get recent articles with enhanced filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(hours=hours)

        query = '''
            SELECT id, url_hash, title, summary, content, url, category, source, 
                   published_date, fetched_date, processed, importance_score, word_count, language
            FROM articles 
            WHERE fetched_date > ? AND importance_score >= ?
        '''
        params = [cutoff_date.isoformat(), min_importance]

        if unprocessed_only:
            query += ' AND processed = FALSE'

        if category:
            query += ' AND category = ?'
            params.append(category)

        query += ' ORDER BY importance_score DESC, fetched_date DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        articles = []

        for row in cursor.fetchall():
            article = Article(
                id=row[0], url_hash=row[1], title=row[2], summary=row[3],
                content=row[4], url=row[5], category=row[6], source=row[7],
                published_date=row[8], fetched_date=row[9], processed=bool(
                    row[10]),
                importance_score=row[11], word_count=row[12], language=row[13]
            )
            articles.append(article)

        conn.close()
        return articles

    def mark_articles_processed(self, article_urls: List[str]):
        """Mark articles as processed to avoid re-summarizing"""
        if not article_urls:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for url in article_urls:
                url_hash = self.hash_url(url)
                cursor.execute(
                    'UPDATE articles SET processed = TRUE WHERE url_hash = ?', (url_hash,))

            conn.commit()
            logger.info(f"Marked {len(article_urls)} articles as processed")

        except Exception as e:
            logger.error(f"Error marking articles as processed: {e}")
        finally:
            conn.close()

    def save_summary(self, summary: Summary) -> int:
        """Save generated summary to database, returns summary ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if not summary.summary_date:
                summary.summary_date = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO summaries (summary_date, category, content, model_used, 
                                     article_count, processing_time, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary.summary_date, summary.category, summary.content,
                summary.model_used, summary.article_count, summary.processing_time,
                summary.quality_score
            ))

            summary_id = cursor.lastrowid
            conn.commit()
            logger.info(
                f"Saved summary {summary_id} for category: {summary.category}")
            return summary_id

        except Exception as e:
            logger.error(f"Error saving summary: {e}")
            return -1
        finally:
            conn.close()

    def update_feed_stats(self, feed_url: str, category: str, article_count: int,
                          response_time: float, success: bool = True):
        """Update feed statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get existing stats
            cursor.execute(
                'SELECT success_rate, avg_response_time FROM feed_stats WHERE feed_url = ?',
                (feed_url,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing record with moving averages
                old_success_rate = old_success_rate or 0.0
                old_avg_time = old_avg_time or 0.0
                new_success_rate = (old_success_rate * 0.9) + \
                    (1.0 if success else 0.0) * 0.1
                new_avg_time = (old_avg_time * 0.9) + (response_time * 0.1)

                cursor.execute('''
                    UPDATE feed_stats 
                    SET last_fetch = ?, article_count = ?, success_rate = ?, avg_response_time = ?
                    WHERE feed_url = ?
                ''', (datetime.now().isoformat(), article_count, new_success_rate, new_avg_time, feed_url))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO feed_stats 
                    (feed_url, category, last_fetch, article_count, success_rate, avg_response_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (feed_url, category, datetime.now().isoformat(), article_count,
                      1.0 if success else 0.0, response_time))

            conn.commit()

        except Exception as e:
            logger.error(f"Error updating feed stats: {e}")
        finally:
            conn.close()

    def get_feed_statistics(self, days: int = 7) -> Dict:
        """Get comprehensive feed statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        # Article counts by category
        cursor.execute('''
            SELECT category, COUNT(*) as count, AVG(importance_score) as avg_importance,
                   COUNT(CASE WHEN processed = TRUE THEN 1 END) as processed_count
            FROM articles 
            WHERE fetched_date > ?
            GROUP BY category
            ORDER BY count DESC
        ''', (cutoff_date.isoformat(),))

        category_stats = {}
        for row in cursor.fetchall():
            category_stats[row[0]] = {
                "count": row[1],
                "avg_importance": round(row[2] or 0, 2),
                "processed_count": row[3],
                "processing_rate": round((row[3] / row[1]) * 100, 1) if row[1] > 0 else 0
            }

        # Feed performance
        cursor.execute('''
            SELECT category, AVG(avg_response_time) as avg_time, 
                   SUM(article_count) as total_articles, AVG(success_rate) as avg_success
            FROM feed_stats
            WHERE last_fetch > ?
            GROUP BY category
        ''', (cutoff_date.isoformat(),))

        performance_stats = {}
        for row in cursor.fetchall():
            performance_stats[row[0]] = {
                "avg_response_time": round(row[1] or 0, 2),
                "total_articles": row[2] or 0,
                "success_rate": round((row[3] or 0) * 100, 1)
            }

        # Overall statistics
        cursor.execute(
            'SELECT COUNT(*) FROM articles WHERE fetched_date > ?',
            (cutoff_date.isoformat(),)
        )
        total_articles = cursor.fetchone()[0]

        cursor.execute(
            'SELECT COUNT(DISTINCT category) FROM articles WHERE fetched_date > ?',
            (cutoff_date.isoformat(),)
        )
        active_categories = cursor.fetchone()[0]

        conn.close()

        return {
            "categories": category_stats,
            "performance": performance_stats,
            "summary": {
                "total_articles": total_articles,
                "active_categories": active_categories,
                "period_days": days
            }
        }

    def cleanup_old_articles(self, days: int = 30) -> int:
        """Remove articles older than specified days, returns count removed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            cursor.execute(
                'DELETE FROM articles WHERE fetched_date < ?',
                (cutoff_date.isoformat(),)
            )
            removed_count = cursor.rowcount
            conn.commit()

            if removed_count > 0:
                logger.info(
                    f"Cleaned up {removed_count} articles older than {days} days")

            return removed_count

        except Exception as e:
            logger.error(f"Error cleaning up old articles: {e}")
            return 0
        finally:
            conn.close()
