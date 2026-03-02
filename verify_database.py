"""
Verify database setup and create test user
"""
from database import Database
from admin_tools import AdminTools

def verify_tables(db):
    """Check if all required tables exist."""
    required_tables = ['users', 'activations', 'usage_logs', 'session_details']
    missing_tables = []
    
    for table in required_tables:
        try:
            result = db.client.table(table).select('*').limit(1).execute()
            print(f"   ✅ Table '{table}' exists")
        except Exception as e:
            print(f"   ❌ Table '{table}' missing or error: {str(e)[:50]}")
            missing_tables.append(table)
    
    return len(missing_tables) == 0

def main():
    print("=" * 70)
    print("Reddit Bot - Database Verification")
    print("=" * 70)
    
    try:
        print("\n1. Testing database connection...")
        db = Database()
        print("   ✅ Connected to Supabase!")
        
        print("\n2. Verifying tables...")
        if verify_tables(db):
            print("\n   ✅ All tables exist! Database is ready.")
            
            # Ask to create test user
            create_user = input("\n3. Create a test user? (y/n): ").strip().lower()
            if create_user == 'y':
                password = input("   Enter password for test user: ").strip()
                if password:
                    admin = AdminTools()
                    license_key, activation_code, success, error = admin.create_user(
                        password, 
                        "Test user created by verification script"
                    )
                    
                    if success:
                        print("\n   ✅ Test user created successfully!")
                        print("\n   " + "=" * 66)
                        print("   USER CREDENTIALS:")
                        print("   " + "=" * 66)
                        print(f"   License Key: {license_key}")
                        print(f"   Password: {password}")
                        print(f"   Activation Code: {activation_code}")
                        print("   " + "=" * 66)
                        print("\n   ⚠️  IMPORTANT: Save these credentials!")
                        print("\n   Next steps:")
                        print("   1. Run: py gui_app.py")
                        print("   2. Click 'Activate Account'")
                        print("   3. Enter the activation code above")
                        print("   4. Then login with license key and password")
                    else:
                        print(f"\n   ❌ Error creating user: {error}")
                else:
                    print("   ⚠️  Password required, skipping user creation")
            else:
                print("\n   Skipping user creation. You can create users later with:")
                print("   py admin_tools.py")
        else:
            print("\n   ❌ Some tables are missing!")
            print("\n   Please run the SQL schema in Supabase:")
            print("   1. Go to: https://supabase.com/dashboard/project/nszfjvbxrbsnnbixnboc/")
            print("   2. SQL Editor → New Query")
            print("   3. Copy/paste contents of 'database/schema_clean.sql'")
            print("   4. Run the query")
            print("   5. Then run this script again")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nPlease check:")
        print("1. Supabase credentials in config.py are correct")
        print("2. Internet connection")
        print("3. Database schema has been run in Supabase")

if __name__ == "__main__":
    main()

