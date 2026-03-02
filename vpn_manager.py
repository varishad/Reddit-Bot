"""
ExpressVPN Manager - Handles VPN connection and rotation for batch processing
"""
import subprocess
import time
import random
import os
import re
from typing import List, Optional, Tuple
from typing import Dict

class ExpressVPNManager:
    def __init__(self, log_callback=None):
        # Use a safe default logger that won't fail
        if log_callback:
            self.log = log_callback
        else:
            self.log = lambda msg: None  # Silent by default
        self.expressvpn_paths = [
            r"C:\Program Files (x86)\ExpressVPN\services\ExpressVPN.CLI.exe",  # CLI in services folder
            r"C:\Program Files\ExpressVPN\services\ExpressVPN.CLI.exe",
            r"C:\Program Files (x86)\ExpressVPN\expressvpn.exe",  # Old location
            r"C:\Program Files\ExpressVPN\expressvpn.exe",
            r"C:\Program Files (x86)\ExpressVPN\ExpressVPN.exe",  # Alternative name
            r"C:\Program Files\ExpressVPN\ExpressVPN.exe",  # Alternative name
            "expressvpn"  # If in PATH
        ]
        self.expressvpn_path = None
        self.available_locations = []
        self.current_location = None
        self.is_connected = False
        # Smart selection memory
        self._location_last_used: Dict[str, float] = {}
        self._location_score: Dict[str, float] = {}  # higher is better (success bias)
        
        # Find ExpressVPN installation
        self._find_expressvpn()
    
    def _find_expressvpn(self) -> bool:
        """Find ExpressVPN executable."""
        for path in self.expressvpn_paths:
            if path == "expressvpn":
                # Check if in PATH
                try:
                    result = subprocess.run(
                        ["expressvpn", "status"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    if result.returncode == 0 or "Not connected" in result.stdout or "Connected" in result.stdout:
                        self.expressvpn_path = "expressvpn"
                        return True
                except:
                    continue
            else:
                if os.path.exists(path):
                    self.expressvpn_path = path
                    # Verify it actually works by testing status command
                    try:
                        result = subprocess.run(
                            [path, "status"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                        )
                        # If we get any output (even error), the executable exists and is accessible
                        if result.stdout or result.stderr:
                            return True
                    except:
                        # If subprocess fails, still return True if file exists
                        # (might be permission issue, but file is there)
                        pass
                    return True
        
        # Last resort: Search in common directories
        common_dirs = [
            r"C:\Program Files (x86)\ExpressVPN",  # Most common
            r"C:\Program Files\ExpressVPN",
            r"C:\Program Files (x86)\ExpressVPN\expressvpn-ui",  # UI folder
            r"C:\Program Files (x86)\ExpressVPN\services",  # Services folder
            os.path.expanduser(r"~\AppData\Local\Programs\ExpressVPN"),
            os.path.expanduser(r"~\AppData\Roaming\ExpressVPN"),
        ]
        
        for base_dir in common_dirs:
            if os.path.exists(base_dir):
                # Look for expressvpn CLI in this directory and subdirectories
                possible_names = ["ExpressVPN.CLI.exe", "expressvpn.exe", "ExpressVPN.exe", "expressvpn-cli.exe"]
                
                # Check services subdirectory first (most common location)
                services_dir = os.path.join(base_dir, "services")
                if os.path.exists(services_dir):
                    for exe_name in possible_names:
                        exe_path = os.path.join(services_dir, exe_name)
                        if os.path.exists(exe_path):
                            try:
                                result = subprocess.run(
                                    [exe_path, "status"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                                )
                                self.expressvpn_path = exe_path
                                return True
                            except:
                                self.expressvpn_path = exe_path
                                return True
                for exe_name in possible_names:
                    exe_path = os.path.join(base_dir, exe_name)
                    if os.path.exists(exe_path):
                        try:
                            # Test if it works
                            result = subprocess.run(
                                [exe_path, "status"],
                                capture_output=True,
                                text=True,
                                timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                            )
                            self.expressvpn_path = exe_path
                            return True
                        except:
                            # Try it anyway
                            self.expressvpn_path = exe_path
                            return True
        
        return False
    
    def is_available(self) -> bool:
        """Check if ExpressVPN is available."""
        return self.expressvpn_path is not None
    
    def get_status(self) -> Tuple[bool, Optional[str]]:
        """Get current VPN status. Returns (is_connected, location_or_error)."""
        if not self.is_available():
            return False, "ExpressVPN not found"
        
        try:
            # Try status command
            result = subprocess.run(
                [self.expressvpn_path, "status"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Check both stdout and stderr (CLI might output to stderr)
            output = (result.stdout + result.stderr).lower()
            full_output = result.stdout + result.stderr
            
            # Check for elevation/permission errors
            if "error 740" in output or "requires elevation" in output or "administrator" in output:
                # VPN is installed but needs admin rights
                # Return a friendly message instead of error
                return False, "Admin rights needed"
            
            # Check for other common errors
            if "error" in output and ("740" in full_output or "access denied" in output.lower()):
                return False, "Access denied"
            
            # Check for "not connected" FIRST - this is most reliable
            if "not connected" in output or "disconnected" in output:
                self.is_connected = False
                self.current_location = None
                return False, "Not connected"
            
            # Only consider connected if we explicitly see "Connected to [location]" with an actual location
            # Don't trust returncode alone - ExpressVPN might return 0 even when not connected
            lines = full_output.split('\n')
            location = None
            
            for line in lines:
                line_lower = line.lower()
                # Look for explicit "Connected to" pattern with a location
                if "connected to" in line_lower:
                    # Extract location
                    parts = line.split("Connected to", 1)
                    if len(parts) > 1:
                        location = parts[1].strip()
                        # Make sure it's a real location (not empty, not just "connected", has some text)
                        if location and len(location) > 2 and location.lower() != "connected":
                            # Verify it's not an error message
                            if "error" not in location.lower() and "not" not in location.lower():
                                self.current_location = location
                                self.is_connected = True
                                return True, location
                elif "connected:" in line_lower:
                    # Alternative format: "Connected: [location]"
                    parts = line.split("Connected:", 1)
                    if len(parts) > 1:
                        location = parts[1].strip()
                        if location and len(location) > 2 and location.lower() != "connected":
                            if "error" not in location.lower() and "not" not in location.lower():
                                self.current_location = location
                                self.is_connected = True
                                return True, location
            
            # If we didn't find explicit "Connected to [location]", assume NOT connected
            # This is safer - we only show connected if we're 100% sure
            self.is_connected = False
            self.current_location = None
            return False, "Not connected"
                
        except Exception as e:
            error_msg = str(e).lower()
            if "740" in error_msg or "elevation" in error_msg or "administrator" in error_msg:
                return False, "Admin rights needed"
            return False, f"Error: {str(e)[:30]}"
    
    def list_locations(self) -> List[str]:
        """Get list of available VPN locations."""
        if not self.is_available():
            return []
        
        if self.available_locations:
            return self.available_locations
        
        try:
            result = subprocess.run(
                [self.expressvpn_path, "list"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            locations = []
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                # Skip headers and separators
                if not line or line.startswith('-') or line.lower().startswith('location') or len(line) < 3:
                    continue
                
                # Parse location format - ExpressVPN can output:
                # "ALIAS - Location Name" or "Location Name    123" (with numbers/spaces)
                # Remove trailing numbers and extra spaces
                location = line
                
                # Remove alias if present (format: "ALIAS - Location")
                if ' - ' in location:
                    location = location.split(' - ')[-1].strip()
                
                # Remove trailing numbers and extra spaces (format: "Location    123")
                # Use regex to remove trailing numbers and spaces
                location = re.sub(r'\s+\d+\s*$', '', location).strip()
                location = re.sub(r'\s+', ' ', location)  # Normalize multiple spaces to single space
                
                # Only add if it's a valid location name (not empty, not just numbers)
                if location and len(location) > 2 and not location.isdigit():
                    # Use the alias part if available, otherwise use the cleaned location
                    if ' - ' in line:
                        # Prefer the alias (first part) for connection
                        alias = line.split(' - ')[0].strip()
                        alias = re.sub(r'\s+\d+\s*$', '', alias).strip()
                        if alias and len(alias) > 2:
                            if alias not in locations:
                                locations.append(alias)
                        elif location not in locations:
                            locations.append(location)
                    else:
                        if location not in locations:
                            locations.append(location)
            
            # Also try "list all" for more locations
            try:
                result2 = subprocess.run(
                    [self.expressvpn_path, "list", "all"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                lines2 = result2.stdout.split('\n')
                for line in lines2:
                    line = line.strip()
                    # Skip headers and separators
                    if not line or line.startswith('-') or line.lower().startswith('location') or len(line) < 3:
                        continue
                    
                    # Parse location format
                    location = line
                    if ' - ' in location:
                        location = location.split(' - ')[-1].strip()
                    
                    # Remove trailing numbers and extra spaces
                    location = re.sub(r'\s+\d+\s*$', '', location).strip()
                    location = re.sub(r'\s+', ' ', location)
                    
                    if location and len(location) > 2 and not location.isdigit():
                        if ' - ' in line:
                            alias = line.split(' - ')[0].strip()
                            alias = re.sub(r'\s+\d+\s*$', '', alias).strip()
                            if alias and len(alias) > 2:
                                if alias not in locations:
                                    locations.append(alias)
                            elif location not in locations:
                                locations.append(location)
                        else:
                            if location not in locations:
                                locations.append(location)
            except:
                pass
            
            self.available_locations = locations
            return locations
        except Exception as e:
            self.log(f"Error getting locations: {str(e)}")
            return []
    
    def connect(self, location: Optional[str] = None) -> Tuple[bool, str]:
        """
        Connect to VPN location.
        If location is None, connects to smart location or random location.
        Returns (success, message).
        """
        if not self.is_available():
            return False, "ExpressVPN not found"
        
        try:
            # Check if logged in first
            login_check = subprocess.run(
                [self.expressvpn_path, "status"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            login_output = (login_check.stdout + login_check.stderr).lower()
            
            # Check for common errors that indicate not logged in
            if "not logged in" in login_output or "please log in" in login_output or "authentication" in login_output:
                return False, "ExpressVPN not logged in. Please log in to ExpressVPN app first."
            
            # Disconnect first if connected
            if self.is_connected:
                self.disconnect()
                time.sleep(0.5)  # Reduced from 2s to 0.5s
            
            # Build command
            if location:
                cmd = [self.expressvpn_path, "connect", location]
                self.log(f"Connecting to: {location}")
            else:
                cmd = [self.expressvpn_path, "connect", "smart"]
                self.log("Connecting to smart location...")
            
            # Connect to location
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # Increased timeout
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Check for elevation error
            output = (result.stdout + result.stderr).lower()
            full_output = result.stdout + result.stderr
            
            if "error 740" in output or "requires elevation" in output or "administrator" in output:
                return False, "Admin rights required. Run app as Administrator."
            
            # Check for other common errors
            if "not logged in" in output or "please log in" in output:
                return False, "ExpressVPN not logged in. Please log in to ExpressVPN app first."
            
            if "invalid" in output or "not found" in output:
                if location:
                    return False, f"Invalid location: {location}. Try 'smart' or check available locations."
                else:
                    return False, "Failed to connect to smart location."
            
            # Check if connection command shows success
            if "connected" in output.lower() or "connecting" in output.lower():
                # Wait for connection to establish (optimized wait)
                self.log("Waiting for connection to establish...")
                time.sleep(3)  # Reduced from 8s to 3s
                
                # Verify connection using get_status() - this is the most reliable check
                is_connected, status_msg = self.get_status()
                
                if is_connected:
                    # Connection successful, return the location
                    self.log(f"Connection verified: {status_msg}")
                    return True, status_msg
                else:
                    # Connection might still be establishing, try one more time
                    self.log("Connection not verified yet, waiting a bit more...")
                    time.sleep(2)  # Reduced from 5s to 2s
                    is_connected, status_msg = self.get_status()
                    
                    if is_connected:
                        return True, status_msg
                    else:
                        # Check output for any location info
                        location_from_output = None
                        lines = full_output.split('\n')
                        for line in lines:
                            line_lower = line.lower()
                            if "connected to" in line_lower:
                                location_from_output = line.split("Connected to", 1)[-1].strip()
                                if location_from_output and len(location_from_output) > 2:
                                    break
                        
                        if location_from_output:
                            return False, f"Connection status unclear. Location: {location_from_output}, but status check failed. Try checking ExpressVPN app manually."
                        else:
                            return False, f"Connection failed: {status_msg}. Check ExpressVPN app or run as Administrator."
            else:
                # No connection message in output
                error_msg = result.stderr or result.stdout or "Unknown error"
                return False, f"Connection failed: {error_msg[:100]}"
                
        except subprocess.TimeoutExpired:
            return False, "Connection timeout. ExpressVPN may be slow to respond."
        except Exception as e:
            error_msg = str(e).lower()
            if "740" in error_msg or "elevation" in error_msg:
                return False, "Admin rights required. Run app as Administrator."
            return False, f"Connection error: {str(e)[:50]}"
    
    def disconnect(self) -> Tuple[bool, str]:
        """Disconnect from VPN. Returns (success, message)."""
        if not self.is_available():
            return False, "ExpressVPN not found"
        
        try:
            result = subprocess.run(
                [self.expressvpn_path, "disconnect"],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            time.sleep(1)
            self.is_connected = False
            self.current_location = None
            return True, "Disconnected"
        except Exception as e:
            return False, f"Disconnect error: {str(e)}"
    
    def connect_random_location(self) -> Tuple[bool, str]:
        """Connect to a random available location."""
        locations = self.list_locations()
        if not locations:
            # Try smart location if list fails
            return self.connect(None)
        
        # Filter out current location if connected
        available = [loc for loc in locations if loc != self.current_location]
        if not available:
            available = locations
        
        location = random.choice(available)
        return self.connect(location)
    
    def rotate_location(self) -> Tuple[bool, str]:
        """Rotate to a new VPN location (disconnect and connect to new one)."""
        # First, get current status to see if we're connected
        current_status, _ = self.get_status()
        
        locations = self.list_locations()
        if not locations:
            # Try smart location
            return self.connect(None)
        
        # Get a different location (avoid current one)
        available = [loc for loc in locations if loc != self.current_location]
        if not available:
            available = locations
        
        # Clean location names (remove extra spaces, numbers) before connecting
        cleaned_available = []
        for loc in available:
            # Remove trailing numbers and extra spaces
            cleaned = re.sub(r'\s+\d+\s*$', '', loc).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize spaces
            if cleaned and len(cleaned) > 2:
                cleaned_available.append(cleaned)
        
        if not cleaned_available:
            cleaned_available = available
        
        new_location = random.choice(cleaned_available)
        self.log(f"Selected location: {new_location}")
        
        # If already connected, disconnect first
        if current_status:
            self.disconnect()
            time.sleep(2)  # Wait for disconnect
        
        # Connect to new location
        return self.connect(new_location)

    def _filter_locations(self, locations: List[str], preferred: List[str], avoid: List[str]) -> List[str]:
        if not locations:
            return []
        norm = lambda s: (s or "").lower()
        avoid_l = [norm(a) for a in avoid or []]
        pref_l = [norm(p) for p in preferred or []]
        # Remove avoid
        filtered = [loc for loc in locations if not any(a in loc.lower() for a in avoid_l)]
        if not filtered:
            filtered = locations[:]  # fallback to all if we filtered too much
        # Prefer preferred
        preferred_list = [loc for loc in filtered if any(p in loc.lower() for p in pref_l)] if pref_l else []
        return preferred_list or filtered

    def connect_with_strategy(self, preferred: Optional[List[str]] = None, avoid: Optional[List[str]] = None, cooldown_seconds: int = 900, max_candidates: int = 10) -> Tuple[bool, str]:
        """
        Connect to a location using cooldown and success-based scoring.
        - Avoid reusing a location within cooldown window
        - Prefer 'preferred' countries/cities; avoid 'avoid'
        - Bias selection towards higher score (past successes)
        """
        locations = self.list_locations()
        if not locations:
            return self.connect(None)
        candidates = self._filter_locations(locations, preferred or [], avoid or [])
        now = time.time()
        # Exclude cooldowned locations
        def not_on_cooldown(loc: str) -> bool:
            last = self._location_last_used.get(loc)
            return (last is None) or ((now - last) >= cooldown_seconds)
        candidates = [c for c in candidates if not_on_cooldown(c)]
        if not candidates:
            candidates = self._filter_locations(locations, preferred or [], avoid or [])
        # Score sort (descending)
        def score(loc: str) -> float:
            return self._location_score.get(loc, 0.0)
        candidates.sort(key=score, reverse=True)
        # Try top-N random shuffle within top slice
        if candidates:
            top_slice = candidates[:max_candidates]
            random.shuffle(top_slice)
        else:
            top_slice = []
        # Try to connect
        tried = 0
        for loc in top_slice or locations:
            tried += 1
            ok, msg = self.connect(loc)
            if ok:
                self._location_last_used[loc] = time.time()
                # Small positive reinforcement
                self._location_score[loc] = self._location_score.get(loc, 0.0) + 1.0
                return ok, msg
            else:
                # Small penalty
                self._location_score[loc] = self._location_score.get(loc, 0.0) - 0.2
            if tried >= max_candidates:
                break
        # Fallback to smart
        return self.connect(None)


