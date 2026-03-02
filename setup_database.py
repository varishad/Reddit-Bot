"""
Quick setup script to verify database connection and create a test user
"""
from database import Database
from admin_tools import AdminTools

def main():
    print("=" * 60)
    print("Reddit Bot - Database Setup Verification")
    print("=" * 60)
    
    try:
        # Test database connection
        print("\n1. Testing database connection...")
        db = Database()
        print("   ✅ Database connection successful!")
        
        # Test admin tools
        print("\n2. Testing admin tools...")
        admin = AdminTools()
        print("   ✅ Admin tools initialized!")
        
        # Create a test user
        print("\n3. Creating test user...")
        print("   (This will create a test account for verification)")
        
        password = input("\nEnter password for test user: ").strip()
        if not password:
            print("   ❌ Password required")
            return
        
        license_key, activation_code, success, error = admin.create_user(password, "Test user created by setup script")
        
        if success:
            print("\n   ✅ Test user created successfully!")
            print(f"\n   License Key: {license_key}")
            print(f"   Password: {password}")
            print(f"   Activation Code: {activation_code}")
            print("\n   ⚠️  IMPORTANT: Save these credentials!")
            print("\n   You can now:")
            print("   1. Run the GUI: py gui_app.py")
            print("   2. Activate with the activation code")
            print("   3. Login with license key and password")
        else:
            print(f"\n   ❌ Error creating user: {error}")
        
        print("\n" + "=" * 60)
        print("Setup complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nPlease check:")
        print("1. Supabase credentials in config.py")
        print("2. Database schema is created (run database/schema.sql)")
        print("3. Internet connection")

if __name__ == "__main__":
    main()

