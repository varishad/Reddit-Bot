from admin_tools import AdminTools
import os

def create_initial_user():
    print("=" * 60)
    print("Reddit Bot - Initial User Setup")
    print("=" * 60)
    
    admin = AdminTools()
    
    # Check if any users already exist
    users = admin.list_users()
    if users:
        print(f"\nℹ️  {len(users)} users already exist in the database.")
        # Proceed anyway to create a known test user if requested or if needed
    
    # Generate a random password for the user if they don't want to provide one
    # But it's better to let them know
    test_password = "password123"
    
    print(f"\nCreating initial test user with password: {test_password}")
    
    license_key, activation_code, success, error = admin.create_user(test_password, "Initial setup test user")
    
    if success:
        print("\n✅ Initial user created successfully!")
        print(f"\nLicense Key: {license_key}")
        print(f"Password: {test_password}")
        print(f"Activation Code: {activation_code}")
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("1. Run 'open_app.command'")
        print("2. When prompted, enter the Activation Code ABOVE to lock your IP.")
        print("3. Then login with the License Key and Password.")
        print("=" * 60)
        
        # Save to a file for easy reference
        with open("TEST_CREDENTIALS.txt", "w") as f:
            f.write(f"License Key: {license_key}\n")
            f.write(f"Password: {test_password}\n")
            f.write(f"Activation Code: {activation_code}\n")
        print("\n📁 Credentials also saved to TEST_CREDENTIALS.txt")
        
    else:
        print(f"\n❌ Error: {error}")

if __name__ == "__main__":
    create_initial_user()
