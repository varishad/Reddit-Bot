"""
ExpressVPN Manager - Handles VPN connection and rotation for batch processing
"""
import subprocess
import time
import random
import os
import re
import asyncio
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
            "/usr/local/bin/expressvpn",
            "/opt/homebrew/bin/expressvpn",
            "/usr/bin/expressvpn",
            "/Applications/ExpressVPN.app/Contents/Resources/expressvpn",
            "/Applications/ExpressVPN.app/Contents/MacOS/expressvpnctl",
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
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Check for common installation issues."""
        # Re-scan for ExpressVPN if not found yet
        if not self.expressvpn_path:
            self._find_expressvpn()

        diag = {
            "os": os.name,
            "exe_found": self.expressvpn_path is not None,
            "exe_path": self.expressvpn_path,
            "is_mac": os.path.exists("/Applications/ExpressVPN.app"),
            "cli_accessible": False,
            "error_hint": None
        }
        
        # Specifically for macOS: check bundle ID
        is_ios_version = False
        is_official_mac = False
        if diag["is_mac"]:
            try:
                plist_path = "/Applications/ExpressVPN.app/Contents/Info.plist"
                if os.path.exists(plist_path):
                    import subprocess
                    bid = subprocess.check_output(
                        ["/usr/libexec/PlistBuddy", "-c", "Print CFBundleIdentifier", plist_path],
                        text=True
                    ).strip()
                    if bid == "com.expressvpn.iosvpn":
                        is_ios_version = True
                    elif bid == "com.expressvpn.expressvpn" or bid == "com.express.vpn":
                        is_official_mac = True
            except:
                pass

        if self.expressvpn_path:
            try:
                result = subprocess.run(
                    [self.expressvpn_path, "status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                diag["cli_accessible"] = True
            except Exception as e:
                diag["error_hint"] = f"CLI Command Error: {str(e)}"
        else:
            if diag["is_mac"]:
                if is_ios_version:
                    diag["error_hint"] = "You still have the 'App Store' version. Please DELETE it and download the 'Official Mac version' from expressvpn.com/vpn-software/vpn-mac"
                elif is_official_mac:
                    diag["error_hint"] = "Official ExpressVPN found, but CLI is missing. Try restarting your Mac or running 'defaults write com.expressvpn.expressvpn.cli InstallCLI -bool true' in Terminal if you know how."
                else:
                    diag["error_hint"] = "ExpressVPN app found, but CLI tools are missing. Please ensure you downloaded the version from expressvpn.com (not the App Store)."
            else:
                diag["error_hint"] = "ExpressVPN not found. Please install it to use VPN features."
        
        return diag

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

        return False

    async def _run_command_async(self, cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Run a command asynchronously and return (returncode, stdout, stderr)."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            return process.returncode, stdout.decode(errors='replace'), stderr.decode(errors='replace')
        except asyncio.TimeoutError:
            try:
                process.kill()
            except:
                pass
            return -1, "", "Timeout"

    async def ensure_app_running(self) -> bool:
        """Attempt to open the ExpressVPN GUI app depending on the OS."""
        try:
            if os.name == 'nt':  # Windows
                ui_paths = [
                    r"C:\Program Files (x86)\ExpressVPN\expressvpn-ui\ExpressVPN.exe",
                    r"C:\Program Files\ExpressVPN\expressvpn-ui\ExpressVPN.exe",
                    r"C:\Program Files (x86)\ExpressVPN\ExpressVPN.exe",
                ]
                for path in ui_paths:
                    if os.path.exists(path):
                        self.log(f"Starting ExpressVPN GUI from {path}...")
                        subprocess.Popen([path], start_new_session=True)
                        return True
            else:  # macOS/Linux
                if os.path.exists("/Applications/ExpressVPN.app"):
                    self.log("Opening ExpressVPN app on macOS...")
                    process = await asyncio.create_subprocess_exec("open", "-a", "ExpressVPN")
                    await process.wait()
                    return True
                else:
                    # Generic linux/fallback
                    try:
                        returncode, stdout, stderr = await self._run_command_async(["expressvpn", "--version"], timeout=5)
                        return returncode == 0
                    except:
                        pass
        except Exception as e:
            self.log(f"Error starting VPN app: {str(e)}")
        return False
    
    def is_available(self) -> bool:
        """Check if ExpressVPN is available."""
        return self.expressvpn_path is not None
    
    async def get_status(self) -> Tuple[bool, Optional[str]]:
        """Get current VPN status. Returns (is_connected, location_or_error)."""
        if not self.is_available():
            return False, "Not installed"
        
        is_ctl = "expressvpnctl" in self.expressvpn_path.lower()
        
        try:
            # For v12 (expressvpnctl), we can get precise connection state
            if is_ctl:
                rc, stdout, stderr = await self._run_command_async([self.expressvpn_path, "get", "connectionstate"], timeout=10)
                state = stdout.strip()
                self.log(f"🔎 VPN Connection State: {state}")
                if state == "Connected":
                    # Get location too
                    rc_loc, stdout_loc, stderr_loc = await self._run_command_async([self.expressvpn_path, "status"], timeout=10)
                    output_loc = (stdout_loc + stderr_loc).lower()
                    match = re.search(r"connected to (.+)", stdout_loc + stderr_loc, re.IGNORECASE)
                    loc = match.group(1).strip() if match else "Connected"
                    self.is_connected = True
                    self.current_location = loc
                    self.log(f"📍 VPN Location: {loc}")
                    return True, loc
                elif state in ["Connecting", "Reconnecting", "DisconnectingToReconnect"]:
                    return False, "Connecting..."
                else:
                    self.is_connected = False
                    self.current_location = None
                    return False, "Not connected"

            # Legacy/Standard parsing for expressvpn (v3)
            returncode, stdout, stderr = await self._run_command_async([self.expressvpn_path, "status"], timeout=10)
            output = (stdout + stderr).lower()
            full_output = stdout + stderr
            
            # Check for elevation/permission errors
            if "error 740" in output or "requires elevation" in output or "administrator" in output:
                return False, "Admin rights needed"
            
            # Check for "connected to"
            if "connected to" in output:
                match = re.search(r"connected to (.+)", full_output, re.IGNORECASE)
                if match:
                    loc = match.group(1).strip()
                    self.is_connected = True
                    self.current_location = loc
                    return True, loc
            
            # Check for "not connected"
            if "not connected" in output or "disconnected" in output:
                self.is_connected = False
                self.current_location = None
                return False, "Not connected"
            
            self.is_connected = False
            self.current_location = None
            return False, "Not connected"
                
        except Exception as e:
            error_msg = str(e).lower()
            if "740" in error_msg or "elevation" in error_msg or "administrator" in error_msg:
                return False, "Admin rights needed"
            return False, f"Error: {str(e)[:30]}"
    
    async def list_locations(self) -> List[str]:
        """Get list of available VPN locations."""
        if not self.is_available():
            return []
        
        if self.available_locations:
            return self.available_locations
        
        is_ctl = "expressvpnctl" in self.expressvpn_path.lower()
        
        try:
            if is_ctl:
                returncode, stdout, stderr = await self._run_command_async([self.expressvpn_path, "get", "regions"], timeout=30)
            else:
                returncode, stdout, stderr = await self._run_command_async([self.expressvpn_path, "list"], timeout=30)
            
            locations = []
            lines = stdout.split('\n')
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
                returncode2, stdout2, stderr2 = await self._run_command_async([self.expressvpn_path, "list", "all"], timeout=30)
                lines2 = stdout2.split('\n')
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
    
    async def connect(self, location: Optional[str] = None) -> Tuple[bool, str]:
        """
        Connect to VPN location.
        If location is None, connects to smart location or random location.
        Returns (success, message).
        """
        if not self.is_available():
            return False, "Not installed"
        
        try:
            # Check if logged in first
            is_ctl = "expressvpnctl" in self.expressvpn_path.lower()
            if is_ctl:
                rc_login, stdout_login, stderr_login = await self._run_command_async([self.expressvpn_path, "get", "connectionstate"], timeout=10)
                if "unauthorized" in (stdout_login + stderr_login).lower():
                    return False, "ExpressVPN not logged in. Please log in to ExpressVPN app first."
            else:
                returncode, stdout, stderr = await self._run_command_async([self.expressvpn_path, "status"], timeout=10)
                login_output = (stdout + stderr).lower()
                if "not logged in" in login_output or "please log in" in login_output or "authentication" in login_output:
                    return False, "ExpressVPN not logged in. Please log in to ExpressVPN app first."
            
            # Disconnect first if connected
            # For expressvpnctl, we can just call connect and it will switch, but let's be safe
            is_connected, _ = await self.get_status()
            if is_connected:
                await self.disconnect()
                await asyncio.sleep(0.5)
            
            # Build command
            if location:
                cmd = [self.expressvpn_path, "connect", location]
                self.log(f"🔗 [VPN] Auto-connecting to: {location}...")
            else:
                cmd = [self.expressvpn_path, "connect", "smart"]
                self.log("🔗 [VPN] Auto-connecting to smart location...")
            
            # Ensure app is running
            await self.ensure_app_running()
            await asyncio.sleep(1)
            
            # Connect to location
            returncode, stdout, stderr = await self._run_command_async(cmd, timeout=60)
            
            # Check for elevation error
            output = (stdout + stderr).lower()
            full_output = stdout + stderr
            
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
                # Wait for connection to establish
                self.log("Waiting for connection to establish...")
                await asyncio.sleep(3)
                
                # Verify connection using get_status()
                is_connected, status_msg = await self.get_status()
                
                if is_connected:
                    # Connection successful, return the location
                    self.log(f"Connection verified: {status_msg}")
                    return True, status_msg
                else:
                    # Connection might still be establishing, try one more time
                    self.log("Connection not verified yet, waiting a bit more...")
                    await asyncio.sleep(2)
                    is_connected, status_msg = await self.get_status()
                    
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
    
    async def disconnect(self) -> Tuple[bool, str]:
        """Disconnect from VPN."""
        if not self.is_available():
            return False, "Not installed"
        
        try:
            cmd = [self.expressvpn_path, "disconnect"]
            returncode, stdout, stderr = await self._run_command_async(cmd, timeout=30)
            self.is_connected = False
            self.current_location = None
            return True, "Disconnected"
        except Exception as e:
            return False, f"Disconnect failed: {str(e)}"

    async def add_app_to_bypass(self, app_path: str) -> Tuple[bool, str]:
        """
        Add an application to the VPN bypass list (Split Tunneling).
        Works only for expressvpnctl (v12).
        """
        if not self.is_available() or "expressvpnctl" not in self.expressvpn_path.lower():
            return False, "Split tunneling CLI only supported in ExpressVPN v12+ on Mac."
            
        try:
            # Enable split tunneling first
            await self._run_command_async([self.expressvpn_path, "set", "splittunnel", "true"])
            # Set to bypass
            cmd = [self.expressvpn_path, "set", "split-app", f"bypass:{app_path}"]
            rc, stdout, stderr = await self._run_command_async(cmd, timeout=10)
            if rc == 0:
                return True, f"Bypass added for {app_path}"
            return False, f"Failed to add bypass: {stdout + stderr}"
        except Exception as e:
            return False, str(e)
    
    async def connect_random_location(self) -> Tuple[bool, str]:
        """Connect to a random available location."""
        locations = await self.list_locations()
        if not locations:
            # Try smart location if list fails
            return await self.connect(None)
        
        # Filter out current location if connected
        available = [loc for loc in locations if loc != self.current_location]
        if not available:
            available = locations
        
        location = random.choice(available)
        return await self.connect(location)
    
    async def rotate_location(self) -> Tuple[bool, str]:
        """Rotate to a new VPN location (disconnect and connect to new one)."""
        # First, get current status to see if we're connected
        current_status, _ = await self.get_status()
        
        locations = await self.list_locations()
        if not locations:
            # Try smart location
            return await self.connect(None)
        
        # Get a different location (avoid current one)
        available = [loc for loc in locations if loc != self.current_location]
        if not available:
            available = locations
        
        # Clean location names
        cleaned_available = []
        for loc in available:
            # Remove trailing numbers and extra spaces
            cleaned = re.sub(r'\s+\d+\s*$', '', loc).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if cleaned and len(cleaned) > 2:
                cleaned_available.append(cleaned)
        
        if not cleaned_available:
            cleaned_available = available
        
        new_location = random.choice(cleaned_available)
        self.log(f"Selected location: {new_location}")
        
        # If already connected, disconnect first
        if current_status:
            await self.disconnect()
            await asyncio.sleep(2)
        
        # Connect to new location
        return await self.connect(new_location)

    def _filter_locations(self, locations: List[str], preferred: List[str], avoid: List[str]) -> List[str]:
        if not locations:
            return []
        norm = lambda s: (s or "").lower()
        avoid_l = [norm(a) for a in avoid or []]
        pref_l = [norm(p) for p in preferred or []]
        # Remove avoid
        filtered = [loc for loc in locations if not any(a in loc.lower() for a in avoid_l)]
        if not filtered:
            filtered = locations[:]  # fallback to all
        # Prefer preferred
        preferred_list = [loc for loc in filtered if any(p in loc.lower() for p in pref_l)] if pref_l else []
        return preferred_list or filtered

    async def connect_with_strategy(self, preferred: Optional[List[str]] = None, avoid: Optional[List[str]] = None, cooldown_seconds: int = 900, max_candidates: int = 10) -> Tuple[bool, str]:
        """
        Connect to a location using cooldown and success-based scoring.
        """
        locations = await self.list_locations()
        if not locations:
            return await self.connect(None)
        candidates = self._filter_locations(locations, preferred or [], avoid or [])
        now = time.time()
        # Exclude cooldowned locations
        def not_on_cooldown(loc: str) -> bool:
            last = self._location_last_used.get(loc)
            return (last is None) or ((now - last) >= cooldown_seconds)
        candidates = [c for c in candidates if not_on_cooldown(c)]
        if not candidates:
            candidates = self._filter_locations(locations, preferred or [], avoid or [])
        # Score sort
        def score(loc: str) -> float:
            return self._location_score.get(loc, 0.0)
        candidates.sort(key=score, reverse=True)
        # Try top-N random shuffle
        if candidates:
            top_slice = candidates[:max_candidates]
            random.shuffle(top_slice)
        else:
            top_slice = []
        # Try to connect
        tried = 0
        for loc in top_slice or locations:
            tried += 1
            ok, msg = await self.connect(loc)
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
        return await self.connect(None)