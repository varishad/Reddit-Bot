"""
Check which Supabase key is being used and test connection
"""
from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client
import jwt
import json

def decode_jwt(token):
    """Decode JWT to see what role it has (without verification)."""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except:
        return None

print("=" * 70)
print("Supabase Key Check")
print("=" * 70)

print(f"\nURL: {SUPABASE_URL}")
print(f"\nKey (first 50 chars): {SUPABASE_KEY[:50]}...")

# Decode JWT to check role
print("\n1. Checking JWT token...")
decoded = decode_jwt(SUPABASE_KEY)
if decoded:
    print(f"   Role: {decoded.get('role', 'unknown')}")
    print(f"   Ref: {decoded.get('ref', 'unknown')}")
    if decoded.get('role') == 'service_role':
        print("   ✅ Using SERVICE_ROLE key (should bypass RLS)")
    else:
        print("   ⚠️  NOT using service_role key!")
        print("   This might be the issue - need service_role key")
else:
    print("   ⚠️  Could not decode JWT")

# Test connection
print("\n2. Testing connection...")
try:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Try a simple query that doesn't require tables
    print("   ✅ Supabase client created")
    
    # Try to query a system table or function
    print("\n3. Testing direct SQL query (if possible)...")
    # Note: Supabase Python client doesn't support raw SQL easily
    # But we can try to insert to see the exact error
    
except Exception as e:
    print(f"   ❌ Error creating client: {e}")

print("\n" + "=" * 70)
print("If role is 'service_role', RLS should be bypassed.")
print("If you still get permission denied, try:")
print("1. Double-check the service_role key in Supabase dashboard")
print("2. Make sure RLS is disabled on the tables")
print("3. Check if the tables actually exist")
print("=" * 70)

