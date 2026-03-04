"""
Reddit Bot Engine - Core bot functionality integrated with database tracking
"""
import time
from typing import Dict, List, Optional, Callable, Tuple
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from database import Database
from config import DELAY_MIN, DELAY_MAX, BROWSER_TIMEOUT, HEADLESS, MAX_PARALLEL_BROWSERS, VPN_ENABLED, VPN_REQUIRE_CONNECTION, VPN_ROTATE_PER_BATCH, VPN_BLOCKED_COUNTRIES, VPN_BLOCK_IF_COUNTRY_MATCHES, VPN_LOCATION_LIST_FILE
from ip_utils import get_ip_info
from ip_utils import get_geo_profile
import asyncio
import threading
# Stealth/humanization config
from config import (
    STEALTH_ENABLED, HUMANIZE_INPUT,
    HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS,
    HUMAN_STEP_WAIT_MIN_S, HUMAN_STEP_WAIT_MAX_S,
    INTER_ACCOUNT_DELAY_MIN_S, INTER_ACCOUNT_DELAY_MAX_S,
    PERSISTENT_CONTEXT, PERSISTENT_PROFILE_DIR,
    USER_AGENT_POOL, VIEWPORT_BASE_WIDTH, VIEWPORT_BASE_HEIGHT, VIEWPORT_VARIATION,
    DIRECT_LOGIN_ENABLED, LOCAL_LOGGING_ENABLED
)
from bot.utils.local_logger import append_to_local_log
import random as _random
import pathlib as _pathlib

try:
    # Optional: Playwright stealth. If not installed, we silently skip.
    from playwright_stealth import stealth_sync as _stealth_apply
except Exception:
    _stealth_apply = None

# Import utilities from new modular structure
from bot.utils.browser_setup import ensure_playwright_browsers, install_playwright_browsers
from bot.utils.credentials import parse_credentials as parse_credentials_util
from bot.utils.file_ops import prune_credentials_entry as prune_credentials_entry_util
from bot.detection.status_detector import detect_status as detect_status_util
from bot.detection.user_info_extractor import extract_user_info as extract_user_info_util
from bot.detection.error_normalizer import normalize_login_error as normalize_login_error_util
from bot.humanization.stealth import apply_stealth as apply_stealth_util, apply_basic_stealth as apply_basic_stealth_util
from bot.humanization.typing import type_human as type_human_util, clear_input as clear_input_util
from bot.humanization.behavior import human_pause as human_pause_util, mouse_jitter as mouse_jitter_util, gentle_scroll as gentle_scroll_util
from bot.browser.browser_manager import (
    launch_browser_and_context as launch_browser_and_context_util, 
    close_context_browser as close_context_browser_util,
    launch_browser_and_context_sync as launch_browser_and_context_sync_util,
    close_context_browser_sync as close_context_browser_sync_util
)
from bot.browser.navigation import navigate_via_address_bar as navigate_via_address_bar_util
from bot.browser.page_utils import get_or_create_page as get_or_create_page_util, close_extra_pages as close_extra_pages_util
from bot.login.form_utils import clear_form_fields as clear_form_fields_util, is_form_visible as is_form_visible_util, ensure_form_ready as ensure_form_ready_util, fill_username_field as fill_username_field_util, fill_password_field as fill_password_field_util, submit_form as submit_form_util
from bot.processing import (
    process_accounts_sequential,
    process_accounts_parallel,
    perform_final_retries,
)
from bot.core.session_manager import SessionManager


class RedditBotEngine:
    def __init__(self, db: Database, session_id: str, log_callback: Optional[Callable] = None, external_vpn_manager=None, skip_vpn_init: bool = False, progress_callback: Optional[Callable] = None, result_callback: Optional[Callable] = None):
        self.db = db
        self.session_id = session_id
        self.log_callback = log_callback or (lambda x: None)
        self.progress_callback = progress_callback
        self.result_callback = result_callback
        self.should_stop = False
        self.last_results = []
        # VPN and failure tracking (new strategy: connect once, use for all)
        self.vpn_manager = external_vpn_manager
        self.vpn_connected_at_start = False
        self.consecutive_failures = 0  # Track consecutive failures for VPN rotation
        self.skip_vpn_init = skip_vpn_init
        # Load threshold from config if available
        try:
            from config import MAX_CONSECUTIVE_FAILURES_BEFORE_VPN_CHANGE
            self.max_failures_before_vpn_change = int(MAX_CONSECUTIVE_FAILURES_BEFORE_VPN_CHANGE)
        except Exception:
            self.max_failures_before_vpn_change = 3  # sensible default
        self.current_vpn_location = None
        self.vpn_rotations = 0
        self.last_vpn_reason = ""
        
        # Ensure external vpn manager also uses the custom list if configured
        if self.vpn_manager and hasattr(self.vpn_manager, 'set_custom_locations_file') and VPN_LOCATION_LIST_FILE:
            try:
                self.vpn_manager.set_custom_locations_file(VPN_LOCATION_LIST_FILE)
            except Exception as e:
                self.log(f"⚠️ Error setting custom locations on VPN manager: {str(e)}")

        self.session_manager = SessionManager(self)
        self.session_manager.register_exit_handlers()
        self._active_browser_lock = threading.Lock()
        self._active_browser_contexts: List[Tuple[Optional[object], Optional[object]]] = []
        self.active_browsers = 0
        self.browser_status = "Waiting..."

    def _track_browser_context(self, browser, context):
        with self._active_browser_lock:
            self._active_browser_contexts.append((browser, context))
            self.active_browsers = len(self._active_browser_contexts)
            self.browser_status = f"Active Browsers: {self.active_browsers}"

    def _untrack_browser_context(self, browser, context):
        with self._active_browser_lock:
            self._active_browser_contexts = [
                pair for pair in self._active_browser_contexts
                if pair[0] is not browser or pair[1] is not context
            ]
            self.active_browsers = len(self._active_browser_contexts)
            if self.active_browsers == 0:
                self.browser_status = "All browsers closed"
            else:
                self.browser_status = f"Active Browsers: {self.active_browsers}"

    def close_all_active_contexts(self):
        with self._active_browser_lock:
            contexts = list(self._active_browser_contexts)
            self._active_browser_contexts.clear()
        for browser, context in contexts:
            try:
                self._run_async(close_context_browser_util(browser, context))
            except Exception as e:
                self.log(f"⚠️ Error closing browser context: {str(e)}")
    
    def log(self, message: str):
        """Log message using callback."""
        self.log_callback(message)
    
    def stop(self, hard: bool = False):
        """Stop the bot and disconnect VPN."""
        self.should_stop = True
        if hard:
            self.log("🧨 [HARD STOP] Killing all browser processes...")
            self.browser_status = "Hard Stopping..."
        else:
            self.log("🛑 Stop request received. Cleaning up...")
            self.browser_status = "Stopping..."
            
        self.session_manager.stop()
        self.close_all_active_contexts()
        
        if hard:
            self.active_browsers = 0
            self.browser_status = "All browsers killed"
            self.log("✅ Hard stop completed.")
    
    def check_vpn_status(self) -> bool:
        """
        Check if VPN is connected. If not, stop the bot.
        Returns True if VPN is connected or skipping check (rotation).
        """
        if not self.vpn_manager:
            return True
            
        # Skip check if we're currently rotating the VPN
        if getattr(self.vpn_manager, "is_rotating_vpn", False):
            # self.log("🔄 [ENGINE] VPN rotation in progress, skipping status check")
            return True
            
        is_connected, status = self._run_async(self.vpn_manager.get_status())
        if not is_connected:
            self.log(f"🚨 [ENGINE] VPN DISCONNECTED! Status: {status}")
            self.log("🛑 [ENGINE] Stopping bot for security...")
            self.stop()
            return False
            
        return True
    
    def _close_context_browser(self, browser, context):
        """Close all pages, then context and browser safely."""
        self._run_async(close_context_browser_util(browser, context))
        self._untrack_browser_context(browser, context)
    
    def _create_clean_page(self, context):
        """Reuse existing page if possible or open a fresh one."""
        try:
            pages = context.pages
            if pages:
                # Close extra pages if more than one
                if len(pages) > 1:
                    for p in pages[1:]:
                        try:
                            p.close()
                        except:
                            pass
                # Reuse the first one
                return pages[0]
        except Exception as e:
            self.log(f"⚠️ Error during clean page reuse: {str(e)}")
        
        return context.new_page()
    
    def parse_credentials(self, file_path: str) -> List[tuple]:
        """Parse credentials from file."""
        return parse_credentials_util(file_path, log_callback=self.log)
    
    def detect_status(self, page) -> tuple:
        """Detect login status and extract user information with specific error detection."""
        return detect_status_util(page, log_callback=self.log)
    
    def extract_user_info(self, page) -> tuple:
        """Extract username and karma from Reddit page, even when account is locked/reset."""
        return extract_user_info_util(page, log_callback=self.log)
    
    def _normalize_login_error(self, error_lower: str):
        """
        Normalize localized login error messages to consistent categories.
        Returns tuple (status, username, karma, reason) or None if no match.
        """
        return normalize_login_error_util(error_lower)
    
    def _run_async(self, coro):
        """Run an async coroutine in a synchronous context safely without interfering with Playwright's loop."""
        import concurrent.futures
        import threading
        
        def run_in_new_loop():
            # Create a completely fresh event loop for this thread/task
            # This avoids any interference from Playwright's event loop or FastAPI's main loop
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

        # Run the isolate loop in a fresh thread to avoid any current-thread loop conflicts
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_new_loop)
            try:
                return future.result(timeout=60)
            except concurrent.futures.TimeoutError:
                self.log(f"⚠️  [ENGINE] Async operation timed out after 60s")
                raise TimeoutError("Async operation timed out")

    def _launch_browser_and_context(self, playwright, profile_name: Optional[str] = None):
        """Launch a new browser and context using current configuration and geo profile."""
        browser, context = self._run_async(launch_browser_and_context_util(playwright, log_callback=self.log, profile_name=profile_name))
        self._track_browser_context(browser, context)
        return browser, context

    def _launch_browser_and_context_sync(self, playwright, profile_name: Optional[str] = None):
        """Synchronous version of browser launch."""
        browser, context = launch_browser_and_context_sync_util(playwright, log_callback=self.log, profile_name=profile_name)
        self._track_browser_context(browser, context)
        return browser, context

    def _close_context_browser_sync(self, browser, context):
        """Synchronous version of browser close."""
        try:
            close_extra_pages_util(context, keep_first=False)
        except:
            pass
        close_context_browser_sync_util(browser, context)

    def login_to_reddit(self, email: str, password: str, playwright, first_attempt=True, reuse_context=None, reuse_page=None, profile_name: Optional[str] = None) -> Dict:
        """Attempt to login to Reddit. Use profile_name for persistent context isolation."""
        result = {
            "email": email,
            "password": password,
            "status": "error",
            "username": None,
            "karma": None,
            "error_message": None,
            "timing": {}
        }
        
        timing = result["timing"]
        account_start_time = time.time()
        credential_input_time = None
        
        browser = None
        context = None
        page = None
        
        try:
            # Check if browsers are installed, install if needed (first attempt only)
            if first_attempt:
                if not ensure_playwright_browsers():
                    self.log("Playwright browsers not found. Installing... (this may take a few minutes)")
                    if not install_playwright_browsers(self.log):
                        result["error_message"] = "Failed to install Playwright browsers. Please wait for download to complete and try again."
                        return result
                    self.log("Browsers installed successfully! Retrying login...")
                    # Retry after installation
                    return self.login_to_reddit(email, password, playwright, first_attempt=False)
            
            # Use existing context if provided (reuse browser), otherwise launch new
            if reuse_context:
                context = reuse_context
                if reuse_page:
                    page = reuse_page
                    self.log("♻️ [ENGINE] Reusing browser context and page for next account")
                else:
                    self.log("🆕 [ENGINE] Reusing browser context, creating new page...")
                    page = self._create_clean_page(context)
                    self.log("✅ [ENGINE] New page created in reused browser")
            else:
                self.log(f"🔧 [ENGINE] Opening browser for profile: {profile_name or 'Incognito'}...")
                browser, context = self._launch_browser_and_context_sync(playwright, profile_name=profile_name)
                self.log("✅ [ENGINE] Browser opened")
                self.log("🔧 [ENGINE] Creating new page...")
                page = self._create_clean_page(context)
                self.log("✅ [ENGINE] New page created")
            
            # Apply stealth patches if available
            if STEALTH_ENABLED:
                try:
                    apply_stealth_util(page, _stealth_apply)
                except Exception as e:
                    self.log(f"⚠️ Stealth apply skip: {str(e)}")
            
            login_url = "https://www.reddit.com/login/?dest=https%3A%2F%2Fwww.reddit.com%2Fuser%2Fme%2F&rdt=46144"

            # If reusing page and we're already on login page with form visible, just clear fields
            if reuse_page:
                try:
                    current_url = page.url
                    # Zero-reload fast refresh logic matching competitor
                    if "login" in current_url and is_form_visible_util(page):
                        self.log("⚡ [ENGINE] Competitor Zero-Reload: Clearing fields without refreshing page.")
                        try:
                            context.clear_cookies()
                        except Exception:
                            pass
                            
                        # Instantly clear HTML input fields instead of network refresh
                        if clear_form_fields_util(page, log_callback=self.log):
                            time.sleep(0.3)
                    elif DIRECT_LOGIN_ENABLED:
                        self.log("🚀 [ENGINE] Using DIRECT LOGIN navigation (Competitor style)")
                        try:
                            context.clear_cookies()
                        except Exception:
                            pass
                        page.goto(login_url, timeout=BROWSER_TIMEOUT)
                    else:
                        self.log("🌐 Loading Reddit login page...")
                        try:
                            context.clear_cookies()
                        except Exception as e:
                            self.log(f"⚠️ Error clearing cookies: {str(e)}")
                        self._navigate_via_address_bar(page, login_url, BROWSER_TIMEOUT)
                except Exception as e:
                    self.log(f"⚠️ Navigation error during page reuse: {str(e)}")
                    self._navigate_via_address_bar(page, login_url, BROWSER_TIMEOUT)
            else:
                self.log("🌐 Loading Reddit login page...")
                try:
                    context.clear_cookies()
                except Exception as e:
                    self.log(f"⚠️ Error clearing cookies: {str(e)}")
                try:
                    context.clear_permissions()
                except Exception as e:
                    self.log(f"⚠️ Error clearing permissions: {str(e)}")
                
                if DIRECT_LOGIN_ENABLED:
                    self.log("🚀 [ENGINE] Using DIRECT LOGIN navigation (Competitor style)")
                    page.goto(login_url, timeout=BROWSER_TIMEOUT)
                else:
                    self._navigate_via_address_bar(page, login_url, BROWSER_TIMEOUT)
                
                try:
                    page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch(e){} }")
                except Exception as e:
                    self.log(f"⚠️ Error clearing localStorage: {str(e)}")
            # Ensure login form exists; if not, force logout then back to login page again
            try:
                if not ensure_form_ready_util(page, timeout=4000):
                    try:
                        self._navigate_via_address_bar(page, 'https://www.reddit.com/logout', 8000)
                    except Exception as e:
                        self.log(f"⚠️ Logout error: {str(e)}")
                    try:
                        self._navigate_via_address_bar(page, login_url, BROWSER_TIMEOUT)
                    except Exception as e:
                        self.log(f"⚠️ Login navigation error: {str(e)}")
            except Exception as e:
                self.log(f"⚠️ Form readiness check error: {str(e)}")
            # Human-like small wait and mouse jitter before interacting
            if HUMANIZE_INPUT:
                try:
                    human_pause_util()
                    mouse_jitter_util(page)
                except Exception as e:
                    self.log(f"⚠️ Humanization pause error: {str(e)}")
            try:
                page.wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception as e:
                self.log(f"⚠️ Load state pause error: {str(e)}")
            time.sleep(0.5)  # Reduced to 0.5s for faster processing
            
            try:
                page.wait_for_selector('input[type="text"], input[name="username"], input[id*="username"]', timeout=5000)
            except Exception as e:
                self.log(f"⚠️ Input selector timeout: {str(e)}")
            
            cred_input_start = time.time()
            # Fill email - using Reddit's new UI (faceplate-text-input) for faster detection
            email_field = fill_username_field_util(page, email, log_callback=self.log)
            
            if not email_field:
                result["error_message"] = "Could not find email/username field"
                return result
            
            # Fill password - using Reddit's new UI
            password_field = fill_password_field_util(page, password, log_callback=self.log)
            
            if not password_field:
                result["error_message"] = "Could not find password field"
                return result
            
            credential_input_time = time.time() - cred_input_start
            timing["credential_input_seconds"] = round(credential_input_time, 3)
            
            # Submit form
            if not submit_form_util(page, password_field, log_callback=self.log):
                result["error_message"] = "Could not submit login form"
                return result
            
            # Wait for navigation - minimal wait with small human-like scroll
            try:
                page.wait_for_load_state('domcontentloaded', timeout=8000)
            except Exception as e:
                self.log(f"⚠️ Post-submit load state timeout: {str(e)}")
            if HUMANIZE_INPUT:
                try:
                    human_pause_util()
                    gentle_scroll_util(page)
                except Exception as e:
                    self.log(f"⚠️ Post-submit humanization error: {str(e)}")
            time.sleep(0.5)  # Reduced to 0.5s for faster detection
            
            # Detect status
            status, username, karma, error_msg = self.detect_status(page)
            result["status"] = status
            result["username"] = username
            result["karma"] = karma
            result["error_message"] = error_msg
            
            # If account is locked/reset-required, ALWAYS try to collect username/karma before closing
            try:
                if status == "error":
                    err_lower = (error_msg or "").lower()
                    is_locked_reset = ('reset' in err_lower and 'password' in err_lower) or ('locked' in err_lower) or ('unusual activity' in err_lower)
                    
                    if is_locked_reset:
                        # Force extraction even if we already have username/karma (might be incomplete)
                        self.log(f"🔍 Extracting user info for locked account...")
                        try:
                            username_extracted, karma_extracted = self.extract_user_info(page)
                            # Update if we got better data
                            if username_extracted and not result.get("username"):
                                result["username"] = username_extracted
                            elif username_extracted and username_extracted != "Unknown":
                                result["username"] = username_extracted
                            
                            if karma_extracted and not result.get("karma"):
                                result["karma"] = karma_extracted
                            elif karma_extracted:
                                result["karma"] = karma_extracted
                            
                            # Update status fields
                            username = result.get("username")
                            karma = result.get("karma")
                        except Exception as ext_err:
                            self.log(f"⚠️  Extraction error: {str(ext_err)}")
                        
                        # Build profile URL and enrich reason with collected data
                        profile_url = None
                        if result.get("username"):
                            profile_url = f"https://www.reddit.com/user/{result['username']}"
                        extra_bits = []
                        if result.get("username"):
                            extra_bits.append(f"user: {result['username']}")
                        if result.get("karma"):
                            extra_bits.append(f"karma: {result['karma']}")
                        if profile_url:
                            extra_bits.append(f"url: {profile_url}")
                        if extra_bits:
                            msg = result.get("error_message") or "Account locked due to unusual activity"
                            result["error_message"] = f"{msg} | " + " | ".join(extra_bits)
                            self.log(f"✅ Collected info: username={result.get('username')}, karma={result.get('karma')}")
            except Exception as e:
                self.log(f"⚠️ Final status processing error: {str(e)}")
            
            # Trigger local logging if enabled
            if LOCAL_LOGGING_ENABLED:
                try:
                    append_to_local_log(
                        status=result.get("status", "error"),
                        email=email,
                        password=password,
                        username=result.get("username"),
                        karma=result.get("karma")
                    )
                except Exception as e:
                    self.log(f"⚠️ Local logging failed: {str(e)}")

        except PlaywrightTimeoutError:
            result["error_message"] = "Timeout waiting for page to load"
        except Exception as e:
            result["error_message"] = f"Error during login attempt: {str(e)}"
        finally:
            # Keep the page open if we are reusing the page; only close per-account page when it was created here
            if page and not reuse_page:
                try:
                    self.log("🔧 [ENGINE] Closing page (not reusing)...")
                    page.close()
                    self.log("✅ [ENGINE] Page closed")
                except Exception as e:
                    self.log(f"⚠️  [ENGINE] Error closing page: {str(e)}")
            else:
                if reuse_page:
                    self.log("♻️  [ENGINE] Keeping page open (reusing for next account)")
            # Only close context/browser if we created them here (not reusing)
            if not reuse_context:
                if context:
                    try:
                        # Persistent context should not be closed aggressively
                        if not PERSISTENT_CONTEXT:
                            self.log("🔧 [ENGINE] Closing context...")
                            context.close()
                            self.log("✅ [ENGINE] Context closed")
                    except Exception as e:
                        self.log(f"⚠️  [ENGINE] Error closing context: {str(e)}")
                if browser:
                    try:
                        self.log("🔧 [ENGINE] Closing browser...")
                        browser.close()
                        self.log("✅ [ENGINE] Browser closed successfully")
                    except Exception as e:
                        self.log(f"⚠️  [ENGINE] Error closing browser: {str(e)}")
            else:
                self.log("♻️  [ENGINE] Keeping browser/context open (reusing for next account)")
        
        timing["total_account_seconds"] = round(time.time() - account_start_time, 3)
        return result
    
    def process_credentials(self, file_path: str, parallel_browsers: int = 1) -> List[Dict]:
        """Process all credentials from file with optional parallel processing."""
        credentials = self.parse_credentials(file_path)
        
        if not credentials:
            self.log("No valid credentials found")
            return []
        
        self.log(f"Found {len(credentials)} credential(s) to process")
        self.log(f"Using {parallel_browsers} parallel browser(s)")
        
        results = []
        
        # Limit parallel browsers
        parallel_browsers = min(parallel_browsers, MAX_PARALLEL_BROWSERS, len(credentials))
        
        # NEW VPN STRATEGY: Use GUI VPN if provided; otherwise connect once at start
        if VPN_ENABLED and not self.skip_vpn_init:
            try:
                if self.vpn_manager:
                    # Use existing VPN managed by GUI
                    is_connected, vpn_location = self._run_async(self.vpn_manager.get_status())
                    if is_connected:
                        self.current_vpn_location = vpn_location
                        self.vpn_connected_at_start = True
                    else:
                        self.log("🔒 [ENGINE] VPN not connected. Attempting auto-connect...")
                        success, msg = self._run_async(self.vpn_manager.connect_random_location())
                        if success:
                            self.vpn_connected_at_start = True
                            self.current_vpn_location = msg
                            self.log(f"✅ [ENGINE] VPN Auto-connected: {msg}")
                        elif VPN_REQUIRE_CONNECTION:
                            self.log(f"❌ [ENGINE] VPN connection required but auto-connect failed: {msg}. Aborting.")
                            raise RuntimeError(f"VPN connection required but failed: {msg}")
                        else:
                            self.log(f"⚠️  [ENGINE] VPN auto-connect failed: {msg}. Continuing as per config.")
                else:
                    from vpn_manager import ExpressVPNManager
                    self.vpn_manager = ExpressVPNManager(log_callback=self.log)
                    if self.vpn_manager.is_available():
                        # Set custom location list if configured
                        if VPN_LOCATION_LIST_FILE:
                            self.vpn_manager.set_custom_locations_file(VPN_LOCATION_LIST_FILE)
                        self.log("🔒 ExpressVPN detected")
                        locs = self._run_async(self.vpn_manager.list_locations())
                        self.log(f"📍 Available locations: {len(locs)}")
                        self.log("🌐 Connecting to ExpressVPN server...")
                        start_ts = time.time()
                        success, msg = self._run_async(self.vpn_manager.connect(None))  # Smart location
                        if not success:
                            success, msg = self._run_async(self.vpn_manager.connect_random_location())
                        # Soft timeout guard
                        if time.time() - start_ts > 30:
                            self.log("⚠️  VPN connect taking long; continue with current status.")
                        if success:
                            time.sleep(5)
                            is_connected, vpn_location = self._run_async(self.vpn_manager.get_status())
                            if is_connected:
                                self.current_vpn_location = vpn_location
                                ip, country, full_location = get_ip_info()
                                self.log(f"✅ Connected server: {vpn_location}")
                                if ip:
                                    self.log(f"📍 IP: {ip} | Country: {country or 'Unknown'} | Location: {full_location or 'Unknown'}")
                                self.log("⏳ Please wait for server location to stabilize...")
                                time.sleep(3)  # Reduced from 10s to 3s
                                self.vpn_connected_at_start = True
                            elif VPN_REQUIRE_CONNECTION:
                                self.log("❌ VPN connection failed and is required. Aborting.")
                                return []
                        elif VPN_REQUIRE_CONNECTION:
                            self.log(f"❌ Could not connect VPN: {msg}. VPN is required. Aborting.")
                            return []
                    else:
                        self.log("⚠️  ExpressVPN not found")
                        if VPN_REQUIRE_CONNECTION:
                            self.log("❌ VPN connection required but ExpressVPN is not available. Aborting.")
                            return []
            except Exception as e:
                self.log(f"⚠️  VPN initialization error: {str(e)}")
                if VPN_REQUIRE_CONNECTION:
                    self.log("❌ VPN error occurred and connection is required. Aborting.")
                    return []
        
        self.browser_status = "Launching..."
        if parallel_browsers == 1:
            results = process_accounts_sequential(self, credentials, file_path)
        else:
            results = process_accounts_parallel(self, credentials, parallel_browsers)

        if not self.should_stop:
            results = perform_final_retries(self, results)

        self.last_results = results
        return results

    # ----------------------
    # Humanization utilities
    # ----------------------
    def _type_human(self, element, text: str):
        """Type with per-character delay to simulate human typing."""
        type_human_util(element, text)

    def _navigate_via_address_bar(self, page, url: str, timeout: int = None):
        """Navigate by pasting URL in address bar - opens browser first, then pastes URL and hits Enter."""
        return navigate_via_address_bar_util(page, url, timeout)

    def _human_pause(self):
        """Small random pause between steps."""
        human_pause_util()

    def _mouse_jitter(self, page):
        """Perform small random mouse movements to simulate human presence."""
        mouse_jitter_util(page)

    def _gentle_scroll(self, page):
        """Perform a small gentle scroll to mimic reading."""
        gentle_scroll_util(page)

    def _apply_basic_stealth(self, page):
        """Enhanced stealth: patch navigator.webdriver, plugins, languages, WebGL, chrome runtime, permissions, and more."""
        apply_basic_stealth_util(page)

    def _clear_input(self, element):
        """Clear an input field robustly without reloading/closing."""
        clear_input_util(element)

    def _prune_credentials_entry(self, file_path: str, email: str, password: str):
        """
        Remove a single 'email:password' token from the credentials source file if present.
        Parsing is by whitespace tokens (matching parse_credentials).
        """
        prune_credentials_entry_util(file_path, email, password, log_callback=self.log)
