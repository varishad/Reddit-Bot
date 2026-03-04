from database import Database
from bot_engine import RedditBotEngine
import sys

print("Checking Database initialization...")
try:
    db = Database()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    sys.exit(1)

print("\nChecking RedditBotEngine initialization...")
try:
    # RedditBotEngine might take some arguments, let's check its __init__
    import inspect
    sig = inspect.signature(RedditBotEngine.__init__)
    print(f"RedditBotEngine.__init__ signature: {sig}")
    
    # Try with minimum args or defaults
    engine = RedditBotEngine()
    print("✅ RedditBotEngine initialized successfully")
except Exception as e:
    print(f"❌ RedditBotEngine initialization failed: {e}")
    sys.exit(1)

print("\nAll core components initialized successfully!")
