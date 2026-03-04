"""
Parallel account processing - manages multi-threaded processing and worker coordination.
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict

from playwright.sync_api import sync_playwright

from config import REUSE_BROWSER_FOR_BATCH, PERSISTENT_CONTEXT
from bot.utils.browser_setup import ensure_playwright_browsers, install_playwright_browsers
from ip_utils import get_ip_info
from bot.browser.page_utils import get_or_create_page, close_extra_pages


def interruptible_sleep(engine, duration: float, check_interval: float = 0.1):
    """
    Sleep that can be interrupted by should_stop flag.
    
    Args:
        engine: RedditBotEngine instance with should_stop flag
        duration: Total sleep duration in seconds
        check_interval: How often to check should_stop (default 0.1s)
    
    Returns:
        True if interrupted, False if completed
    """
    elapsed = 0.0
    while elapsed < duration:
        if engine.should_stop:
            return True  # Interrupted
        sleep_chunk = min(check_interval, duration - elapsed)
        time.sleep(sleep_chunk)
        elapsed += sleep_chunk
    return False  # Completed


def process_accounts_parallel(engine, credentials: List[Tuple[str, str]], parallel_browsers: int) -> List[Dict]:
    """
    Parallel processing - each worker uses its own browser/context instances.

    Args:
        engine: RedditBotEngine instance
        credentials: List of (email, password) tuples
        parallel_browsers: Desired number of parallel browsers

    Returns:
        List of result dictionaries
    """
    results: List[Dict] = []

    vpn_manager = engine.vpn_manager

    if not ensure_playwright_browsers():
        engine.log("Playwright browsers not found. Installing... (this may take a few minutes)")
        if not install_playwright_browsers(engine.log):
            engine.log("ERROR: Failed to install Playwright browsers")
            return []
        engine.log("Browsers installed successfully!")

    total = len(credentials)
    batch_size = total  # process entire run in one batch so each worker reuses its browser
    num_batches = (total + batch_size - 1) // batch_size

    engine.log(f"Starting {total} accounts with {parallel_browsers} parallel browsers...")
    if vpn_manager and engine.current_vpn_location:
        engine.log(f"Using ExpressVPN: {engine.current_vpn_location} (same VPN for all accounts)")
    engine.log("All browsers will work simultaneously!")

    batch_num = 0
    for batch_start in range(0, total, batch_size):
        if engine.should_stop:
            break

        batch_num += 1
        batch_end = min(batch_start + batch_size, total)
        batch_credentials = credentials[batch_start:batch_end]

        engine.log(f"\n{'='*60}")
        engine.log(f"🔄 BATCH {batch_num}/{num_batches}: Processing {len(batch_credentials)} accounts")
        if vpn_manager and engine.current_vpn_location:
            engine.log(f"Using ExpressVPN: {engine.current_vpn_location}")
        engine.log(f"{'='*60}")

        completed_lock = threading.Lock()
        batch_results: List[Dict] = []
        
        # Smart Hybrid VPN Rotation Tracking
        vpn_rotation_lock = threading.Lock()
        vpn_rotation_requested = False
        worker_retry_errors: Dict[int, int] = {}  # Track retry errors per worker (start_index -> count)
        batch_retry_error_count = 0  # Track total retry errors in batch
        consecutive_retry_failures = 0  # Track consecutive retry failures
        
        # Account-based VPN rotation tracking
        accounts_processed_since_vpn_change = 0  # Track accounts processed since last VPN change
        try:
            from config import VPN_ROTATE_AFTER_ACCOUNTS
            vpn_rotate_after_accounts = int(VPN_ROTATE_AFTER_ACCOUNTS) if VPN_ROTATE_AFTER_ACCOUNTS > 0 else 0
        except Exception:
            vpn_rotate_after_accounts = 0  # Disabled by default if not configured
        
        # Log VPN rotation settings
        if vpn_manager:
            if vpn_rotate_after_accounts > 0:
                engine.log(f"📊 Account-based VPN rotation: Enabled (will rotate every {vpn_rotate_after_accounts} accounts)")
            else:
                engine.log(f"📊 Account-based VPN rotation: Disabled (only rotates on errors/blocked)")
        
        # Smart Hybrid: Critical Error Queue for deferred retry after VPN rotation
        critical_error_queue: List[Dict] = []  # Queue accounts with blocked/rate limit for deferred retry
        critical_error_queue_lock = threading.Lock()
        
        # Error period tracking: Track accounts processed during error periods (rate limit/too many requests)
        error_period_accounts: List[Dict] = []  # Accounts processed during error period
        error_period_active = False  # Flag indicating if we're in an error period
        error_period_lock = threading.Lock()

        def process_worker_stealing(worker_id, work_queue, queue_lock, start_account_counter):
            """
            Work-Stealing Worker: Pulls accounts from shared queue dynamically.
            Worker stays alive until queue is empty, ensuring maximum browser utilization.
            """
            nonlocal vpn_rotation_requested  # Allow modification of outer scope variable
            accounts_processed = 0  # Track accounts processed by this worker
            
            try:
                with sync_playwright() as playwright_worker:
                    browser_w = None
                    context_w = None
                    page_w = None
                    worker_retry_count = 0  # Track retry errors for this worker
                    worker_consecutive_retry_failures = 0  # Track consecutive retry failures

                    def close_worker_browser(reason: str = ""):
                        nonlocal browser_w, context_w, page_w
                        if not browser_w and not context_w:
                            page_w = None
                            return
                        if reason:
                            engine.log(f"🛑 Worker [{worker_id}] closing browser ({reason})")
                        try:
                            engine._close_context_browser_sync(browser_w, context_w)
                        except Exception:
                            pass
                        browser_w = None
                        context_w = None
                        page_w = None

                    if engine.should_stop:
                        engine.log(f"⏹️ Worker [{worker_id}] stop requested before launch; exiting worker")
                        return
                    
                    # Open browser once for this worker (will be reused for all accounts)
                    try:
                        engine.log(f"🎬 [WORKER {worker_id}] Launching browser (Initial)...")
                        browser_w, context_w = engine._launch_browser_and_context_sync(playwright_worker)
                        engine.log(f"✅ [WORKER {worker_id}] Browser launch completed")
                        try:
                            engine.log(f"🔧 Worker [{worker_id}]: Creating/Getting page...")
                            page_w = get_or_create_page(context_w)
                            close_extra_pages(context_w, keep_first=True)
                            engine.log(f"✅ Worker [{worker_id}]: Page ready")
                        except Exception as page_err:
                            engine.log(f"⚠️  Worker [{worker_id}]: Failed to create page: {str(page_err)}")
                            page_w = None
                    except Exception as init_err:
                        err_msg = str(init_err)
                        if "Executable doesn't exist" in err_msg or "executable_path" in err_msg:
                            engine.log(f"❌ [WORKER {worker_id}] Playwright browser not found!")
                            engine.log("💡 [FIX] Please run this in your terminal: python3 -m playwright install chromium")
                            engine.browser_status = "Error: Browser Missing"
                        else:
                            engine.log(f"⚠️  [WORKER {worker_id}] Browser launch error: {err_msg}")
                            engine.browser_status = "Error: Launch Failed"
                        return

                    # Work-Stealing Loop: Keep pulling accounts from queue until empty
                    while True:
                        if engine.should_stop:
                            engine.log(f"⏹️ Worker [{worker_id}]: Stop requested, exiting work-stealing loop")
                            # Immediately close browser on stop
                            close_worker_browser("stop requested")
                            break
                        
                        # Check VPN status - if disconnected (and not rotating), stop the bot
                        if not engine.check_vpn_status():
                            close_worker_browser("VPN disconnected")
                            break
                        
                        # Get next account from queue (thread-safe)
                        account_data = None
                        with queue_lock:
                            if len(work_queue) == 0:
                                # Queue is empty, worker can exit
                                break
                            account_data = work_queue.pop(0)  # Get first account from queue
                        
                        if account_data is None:
                            break
                        
                        email = account_data["email"]
                        password = account_data["password"]
                        index = account_data["index"]
                        
                        # Check stop before processing account
                        if engine.should_stop:
                            engine.log(f"⏹️ Worker [{worker_id}]: Stop requested before processing account {index}")
                            # Return account to queue for potential retry later
                            with queue_lock:
                                work_queue.insert(0, account_data)
                            break
                        
                        accounts_processed += 1
                        
                        try:
                            # Verify browser/context/page are still valid before reuse 
                            # (or force recreate if PERSISTENT_CONTEXT is enabled for isolation)
                            if context_w is None or page_w is None or PERSISTENT_CONTEXT:
                                if PERSISTENT_CONTEXT and context_w is not None:
                                    engine.log(f"🔄 Worker [{worker_id}]: Switching profile context to {email}...")
                                    close_worker_browser("profile switch")
                                
                                engine.log(f"🎬 [WORKER {worker_id}] Launching browser (Profile: {email if PERSISTENT_CONTEXT else 'Incognito'})...")
                                try:
                                    self_profile_name = email if PERSISTENT_CONTEXT else None
                                    browser_w, context_w = engine._launch_browser_and_context_sync(playwright_worker, profile_name=self_profile_name)
                                    engine.log(f"✅ [WORKER {worker_id}] Browser launch completed")
                                    page_w = get_or_create_page(context_w)
                                    close_extra_pages(context_w, keep_first=True)
                                    engine.log(f"✅ [WORKER {worker_id}] Page ready")
                                except Exception as rec_err:
                                    # ... error handling ... (existing logic below)
                                    err_msg = str(rec_err)
                                    if "Executable doesn't exist" in err_msg or "executable_path" in err_msg:
                                        engine.log(f"❌ [WORKER {worker_id}] Playwright browser not found during recreate!")
                                        engine.log("💡 [FIX] Please run this in your terminal: python3 -m playwright install chromium")
                                    else:
                                        engine.log(f"❌ [WORKER {worker_id}] Recreate launch error: {err_msg}")
                                    break # Exit worker if recreate fails
                            
                            # Check stop before calling login_to_reddit (long operation)
                            if engine.should_stop:
                                engine.log(f"⏹️ Worker [{worker_id}]: Stop requested before login_to_reddit for account {index}")
                                # Return account to queue
                                with queue_lock:
                                    work_queue.insert(0, account_data)
                                break
                            
                            # Initialize variables that might be referenced if IP fetching is skipped
                            ip = ""
                            country = ""
                            location = ""
                            
                            engine.log(f"🔍 Worker [{worker_id}]: Calling login_to_reddit for account {index} with reuse_context={'VALID' if context_w else 'None'}, reuse_page={'VALID' if page_w else 'None'}")
                            engine.browser_status = f"W[{worker_id}] > {email}"
                            result = engine.login_to_reddit(
                                email,
                                password,
                                playwright_worker,
                                first_attempt=False,
                                reuse_context=context_w,
                                reuse_page=page_w,
                                profile_name=email if PERSISTENT_CONTEXT else None
                            )
                            
                            # Check stop after login_to_reddit (may have taken time)
                            if engine.should_stop:
                                engine.log(f"⏹️ Worker [{worker_id}]: Stop requested after login_to_reddit for account {index}")
                                with completed_lock:
                                    batch_results.append(result)
                                break

                            status = (result.get("status") or "").lower()
                            err_lower = (result.get("error_message", "") or "").lower()
                            
                            # Smart Hybrid: Detect critical errors (blocked/rate limit) for immediate retry
                            is_blocked = 'blocked' in err_lower or 'detect' in err_lower
                            is_rate_limit = 'rate limit' in err_lower or 'too many' in err_lower
                            is_critical_error = is_blocked or is_rate_limit
                            
                            is_something_wrong = ("something went wrong logging in" in err_lower) or ("went wrong" in err_lower)
                            
                            # Immediate VPN rotation triggers: Rate limit, too many requests, something went wrong
                            is_immediate_vpn_trigger = is_rate_limit or is_something_wrong
                            
                            # Track accounts during error period (for re-check after VPN rotation)
                            if is_immediate_vpn_trigger and status == "error":
                                with error_period_lock:
                                    if not error_period_active:
                                        error_period_active = True
                                        engine.log(f"⚠️  Error period started: {'Rate limit' if is_rate_limit else 'Something went wrong'} detected")
                                    # Track this account for re-check
                                    error_period_accounts.append({
                                        "email": email,
                                        "password": password,
                                        "original_result": result.copy(),
                                        "original_index": index,
                                        "error_type": "rate_limit" if is_rate_limit else "something_wrong"
                                    })
                                
                                # Trigger immediate VPN rotation
                                if vpn_manager:
                                    with vpn_rotation_lock:
                                        if not vpn_rotation_requested:
                                            vpn_rotation_requested = True
                                            error_reason = "rate limit/too many requests" if is_rate_limit else "something went wrong"
                                            engine.log(f"🔄 VPN rotation triggered IMMEDIATELY: {error_reason} detected")
                                            engine.log(f"📋 Will re-check {len(error_period_accounts)} account(s) processed during error period")
                            is_error_occurred = (
                                ("an error occurred" in err_lower)
                                or ("disable any extensions" in err_lower)
                                or ("try using a different web browser" in err_lower)
                            )
                            
                            # Smart Hybrid: Immediate retry for critical errors (blocked/rate limit)
                            # IMPORTANT: Never queue invalid credentials for retry (they are account-specific, not VPN issues)
                            if is_critical_error and status == "error" and status != "invalid":
                                engine.log(f"🔄 Worker [{worker_id}]: Critical error detected ({'blocked' if is_blocked else 'rate limit'}) for account {index} - attempting immediate retry...")
                                
                                # Close current browser and create fresh one for immediate retry
                                try:
                                    if page_w:
                                        try:
                                            page_w.close()
                                        except:
                                            pass
                                except:
                                    pass
                                try:
                                    if context_w:
                                        try:
                                            context_w.close()
                                        except:
                                            pass
                                except:
                                    pass
                                try:
                                    if browser_w:
                                        try:
                                            browser_w.close()
                                        except:
                                            pass
                                except:
                                    pass
                                
                                try:
                                    engine.log(f"🔧 Worker [{worker_id}]: Opening fresh browser for immediate retry (account {index})...")
                                    browser_w, context_w = engine._launch_browser_and_context_sync(playwright_worker)
                                    page_w = get_or_create_page(context_w)
                                    close_extra_pages(context_w, keep_first=True)
                                    engine.log(f"✅ Worker [{worker_id}]: Fresh browser opened for immediate retry")
                                    
                                    immediate_retry_result = engine.login_to_reddit(
                                        email,
                                        password,
                                        playwright_worker,
                                        first_attempt=False,
                                        reuse_context=context_w,
                                        reuse_page=page_w,
                                    )
                                    
                                    immediate_retry_status = immediate_retry_result.get("status", "").lower()
                                    immediate_retry_err = (immediate_retry_result.get("error_message", "") or "").lower()
                                    immediate_retry_is_blocked = 'blocked' in immediate_retry_err or 'detect' in immediate_retry_err
                                    immediate_retry_is_rate_limit = 'rate limit' in immediate_retry_err or 'too many' in immediate_retry_err
                                    
                                    if immediate_retry_status in ["success", "invalid", "banned", "locked"]:
                                        # Immediate retry succeeded - use this result
                                        result = immediate_retry_result
                                        status = immediate_retry_status
                                        err_lower = immediate_retry_err
                                        engine.log(f"✅ Worker [{worker_id}]: Immediate retry successful for account {index} - Status: {result.get('status')}")
                                        # Don't queue for deferred retry since it succeeded
                                    elif immediate_retry_is_blocked or immediate_retry_is_rate_limit:
                                        # Still blocked/rate limited - queue for deferred retry after VPN rotation
                                        engine.log(f"⚠️  Worker [{worker_id}]: Immediate retry still shows {'blocked' if immediate_retry_is_blocked else 'rate limit'} for account {index} - queuing for deferred retry after VPN rotation")
                                        with critical_error_queue_lock:
                                            # Store original result with verification attempt marker
                                            result["verification_attempts"] = 1
                                            result["needs_deferred_retry"] = True
                                            critical_error_queue.append({
                                                "email": email,
                                                "password": password,
                                                "original_result": result.copy(),
                                                "original_index": index
                                            })
                                        # Keep the failed result for now, will be updated after deferred retry
                                    else:
                                        # Different error - use immediate retry result
                                        result = immediate_retry_result
                                        status = immediate_retry_status
                                        err_lower = immediate_retry_err
                                        engine.log(f"⚠️  Worker [{worker_id}]: Immediate retry shows different error for account {index}: {immediate_retry_err[:50]}")
                                except Exception as immediate_retry_err:
                                    engine.log(f"⚠️  Worker [{worker_id}]: Immediate retry failed for account {index} with exception: {str(immediate_retry_err)}")
                                    # Queue for deferred retry if exception occurred
                                    with critical_error_queue_lock:
                                        result["verification_attempts"] = 1
                                        result["needs_deferred_retry"] = True
                                        critical_error_queue.append({
                                            "email": email,
                                            "password": password,
                                            "original_result": result.copy(),
                                            "original_index": index
                                        })

                            if (is_something_wrong or is_error_occurred) and status == "error":
                                error_type = "an error occurred" if is_error_occurred else "something went wrong"
                                engine.log(f"🔄 Worker retrying {email} due to '{error_type}' error...")
                                
                                # Track retry attempt (before retry)
                                worker_retry_count += 1
                                with completed_lock:
                                    worker_retry_errors[worker_id] = worker_retry_count
                                    batch_retry_error_count += 1
                                
                                # Check for critical error combinations (immediate VPN rotation trigger)
                                is_blocked_error = 'blocked' in err_lower or 'detect' in err_lower
                                is_rate_limit_error = 'rate limit' in err_lower or 'too many' in err_lower
                                
                                # Close current browser and create fresh one for retry
                                engine.log(f"🔧 Worker [{worker_id}]: Closing browser for retry (account {index})...")
                                try:
                                    if page_w:
                                        try:
                                            engine.log(f"  🔧 Closing page for retry...")
                                            page_w.close()
                                            engine.log(f"  ✅ Page closed")
                                        except Exception as e:
                                            engine.log(f"  ⚠️  Error closing page: {str(e)}")
                                except:
                                    pass
                                try:
                                    if context_w:
                                        try:
                                            engine.log(f"  🔧 Closing context for retry...")
                                            context_w.close()
                                            engine.log(f"  ✅ Context closed")
                                        except Exception as e:
                                            engine.log(f"  ⚠️  Error closing context: {str(e)}")
                                except:
                                    pass
                                try:
                                    if browser_w:
                                        try:
                                            engine.log(f"  🔧 Closing browser for retry...")
                                            browser_w.close()
                                            engine.log(f"  ✅ Browser closed")
                                        except Exception as e:
                                            engine.log(f"  ⚠️  Error closing browser: {str(e)}")
                                except:
                                    pass
                                try:
                                    engine.log(f"🔧 Worker [{worker_id}]: Opening fresh browser for retry (account {index})...")
                                    browser_w, context_w = engine._launch_browser_and_context_sync(playwright_worker)
                                    engine.log(f"✅ Worker [{worker_id}]: Fresh browser opened for retry")
                                    engine.log(f"🔧 Worker [{worker_id}]: Getting page for retry...")
                                    page_w = get_or_create_page(context_w)
                                    close_extra_pages(context_w, keep_first=True)
                                    engine.log(f"✅ Worker [{worker_id}]: Page ready for retry")
                                    retry_result = engine.login_to_reddit(
                                        email,
                                        password,
                                        playwright_worker,
                                        first_attempt=False,
                                        reuse_context=context_w,
                                        reuse_page=page_w,
                                    )
                                    retry_status = retry_result.get("status", "").lower()
                                    retry_err_lower = (retry_result.get("error_message", "") or "").lower()
                                    
                                    if retry_status in ["success", "invalid", "banned", "locked"]:
                                        result = retry_result
                                        if retry_status == "success":
                                            engine.log(f"✅ Worker retry successful - Status: {result.get('status')}")
                                            # Reset consecutive failures on success
                                            worker_consecutive_retry_failures = 0
                                            with completed_lock:
                                                consecutive_retry_failures = 0
                                        else:
                                            engine.log(f"✅ Worker retry completed - Status: {result.get('status')} (not a VPN issue)")
                                            # For invalid/banned/locked - not VPN issues, reset counters
                                            worker_consecutive_retry_failures = 0
                                        # Update status and error message for browser restart check below
                                        status = retry_status
                                        err_lower = retry_err_lower
                                    else:
                                        # Retry still failed - this indicates potential VPN issue
                                        engine.log(f"⚠️  Worker retry still shows error: {retry_result.get('error_message', 'Unknown')}")
                                        worker_consecutive_retry_failures += 1
                                        with completed_lock:
                                            consecutive_retry_failures += 1
                                        
                                        # Check for VPN rotation triggers (Smart Hybrid Strategy)
                                        # Rule 1: Critical errors (Blocked/RateLimit + Retry Failure) = Immediate VPN rotation
                                        retry_is_blocked = 'blocked' in retry_err_lower or 'detect' in retry_err_lower
                                        retry_is_rate_limit = 'rate limit' in retry_err_lower or 'too many' in retry_err_lower
                                        
                                        # Rule 2: Worker has 2+ retry failures (worker-level pattern)
                                        # Rule 3: 3+ consecutive retry failures (strong indicator)
                                        # Rule 4: Batch has 2+ retry errors from different workers (batch-level pattern)
                                        
                                        should_rotate_vpn_now = False
                                        rotation_reason = ""
                                        
                                        if retry_is_blocked or retry_is_rate_limit:
                                            # Rule 1: Critical error - immediate rotation
                                            should_rotate_vpn_now = True
                                            rotation_reason = "critical error (blocked/rate-limit + retry failed)"
                                        elif worker_retry_count >= 2:
                                            # Rule 2: Worker pattern - 2+ retry failures in same worker
                                            should_rotate_vpn_now = True
                                            rotation_reason = f"worker pattern (2+ retry errors in worker [{worker_id}])"
                                        elif consecutive_retry_failures >= 3:
                                            # Rule 3: Consecutive failures - strong VPN issue indicator
                                            should_rotate_vpn_now = True
                                            rotation_reason = f"consecutive failures (3+ consecutive retry failures)"
                                        elif batch_retry_error_count >= 2 and len(worker_retry_errors) >= 2:
                                            # Rule 4: Batch pattern - 2+ retry errors across multiple workers
                                            should_rotate_vpn_now = True
                                            rotation_reason = f"batch pattern (2+ retry errors from {len(worker_retry_errors)} workers)"
                                        
                                        # Trigger VPN rotation if needed (thread-safe)
                                        if should_rotate_vpn_now and vpn_manager:
                                            with vpn_rotation_lock:
                                                if not vpn_rotation_requested:
                                                    vpn_rotation_requested = True
                                                    engine.log(f"🔄 VPN rotation triggered: {rotation_reason}")
                                                    # Request VPN rotation (will execute after current batch or immediately if critical)
                                                    if retry_is_blocked or retry_is_rate_limit:
                                                        # Critical error - mark for immediate rotation after this batch
                                                        engine.log(f"⚠️  Critical VPN issue detected - rotation will happen after current batch")
                                        
                                        # Keep the fresh browser for next account, don't close it
                                        # Browser will be reused for next account in chunk
                                except Exception as retry_err:
                                    engine.log(f"⚠️  Worker retry failed: {str(retry_err)}")
                                    worker_consecutive_retry_failures += 1
                                    with completed_lock:
                                        consecutive_retry_failures += 1

                            # IMPORTANT: Never trigger VPN rotation for invalid credentials
                            # Invalid credentials are account-specific, not VPN issues
                            if status == 'invalid':
                                # Reset retry counters for invalid credentials (not VPN related)
                                worker_retry_count = 0
                                worker_consecutive_retry_failures = 0
                                with completed_lock:
                                    if worker_id in worker_retry_errors:
                                        worker_retry_errors[worker_id] = 0
                            
                            ip, country, location = get_ip_info()
                            result["ip_address"] = ip
                            result["country"] = country
                            result["location"] = location
                            with completed_lock:
                                batch_results.append(result)
                                results.append(result)
                                # Track accounts processed for VPN rotation
                                accounts_processed_since_vpn_change += 1
                                
                                # Track accounts during error period (if error period is active)
                                if error_period_active:
                                    with error_period_lock:
                                        # Add to error period accounts if not already added
                                        if not any(acc["email"] == email for acc in error_period_accounts):
                                            error_period_accounts.append({
                                                "email": email,
                                                "password": password,
                                                "original_result": result.copy(),
                                                "original_index": index,
                                                "error_type": "error_period"
                                            })
                                
                                # Account-based VPN rotation: Rotate after N accounts
                                if vpn_rotate_after_accounts > 0 and accounts_processed_since_vpn_change >= vpn_rotate_after_accounts:
                                    if vpn_manager:
                                        with vpn_rotation_lock:
                                            if not vpn_rotation_requested:
                                                vpn_rotation_requested = True
                                                engine.log(f"🔄 VPN rotation triggered: Account-based rotation ({accounts_processed_since_vpn_change} accounts processed since last VPN change)")
                                                engine.log(f"📊 Rotation threshold: Every {vpn_rotate_after_accounts} accounts")

                            if engine.result_callback:
                                try:
                                    engine.result_callback(result)
                                except Exception:
                                    pass

                            try:
                                engine.db.log_account_result(
                                    engine.session_id,
                                    email,
                                    result.get("status"),
                                    password=password,
                                    username=result.get("username"),
                                    karma=result.get("karma"),
                                    error_message=result.get("error_message"),
                                )
                            except Exception as db_e:
                                engine.log(f"Database log error for {email}: {str(db_e)}")

                            status = (result.get("status") or "").lower()
                            if status == "success":
                                engine.log(f"✅ Login successful: {email}")
                            elif status == "locked":
                                engine.log(
                                    f"⚠️  Account locked (password reset required): {email} | Username: {result.get('username')} | Karma: {result.get('karma')}"
                                )
                            elif status == "invalid":
                                engine.log(f"❌ Wrong password: {email}")
                            elif status == "banned":
                                engine.log(f"❌❌❌ Banned: {email}")
                            elif "blocked" in (result.get("error_message", "").lower()) or "detect" in (result.get("error_message", "").lower()):
                                engine.log(f"❌Check failed>>>Reddit detect & Blocked❌: {email}")
                            else:
                                emsg_lower = (result.get("error_message", "").lower())
                                if 'reset' in emsg_lower and 'password' in emsg_lower:
                                    engine.log(f"⚠️  Account locked (password reset required): {email}")
                                elif 'locked' in emsg_lower or 'unusual activity' in emsg_lower:
                                    engine.log(f"⚠️  Account locked due to unusual activity: {email}")
                                else:
                                    engine.log(f"❌ Failed to login (Unclear reason): {email}")

                            # Only restart browser for session-risk issues, NOT for invalid credentials
                            # Invalid credentials should reuse the same page/browser
                            should_restart_browser = False
                            if status != 'invalid':
                                # Check for session-risk issues that require browser restart
                                if (
                                    status == 'success'
                                    or status in ['banned', 'locked']
                                    or ('blocked' in err_lower)
                                    or ('rate limit' in err_lower)
                                    or ('too many' in err_lower)
                                    or (status == 'error' and (
                                        ('reset' in err_lower and 'password' in err_lower)
                                        or ('locked' in err_lower)
                                        or ('unusual activity' in err_lower)
                                        or ('blocked' in err_lower)
                                        or ('rate limit' in err_lower)
                                    ))
                                ):
                                    should_restart_browser = True
                            
                            # For work-stealing, we don't know if it's the last account, so always restart if needed
                            # (Workers will continue until queue is empty)
                            
                            if should_restart_browser or not REUSE_BROWSER_FOR_BATCH:
                                reason = f"status: {status}" if should_restart_browser else "REUSE_BROWSER_FOR_BATCH=False"
                                engine.log(f"🔁 Worker [{worker_id}]: Restarting browser ({reason})...")
                                try:
                                    if page_w:
                                        try:
                                            engine.log(f"  🔧 Closing page...")
                                            page_w.close()
                                            engine.log(f"  ✅ Page closed")
                                        except Exception as e:
                                            engine.log(f"  ⚠️  Error closing page: {str(e)}")
                                except:
                                    pass
                                try:
                                    if context_w:
                                        try:
                                            engine.log(f"  🔧 Closing context...")
                                            context_w.close()
                                            engine.log(f"  ✅ Context closed")
                                        except Exception as e:
                                            engine.log(f"  ⚠️  Error closing context: {str(e)}")
                                except:
                                    pass
                                try:
                                    if browser_w:
                                        try:
                                            engine.log(f"  🔧 Closing browser...")
                                            browser_w.close()
                                            engine.log(f"  ✅ Browser closed")
                                        except Exception as e:
                                            engine.log(f"  ⚠️  Error closing browser: {str(e)}")
                                except:
                                    pass
                                
                                browser_w, context_w, page_w = None, None, None
                                # Browser will be recreated at the start of next iteration
                            else:
                                if status == 'invalid':
                                    engine.log(f"♻️  Worker [{worker_id}]: Keeping browser open for next account (invalid credentials - will reuse)")
                                else:
                                    engine.log(f"♻️  Worker [{worker_id}]: Keeping browser open for next account (no restart needed)")

                            if engine.progress_callback:
                                try:
                                    results_count = len(results)
                                    success_count = sum(1 for r in results if (r.get("status") or "").lower() == "success")
                                    invalid_count = sum(1 for r in results if (r.get("status") or "").lower() == "invalid")
                                    banned_count = sum(1 for r in results if (r.get("status") or "").lower() == "banned")
                                    error_count = sum(1 for r in results if (r.get("status") or "").lower() == "error")
                                    engine.progress_callback(
                                        {
                                            "total": results_count,
                                            "success": success_count,
                                            "invalid": invalid_count,
                                            "banned": banned_count,
                                            "error": error_count,
                                        }
                                    )
                                except:
                                    pass
                        except Exception as account_err:
                            ip, country, location = get_ip_info()
                            error_result = {
                                "email": email,
                                "password": password,
                                "status": "error",
                                "username": None,
                                "karma": None,
                                "error_message": f"Thread error: {str(account_err)}",
                                "ip_address": ip,
                                "country": country,
                                "location": location,
                            }
                            with completed_lock:
                                batch_results.append(error_result)
                                results.append(error_result)
                            engine.log(f"⚠️  Worker [{worker_id}]: Error processing account {index}: {str(account_err)}")
                            # Continue to next account in queue
                    
                    # End of work-stealing loop
                    engine.log(f"✅ Worker [{worker_id}]: Finished processing {accounts_processed} account(s), queue is empty")
                    
            except Exception as e_worker:
                engine.log(f"⚠️  WORKER [{worker_id}] ERROR: {str(e_worker)}")
            finally:
                engine.log(f"🧹 Worker [{worker_id}]: Cleaning up browser resources...")
                try:
                    if context_w and browser_w is None:
                        try:
                            engine.log(f"  🔧 Closing context (browser already closed)...")
                            context_w.close()
                            engine.log(f"  ✅ Context closed")
                        except Exception as e:
                            engine.log(f"  ⚠️  Error closing context: {str(e)}")
                except:
                    pass
                try:
                    if browser_w:
                        try:
                            engine.log(f"  🔧 Closing browser...")
                            browser_w.close()
                            engine.log(f"  ✅ Browser closed successfully")
                        except Exception as e:
                            engine.log(f"  ⚠️  Error closing browser: {str(e)}")
                except:
                    pass
                engine.log(f"✅ Worker [{worker_id}]: Cleanup completed")

        # Work-Stealing Queue Approach: Best Practice for Maximum Browser Utilization
        total_accounts = len(batch_credentials)
        
        # Edge case: Empty batch
        if total_accounts == 0:
            engine.log("⚠️  No accounts in batch, skipping...")
            continue
        
        # Edge case: Invalid parallel_browsers
        if parallel_browsers < 1:
            engine.log(f"⚠️  Invalid parallel_browsers={parallel_browsers}, using 1 instead")
            parallel_browsers = 1
        
        # Work-Stealing Queue: Create shared queue with all accounts
        # Each account is stored with its index for tracking
        work_queue = []
        queue_lock = threading.Lock()
        account_counter = batch_start  # Track global account index
        
        for idx, (email, password) in enumerate(batch_credentials):
            work_queue.append({
                "email": email,
                "password": password,
                "index": batch_start + idx
            })
        
        # Determine number of workers (use all available browsers)
        num_workers = min(parallel_browsers, total_accounts) if parallel_browsers > 1 else 1
        
        if parallel_browsers == 1:
            engine.log(f"📦 Work-Stealing Queue: 1 worker will process {total_accounts} account(s) (single browser mode)")
        else:
            engine.log(f"📦 Work-Stealing Queue: {num_workers} workers will process {total_accounts} account(s) dynamically")
            engine.log(f"✅ All {num_workers} browsers will stay active until queue is empty (no early closure)")

        # Launch workers with work-stealing queue
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(process_worker_stealing, worker_id, work_queue, queue_lock, account_counter) 
                      for worker_id in range(num_workers)]
            engine.log(f"✅ Launched {len(futures)} worker(s) with work-stealing queue")
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    engine.log(f"⚠️  EXCEPTION in worker: {str(e)}")

        engine.log(f"\n✓ Batch {batch_num} completed: {len(batch_results)} accounts processed")

        batch_failures = sum(1 for r in batch_results if r.get("status", "").lower() in ["banned", "error"])
        batch_blocked = any(("blocked" in (r.get("error_message", "") or "").lower()) or ("detect" in (r.get("error_message", "") or "").lower()) for r in batch_results)
        batch_rate_limit = any(("rate limit" in (r.get("error_message", "") or "").lower()) or ("too many" in (r.get("error_message", "") or "").lower()) for r in batch_results)
        batch_something_wrong = any(
            ("something went wrong logging in" in (r.get("error_message", "") or "").lower())
            or ("went wrong" in (r.get("error_message", "") or "").lower())
            or ("an error occurred" in (r.get("error_message", "") or "").lower())
            or ("disable any extensions" in (r.get("error_message", "") or "").lower())
            or ("try using a different web browser" in (r.get("error_message", "") or "").lower())
            for r in batch_results
        )
        
        # Check if error period is still active (rate limit/too many requests detected during processing)
        with error_period_lock:
            if error_period_active and len(error_period_accounts) > 0:
                engine.log(f"⚠️  Error period detected: {len(error_period_accounts)} account(s) processed during error period will be re-checked")

        if batch_failures > 0:
            engine.consecutive_failures += batch_failures
        else:
            if any(r.get("status", "").lower() == "success" for r in batch_results):
                engine.consecutive_failures = 0

        # Smart Hybrid VPN Rotation Strategy
        # Include retry error patterns in VPN rotation decision
        # Exclude invalid credentials from VPN rotation triggers
        has_retry_error_pattern = (
            batch_retry_error_count >= 2  # 2+ retry errors in batch
            or consecutive_retry_failures >= 3  # 3+ consecutive retry failures
            or len([count for count in worker_retry_errors.values() if count >= 2]) >= 1  # Worker with 2+ retry errors
        )
        
        should_change_vpn = (
            batch_blocked
            or batch_rate_limit
            or batch_something_wrong
            or has_retry_error_pattern  # Smart Hybrid: Include retry error patterns
            or vpn_rotation_requested  # Immediate rotation requested (critical errors or account-based)
            or (engine.consecutive_failures >= engine.max_failures_before_vpn_change)
        )

        if should_change_vpn and vpn_manager:
            # Build detailed reason for VPN rotation
            reasons = []
            if batch_blocked or batch_rate_limit:
                reasons.append("blocked/rate-limit")
            if vpn_rotation_requested:
                if vpn_rotate_after_accounts > 0 and accounts_processed_since_vpn_change >= vpn_rotate_after_accounts:
                    reasons.append(f"account-based rotation ({accounts_processed_since_vpn_change}/{vpn_rotate_after_accounts} accounts)")
                else:
                    reasons.append("critical error detected")
            if has_retry_error_pattern:
                if batch_retry_error_count >= 2:
                    reasons.append(f"retry error pattern ({batch_retry_error_count} retry errors)")
                if consecutive_retry_failures >= 3:
                    reasons.append(f"consecutive retry failures ({consecutive_retry_failures})")
            if engine.consecutive_failures >= engine.max_failures_before_vpn_change:
                reasons.append(f"consecutive failures>={engine.max_failures_before_vpn_change}")
            
            reason = " | ".join(reasons) if reasons else f"failures>={engine.max_failures_before_vpn_change}"
            engine.last_vpn_reason = reason
            engine.vpn_rotations += 1
            engine.log(f"🔄 Changing VPN ({reason}). Rotations: {engine.vpn_rotations}")
            
            # Check stop before VPN operations
            if engine.should_stop:
                engine.log("⏹️ Stop requested during VPN rotation - aborting VPN change")
                return
            
            engine.log("🚫 Disconnecting current ExpressVPN connection...")
            engine._run_async(vpn_manager.disconnect())
            if interruptible_sleep(engine, 0.5):
                engine.log("⏹️ Stop requested during VPN disconnect - aborting")
                return
            engine.log("✅ Disconnected ExpressVPN")
            
            # Check stop before connecting
            if engine.should_stop:
                engine.log("⏹️ Stop requested before VPN connect - aborting")
                return

            engine.log("🌐 Connecting to new ExpressVPN server...")
            try:
                from config import (
                    VPN_PREFERRED_COUNTRIES,
                    VPN_AVOID_COUNTRIES,
                    VPN_LOCATION_COOLDOWN_SECONDS,
                    VPN_LOCATION_MAX_TRIES_PER_ROTATION,
                )
            except Exception:
                VPN_PREFERRED_COUNTRIES, VPN_AVOID_COUNTRIES = [], []
                VPN_LOCATION_COOLDOWN_SECONDS = 900
                VPN_LOCATION_MAX_TRIES_PER_ROTATION = 10
            success, msg = engine._run_async(vpn_manager.connect_with_strategy(
                preferred=VPN_PREFERRED_COUNTRIES,
                avoid=VPN_AVOID_COUNTRIES,
                cooldown_seconds=int(VPN_LOCATION_COOLDOWN_SECONDS),
                max_candidates=int(VPN_LOCATION_MAX_TRIES_PER_ROTATION),
            ))
            if success:
                if interruptible_sleep(engine, 2.0):
                    engine.log("⏹️ Stop requested during VPN stabilization - aborting")
                    return
                is_connected, new_vpn_location = engine._run_async(vpn_manager.get_status())
                if is_connected:
                    engine.current_vpn_location = new_vpn_location
                    engine.log(f"✅ Connected to new server: {new_vpn_location}")
                    engine.log("⏳ Please wait for server location to stabilize...")
                    if interruptible_sleep(engine, 2.0):
                        engine.log("⏹️ Stop requested during VPN stabilization - aborting")
                        return
                    engine.consecutive_failures = 0
                    # Reset retry tracking after successful VPN rotation
                    with completed_lock:
                        worker_retry_errors.clear()
                        batch_retry_error_count = 0
                        consecutive_retry_failures = 0
                        # Reset account counter for account-based rotation
                        accounts_processed_since_vpn_change = 0
                    vpn_rotation_requested = False
                    engine.log(f"📊 Account-based rotation counter reset - will rotate again after {vpn_rotate_after_accounts} accounts")
                    if engine.progress_callback:
                        try:
                            engine.progress_callback(
                                {
                                    "vpn_rotations": engine.vpn_rotations,
                                    "last_vpn_reason": engine.last_vpn_reason,
                                }
                            )
                        except:
                            pass
                    
                    # Smart Hybrid: Parallel Deferred Retry for queued critical errors after VPN rotation
                    # Combine critical_error_queue and error_period_accounts for re-checking
                    all_accounts_to_recheck = []
                    with critical_error_queue_lock:
                        all_accounts_to_recheck.extend(critical_error_queue)
                    with error_period_lock:
                        all_accounts_to_recheck.extend(error_period_accounts)
                    
                    if all_accounts_to_recheck and not engine.should_stop:
                        engine.log(f"\n🔄 Parallel Deferred Retry: Verifying {len(all_accounts_to_recheck)} account(s) after VPN rotation...")
                        engine.log(f"🌐 Using new VPN: {new_vpn_location}")
                        engine.log(f"🚀 Using {min(parallel_browsers, len(all_accounts_to_recheck))} parallel browsers for fast re-checking")
                        
                        # Create work queue for parallel deferred retry
                        deferred_work_queue = []
                        deferred_queue_lock = threading.Lock()
                        
                        for queued_account in all_accounts_to_recheck:
                            deferred_work_queue.append({
                                "email": queued_account["email"],
                                "password": queued_account["password"],
                                "index": queued_account.get("original_index", 0),
                                "original_result": queued_account.get("original_result", {})
                            })
                        
                        deferred_results = []
                        deferred_completed_lock = threading.Lock()
                        
                        def process_deferred_account(worker_id, deferred_queue, deferred_lock):
                            """Process deferred retry account using parallel browser"""
                            nonlocal deferred_results
                            accounts_processed = 0
                            
                            try:
                                with sync_playwright() as deferred_playwright:
                                    deferred_browser = None
                                    deferred_context = None
                                    deferred_page = None
                                    
                                    try:
                                        deferred_browser, deferred_context = engine._launch_browser_and_context_sync(deferred_playwright)
                                        deferred_page = deferred_context.new_page()
                                        engine.log(f"✅ Worker [{worker_id}]: Browser opened for deferred retry")
                                    except Exception as init_err:
                                        engine.log(f"⚠️  Worker [{worker_id}]: Failed to open browser for deferred retry: {str(init_err)}")
                                        return
                                    
                                    # Work-stealing loop for deferred retry
                                    while True:
                                        if engine.should_stop:
                                            engine.log(f"⏹️ Worker [{worker_id}]: Stop requested in deferred retry loop")
                                            # Close browser immediately
                                            try:
                                                if deferred_page:
                                                    try:
                                                        deferred_page.close()
                                                    except:
                                                        pass
                                            except:
                                                pass
                                            try:
                                                if deferred_context:
                                                    try:
                                                        deferred_context.close()
                                                    except:
                                                        pass
                                            except:
                                                pass
                                            try:
                                                if deferred_browser:
                                                    try:
                                                        deferred_browser.close()
                                                    except:
                                                        pass
                                            except:
                                                pass
                                            break
                                        
                                        account_data = None
                                        with deferred_lock:
                                            if len(deferred_queue) == 0:
                                                break
                                            account_data = deferred_queue.pop(0)
                                        
                                        if account_data is None:
                                            break
                                        
                                        queued_email = account_data["email"]
                                        queued_password = account_data["password"]
                                        queued_index = account_data["index"]
                                        
                                        # Check stop before processing deferred account
                                        if engine.should_stop:
                                            engine.log(f"⏹️ Worker [{worker_id}]: Stop requested before deferred retry for account {queued_index}")
                                            # Return to queue
                                            with deferred_lock:
                                                deferred_queue.insert(0, account_data)
                                            break
                                        
                                        accounts_processed += 1
                                        
                                        try:
                                            engine.log(f"🔄 Worker [{worker_id}]: Deferred retry [{accounts_processed}] for account {queued_index}: {queued_email}")
                                            
                                            # Check stop before login_to_reddit
                                            if engine.should_stop:
                                                engine.log(f"⏹️ Worker [{worker_id}]: Stop requested before deferred login_to_reddit for account {queued_index}")
                                                with deferred_lock:
                                                    deferred_queue.insert(0, account_data)
                                                break
                                            
                                            deferred_retry_result = engine.login_to_reddit(
                                                queued_email,
                                                queued_password,
                                                deferred_playwright,
                                                first_attempt=False,
                                                reuse_context=deferred_context,
                                                reuse_page=deferred_page,
                                            )
                                            
                                            # Check stop after login_to_reddit
                                            if engine.should_stop:
                                                engine.log(f"⏹️ Worker [{worker_id}]: Stop requested after deferred login_to_reddit for account {queued_index}")
                                                with deferred_completed_lock:
                                                    deferred_results.append(deferred_retry_result)
                                                break
                                            
                                            deferred_status = deferred_retry_result.get("status", "").lower()
                                            deferred_err = (deferred_retry_result.get("error_message", "") or "").lower()
                                            
                                            if deferred_status in ["success", "invalid", "banned", "locked"]:
                                                engine.log(f"✅ Worker [{worker_id}]: Deferred retry successful for {queued_email} - Status: {deferred_status}")
                                                # Update result in results list
                                                with deferred_completed_lock:
                                                    for res in results:
                                                        if res.get("email") == queued_email:
                                                            res.update(deferred_retry_result)
                                                            res["verification_attempts"] = 2
                                                            res["needs_deferred_retry"] = False
                                                            break
                                                    for res in batch_results:
                                                        if res.get("email") == queued_email:
                                                            res.update(deferred_retry_result)
                                                            res["verification_attempts"] = 2
                                                            res["needs_deferred_retry"] = False
                                                            break
                                            else:
                                                engine.log(f"⚠️  Worker [{worker_id}]: Deferred retry still shows error for {queued_email}: {deferred_err[:50]}")
                                                with deferred_completed_lock:
                                                    for res in results:
                                                        if res.get("email") == queued_email:
                                                            res["verification_attempts"] = 2
                                                            res["needs_deferred_retry"] = False
                                                            res["deferred_retry_failed"] = True
                                                            break
                                        
                                        except Exception as deferred_err:
                                            engine.log(f"⚠️  Worker [{worker_id}]: Deferred retry exception for {queued_email}: {str(deferred_err)}")
                                    
                                    # Close browser
                                    if deferred_browser or deferred_context:
                                        try:
                                            engine._close_context_browser(deferred_browser, deferred_context)
                                        except:
                                            pass
                                    
                                    engine.log(f"✅ Worker [{worker_id}]: Deferred retry completed - {accounts_processed} account(s) processed")
                            
                            except Exception as worker_err:
                                engine.log(f"⚠️  Worker [{worker_id}]: Deferred retry worker error: {str(worker_err)}")
                        
                        # Launch parallel workers for deferred retry
                        num_deferred_workers = min(parallel_browsers, len(deferred_work_queue))
                        engine.log(f"🚀 Launching {num_deferred_workers} parallel browser(s) for deferred retry...")
                        
                        with ThreadPoolExecutor(max_workers=num_deferred_workers) as deferred_executor:
                            deferred_futures = [deferred_executor.submit(process_deferred_account, worker_id, deferred_work_queue, deferred_queue_lock) 
                                               for worker_id in range(num_deferred_workers)]
                            for f in as_completed(deferred_futures):
                                try:
                                    f.result()
                                except Exception as e:
                                    engine.log(f"⚠️  EXCEPTION in deferred retry worker: {str(e)}")
                        
                        engine.log(f"✅ Parallel deferred retry completed - {len(all_accounts_to_recheck)} account(s) verified")
                        
                        # Clear queues after processing
                        with critical_error_queue_lock:
                            critical_error_queue.clear()
                        with error_period_lock:
                            error_period_accounts.clear()
                            error_period_active = False

    return results