# Digestr.ai API Documentation

## Core Modules

### Database Manager (`digestr.core.database`)

#### DatabaseManager Class
Handles all SQLite operations, schema management, and statistics.

```python
from digestr.core.database import DatabaseManager, Article

# Initialize
db = DatabaseManager("path/to/database.db")

# Get recent articles
articles = db.get_recent_articles(
    hours=24,           # Last 24 hours
    category="tech",    # Optional category filter
    limit=50,          # Maximum articles
    min_importance=2.0  # Minimum importance score
)

# Statistics
stats = db.get_feed_statistics(days=7)


#RSS Fetcher (digestr.core.fetcher)
#FeedManager Class
#Manages RSS feed configurations and categories.

 digestr.core.fetcher import FeedManager

feed_mgr = FeedManager()

# Get available categories
categories = feed_mgr.get_categories()
# Returns: ['tech', 'world_news', 'sports', 'cutting_edge', 'business', 'security']

# Get feeds for category
tech_feeds = feed_mgr.get_feeds_for_category("tech")


#LLM PROVIDERS

from digestr.llm_providers.ollama import OllamaProvider

llm = OllamaProvider(
    ollama_url="http://localhost:11434",
    models={
        "default": "llama3.1:8b",
        "technical": "deepseek-coder:6.7b",
        "academic": "qwen2.5:14b"
    }
)

# Generate briefing
briefing = await llm.generate_briefing(
    articles,
    briefing_type="comprehensive",  # or "quick", "analytical"
    model="llama3.1:8b"            # Optional specific model
)






#CLI Interface
#Command Reference
#Status Command


'''bash

python digestr_cli_enhanced.py status

Shows system health, module status, and configuration summary.
#Fetch Command

bash

python digestr_cli_enhanced.py fetch

Retrieves latest articles from configured RSS feeds.

#Articles Command
bash
python digestr_cli_enhanced.py articles

Displays recent articles with importance scores and sources.
#Briefing Command
bash
python digestr_cli_enhanced.py briefing [--style STYLE]


#Generates AI-powered news briefing.
Options:

--style: comprehensive (default), quick, analytical

#Integration Examples

#Custom Briefing Script

python
import asyncio
from digestr.core.database import DatabaseManager
from digestr.llm_providers.ollama import OllamaProvider

async def custom_briefing():
    db = DatabaseManager()
    llm = OllamaProvider()
    
    # Get tech articles from last 12 hours
    articles = db.get_recent_articles(
        hours=12, 
        category="tech", 
        min_importance=3.0
    )
    
    if articles:
        # Convert to dict format for LLM
        article_dicts = [
            {
                'title': a.title,
                'summary': a.summary,
                'category': a.category,
                'importance_score': a.importance_score
            }
            for a in articles
        ]
        
        # Generate focused briefing
        briefing = await llm.generate_briefing(
            article_dicts, 
            briefing_type="analytical"
        )
        
        print(briefing)

# Run
asyncio.run(custom_briefing())
