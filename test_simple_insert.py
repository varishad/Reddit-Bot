"""
Simple test to verify database access
"""
from database import Database

def main():
    print("Testing database with simple operations...")
    
    try:
        db = Database()
        
        # Try to get client IP (this should work)
        print("\n1. Testing IP detection...")
        ip = db.get_client_ip()
        print(f"   ✅ Your IP: {ip}")
        
        # Try to create a test user directly
        print("\n2. Testing user creation...")
        from admin_tools import AdminTools
        admin = AdminTools()
        
        license_key, activation_code, success, error = admin.create_user("test123", "Test user")
        
        if success:
            print(f"   ✅ User created successfully!")
            print(f"   License Key: {license_key}")
            print(f"   Activation Code: {activation_code}")
            print("\n   🎉 Database is working correctly!")
            return True
        else:
            print(f"   ❌ Error: {error}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()


