#!/usr/bin/env python3
"""
Trend Database Manager
Handles database operations specific to trend analysis and correlation storage
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import asdict

from digestr.analysis.trend_structures import TrendingTopic, TrendCorrelation

logger = logging.getLogger(__name__)


class TrendDatabaseManager:
    """Database operations for trend analysis"""
    
    def __init__(self, db_path: str = "rss_feeds.db"):
        self.db_path = db_path
    
    async def save_trending_topic(self, trend: TrendingTopic) -> bool:
        """Save or update trending topic in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if trend already exists
            cursor.execute(
                'SELECT id, first_detected FROM trending_topics WHERE keyword = ? AND source = ?',
                (trend.keyword, trend.source)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing trend
                trend_id, first_detected = existing
                
                cursor.execute('''
                    UPDATE trending_topics SET
                        aliases = ?, category = ?, region = ?, velocity = ?,
                        reach = ?, momentum = ?, peak_time = ?, last_updated = ?,
                        correlation_score = ?, geographic_relevance = ?, is_active = ?
                    WHERE id = ?
                ''', (
                    json.dumps(trend.aliases), trend.category, trend.region, trend.velocity,
                    trend.reach, trend.momentum, 
                    trend.peak_time.isoformat() if trend.peak_time else None,
                    trend.last_updated.isoformat() if trend.last_updated else datetime.now().isoformat(),
                    trend.correlation_score, trend.geographic_relevance, trend.is_active,
                    trend_id
                ))
                
                logger.debug(f"Updated trending topic: {trend.keyword}")
                
            else:
                # Insert new trend
                cursor.execute('''
                    INSERT INTO trending_topics 
                    (keyword, aliases, category, source, region, velocity, reach, momentum,
                     first_detected, peak_time, last_updated, correlation_score, 
                     geographic_relevance, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trend.keyword, json.dumps(trend.aliases), trend.category, trend.source,
                    trend.region, trend.velocity, trend.reach, trend.momentum,
                    trend.first_detected.isoformat() if trend.first_detected else datetime.now().isoformat(),
                    trend.peak_time.isoformat() if trend.peak_time else None,
                    trend.last_updated.isoformat() if trend.last_updated else datetime.now().isoformat(),
                    trend.correlation_score, trend.geographic_relevance, trend.is_active
                ))
                
                logger.debug(f"Inserted new trending topic: {trend.keyword}")
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving trending topic {trend.keyword}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def save_trend_correlation(self, correlation: TrendCorrelation) -> bool:
        """Save trend correlation to database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check for existing correlation
            cursor.execute('''
                SELECT id FROM trend_correlations 
                WHERE trend_keyword = ? AND content_id = ? AND content_source = ?
            ''', (correlation.trend_keyword, correlation.content_id, correlation.content_source))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing correlation
                cursor.execute('''
                    UPDATE trend_correlations SET
                        correlation_strength = ?, correlation_type = ?, match_types = ?,
                        detected_at = ?, is_cross_source = ?
                    WHERE id = ?
                ''', (
                    correlation.correlation_strength, correlation.correlation_type,
                    json.dumps(correlation.match_types),
                    correlation.detected_at.isoformat() if correlation.detected_at else datetime.now().isoformat(),
                    correlation.is_cross_source, existing[0]
                ))
                
            else:
                # Insert new correlation
                cursor.execute('''
                    INSERT INTO trend_correlations
                    (trend_keyword, content_id, content_source, correlation_strength,
                     correlation_type, match_types, detected_at, is_cross_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    correlation.trend_keyword, correlation.content_id, correlation.content_source,
                    correlation.correlation_strength, correlation.correlation_type,
                    json.dumps(correlation.match_types),
                    correlation.detected_at.isoformat() if correlation.detected_at else datetime.now().isoformat(),
                    correlation.is_cross_source
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving correlation for {correlation.trend_keyword}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def update_source_coverage(self, trend_keyword: str, source_name: str, 
                                   strength: float) -> bool:
        """Update trend source coverage tracking"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now().isoformat()
            
            # Check for existing coverage
            cursor.execute('''
                SELECT mention_count, total_strength FROM trend_source_coverage
                WHERE trend_keyword = ? AND source_name = ?
            ''', (trend_keyword, source_name))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing coverage
                new_count = existing[0] + 1
                new_strength = existing[1] + strength
                
                cursor.execute('''
                    UPDATE trend_source_coverage SET
                        mention_count = ?, total_strength = ?, last_mention = ?
                    WHERE trend_keyword = ? AND source_name = ?
                ''', (new_count, new_strength, current_time, trend_keyword, source_name))
                
            else:
                # Insert new coverage
                cursor.execute('''
                    INSERT INTO trend_source_coverage
                    (trend_keyword, source_name, mention_count, total_strength, 
                     first_mention, last_mention)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (trend_keyword, source_name, 1, strength, current_time, current_time))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating source coverage for {trend_keyword}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_trending_topics(self, hours: int = 24, source: Optional[str] = None,
                          limit: int = 50, min_velocity: float = 0.0) -> List[TrendingTopic]:
        """Get recent trending topics"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(hours=hours)
        
        query = '''
            SELECT keyword, aliases, category, source, region, velocity, reach, momentum,
                   first_detected, peak_time, last_updated, correlation_score, 
                   geographic_relevance, is_active
            FROM trending_topics 
            WHERE last_updated > ? AND is_active = TRUE AND velocity >= ?
        '''
        params = [cutoff_date.isoformat(), min_velocity]
        
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        query += ' ORDER BY velocity DESC, correlation_score DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        trends = []
        for row in cursor.fetchall():
            trend = TrendingTopic(
                keyword=row[0],
                aliases=json.loads(row[1]) if row[1] else [],
                category=row[2] or 'general',
                source=row[3] or '',
                region=row[4] or 'worldwide',
                velocity=row[5] or 0.0,
                reach=row[6] or 0,
                momentum=row[7] or 'emerging',
                first_detected=datetime.fromisoformat(row[8]) if row[8] else None,
                peak_time=datetime.fromisoformat(row[9]) if row[9] else None,
                last_updated=datetime.fromisoformat(row[10]) if row[10] else None,
                correlation_score=row[11] or 0.0,
                geographic_relevance=row[12] or 0.0,
                is_active=bool(row[13])
            )
            trends.append(trend)
        
        conn.close()
        return trends
    
    def get_trend_correlations(self, trend_keyword: str) -> List[TrendCorrelation]:
        """Get correlations for a specific trend"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT trend_keyword, content_id, content_source, correlation_strength,
                   correlation_type, match_types, detected_at, is_cross_source
            FROM trend_correlations
            WHERE trend_keyword = ?
            ORDER BY correlation_strength DESC
        ''', (trend_keyword,))
        
        correlations = []
        for row in cursor.fetchall():
            correlation = TrendCorrelation(
                trend_keyword=row[0],
                content_id=row[1],
                content_source=row[2],
                correlation_strength=row[3],
                correlation_type=row[4] or '',
                match_types=json.loads(row[5]) if row[5] else [],
                detected_at=datetime.fromisoformat(row[6]) if row[6] else None,
                is_cross_source=bool(row[7])
            )
            correlations.append(correlation)
        
        conn.close()
        return correlations
    
    def get_cross_source_trends(self, min_sources: int = 2) -> List[Dict[str, Any]]:
        """Get trends that appear across multiple sources"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.keyword, t.category, t.velocity, t.correlation_score,
                   COUNT(DISTINCT tsc.source_name) as source_count,
                   GROUP_CONCAT(DISTINCT tsc.source_name) as sources,
                   SUM(tsc.total_strength) as total_strength
            FROM trending_topics t
            JOIN trend_source_coverage tsc ON t.keyword = tsc.trend_keyword
            WHERE t.is_active = TRUE
            GROUP BY t.keyword
            HAVING source_count >= ?
            ORDER BY source_count DESC, total_strength DESC
        ''', (min_sources,))
        
        cross_source_trends = []
        for row in cursor.fetchall():
            trend_data = {
                'keyword': row[0],
                'category': row[1],
                'velocity': row[2],
                'correlation_score': row[3],
                'source_count': row[4],
                'sources': row[5].split(',') if row[5] else [],
                'total_strength': row[6] or 0.0
            }
            cross_source_trends.append(trend_data)
        
        conn.close()
        return cross_source_trends
    
    def get_trend_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get comprehensive trend statistics"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Total trends
        cursor.execute(
            'SELECT COUNT(*) FROM trending_topics WHERE last_updated > ?',
            (cutoff_date.isoformat(),)
        )
        total_trends = cursor.fetchone()[0]
        
        # Trends by source
        cursor.execute('''
            SELECT source, COUNT(*) as count, AVG(velocity) as avg_velocity
            FROM trending_topics 
            WHERE last_updated > ?
            GROUP BY source
            ORDER BY count DESC
        ''', (cutoff_date.isoformat(),))
        
        source_stats = {}
        for row in cursor.fetchall():
            source_stats[row[0]] = {
                'count': row[1],
                'avg_velocity': round(row[2] or 0, 2)
            }
        
        # Cross-source trends
        cursor.execute('''
            SELECT COUNT(DISTINCT t.keyword) 
            FROM trending_topics t
            JOIN trend_source_coverage tsc ON t.keyword = tsc.trend_keyword
            WHERE t.last_updated > ?
            GROUP BY t.keyword
            HAVING COUNT(DISTINCT tsc.source_name) >= 2
        ''', (cutoff_date.isoformat(),))
        
        cross_source_count = len(cursor.fetchall())
        
        # Total correlations
        cursor.execute(
            'SELECT COUNT(*) FROM trend_correlations WHERE detected_at > ?',
            (cutoff_date.isoformat(),)
        )
        total_correlations = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_trends': total_trends,
            'cross_source_trends': cross_source_count,
            'total_correlations': total_correlations,
            'source_breakdown': source_stats,
            'period_days': days
        }
    
    def cleanup_old_trends(self, days: int = 30) -> int:
        """Remove old trending topics and correlations"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Remove old trends
            cursor.execute(
                'DELETE FROM trending_topics WHERE last_updated < ?',
                (cutoff_date.isoformat(),)
            )
            trends_removed = cursor.rowcount
            
            # Remove old correlations
            cursor.execute(
                'DELETE FROM trend_correlations WHERE detected_at < ?',
                (cutoff_date.isoformat(),)
            )
            correlations_removed = cursor.rowcount
            
            # Remove old source coverage
            cursor.execute(
                'DELETE FROM trend_source_coverage WHERE last_mention < ?',
                (cutoff_date.isoformat(),)
            )
            coverage_removed = cursor.rowcount
            
            conn.commit()
            
            total_removed = trends_removed + correlations_removed + coverage_removed
            if total_removed > 0:
                logger.info(f"Cleaned up {trends_removed} trends, {correlations_removed} correlations, {coverage_removed} coverage records")
            
            return total_removed
            
        except Exception as e:
            logger.error(f"Error cleaning up old trends: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()


# Integration with existing DatabaseManager
def add_trend_methods_to_database_manager():
    """Add trend methods to existing DatabaseManager class"""
    
    # This would be added to the existing DatabaseManager class
    def __init__(self, db_path: str = "rss_feeds.db"):
        # ... existing init code ...
        self.trend_db = TrendDatabaseManager(db_path)
    
    async def save_trending_topic(self, trend: TrendingTopic) -> bool:
        """Save trending topic to database"""
        return await self.trend_db.save_trending_topic(trend)
    
    async def save_trend_correlation(self, correlation: TrendCorrelation) -> bool:
        """Save trend correlation to database"""
        return await self.trend_db.save_trend_correlation(correlation)
    
    def get_trending_topics(self, **kwargs) -> List[TrendingTopic]:
        """Get trending topics from database"""
        return self.trend_db.get_trending_topics(**kwargs)
    
    def get_trend_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get trend statistics"""
        return self.trend_db.get_trend_statistics(days)
    
    def cleanup_old_trends(self, days: int = 30) -> int:
        """Cleanup old trend data"""
        return self.trend_db.cleanup_old_trends(days)