import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from digestr.core.database import DatabaseManager
    print("✅ Import successful!")
    print("✅ Digestr modules are working!")
except ImportError as e:
    print(f"❌ Import failed: {e}")
