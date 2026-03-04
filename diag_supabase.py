import traceback
import sys
import os

print("-" * 50)
print(f"Python: {sys.version}")
try:
    import supabase
    print(f"Supabase version: {getattr(supabase, '__version__', 'unknown')}")
    print(f"Supabase file: {supabase.__file__}")
except Exception as e:
    print(f"Error importing supabase: {e}")

print("-" * 50)
print("Testing create_client...")
try:
    from supabase import create_client
    # Use dummy values
    url = "https://example.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV4YW1wbGUiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYwMDAwMDAwMCwiZXhwIjoyMDAwMDAwMDAwfQ.dummy-key"
    client = create_client(url, key)
    print("✅ create_client succeeded with dummy values")
except Exception:
    traceback.print_exc()

print("-" * 50)
print("Testing Database initialization...")
try:
    from database import Database
    db = Database()
    print("✅ Database initialized successfully")
except Exception:
    traceback.print_exc()
