import sqlite3
import sys
import os

def migrate_database():
    """Add trend analysis tables to existing database"""
    
    db_path = "rss_feeds.db"
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Run the main application first.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if trend tables already exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trending_topics'")
        if cursor.fetchone():
            print("Trend tables already exist.")
            return
        
        # Add trending topics table
        cursor.execute('''
            CREATE TABLE trending_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                aliases TEXT,
                category TEXT,
                source TEXT,
                region TEXT,
                velocity REAL DEFAULT 0.0,
                reach INTEGER DEFAULT 0,
                momentum TEXT DEFAULT 'emerging',
                first_detected TEXT,
                peak_time TEXT,
                last_updated TEXT,
                correlation_score REAL DEFAULT 0.0,
                geographic_relevance REAL DEFAULT 0.0,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Add trend correlations table
        cursor.execute('''
            CREATE TABLE trend_correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trend_keyword TEXT NOT NULL,
                content_id TEXT NOT NULL,
                content_source TEXT NOT NULL,
                correlation_strength REAL NOT NULL,
                correlation_type TEXT,
                match_types TEXT,
                detected_at TEXT,
                is_cross_source BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Add trend source coverage table
        cursor.execute('''
            CREATE TABLE trend_source_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trend_keyword TEXT NOT NULL,
                source_name TEXT NOT NULL,
                mention_count INTEGER DEFAULT 1,
                total_strength REAL DEFAULT 0.0,
                first_mention TEXT,
                last_mention TEXT,
                UNIQUE(trend_keyword, source_name)
            )
        ''')
        
        # Add indexes
        cursor.execute('CREATE INDEX idx_trending_topics_keyword ON trending_topics(keyword)')
        cursor.execute('CREATE INDEX idx_trending_topics_active ON trending_topics(is_active)')
        cursor.execute('CREATE INDEX idx_trend_correlations_keyword ON trend_correlations(trend_keyword)')
        cursor.execute('CREATE INDEX idx_trend_correlations_content ON trend_correlations(content_id)')
        cursor.execute('CREATE INDEX idx_trend_coverage_keyword ON trend_source_coverage(trend_keyword)')
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        print("✅ Trend analysis tables added")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()