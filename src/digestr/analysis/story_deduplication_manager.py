#!/usr/bin/env python3
"""
Story Deduplication Manager
Tracks recent stories and prevents repetitive coverage
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class StoryDeduplicationManager:
    """Manages story tracking and deduplication across briefings"""
    
    def __init__(self, db_path: str = "rss_feeds.db"):
        self.db_path = db_path
        self.similarity_threshold = 0.55  # 55% similarity = duplicate
        self.memory_days = 5
        self._init_story_tracking_table()
    
    def _init_story_tracking_table(self):
        """Initialize story tracking table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS story_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_hash TEXT UNIQUE,
                title TEXT,
                summary TEXT,
                main_topics TEXT,
                first_mentioned TEXT,
                last_mentioned TEXT,
                mention_count INTEGER DEFAULT 1,
                importance_score REAL,
                category TEXT,
                is_ongoing BOOLEAN DEFAULT FALSE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_story_tracking_hash ON story_tracking(story_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_story_tracking_date ON story_tracking(last_mentioned)')
        
        conn.commit()
        conn.close()
    
    def filter_articles_for_freshness(self, articles: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter articles into fresh vs duplicate/update categories
        Returns: (fresh_articles, update_articles)
        """
        if not articles:
            return [], []
        
        fresh_articles = []
        update_articles = []
        
        # Get recent stories from tracking
        recent_stories = self._get_recent_stories()
        
        for article in articles:
            story_analysis = self._analyze_article_freshness(article, recent_stories)
            
            if story_analysis['is_fresh']:
                fresh_articles.append(article)
                # Track this new story
                self._track_new_story(article)
                
            elif story_analysis['is_significant_update']:
                # Add update context to article
                article['update_context'] = story_analysis['update_reason']
                article['previous_coverage'] = story_analysis['similar_story']
                update_articles.append(article)
                # Update existing story tracking
                self._update_story_tracking(story_analysis['similar_story']['story_hash'], article)
            
            # Skip articles that are too similar to recent coverage
        
        logger.info(f"Story filtering: {len(fresh_articles)} fresh, {len(update_articles)} updates, {len(articles) - len(fresh_articles) - len(update_articles)} duplicates skipped")
        
        return fresh_articles, update_articles
    
    def _get_recent_stories(self) -> List[Dict]:
        """Get stories from the last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=self.memory_days)
        
        cursor.execute('''
            SELECT story_hash, title, summary, main_topics, first_mentioned, 
                   last_mentioned, mention_count, importance_score, category, is_ongoing
            FROM story_tracking 
            WHERE last_mentioned > ?
            ORDER BY last_mentioned DESC
        ''', (cutoff_date.isoformat(),))
        
        stories = []
        for row in cursor.fetchall():
            stories.append({
                'story_hash': row[0],
                'title': row[1],
                'summary': row[2],
                'main_topics': json.loads(row[3]) if row[3] else [],
                'first_mentioned': row[4],
                'last_mentioned': row[5],
                'mention_count': row[6],
                'importance_score': row[7],
                'category': row[8],
                'is_ongoing': bool(row[9])
            })
        
        conn.close()
        return stories
    
    def _analyze_article_freshness(self, article: Dict, recent_stories: List[Dict]) -> Dict:
        """Analyze if an article is fresh, duplicate, or significant update"""
        
        article_topics = self._extract_key_topics(article.get('title', ''), article.get('summary', ''))
        
        # Check against recent stories
        for story in recent_stories:
            similarity_score = self._calculate_story_similarity(article, story)
            
            if similarity_score > self.similarity_threshold:
                # This is likely the same story
                
                # Check if it's a significant update
                if self._is_significant_update(article, story):
                    return {
                        'is_fresh': False,
                        'is_significant_update': True,
                        'similar_story': story,
                        'similarity_score': similarity_score,
                        'update_reason': self._determine_update_reason(article, story)
                    }
                else:
                    # Just a duplicate, skip it
                    return {
                        'is_fresh': False,
                        'is_significant_update': False,
                        'similar_story': story,
                        'similarity_score': similarity_score,
                        'skip_reason': 'duplicate_content'
                    }
        
        # This is a fresh story
        return {
            'is_fresh': True,
            'is_significant_update': False,
            'similarity_score': 0.0
        }
    
    def _calculate_story_similarity(self, article: Dict, story: Dict) -> float:
        """Calculate similarity between article and tracked story"""
        
        # Title similarity (weighted heavily)
        title_sim = SequenceMatcher(None, 
                                   article.get('title', '').lower(), 
                                   story['title'].lower()).ratio()
        
        # Topic overlap
        article_topics = set(self._extract_key_topics(article.get('title', ''), article.get('summary', '')))
        story_topics = set(story['main_topics'])
        
        if article_topics and story_topics:
            topic_overlap = len(article_topics.intersection(story_topics)) / len(article_topics.union(story_topics))
        else:
            topic_overlap = 0.0
        
        # Category match bonus
        category_match = 1.0 if article.get('category') == story.get('category') else 0.0
        
        # Weighted combination
        similarity = (title_sim * 0.5) + (topic_overlap * 0.4) + (category_match * 0.1)
        
        return similarity
    
    def _is_significant_update(self, article: Dict, story: Dict) -> bool:
        """Determine if article represents significant new information"""
        
        # Time-based: if the original story is ongoing and this is recent
        last_mentioned = datetime.fromisoformat(story['last_mentioned'])
        hours_since = (datetime.now() - last_mentioned).total_seconds() / 3600
        
        # For ongoing stories, updates within 24 hours might be significant
        if story['is_ongoing'] and hours_since < 24:
            return self._has_new_developments(article, story)
        
        # For major stories, longer gaps might still be worth updating
        if story['importance_score'] > 7.0 and hours_since < 72:  # 3 days
            return self._has_new_developments(article, story)
        
        return False
    
    def _has_new_developments(self, article: Dict, story: Dict) -> bool:
        """Check if article contains new developments"""
        
        # Keywords that indicate new developments
        update_keywords = [
            'breaking', 'update', 'new', 'latest', 'developing', 'just', 'now',
            'confirmed', 'announced', 'revealed', 'leaked', 'exclusive',
            'first time', 'unprecedented', 'major', 'significant', 'emergency'
        ]
        
        article_text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        
        # Check for update keywords
        has_update_keywords = any(keyword in article_text for keyword in update_keywords)
        
        # Check for numbers/data that might be new
        import re
        numbers_in_article = set(re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', article_text))
        numbers_in_story = set(re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', story['summary'].lower()))
        
        has_new_numbers = bool(numbers_in_article - numbers_in_story)
        
        return has_update_keywords or has_new_numbers
    
    def _determine_update_reason(self, article: Dict, story: Dict) -> str:
        """Determine why this is considered an update"""
        
        article_text = article.get('title', '').lower()
        
        if 'breaking' in article_text:
            return "Breaking development"
        elif any(word in article_text for word in ['confirmed', 'announced', 'revealed']):
            return "New information confirmed"
        elif any(word in article_text for word in ['update', 'latest', 'new']):
            return "Story update"
        else:
            return "Continuing coverage"
    
    def _extract_key_topics(self, title: str, summary: str) -> List[str]:
        """Extract key topics from title and summary"""
        
        text = f"{title} {summary}".lower()
        
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those'
        }
        
        # Extract meaningful words (3+ characters)
        import re
        words = re.findall(r'\b\w{3,}\b', text)
        meaningful_words = [word for word in words if word not in stop_words]
        
        # Get most frequent words as topics
        from collections import Counter
        word_counts = Counter(meaningful_words)
        
        # Return top 5 most common meaningful words
        return [word for word, count in word_counts.most_common(5)]
    
    def _track_new_story(self, article: Dict):
        """Add new story to tracking"""
        
        story_hash = self._generate_story_hash(article)
        main_topics = self._extract_key_topics(article.get('title', ''), article.get('summary', ''))
        
        # Determine if this is likely an ongoing story
        is_ongoing = self._is_likely_ongoing_story(article)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO story_tracking 
                (story_hash, title, summary, main_topics, first_mentioned, last_mentioned,
                 importance_score, category, is_ongoing)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                story_hash,
                article.get('title', ''),
                article.get('summary', '')[:500],  # Truncate summary
                json.dumps(main_topics),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                article.get('importance_score', 0.0),
                article.get('category', ''),
                is_ongoing
            ))
            
            conn.commit()
            
        except sqlite3.IntegrityError:
            # Story already exists, just update last_mentioned
            cursor.execute('''
                UPDATE story_tracking 
                SET last_mentioned = ?, mention_count = mention_count + 1
                WHERE story_hash = ?
            ''', (datetime.now().isoformat(), story_hash))
            conn.commit()
        
        finally:
            conn.close()
    
    def _update_story_tracking(self, story_hash: str, article: Dict):
        """Update existing story with new mention"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE story_tracking 
            SET last_mentioned = ?, mention_count = mention_count + 1,
                importance_score = MAX(importance_score, ?)
            WHERE story_hash = ?
        ''', (
            datetime.now().isoformat(),
            article.get('importance_score', 0.0),
            story_hash
        ))
        
        conn.commit()
        conn.close()
    
    def _generate_story_hash(self, article: Dict) -> str:
        """Generate unique hash for story tracking"""
        
        # Use title + category + main topic words for hash
        title = article.get('title', '').lower()
        category = article.get('category', '')
        
        # Extract key words from title for more robust matching
        key_words = sorted(self._extract_key_topics(title, '')[:3])  # Top 3 words
        
        hash_input = f"{title[:50]}_{category}_{'_'.join(key_words)}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _is_likely_ongoing_story(self, article: Dict) -> bool:
        """Determine if story is likely to have ongoing coverage"""
        
        ongoing_indicators = [
            'crisis', 'war', 'conflict', 'investigation', 'trial', 'election',
            'pandemic', 'outbreak', 'emergency', 'disaster', 'negotiations',
            'summit', 'conference', 'developing', 'ongoing', 'continues'
        ]
        
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        
        return any(indicator in text for indicator in ongoing_indicators)
    
    def cleanup_old_stories(self):
        """Remove stories older than memory_days"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=self.memory_days + 1)  # Keep an extra day
        
        cursor.execute(
            'DELETE FROM story_tracking WHERE last_mentioned < ?',
            (cutoff_date.isoformat(),)
        )
        
        removed_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old story tracking records")
        
        return removed_count
    
    def get_story_statistics(self) -> Dict:
        """Get statistics about story tracking"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total tracked stories
        cursor.execute('SELECT COUNT(*) FROM story_tracking')
        total_stories = cursor.fetchone()[0]
        
        # Ongoing stories
        cursor.execute('SELECT COUNT(*) FROM story_tracking WHERE is_ongoing = TRUE')
        ongoing_stories = cursor.fetchone()[0]
        
        # Stories by mention count
        cursor.execute('''
            SELECT mention_count, COUNT(*) 
            FROM story_tracking 
            GROUP BY mention_count 
            ORDER BY mention_count DESC
        ''')
        mention_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_stories': total_stories,
            'ongoing_stories': ongoing_stories,
            'mention_distribution': mention_distribution,
            'memory_days': self.memory_days
        }