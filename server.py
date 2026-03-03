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

# --- Shared State Management ---
class AppState:
    def __init__(self):
        self.db = Database()
        self.vpn_manager = ExpressVPNManager()
        self.bot_instance: Optional[RedditBotEngine] = None
        self.is_running = False
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
        self.current_session_id = None
        self.current_vpn_location = "Initializing..."
        self.lock = threading.Lock()
        self.stop_requested = False
        
        # Load user settings
        self.settings = self.load_user_settings()

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
            "persistent_context": False
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

state = AppState()

# --- Helpers ---
def log_to_state(message: str, level: str = "info"):
    """Callback for bot engine to write logs into shared state and persistent logger."""
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
    
    # Mirror to persistent logger
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)

def progress_update(snapshot: Dict[str, Any]):
    """Callback for bot engine to update stats."""
    with state.lock:
        state.stats.update(snapshot)

# --- App Lifecycle ---
@app.on_event("startup")
async def startup_event():
    """Perform async startup tasks."""
    logger.info("Application starting up...")
    try:
        is_connected, loc = await state.vpn_manager.get_status()
        state.current_vpn_location = loc if is_connected else "Disconnected"
        logger.info(f"Initial VPN Status: {state.current_vpn_location}")
    except Exception as e:
        logger.error(f"Failed to get initial VPN status: {e}")
        state.current_vpn_location = "Error"

# --- Background Worker ---
def bot_worker(file_path: str, parallel_browsers: int):
    """Thread worker that executes the bot logic."""
    try:
        with state.lock:
            state.stop_requested = False
            state.is_running = True
            state.current_session_id = state.db.create_session()
            
        state.bot_instance = RedditBotEngine(
            db=state.db,
            session_id=state.current_session_id,
            log_callback=log_to_state,
            external_vpn_manager=state.vpn_manager,
            skip_vpn_init=True,
            progress_callback=progress_update
        )
        
        log_to_state(f"🚀 Bot execution started (Session: {state.current_session_id})")
        state.bot_instance.process_credentials(file_path, parallel_browsers)
        log_to_state("✅ Bot execution completed successfully.")
        
    except Exception as e:
        log_to_state(f"❌ Critical Error in Bot Worker: {str(e)}")
    finally:
        with state.lock:
            state.is_running = False
            state.bot_instance = None

# --- API Endpoints ---

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
    return {"status": "success", "settings": state.settings}

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
            
        # Log as pending for UI visibility
        accounts = parse_credentials_text(text)
        state.db.log_batch_results(accounts)
        
        log_to_state(f"📁 Credentials file uploaded: {file.filename} ({len(accounts)} accounts)")
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
            
        # Log as pending for UI visibility
        accounts = parse_credentials_text(text)
        state.db.log_batch_results(accounts)
        
        log_to_state(f"📋 Credentials pasted and saved ({len(accounts)} accounts)")
        return {"status": "success", "message": f"Successfully saved {len(accounts)} accounts"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/bot/start")
async def start_bot(
    background_tasks: BackgroundTasks,
    file_path: str = "credentials.txt",
    parallel_browsers: int = 1
):
    if state.is_running:
        return {"status": "error", "message": "Bot is already running."}
    
    # VPN Check and Auto-Connect
    try:
        is_connected, location = await state.vpn_manager.get_status()
        if not is_connected:
            log_to_state("🔒 VPN not connected. Attempting auto-connect...")
            success, msg = await state.vpn_manager.connect_random_location()
            if not success:
                state.current_vpn_location = "Failed to connect"
                if VPN_REQUIRE_CONNECTION:
                    return {"status": "error", "message": f"VPN Auto-connect failed: {msg}. Connection is mandatory."}
                log_to_state(f"⚠️ VPN Auto-connect failed: {msg}. Continuing as per config.", "warning")
            else:
                state.current_vpn_location = msg
                log_to_state(f"✅ VPN Auto-connected: {msg}")
    except Exception as e:
        state.current_vpn_location = "Error"
        logger.exception("VPN Check/Connect failed")
        if VPN_REQUIRE_CONNECTION:
            return {"status": "error", "message": f"VPN check/connect failed: {str(e)}"}
    
    state.reset_stats()
    background_tasks.add_task(bot_worker, file_path, parallel_browsers)
    return {"status": "success", "message": "Bot started in background."}

@app.post("/bot/stop")
async def stop_bot():
    if not state.is_running or not state.bot_instance:
        return {"status": "error", "message": "Bot is not running."}
    
    state.bot_instance.stop()
    log_to_state("🛑 Stop signal sent to bot engine...")
    return {"status": "success", "message": "Stop signal sent."}

@app.get("/bot/status")
async def get_status():
    uptime = 0
    if state.is_running and state.stats["start_time"]:
        start_dt = datetime.fromisoformat(state.stats["start_time"])
        uptime = int((datetime.now() - start_dt).total_seconds())

    with state.lock:
        return {
            "is_running": state.is_running,
            "session_id": state.current_session_id,
            "vpn_location": state.current_vpn_location,
            "stats": {**state.stats, "uptime_seconds": uptime},
            "recent_logs": list(state.logs)[-20:]  # Return last 20 logs for UI snappiness
        }

@app.get("/bot/full-logs")
async def get_all_logs():
    with state.lock:
        return list(state.logs)

# --- Accounts ---
@app.get("/accounts/results")
async def get_results():
    """Return results from local storage."""
    try:
        import json
        import os
        results_file = "session_results.json"
        
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                all_results = json.load(f)
            
            # Filter by current session if active, otherwise show recent
            if state.current_session_id:
                # Include current session results AND any pending (session_id=None) accounts
                return [r for r in all_results if r.get('session_id') == state.current_session_id or r.get('session_id') is None]
            return all_results[:500]
            
    except Exception as e:
        print(f"Error reading local results: {e}")
        
    return []

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
