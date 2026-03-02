"""
Admin Tools for Managing Users and Activations
Run this script to create users, generate activation codes, and manage accounts.
"""
import hashlib
import secrets
import string
from database import Database
from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

class AdminTools:
    def __init__(self):
        self.db = Database()
        self.client = self.db.client
    
    def hash_password(self, password: str) -> str:
        """Hash password."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def generate_license_key(self) -> str:
        """Generate a unique license key."""
        chars = string.ascii_uppercase + string.digits
        while True:
            key = f"REDDIT-{''.join(secrets.choice(chars) for _ in range(4))}-{''.join(secrets.choice(chars) for _ in range(4))}-{''.join(secrets.choice(chars) for _ in range(4))}"
            # Check if exists
            result = self.client.table('users').select('license_key').eq('license_key', key).execute()
            if not result.data:
                return key
    
    def generate_activation_code(self) -> str:
        """Generate a unique activation code."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(12))
    
    def create_user(self, password: str, notes: str = "") -> tuple:
        """
        Create a new user account.
        Returns: (license_key, activation_code, success, error_message)
        """
        try:
            license_key = self.generate_license_key()
            password_hash = self.hash_password(password)
            
            # Create user
            user_result = self.client.table('users').insert({
                'license_key': license_key,
                'password_hash': password_hash,
                'notes': notes
            }).execute()
            
            if not user_result.data:
                return None, None, False, "Failed to create user"
            
            user_id = user_result.data[0]['id']
            
            # Generate activation code
            activation_code = self.generate_activation_code()
            
            # Create activation record
            activation_result = self.client.table('activations').insert({
                'license_key': license_key,
                'activation_code': activation_code,
                'activation_ip': '0.0.0.0',  # Will be set on first use
                'user_id': user_id
            }).execute()
            
            if not activation_result.data:
                return None, None, False, "Failed to create activation code"
            
            return license_key, activation_code, True, None
            
        except Exception as e:
            return None, None, False, str(e)
    
    def list_users(self):
        """List all users."""
        try:
            result = self.client.table('users').select('*').order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error listing users: {e}")
            return []
    
    def get_user_stats(self, license_key: str):
        """Get detailed stats for a user."""
        try:
            # Get user
            user_result = self.client.table('users').select('*').eq('license_key', license_key).execute()
            if not user_result.data:
                return None
            
            user = user_result.data[0]
            user_id = user['id']
            
            # Get usage logs
            logs_result = self.client.table('usage_logs').select('*').eq('user_id', user_id).order('session_start', desc=True).limit(10).execute()
            
            return {
                'user': user,
                'recent_sessions': logs_result.data if logs_result.data else []
            }
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return None
    
    def deactivate_user(self, license_key: str):
        """Deactivate a user account."""
        try:
            self.client.table('users').update({
                'is_active': False
            }).eq('license_key', license_key).execute()
            return True, None
        except Exception as e:
            return False, str(e)


def main():
    """Interactive admin tool."""
    admin = AdminTools()
    
    while True:
        print("\n" + "=" * 60)
        print("Reddit Bot - Admin Tools")
        print("=" * 60)
        print("1. Create new user")
        print("2. List all users")
        print("3. View user stats")
        print("4. Deactivate user")
        print("5. Exit")
        print("=" * 60)
        
        choice = input("\nSelect option: ").strip()
        
        if choice == "1":
            password = input("Enter password for new user: ").strip()
            notes = input("Enter notes (optional): ").strip()
            
            license_key, activation_code, success, error = admin.create_user(password, notes)
            
            if success:
                print("\n✅ User created successfully!")
                print(f"License Key: {license_key}")
                print(f"Activation Code: {activation_code}")
                print("\n⚠️  IMPORTANT: Save these credentials securely!")
            else:
                print(f"\n❌ Error: {error}")
        
        elif choice == "2":
            users = admin.list_users()
            if users:
                print(f"\nTotal users: {len(users)}")
                print("\n" + "-" * 60)
                for user in users:
                    status = "Active" if user.get('is_active') else "Inactive"
                    print(f"License: {user['license_key']}")
                    print(f"Status: {status}")
                    print(f"Created: {user.get('created_at', 'N/A')}")
                    print(f"Total Sessions: {user.get('total_sessions', 0)}")
                    print(f"Accounts Processed: {user.get('total_accounts_processed', 0)}")
                    print("-" * 60)
            else:
                print("\nNo users found")
        
        elif choice == "3":
            license_key = input("Enter license key: ").strip().upper()
            stats = admin.get_user_stats(license_key)
            if stats:
                user = stats['user']
                print(f"\nUser: {user['license_key']}")
                print(f"Status: {'Active' if user.get('is_active') else 'Inactive'}")
                print(f"Total Sessions: {user.get('total_sessions', 0)}")
                print(f"Total Accounts Processed: {user.get('total_accounts_processed', 0)}")
                print(f"Last Login: {user.get('last_login', 'Never')}")
                
                if stats['recent_sessions']:
                    print("\nRecent Sessions:")
                    for session in stats['recent_sessions'][:5]:
                        print(f"  - {session.get('session_start', 'N/A')}: {session.get('accounts_processed', 0)} accounts")
            else:
                print("User not found")
        
        elif choice == "4":
            license_key = input("Enter license key to deactivate: ").strip().upper()
            confirm = input(f"Deactivate {license_key}? (yes/no): ").strip().lower()
            if confirm == "yes":
                success, error = admin.deactivate_user(license_key)
                if success:
                    print("✅ User deactivated")
                else:
                    print(f"❌ Error: {error}")
        
        elif choice == "5":
            print("Goodbye!")
            break
        
        else:
            print("Invalid option")


if __name__ == "__main__":
    main()

