"""
Supabase Database Connection and Functions
Handles all database operations for user authentication, activation, and usage tracking.
"""
import os
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from supabase import create_client, Client
import requests
from config import SUPABASE_URL, SUPABASE_KEY

class Database:
    def __init__(self):
        """Initialize Supabase connection."""
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_KEY
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in config.py")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        self.current_user_id = None
        self.current_license_key = None
    
    def get_client_ip(self) -> str:
        """Get the current client's public IP address."""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json().get('ip', '0.0.0.0')
        except:
            return '0.0.0.0'
    
    def get_hwid(self) -> str:
        """
        Generate a unique Hardware ID (HWID) for the current machine.
        Uses a combination of MAC address and system-specific markers.
        """
        try:
            # Get MAC address as a base
            mac = uuid.getnode()
            # Create a stable hash of the hardware identifier
            hwid_str = f"RB-HWID-{mac}"
            return hashlib.sha256(hwid_str.encode()).hexdigest().upper()[:24]
        except:
            # Fallback to a random UUID stored in a local file if hardware check fails
            hwid_file = os.path.join(os.path.expanduser("~"), ".reddit_bot_hwid")
            if os.path.exists(hwid_file):
                with open(hwid_file, "r") as f:
                    return f.read().strip()
            else:
                new_hwid = str(uuid.uuid4()).upper()[:24]
                with open(hwid_file, "w") as f:
                    f.write(new_hwid)
                return new_hwid

    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, license_key: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Authenticate user with license key, password, and Hardware ID (HWID).
        Returns: (success, error_message, user_data)
        """
        try:
            # Find user by license key
            result = self.client.table('users').select('*').eq('license_key', license_key.upper()).execute()
            
            if not result.data:
                return False, "Invalid license key", None
            
            user = result.data[0]
            
            # Check password
            password_hash = self.hash_password(password)
            if user['password_hash'] != password_hash:
                return False, "Invalid password", None
            
            # --- DEVICE LOCKING (HWID) CHECK ---
            current_hwid = self.get_hwid()
            stored_hwid = user.get('machine_id')
            
            # If account is active but has a different HWID, block access
            if user.get('is_active') and stored_hwid and stored_hwid != current_hwid:
                return False, f"Account Locked: This license is already registered to another device. (ID: ...{stored_hwid[-6:]})", None
            
            # --- SUBSCRIPTION PLAN DATE CHECK ---
            now = datetime.utcnow()
            start_date_str = user.get('plan_start_date')
            end_date_str = user.get('plan_end_date')
            
            if user.get('is_active'):
                if start_date_str:
                    start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    if now < start_date:
                        return False, f"Plan Error: Your plan is scheduled to start on {start_date.strftime('%Y-%m-%d')}.", None
                
                if end_date_str:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    if now > end_date:
                        return False, f"Plan Expired: Your subscription ended on {end_date.strftime('%Y-%m-%d')}. Please renew to continue.", None

            # Logic for VPN/IP remains, but HWID takes precedence
            client_ip = self.get_client_ip()
            activation_ip = user.get('activation_ip')
            current_hwid = self.get_hwid()
            stored_hwid = user.get('machine_id')
            
            # If HWID matches, we trust it even if IP changed (dynamic IP/VPN)
            hwid_matches = stored_hwid and stored_hwid == current_hwid
            
            if not hwid_matches and activation_ip and str(activation_ip) != '0.0.0.0':
                if str(activation_ip) != client_ip:
                    return False, f"Account locked to activation IP: {activation_ip}. Please login from your home network first.", None
            
            # Update last login info
            self.client.table('users').update({
                'last_login': datetime.utcnow().isoformat(),
                'last_login_ip': client_ip,
                'machine_id': current_hwid # Ensure HWID is saved if it was missing 
            }).eq('id', user['id']).execute()
            
            self.current_user_id = user['id']
            self.current_license_key = license_key.upper()
            
            return True, None, user
            
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None

    def verify_license_key(self, license_key: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Verify a license key for session recovery (no password required).
        Checks for existence, active status, HWID match, and plan validity.
        """
        try:
            result = self.client.table('users').select('*').eq('license_key', license_key.upper()).execute()
            if not result.data:
                return False, "Invalid license key", None
            
            user = result.data[0]
            
            # Basic validation
            if not user.get('is_active'):
                return False, "License is not active", None
            
            # HWID Check
            current_hwid = self.get_hwid()
            stored_hwid = user.get('machine_id')
            if stored_hwid and stored_hwid != current_hwid:
                return False, "License registered to another device", None
            
            # Plan Check
            now = datetime.utcnow()
            end_date_str = user.get('plan_end_date')
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                if now > end_date:
                    return False, "Subscription expired", None
            
            # Set current session if verified
            self.current_user_id = user['id']
            self.current_license_key = license_key.upper()
            
            return True, None, user
        except Exception as e:
            return False, str(e), None
    
    def activate_account(self, activation_code: str) -> Tuple[bool, Optional[str]]:
        """
        Activate account and lock it to the current Hardware ID (HWID) and IP.
        """
        try:
            client_ip = self.get_client_ip()
            current_hwid = self.get_hwid()
            
            # Check activation code
            activation_result = self.client.table('activations').select('*').eq('activation_code', activation_code.upper()).execute()
            
            if not activation_result.data:
                return False, "Invalid activation code"
            
            activation = activation_result.data[0]
            
            if activation.get('is_used', False):
                return False, "This activation code has already been used"
            
            license_key = activation['license_key']
            user_result = self.client.table('users').select('*').eq('license_key', license_key).execute()
            
            if not user_result.data:
                return False, "User account not found"
            
            user = user_result.data[0]
            
            # Activate and LOCK to this machine
            # Set default monthly plan (30 days) if not already set
            now = datetime.utcnow()
            start_date = user.get('plan_start_date') or now.isoformat()
            end_date = user.get('plan_end_date') or (now + timedelta(days=30)).isoformat()

            self.client.table('users').update({
                'is_active': True,
                'activated_at': now.isoformat(),
                'activation_ip': client_ip,
                'machine_id': current_hwid,
                'plan_start_date': start_date,
                'plan_end_date': end_date
            }).eq('id', user['id']).execute()
            
            # Mark activation record
            self.client.table('activations').update({
                'is_used': True,
                'activation_ip': client_ip,
                'machine_id': current_hwid,
                'user_id': user['id']
            }).eq('id', activation['id']).execute()
            
            self.current_user_id = user['id']
            self.current_license_key = license_key
            
            return True, None
            
        except Exception as e:
            return False, f"Activation error: {str(e)}"
    
    def create_session(self) -> Optional[str]:
        """Create a new usage session and return session_id."""
        if not self.current_user_id:
            return None
        
        try:
            client_ip = self.get_client_ip()
            session_id = str(uuid.uuid4())
            
            self.client.table('usage_logs').insert({
                'user_id': self.current_user_id,
                'license_key': self.current_license_key,
                'session_id': session_id,
                'ip_address': client_ip,
                'session_start': datetime.utcnow().isoformat()
            }).execute()
            
            return session_id
            
        except Exception as e:
            print(f"Error creating session: {e}")
            return None
    
    def end_session(self, session_id: str, accounts_processed: int, 
                   success_count: int, invalid_count: int, 
                   banned_count: int, error_count: int):
        """End a usage session and update statistics."""
        if not session_id:
            return
        
        try:
            end_time = datetime.utcnow()
            
            # Calculate duration
            result = self.client.table('usage_logs').select('session_start').eq('session_id', session_id).execute()
            if result.data:
                start_time = datetime.fromisoformat(result.data[0]['session_start'].replace('Z', '+00:00'))
                duration = int((end_time - start_time.replace(tzinfo=None)).total_seconds())
            else:
                duration = 0
            
            self.client.table('usage_logs').update({
                'session_end': end_time.isoformat(),
                'accounts_processed': accounts_processed,
                'success_count': success_count,
                'invalid_count': invalid_count,
                'banned_count': banned_count,
                'error_count': error_count,
                'duration_seconds': duration
            }).eq('session_id', session_id).execute()
            
        except Exception as e:
            print(f"Error ending session: {e}")
    
    def log_account_result(self, session_id: str, email: str, status: str, 
                          password: Optional[str] = None,
                          username: Optional[str] = None, karma: Optional[str] = None,
                          error_message: Optional[str] = None):
        """Log or update individual account processing result locally."""
        if not session_id:
            return
        
        try:
            import json
            import os
            
            results_file = "session_results.json"
            results = []
            if os.path.exists(results_file):
                try:
                    with open(results_file, 'r') as f:
                        results = json.load(f)
                except:
                    results = []

            # Upsert logic: If email exists in THIS session, update it
            found = False
            for r in results:
                if r.get('email') == email and r.get('session_id') == session_id:
                    r.update({
                        'reddit_password': password or r.get('reddit_password'),
                        'status': status,
                        'username': username or r.get('username'),
                        'karma': karma or r.get('karma'),
                        'error_message': error_message or r.get('error_message'),
                        'processed_at': datetime.utcnow().isoformat()
                    })
                    found = True
                    break
            
            if not found:
                result_item = {
                    'id': str(uuid.uuid4()),
                    'session_id': session_id,
                    'email': email,
                    'reddit_password': password,
                    'status': status,
                    'username': username,
                    'karma': karma,
                    'error_message': error_message,
                    'created_at': datetime.utcnow().isoformat()
                }
                results.insert(0, result_item)
            
            # Prune to 30,000 for high-volume support
            if len(results) > 30000:
                results = results[:30000]
                
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            print(f"Error logging account result locally: {e}")

    def log_batch_results(self, accounts: List[Dict], status: str = "pending"):
        """Log a bulk list of accounts (e.g., during import) as pending."""
        try:
            import json
            import os
            
            # Since we don't have a session_id yet, we use a placeholder or None
            # This allows them to show up in the UI immediately
            results_file = "session_results.json"
            results = []
            if os.path.exists(results_file):
                try:
                    with open(results_file, 'r') as f:
                        results = json.load(f)
                except:
                    results = []

            new_entries = []
            now = datetime.utcnow().isoformat()
            
            for acc in accounts:
                new_entries.append({
                    'id': str(uuid.uuid4()),
                    'session_id': None, # Means not checked yet
                    'email': acc['email'],
                    'reddit_password': acc['password'],
                    'status': status,
                    'username': None,
                    'karma': None,
                    'error_message': None,
                    'created_at': now
                })
            
            # Put new at the top
            results = new_entries + results
            
            if len(results) > 30000:
                results = results[:30000]
                
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error logging batch: {e}")
            return False
    
    def get_user_stats(self) -> Optional[Dict]:
        """Get current user statistics."""
        if not self.current_user_id:
            return None
        
        try:
            result = self.client.table('users').select('*').eq('id', self.current_user_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (Admin only check should be in server.py)."""
        try:
            result = self.client.table('users').select('*').order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []

    def create_user(self, username: str, license_key: str, password: str, 
                   role: str = 'User', plan_name: str = 'Monthly Normal', 
                   days: int = 30) -> Tuple[bool, str]:
        """Create a new user in the database."""
        try:
            password_hash = self.hash_password(password)
            now = datetime.utcnow()
            plan_end = now + timedelta(days=days)
            
            result = self.client.table('users').insert({
                'username': username,
                'license_key': license_key.upper(),
                'password_hash': password_hash,
                'role': role,
                'plan_name': plan_name,
                'plan_start_date': now.isoformat(),
                'plan_end_date': plan_end.isoformat(),
                'is_active': True,
                'created_at': now.isoformat()
            }).execute()
            
            if result.data:
                return True, f"User {username} created successfully with license {license_key}"
            return False, "Failed to create user"
        except Exception as e:
            if "duplicate key value violates unique constraint" in str(e):
                return False, f"License key {license_key} already exists"
            return False, f"Creation error: {str(e)}"

    def reset_password(self, license_key: str, new_password: str) -> Tuple[bool, str]:
        """Update a user's password using their license key."""
        try:
            new_hash = self.hash_password(new_password)
            result = self.client.table('users').update({
                'password_hash': new_hash
            }).eq('license_key', license_key.upper()).execute()
            
            if result.data:
                return True, f"Password reset successful for {license_key}"
            return False, "License key not found"
        except Exception as e:
            return False, f"Reset error: {str(e)}"

    def update_username(self, license_key: str, username: str) -> Tuple[bool, str]:
        """Update a user's display name."""
        try:
            result = self.client.table('users').update({
                'username': username
            }).eq('license_key', license_key.upper()).execute()
            
            if result.data:
                return True, f"Username updated to {username} for {license_key}"
            return False, "License key not found"
        except Exception as e:
            return False, f"Update error: {str(e)}"

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent usage sessions for current user."""
        if not self.current_user_id:
            return []
        
        try:
            result = self.client.table('usage_logs').select('*').eq('user_id', self.current_user_id).order('session_start', desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting recent sessions: {e}")
            return []

