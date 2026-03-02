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
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, license_key: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Authenticate user with license key and password.
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
            
            # Don't check activation here - let GUI handle it
            # This allows login to check activation status and show activation window
            
            # Check IP address - allow VPN usage after initial activation
            client_ip = self.get_client_ip()
            activation_ip = user.get('activation_ip')
            last_login_ip = user.get('last_login_ip')
            
            # IP validation logic:
            # 1. If no activation IP set, allow (shouldn't happen, but be safe)
            # 2. If current IP matches activation IP, allow (same network)
            # 3. If user has logged in from activation IP before, allow VPN usage (any IP)
            # 4. Otherwise, block (different device/IP without prior successful login)
            
            if activation_ip and str(activation_ip) != '0.0.0.0':
                # Check if IP matches activation IP
                if str(activation_ip) == client_ip:
                    # Same IP as activation - allow
                    pass
                # Check if user has logged in from activation IP before (allows VPN after first login)
                elif last_login_ip and str(last_login_ip) == str(activation_ip):
                    # User has logged in from activation IP before - allow VPN usage
                    # This allows users to use VPN after initial activation/login
                    pass
                else:
                    # Different IP and hasn't logged in from activation IP - block
                    return False, f"Account is locked to activation IP: {activation_ip}. Your IP: {client_ip}. Please login from the original network first, then VPN usage will be allowed.", None
            
            # Update last login
            self.client.table('users').update({
                'last_login': datetime.utcnow().isoformat(),
                'last_login_ip': client_ip
            }).eq('id', user['id']).execute()
            
            self.current_user_id = user['id']
            self.current_license_key = license_key.upper()
            
            return True, None, user
            
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None
    
    def activate_account(self, activation_code: str) -> Tuple[bool, Optional[str]]:
        """
        Activate account using activation code.
        IP address will be locked to the first IP that activates.
        Returns: (success, error_message)
        """
        try:
            client_ip = self.get_client_ip()
            
            # Check if activation code exists
            activation_result = self.client.table('activations').select('*').eq('activation_code', activation_code.upper()).execute()
            
            if not activation_result.data:
                return False, "Invalid activation code"
            
            activation = activation_result.data[0]
            
            # Check if already used
            if activation.get('is_used', False):
                # Check if trying to activate from different IP
                activation_ip = activation.get('activation_ip')
                if activation_ip and str(activation_ip) != '0.0.0.0' and str(activation_ip) != client_ip:
                    return False, f"This activation code is already used on a different device/IP. Your IP: {client_ip}. Cannot use on multiple devices."
                else:
                    return False, "This activation code has already been used"
            
            # Get license key from activation
            license_key = activation['license_key']
            
            # Check if user exists
            user_result = self.client.table('users').select('*').eq('license_key', license_key).execute()
            
            if not user_result.data:
                return False, "User account not found for this activation code"
            
            user = user_result.data[0]
            
            # Check if already activated
            if user.get('is_active', False):
                # Check IP match
                user_activation_ip = user.get('activation_ip')
                if user_activation_ip and str(user_activation_ip) != client_ip:
                    return False, f"Account is already activated on a different device/IP. Your IP: {client_ip}. Cannot use on multiple devices."
                else:
                    return False, "This account is already activated"
            
            # Activate the account - lock to current IP
            self.client.table('users').update({
                'is_active': True,
                'activated_at': datetime.utcnow().isoformat(),
                'activation_ip': client_ip
            }).eq('id', user['id']).execute()
            
            # Mark activation code as used and lock to IP
            self.client.table('activations').update({
                'is_used': True,
                'activation_ip': client_ip,
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
                          username: Optional[str] = None, karma: Optional[str] = None,
                          error_message: Optional[str] = None):
        """Log individual account processing result."""
        if not session_id or not self.current_user_id:
            return
        
        try:
            self.client.table('session_details').insert({
                'session_id': session_id,
                'user_id': self.current_user_id,
                'reddit_email': email,
                'status': status,
                'username': username,
                'karma': karma,
                'error_message': error_message
            }).execute()
            
        except Exception as e:
            print(f"Error logging account result: {e}")
    
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

