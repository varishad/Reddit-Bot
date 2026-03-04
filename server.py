import os
import threading
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import deque

from fastapi import FastAPI, BackgroundTasks, HTTPException, Body, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

# Internal imports
from database import Database
from bot_engine import RedditBotEngine
from vpn_manager import ExpressVPNManager
from config import VPN_REQUIRE_CONNECTION
from logger import logger

app = FastAPI(title="Reddit Bot API - Modern UI Gateway")

# Enable CORS for Next.js (standard port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication Middleware ---
from fastapi import Request
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Automatically recover session from Authorization header if possible."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        license_key = auth_header.split(" ")[1]
        
        # Recover session if not authenticated or license changed
        if not state.db.current_user_id or state.db.current_license_key != license_key.upper():
            state.db.verify_license_key(license_key)
            
    response = await call_next(request)
    return response

# --- Helpers ---
def log_to_state(message: str, level: str = "info"):
    """Callback for bot engine to write logs into shared state and persistent logger."""
    # Mirror to persistent logger first (always safe)
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)
        
    # Attempt to write to state if initialized
    try:
        # Check if 'state' exists in globals and is not None
        if 'state' in globals() and state is not None:
            with state.lock:
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_type = "info"
                if "success" in message.lower(): log_type = "success"
                elif "error" in message.lower() or "failed" in message.lower(): log_type = "error"
                elif "warning" in message.lower(): log_type = "warning"
                
                state.logs.append({
                    "timestamp": timestamp,
                    "message": message,
                    "type": log_type
                })
    except (NameError, AttributeError):
        # State not ready yet, that's fine as we logged to file above
        pass

def progress_update(snapshot: Dict[str, Any]):
    """Callback for bot engine to update stats."""
    try:
        if 'state' in globals() and state is not None:
            with state.lock:
                state.stats.update(snapshot)
    except (NameError, AttributeError):
        pass

# --- App Lifecycle ---
@app.on_event("startup")
async def startup_event():
    """Perform async startup tasks in background to avoid blocking API readiness."""
    logger.info("Application starting up...")
    
    async def initialize_vpn():
        try:
            is_connected, loc = await state.vpn_manager.get_status()
            state.current_vpn_location = loc if is_connected else "Disconnected"
            logger.info(f"Initial VPN Status: {state.current_vpn_location}")
            
            # Try to bypass the current Python process from VPN to avoid dashboard connectivity issues
            if "expressvpnctl" in getattr(state.vpn_manager, "expressvpn_path", "").lower():
                import sys
                logger.info(f"🛡️ Attempting to bypass VPN for Python: {sys.executable}")
                success, msg = await state.vpn_manager.add_app_to_bypass(sys.executable)
                if success:
                    logger.info(f"✅ VPN Bypass active: {msg}")
                else:
                    logger.warning(f"⚠️ VPN Bypass failed: {msg}")
        except Exception as e:
            logger.error(f"Failed to get initial VPN status: {e}")
            state.current_vpn_location = "Error"
            
    asyncio.create_task(initialize_vpn())

# --- Background Worker ---
def bot_worker(file_path: str, parallel_browsers: int, batch_limit: int = 100, include_statuses: List[str] = ["pending", "error"]):
    """Thread worker that executes the bot logic."""
    try:
        with state.lock:
            state.stop_requested = False
            state.is_running = True
            state.current_session_id = state.db.create_session()
            state.browser_status = "Initializing..."
        
        # --- VPN Pre-flight (Background) ---
        from config import VPN_ALWAYS_ROTATE_AT_START, VPN_ENABLED, VPN_REQUIRE_CONNECTION
        
        async def vpn_preflight():
            if not VPN_ENABLED:
                return True
            
            try:
                if VPN_ALWAYS_ROTATE_AT_START:
                    state.browser_status = "VPN Connecting..."
                    log_to_state("🔄 [VPN] Pre-flight: Connecting to random server for maximum stealth...")
                    success, msg = await state.vpn_manager.connect_random_location()
                    if success:
                        state.current_vpn_location = msg
                        log_to_state(f"✅ VPN Connected: {msg}")
                        return True
                    else:
                        state.current_vpn_location = "Failed"
                        if VPN_REQUIRE_CONNECTION:
                            log_to_state(f"❌ VPN Connection required but failed: {msg}", "error")
                            return False
                        log_to_state(f"⚠️ VPN Auto-connect failed: {msg}. Continuing as per config.", "warning")
                        return True
                else:
                    state.browser_status = "Checking VPN..."
                    log_to_state("🔍 Checking VPN status...")
                    is_connected, location = await state.vpn_manager.get_status()
                    
                    if is_connected:
                        state.current_vpn_location = location
                        log_to_state(f"✅ VPN already connected: {location}")
                        return True
                    else:
                        state.browser_status = "VPN Connecting..."
                        log_to_state("🔒 VPN not connected - attempting to connect...")
                        success, msg = await state.vpn_manager.connect_random_location()
                        if not success:
                            state.current_vpn_location = "Failed"
                            if VPN_REQUIRE_CONNECTION:
                                log_to_state(f"❌ VPN Connection required but failed: {msg}", "error")
                                return False
                            log_to_state(f"⚠️ VPN Auto-connect failed: {msg}. Continuing as per config.", "warning")
                            return True
                        else:
                            state.current_vpn_location = msg
                            log_to_state(f"✅ VPN Connected! Location: {msg}")
                            return True
            except Exception as e:
                log_to_state(f"⚠️ VPN Pre-flight Warning: {str(e)}", "warning")
                return not VPN_REQUIRE_CONNECTION

        # Execute VPN pre-flight in current thread's event loop
        vpn_ok = asyncio.run(vpn_preflight())
        if not vpn_ok:
            log_to_state("🛑 Bot execution aborted: VPN connection failed and is required.", "error")
            with state.lock:
                state.is_running = False
            return

        state.browser_status = "Launching..."
        state.bot_instance = RedditBotEngine(
            db=state.db,
            session_id=state.current_session_id,
            log_callback=log_to_state,
            external_vpn_manager=state.vpn_manager,
            skip_vpn_init=True,
            progress_callback=progress_update
        )

        def sync_status_loop():
            while state.is_running and state.bot_instance:
                if state.bot_instance.current_vpn_location:
                    state.current_vpn_location = state.bot_instance.current_vpn_location
                
                # Sync browser telemetry
                state.active_browsers = state.bot_instance.active_browsers
                state.browser_status = state.bot_instance.browser_status
                
                time.sleep(1)
        
        threading.Thread(target=sync_status_loop, daemon=True).start()
        
        log_to_state(f"🚀 Bot execution started (Session: {state.current_session_id}, Filter: {', '.join(include_statuses)}, Batch: {batch_limit})")
        state.bot_instance.process_credentials(file_path, parallel_browsers, batch_limit=batch_limit, include_statuses=include_statuses)
        log_to_state("✅ Bot execution completed successfully.")
        
    except Exception as e:
        log_to_state(f"❌ Critical Error in Bot Worker: {str(e)}")
    finally:
        with state.lock:
            state.is_running = False
            state.bot_instance = None

# --- Shared State Management ---
class AppState:
    def __init__(self):
        logger.info("Initializing AppState...")
        self.db = Database()
        self.vpn_manager = ExpressVPNManager(log_callback=log_to_state)
        self.bot_instance: Optional[RedditBotEngine] = None
        self.is_running = False
        self.is_starting = False  # Track pre-flight state
        self.is_stopping = False
        self.logs = deque(maxlen=1000)
        self.stats = {
            "total": 0,
            "success": 0,
            "invalid": 0,
            "banned": 0,
            "error": 0,
            "vpn_rotations": 0,
            "uptime_seconds": 0,
            "start_time": None
        }
        self.current_vpn_location = "Initializing..."
        self.active_browsers = 0
        self.browser_status = "Waiting..."
        self.lock = threading.Lock()
        self.stop_requested = False
        
        # Load user settings
        self.settings = self.load_user_settings()
        
        # --- AUTO-SESSION RESTORATION ---
        # If we have saved credentials, auto-authenticate to restore current_user_id
        try:
            if os.path.exists("saved_credentials.json"):
                with open("saved_credentials.json", "r") as f:
                    creds = json.load(f)
                    license_key = creds.get("license_key")
                    password = creds.get("password")
                    if license_key and password:
                        logger.info(f"🔑 [AUTO-LOGIN] Attempting to restore session for {license_key[:10]}...")
                        success, _, _ = self.db.authenticate_user(license_key, password)
                        if success:
                            logger.info("✅ [AUTO-LOGIN] Session restored successfully.")
                        else:
                            logger.warning("⚠️ [AUTO-LOGIN] Failed to restore session.")
        except Exception as e:
            logger.error(f"Error during auto-login: {e}")

    def load_user_settings(self) -> Dict[str, Any]:
        import json
        default_settings = {
            "browser_type": "chromium",
            "headless": False,
            "delay_min": 3,
            "delay_max": 5,
            "max_parallel_browsers": 5,
            "stealth_enabled": True,
            "humanize_input": True,
            "vpn_enabled": True,
            "vpn_rotate_per_batch": True,
            "persistent_context": False,
            "proxy_enabled": False,
            "proxy_host": "",
            "proxy_port": "",
            "proxy_user": "",
            "proxy_pass": ""
        }
        try:
            if os.path.exists("user_settings.json"):
                with open("user_settings.json", "r") as f:
                    return {**default_settings, **json.load(f)}
        except Exception:
            pass
        return default_settings

    def save_user_settings(self):
        import json
        try:
            with open("user_settings.json", "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception:
            pass

    def reset_stats(self):
        self.stats = {
            "total": 0,
            "success": 0,
            "invalid": 0,
            "banned": 0,
            "error": 0,
            "vpn_rotations": 0,
            "uptime_seconds": 0,
            "start_time": datetime.now().isoformat()
        }
        self.logs.clear()

# --- Global State Initialization ---
try:
    state = AppState()
    logger.info("✅ Global AppState created successfully")
except Exception as e:
    logger.error(f"❌ CRITICAL: Failed to initialize AppState: {e}")
    # Still raise as this is likely fatal for the API
    raise

# --- Port helpers --- (No changes here, just for context)

class LoginRequest(BaseModel):
    license_key: str
    password: str

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/user/info")
async def user_info():
    """Return comprehensive info about the licensed user."""
    try:
        user = state.db.get_user_stats()
        if user:
            return {
                "license_key": user.get('license_key', 'Unknown'),
                "username": user.get('username', 'Unknown'),
                "is_active": user.get('is_active', False),
                "activated_at": user.get('activated_at'),
                "plan_start_date": user.get('plan_start_date'),
                "plan_end_date": user.get('plan_end_date'),
                "plan_name": user.get('plan_name', 'Monthly Normal'),
                "role": user.get('role', 'User'),
                "machine_id": user.get('machine_id')
            }
    except Exception:
        pass
    return {"license_key": "Unknown", "is_active": False, "role": "User"}

# --- Admin Endpoints ---

@app.get("/admin/users")
async def admin_get_users():
    """List all registered users/licenses (Admin only)."""
    # In a real app, we'd check state.db.current_user_id's role here
    return state.db.get_all_users()

class ResetPasswordRequest(BaseModel):
    license_key: str
    new_password: str

@app.post("/admin/reset-password")
async def admin_reset_password(req: ResetPasswordRequest):
    """Reset a user's password (Admin only)."""
    success, msg = state.db.reset_password(req.license_key, req.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}

class CreateUserRequest(BaseModel):
    username: str
    license_key: str
    password: str
    role: str = "User"
    plan_name: str = "Monthly Normal"
    days: int = 30

@app.post("/admin/create-user")
async def admin_create_user(req: CreateUserRequest):
    """Create a new user (Admin only)."""
    # In a real app, check state.db.current_user_id's role here
    success, msg = state.db.create_user(
        username=req.username,
        license_key=req.license_key,
        password=req.password,
        role=req.role,
        plan_name=req.plan_name,
        days=req.days
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}

class UpdateUsernameRequest(BaseModel):
    username: str

@app.post("/user/update-username")
async def update_username(req: UpdateUsernameRequest):
    """Update the current user's display name."""
    user_stats = state.db.get_user_stats()
    if not user_stats:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    success, msg = state.db.update_username(user_stats['license_key'], req.username)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}

@app.get("/bot/settings")
async def get_bot_settings():
    """Return user-configurable bot settings (safe for UI)."""
    return state.settings

@app.post("/bot/settings")
async def update_bot_settings(new_settings: Dict[str, Any]):
    """Update bot settings and persist them."""
    state.settings.update(new_settings)
    state.save_user_settings()
    
    # Update global config for bot engine/browser manager
    import config
    config.PROXY_ENABLED = state.settings.get("proxy_enabled", False)
    config.PROXY_HOST = state.settings.get("proxy_host", "")
    config.PROXY_PORT = state.settings.get("proxy_port", "")
    config.PROXY_USER = state.settings.get("proxy_user", "")
    config.PROXY_PASS = state.settings.get("proxy_pass", "")
    
    return {"status": "success", "settings": state.settings}

@app.get("/vpn/diag")
async def get_vpn_diag():
    """Return detailed VPN diagnostic info."""
    return state.vpn_manager.get_diagnostics()

@app.get("/auth/saved-credentials")
async def get_saved_credentials():
    """Retrieve saved credentials for auto-login."""
    import json
    try:
        if os.path.exists("saved_credentials.json"):
            with open("saved_credentials.json", "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

@app.post("/auth/login")
async def login(credentials: LoginRequest):
    import json
    success, msg, user = state.db.authenticate_user(credentials.license_key, credentials.password)
    if not success:
        raise HTTPException(status_code=401, detail=msg)
    
    # Save credentials for persistence (ExpressVPN style)
    try:
        with open("saved_credentials.json", "w") as f:
            json.dump({
                "license_key": credentials.license_key,
                "password": credentials.password
            }, f)
    except Exception:
        pass
        
    return {"status": "success", "user": user}

@app.post("/auth/logout")
async def logout():
    """Explicit logout to clear saved credentials."""
    try:
        if os.path.exists("saved_credentials.json"):
            os.remove("saved_credentials.json")
        
        # Reset current user in DB state
        state.db.current_user_id = None
        state.db.current_license_key = None
        
        return {"status": "success", "message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def parse_credentials_text(text: str) -> List[Dict]:
    """Parse email:password format from text."""
    lines = text.strip().split('\n')
    results = []
    for line in lines:
        line = line.strip()
        if not line: continue
        if ':' in line:
            parts = line.split(':', 1)
            results.append({"email": parts[0].strip(), "password": parts[1].strip()})
        else:
            # Fallback for just email or other formats
            results.append({"email": line, "password": ""})
    return results

@app.post("/bot/upload-credentials")
async def upload_credentials(file: UploadFile = File(...)):
    """Save the uploaded credentials file to disk and log as pending."""
    try:
        content = await file.read()
        text = content.decode('utf-8')
        
        # Save to file for bot engine
        with open("credentials.txt", "w") as f:
            f.write(text)
            
        # Save persistently to Database
        accounts = parse_credentials_text(text)
        success, msg = state.db.save_accounts(accounts)
        
        if success:
            log_to_state(f"📁 Credentials file uploaded and saved to DB: {file.filename} ({len(accounts)} accounts)")
        else:
            log_to_state(f"⚠️ File uploaded but DB save failed: {msg}", "warning")

        return {"status": "success", "message": f"Successfully uploaded {len(accounts)} accounts"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/bot/paste-credentials")
async def paste_credentials(text: str = Body(..., embed=True)):
    """Save pasted credentials text to disk and log as pending."""
    try:
        # Save to file for bot engine
        with open("credentials.txt", "w") as f:
            f.write(text)
            
        # Save persistently to Database
        accounts = parse_credentials_text(text)
        success, msg = state.db.save_accounts(accounts)
        
        if success:
            log_to_state(f"📋 Credentials pasted and saved to DB ({len(accounts)} accounts)")
        else:
            log_to_state(f"⚠️ Credentials pasted but DB save failed: {msg}", "warning")

        return {"status": "success", "message": f"Successfully saved {len(accounts)} accounts"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/bot/start")
async def start_bot(
    background_tasks: BackgroundTasks,
    file_path: Optional[str] = None,
    parallel_browsers: int = 1,
    batch_limit: int = 100,
    include_statuses: List[str] = Body(["pending", "error"])
):
    if state.is_running or state.is_starting:
        return {"status": "error", "message": "Bot is already running or starting."}
    
    state.is_starting = True
    try:
        state.reset_stats()
        background_tasks.add_task(bot_worker_wrapper, file_path, parallel_browsers, batch_limit, include_statuses)
        return {"status": "success", "message": "Bot startup initiated."}
    except Exception as e:
        state.is_starting = False
        log_to_state(f"❌ Startup Request Error: {str(e)}", "error")
        return {"status": "error", "message": f"Startup failed: {str(e)}"}

def bot_worker_wrapper(file_path: str, parallel_browsers: int, batch_limit: int, include_statuses: List[str]):
    """Small wrapper to manage is_starting flag outside the main worker logic."""
    try:
        bot_worker(file_path, parallel_browsers, batch_limit, include_statuses)
    finally:
        state.is_starting = False

@app.post("/bot/stop")
async def stop_bot():
    if not state.is_running or not state.bot_instance:
        return {"status": "error", "message": "Bot is not running."}
    
    state.bot_instance.stop(hard=True)
    state.browser_status = "Hard Stop Triggered"
    log_to_state("🧨 [UI] Hard stop signal sent to bot engine...")
    return {"status": "success", "message": "Hard stop signal sent."}

@app.get("/bot/status")
async def get_status():
    uptime = 0
    if state.is_running and state.stats["start_time"]:
        start_dt = datetime.fromisoformat(state.stats["start_time"])
        uptime = int((datetime.now() - start_dt).total_seconds())

    # Get industrial stats from Supabase
    db_stats = state.db.get_processing_stats()

    with state.lock:
        return {
            "is_running": state.is_running,
            "is_starting": state.is_starting,
            "session_id": state.current_session_id,
            "vpn_location": state.current_vpn_location,
            "active_browsers": state.active_browsers,
            "browser_status": state.browser_status,
            "stats": {
                **state.stats, 
                "uptime_seconds": uptime,
                "db_stats": db_stats # Industry stats for progress bar
            },
            "recent_logs": list(state.logs)[-200:]
        }

@app.post("/accounts/cleanup-invalid")
async def cleanup_invalid():
    """Bulk delete all invalid or error accounts."""
    success, msg = state.db.delete_invalid_accounts()
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}

@app.get("/bot/full-logs")
async def get_all_logs():
    with state.lock:
        return list(state.logs)

# --- Accounts ---
@app.get("/accounts/results")
async def get_results():
    """Return results from local storage and persistent database."""
    combined_results = []
    
    # 1. Fetch persistent accounts from Supabase
    if state.db.current_user_id:
        try:
            res = state.db.client.table("accounts").select("*").eq("user_id", state.db.current_user_id).order("created_at", desc=True).execute()
            if res.data:
                # Map DB format to UI format
                for acc in res.data:
                    combined_results.append({
                        'id': acc['id'],
                        'session_id': None, # Persistent accounts aren't tied to a volatile session
                        'email': acc['email'],
                        'reddit_password': acc.get('password'),
                        'status': acc.get('status', 'pending'),
                        'username': acc.get('username'),
                        'profile_url': acc.get('profile_url'),
                        'remark': acc.get('remark'),
                        'karma': acc.get('karma'),
                        'vpn_location': acc.get('vpn_location'),
                        'vpn_ip': acc.get('vpn_ip'),
                        'error_message': None,
                        'created_at': acc.get('created_at')
                    })
        except Exception as e:
            logger.error(f"Error fetching persistent accounts: {e}")

    # --- Account Management ---
    @app.delete("/accounts/{account_id}")
    async def delete_account(account_id: str):
        """Delete an account from persistent storage."""
        success, msg = state.db.delete_account(account_id)
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        return {"status": "success", "message": msg}

    # 2. Add/Overlay local session results
    try:
        import json
        import os
        results_file = "session_results.json"
        
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                local_results = json.load(f)
            
            # Use email as key to avoid duplicates (favor local session info if active)
            seen_emails = {r['email'] for r in combined_results}
            for lr in local_results:
                if lr['email'] not in seen_emails:
                    combined_results.append(lr)
                else:
                    # Update existing with session info if more recent/specific
                    for i, cr in enumerate(combined_results):
                        if cr['email'] == lr['email'] and lr.get('session_id') == state.current_session_id:
                            combined_results[i] = lr
                            break
                            
    except Exception as e:
        logger.error(f"Error reading local results: {e}")
        
    return combined_results

# --- VPN ---
@app.get("/vpn/status")
async def vpn_status():
    try:
        is_connected, location = await state.vpn_manager.get_status()
        state.current_vpn_location = location if is_connected else "Disconnected"
        return {"connected": bool(is_connected), "location": location}
    except Exception as e:
        logger.error(f"VPN status error: {e}")
        return {"connected": False, "location": None}

@app.post("/vpn/connect")
async def vpn_connect(location: str = None):
    try:
        if location:
            success, msg = await state.vpn_manager.connect(location)
        else:
            success, msg = await state.vpn_manager.connect_random_location()
        
        if success:
            state.current_vpn_location = msg
        return {"success": success, "message": msg}
    except Exception as e:
        logger.exception("VPN connect endpoint failed")
        return {"success": False, "message": str(e)}

@app.post("/vpn/disconnect")
async def vpn_disconnect():
    try:
        success, msg = await state.vpn_manager.disconnect()
        state.current_vpn_location = "Disconnected"
        return {"success": success, "message": msg}
    except Exception as e:
        logger.error(f"VPN disconnect error: {e}")
        return {"success": False, "message": str(e)}

@app.post("/vpn/rotate")
async def vpn_rotate():
    """Explicitly trigger a VPN rotation."""
    try:
        log_to_state("🔄 Rotating VPN location...")
        success, msg = await state.vpn_manager.rotate_location()
        if success:
            state.current_vpn_location = msg
            log_to_state(f"✅ VPN Rotated: {msg}")
        return {"success": success, "message": msg}
    except Exception as e:
        logger.exception("VPN rotate endpoint failed")
        return {"success": False, "message": str(e)}

@app.get("/vpn/locations")
async def vpn_locations():
    try:
        locs = await state.vpn_manager.list_locations()
        return locs or []
    except Exception as e:
        logger.error(f"VPN list locations error: {e}")
        return []

# --- Entry Point ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
