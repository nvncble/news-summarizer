import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from digestr.core.database import DatabaseManager
    print("✅ Database module: OK")
except Exception as e:
    print(f"❌ Database module: {e}")

try:
    from digestr.core.fetcher import FeedManager, RSSFetcher  
    print("✅ Fetcher module: OK")
except Exception as e:
    print(f"❌ Fetcher module: {e}")

try:
    from digestr.llm_providers.ollama import OllamaProvider
    print("✅ Ollama provider: OK")
except Exception as e:
    print(f"❌ Ollama provider: {e}")
