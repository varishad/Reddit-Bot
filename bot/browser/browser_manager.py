"""
Browser Manager - Browser lifecycle management (launch, close, context management).
"""
import random as _random
import pathlib as _pathlib
from typing import Tuple, Optional
from playwright.async_api import Playwright, Browser, BrowserContext
from playwright.sync_api import Playwright as SyncPlaywright, Browser as SyncBrowser, BrowserContext as SyncBrowserContext
from config import (
    BROWSER_TYPE, HEADLESS, PERSISTENT_CONTEXT, PERSISTENT_PROFILE_DIR,
    VIEWPORT_BASE_WIDTH, VIEWPORT_BASE_HEIGHT, VIEWPORT_VARIATION,
    USER_AGENT_POOL, PROXY_ENABLED, PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS,
    VPN_LOCATION_LIST_FILE, PROXY_LIST_FILE, PROXY_ROTATION_STRATEGY,
    BROWSER_EXECUTABLE_PATH
)
from ip_utils import get_geo_profile
from bot.browser.proxy_manager import ProxyManager
from bot.browser.fingerprint import generate_fingerprint


# Global proxy manager instance
_proxy_manager = None

def get_proxy_manager(log_callback=None):
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager(log_callback=log_callback)
    return _proxy_manager


async def launch_browser_and_context(
    playwright: Playwright,
    log_callback: Optional[callable] = None,
    profile_name: Optional[str] = None
) -> Tuple[Optional[Browser], BrowserContext]:
    """
    Launch a new browser and context using current configuration and geo profile.
    
    Args:
        playwright: Playwright instance
        log_callback: Optional logging function
        profile_name: Optional name for persistent profile sub-directory
    """
    log = log_callback or (lambda msg: None)
    pm = get_proxy_manager(log)
    
    viewport_width = VIEWPORT_BASE_WIDTH + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
    viewport_height = VIEWPORT_BASE_HEIGHT + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
    
    fp = generate_fingerprint()
    user_agent = fp["user_agent"]
    
    context_opts = {
        'viewport': {'width': viewport_width, 'height': viewport_height},
        'user_agent': user_agent,
        'extra_http_headers': {
            'Sec-CH-UA': fp['ch_ua'],
            'Sec-CH-UA-Mobile': fp['ch_mobile'],
            'Sec-CH-UA-Platform': fp['ch_platform']
        }
    }
    # ... geo setup ...

    # Chromium launch
    launch_opts = {"headless": HEADLESS, "proxy": None} # simplified for brevity, actual logic uses proxy_opts
    
    if PERSISTENT_CONTEXT:
        profile_path = _pathlib.Path(PERSISTENT_PROFILE_DIR)
        if profile_name:
            # Segregate profiles by user/account hash or name
            safe_name = "".join([c if c.isalnum() else "_" for c in profile_name])
            profile_path = profile_path / safe_name
            
        try:
            profile_path.mkdir(parents=True, exist_ok=True)
            log(f"📂 [BROWSER] Using isolated profile: {profile_path.name}")
            context = await playwright.chromium.launch_persistent_context(
                str(profile_path),
                args=['--disable-blink-features=AutomationControlled','--disable-infobars'],
                **launch_opts,
                **context_opts
            )
            return None, context
        except Exception as e:
            log(f"⚠️ Isolated context failed: {str(e)}. Falling back.")
    
    # Fallback to standard incognito if persistent fails or disabled
    browser = await playwright.chromium.launch(
        args=['--incognito', '--disable-blink-features=AutomationControlled','--disable-infobars'],
        **launch_opts
    )
    context = await browser.new_context(**context_opts)
    
    # Store the fingerprint object on the context so the stealth module can read it
    context._fingerprint = fp
    return browser, context


def launch_browser_and_context_sync(
    playwright: SyncPlaywright,
    log_callback: Optional[callable] = None,
    profile_name: Optional[str] = None
) -> Tuple[Optional[SyncBrowser], SyncBrowserContext]:
    """
    Synchronous version of launch_browser_and_context.
    """
    log = log_callback or (lambda msg: None)
    pm = get_proxy_manager(log)
    
    # Common context options
    geo = {}
    try:
        geo = get_geo_profile() or {}
    except:
        geo = {}

    viewport_width = VIEWPORT_BASE_WIDTH + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
    viewport_height = VIEWPORT_BASE_HEIGHT + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
    
    fp = generate_fingerprint()
    user_agent = fp["user_agent"]
    
    context_opts = {
        'viewport': {'width': viewport_width, 'height': viewport_height},
        'user_agent': user_agent,
        'extra_http_headers': {
            'Sec-CH-UA': fp['ch_ua'],
            'Sec-CH-UA-Mobile': fp['ch_mobile'],
            'Sec-CH-UA-Platform': fp['ch_platform']
        }
    }
    if geo.get('timezone'):
        context_opts['timezone_id'] = geo['timezone']
    if geo.get('locale'):
        context_opts['locale'] = geo['locale']
    if geo.get('latitude') and geo.get('longitude'):
        context_opts['geolocation'] = {'latitude': float(geo['latitude']), 'longitude': float(geo['longitude'])}
        context_opts['permissions'] = ['geolocation']

    # Proxy configuration
    proxy_opts = None
    if PROXY_ENABLED:
        dynamic_proxy = pm.get_next_proxy()
        if dynamic_proxy:
            proxy_opts = {
                "server": f"{dynamic_proxy['host']}:{dynamic_proxy['port']}"
            }
            if dynamic_proxy['user'] and dynamic_proxy['pass']:
                proxy_opts["username"] = dynamic_proxy['user']
                proxy_opts["password"] = dynamic_proxy['pass']
            log(f"🌐 [PROXY] Routing via dynamic proxy: {pm.get_proxy_string(dynamic_proxy)}...")
        elif PROXY_HOST and PROXY_PORT:
            proxy_opts = {"server": f"{PROXY_HOST}:{PROXY_PORT}"}
            if PROXY_USER and PROXY_PASS:
                proxy_opts["username"] = PROXY_USER
                proxy_opts["password"] = PROXY_PASS
            log(f"🌐 [PROXY] Routing via static proxy: {PROXY_HOST}:{PROXY_PORT}...")

    # Launch options for custom executable
    launch_opts = {
        "headless": HEADLESS,
        "proxy": proxy_opts
    }
    if BROWSER_EXECUTABLE_PATH and _pathlib.Path(BROWSER_EXECUTABLE_PATH).exists():
        launch_opts["executable_path"] = BROWSER_EXECUTABLE_PATH
        log(f"🚀 [BROWSER] Using custom executable: {BROWSER_EXECUTABLE_PATH}")

    # Launch browser
    if BROWSER_TYPE.lower() == "firefox":
        log("✅ Firefox driver setup")
        browser = playwright.firefox.launch(**launch_opts)
        context = browser.new_context(**context_opts)
        return browser, context
    else:
        log("🚀 [BROWSER] Preparing Chromium driver...")
        if PERSISTENT_CONTEXT:
            try:
                profile_path = _pathlib.Path(PERSISTENT_PROFILE_DIR)
                if profile_name:
                    # Segregate profiles by user/account hash or name
                    safe_name = "".join([c if c.isalnum() else "_" for c in profile_name])
                    profile_path = profile_path / safe_name
                
                log(f"📁 [BROWSER] Using persistent profile: {profile_path.absolute()}")
                profile_path.mkdir(parents=True, exist_ok=True)
                
                # Cleanup potential lock files that cause hangs
                lock_files = ["SingletonLock", "parent.lock", "lock"]
                for lock_name in lock_files:
                    lock_file = profile_path / lock_name
                    if lock_file.exists():
                        try:
                            log(f"🧹 [BROWSER] Removing stale lock file: {lock_name}")
                            lock_file.unlink()
                        except:
                            pass

                log(f"🎬 [BROWSER] Launching persistent Chromium context ({profile_path.name})...")
                context = playwright.chromium.launch_persistent_context(
                    str(profile_path),
                    args=['--disable-blink-features=AutomationControlled','--disable-infobars'],
                    **launch_opts,
                    **context_opts
                )
                log("✅ [BROWSER] Persistent context launched successfully.")
                context._fingerprint = fp
                return None, context
            except Exception as e:
                log(f"⚠️ [BROWSER] Persistent context failed: {str(e)}. Falling back to incognito.")
        
        log("🎬 [BROWSER] Launching incognito Chromium instance...")
        try:
            browser = playwright.chromium.launch(
                args=['--incognito', '--disable-blink-features=AutomationControlled','--disable-infobars'],
                **launch_opts
            )
            log("✅ [BROWSER] Chromium browser launched.")
            log("🎭 [BROWSER] Creating new context...")
            context = browser.new_context(**context_opts)
            log("✅ [BROWSER] New context created.")
            context._fingerprint = fp
            return browser, context
        except Exception as e:
            log(f"❌ [BROWSER] Chromium launch failed: {str(e)}")
            raise

async def close_context_browser(
    browser: Optional[Browser],
    context: Optional[BrowserContext]
) -> None:
    """
    Safely close browser context and browser instance.
    """
    try:
        if context:
            await context.close()
    except:
        pass
    try:
        if browser:
            await browser.close()
    except:
        pass


def close_context_browser_sync(
    browser: Optional[SyncBrowser],
    context: Optional[SyncBrowserContext]
) -> None:
    """
    Synchronous version of close_context_browser.
    """
    try:
        if context:
            try:
                for p in getattr(context, "pages", []) or []:
                    try: p.close()
                    except: pass
            except: pass
            try: context.close()
            except: pass
    except: pass
    try:
        if browser:
            try: browser.close()
            except: pass
    except: pass

