"""
Direct database test to check table creation
"""
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

def test_database():
    print("=" * 70)
    print("Direct Database Test")
    print("=" * 70)
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Try to check if users table exists by attempting to query it
        print("\n1. Testing users table...")
        try:
            result = client.table('users').select('id').limit(1).execute()
            print("   ✅ Users table exists and is accessible!")
            print(f"   Current records: {len(result.data)}")
        except Exception as e:
            error_msg = str(e)
            if 'permission denied' in error_msg.lower():
                print("   ⚠️  Permission denied - checking if table exists...")
                # Try to insert a test record (will fail if table doesn't exist)
                try:
                    # This will fail if table doesn't exist, succeed if RLS is blocking
                    test_result = client.table('users').insert({
                        'license_key': 'TEST-CHECK-1234-5678',
                        'password_hash': 'test'
                    }).execute()
                    print("   ✅ Table exists! (Test record inserted, you can delete it)")
                except Exception as insert_error:
                    if 'does not exist' in str(insert_error).lower() or 'relation' in str(insert_error).lower():
                        print("   ❌ Table 'users' does not exist!")
                        print("   Please run the SQL schema in Supabase.")
                    else:
                        print(f"   ⚠️  Error: {str(insert_error)[:100]}")
            else:
                print(f"   ❌ Error: {error_msg[:100]}")
        
        # Test other tables
        tables = ['activations', 'usage_logs', 'session_details']
        for table in tables:
            print(f"\n2. Testing {table} table...")
            try:
                result = client.table(table).select('id').limit(1).execute()
                print(f"   ✅ {table} table exists!")
            except Exception as e:
                error_msg = str(e)
                if 'permission denied' in error_msg.lower():
                    print(f"   ⚠️  {table} - Permission denied (table may exist)")
                elif 'does not exist' in error_msg.lower() or 'relation' in error_msg.lower():
                    print(f"   ❌ {table} table does not exist!")
                else:
                    print(f"   ⚠️  {table} - {error_msg[:80]}")
        
        print("\n" + "=" * 70)
        print("If you see 'permission denied' for all tables:")
        print("1. Check if you ran the SQL schema completely")
        print("2. Check if RLS policies were created correctly")
        print("3. Verify the service role key has proper permissions")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Connection error: {str(e)}")

if __name__ == "__main__":
    test_database()


