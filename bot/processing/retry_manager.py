"""
Retry manager - handles final retry attempts for transient errors.
"""
import time
from typing import List, Dict, Tuple

from playwright.sync_api import sync_playwright


def perform_final_retries(engine, results: List[Dict]) -> List[Dict]:
    """
    Retry accounts with retryable errors (e.g., 'something went wrong') up to 3 times.

    Args:
        engine: RedditBotEngine instance
        results: List of existing results to examine and modify

    Returns:
        Updated list of results (same list instance, modified in-place)
    """
    retry_error_accounts: List[Tuple[int, Dict]] = []
    for i, result in enumerate(results):
        status = result.get("status", "").lower()
        err_msg = (result.get("error_message", "") or "").lower()
        should_retry = status == "error" and any(
            marker in err_msg
            for marker in [
                "something went wrong logging in",
                "went wrong",
                "an error occurred",
                "disable any extensions",
                "try using a different web browser",
            ]
        )
        if should_retry:
            retry_error_accounts.append((i, result))

    if not retry_error_accounts or engine.should_stop:
        return results

    engine.log(f"\n🔄 Final retry pass: Retrying {len(retry_error_accounts)} account(s) with retryable errors (3 attempts with VPN rotation)...")

    with sync_playwright() as playwright:
        for idx, (original_idx, failed_result) in enumerate(retry_error_accounts):
            if engine.should_stop:
                break
            email = failed_result.get("email")
            password = failed_result.get("password")
            if not email or not password:
                continue

            engine.log(f"\n🔄 Final retry [{idx+1}/{len(retry_error_accounts)}]: {email}")
            max_retries = 3
            retry_successful = False

            for retry_attempt in range(1, max_retries + 1):
                if retry_successful or engine.should_stop:
                    break

                engine.log(f"  Attempt {retry_attempt}/{max_retries}...")

                if retry_attempt > 1 and engine.vpn_manager:
                    engine.log(f"  🌐 Changing VPN for attempt {retry_attempt}...")
                    try:
                        if 'browser' in locals():
                            engine._close_context_browser(browser, context)
                        engine.vpn_manager.disconnect()
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

                    success, msg = engine.vpn_manager.connect_with_strategy(
                        preferred=VPN_PREFERRED_COUNTRIES,
                        avoid=VPN_AVOID_COUNTRIES,
                        cooldown_seconds=int(VPN_LOCATION_COOLDOWN_SECONDS),
                        max_candidates=int(VPN_LOCATION_MAX_TRIES_PER_ROTATION),
                    )
                    if success:
                        time.sleep(2)
                        is_connected, vpn_location = engine.vpn_manager.get_status()
                        if is_connected:
                            engine.current_vpn_location = vpn_location
                            engine.log(f"  ✅ Connected to VPN: {vpn_location}")
                            time.sleep(2)

                try:
                    browser, context = engine._launch_browser_and_context(playwright)
                    pages = getattr(context, "pages", [])
                    page = pages[0] if pages else context.new_page()
                    for p in pages[1:]:
                        try:
                            p.close()
                        except:
                            pass

                    retry_result = engine.login_to_reddit(
                        email,
                        password,
                        playwright,
                        first_attempt=False,
                        reuse_context=context,
                        reuse_page=page,
                    )

                    if retry_result.get("status") in ["success", "invalid", "banned", "locked"]:
                        if "ip_address" in failed_result:
                            retry_result["ip_address"] = failed_result.get("ip_address")
                        if "country" in failed_result:
                            retry_result["country"] = failed_result.get("country")
                        if "location" in failed_result:
                            retry_result["location"] = failed_result.get("location")

                        results[original_idx] = retry_result
                        engine.log(f"  ✅ Attempt {retry_attempt} successful - Status: {retry_result.get('status')}")
                        retry_successful = True
                        engine._close_context_browser(browser, context)
                        break
                    else:
                        if retry_attempt < max_retries:
                            engine.log(f"  ⚠️  Attempt {retry_attempt} failed, trying again...")
                        else:
                            engine.log(f"  ⚠️  All {max_retries} attempts failed: {retry_result.get('error_message', 'Unknown')}")

                    engine._close_context_browser(browser, context)
                    if retry_attempt < max_retries:
                        time.sleep(1)
                except Exception as retry_err:
                    engine.log(f"  ⚠️  Attempt {retry_attempt} exception: {str(retry_err)}")
                    if retry_attempt < max_retries:
                        time.sleep(1)

            if idx < len(retry_error_accounts) - 1:
                time.sleep(1)

    engine.log("✅ Final retry pass completed")
    return results

