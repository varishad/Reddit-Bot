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


# Global proxy manager instance
_proxy_manager = None

def get_proxy_manager(log_callback=None):
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager(log_callback=log_callback)
    return _proxy_manager


async def launch_browser_and_context(
    playwright: Playwright,
    log_callback: Optional[callable] = None
) -> Tuple[Optional[Browser], BrowserContext]:
    """
    Launch a new browser and context using current configuration and geo profile.
    
    Args:
        playwright: Playwright instance
        log_callback: Optional logging function
        
    Returns:
        Tuple of (browser, context). Browser may be None for persistent contexts.
    """
    log = log_callback or (lambda msg: None)
    pm = get_proxy_manager(log)
    
    # Launch browser based on config
    if BROWSER_TYPE.lower() == "firefox":
        # ... logic for firefox ...
        pass # placeholder for brevity, actual edit below
    
    # Randomize viewport slightly
    geo = {}
    try:
        geo = get_geo_profile() or {}
    except:
        geo = {}

    viewport_width = VIEWPORT_BASE_WIDTH + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
    viewport_height = VIEWPORT_BASE_HEIGHT + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
    user_agent = _random.choice(USER_AGENT_POOL) if USER_AGENT_POOL else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    context_opts = {
        'viewport': {'width': viewport_width, 'height': viewport_height},
        'user_agent': user_agent
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
        # Try dynamic proxy list first
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
            # Fallback to static config
            proxy_opts = {
                "server": f"{PROXY_HOST}:{PROXY_PORT}"
            }
            if PROXY_USER and PROXY_PASS:
                proxy_opts["username"] = PROXY_USER
                proxy_opts["password"] = PROXY_PASS
            log(f"🌐 [PROXY] Routing via static proxy: {PROXY_HOST}:{PROXY_PORT}...")

    context = None
    browser = None
    
    # Launch options for custom executable
    launch_opts = {
        "headless": HEADLESS,
        "proxy": proxy_opts
    }
    if BROWSER_EXECUTABLE_PATH and _pathlib.Path(BROWSER_EXECUTABLE_PATH).exists():
        launch_opts["executable_path"] = BROWSER_EXECUTABLE_PATH
        log(f"🚀 [BROWSER] Using custom executable: {BROWSER_EXECUTABLE_PATH}")

    # Firefox launch (keeping existing structure but updating with proxy_opts)
    if BROWSER_TYPE.lower() == "firefox":
        log("✅ Firefox driver setup")
        browser = await playwright.firefox.launch(**launch_opts)
        context = await browser.new_context(**context_opts)
        return browser, context

    # Chromium launch
    log("✅ Chromium driver setup")
    if PERSISTENT_CONTEXT:
        try:
            _pathlib.Path(PERSISTENT_PROFILE_DIR).mkdir(parents=True, exist_ok=True)
            context = await playwright.chromium.launch_persistent_context(
                PERSISTENT_PROFILE_DIR,
                args=['--disable-blink-features=AutomationControlled','--disable-infobars'],
                **launch_opts,
                **context_opts
            )
            browser = None
        except Exception as e:
            log(f"⚠️  Persistent context failed: {str(e)}. Falling back.")
    
    if context is None:
        browser = await playwright.chromium.launch(
            args=['--incognito', '--disable-blink-features=AutomationControlled','--disable-infobars'],
            **launch_opts
        )
        context = await browser.new_context(**context_opts)
        
    return browser, context


def launch_browser_and_context_sync(
    playwright: SyncPlaywright,
    log_callback: Optional[callable] = None
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
    user_agent = _random.choice(USER_AGENT_POOL) if USER_AGENT_POOL else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    context_opts = {
        'viewport': {'width': viewport_width, 'height': viewport_height},
        'user_agent': user_agent
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
        log("✅ Chromium driver setup")
        if PERSISTENT_CONTEXT:
            try:
                _pathlib.Path(PERSISTENT_PROFILE_DIR).mkdir(parents=True, exist_ok=True)
                context = playwright.chromium.launch_persistent_context(
                    PERSISTENT_PROFILE_DIR,
                    args=['--disable-blink-features=AutomationControlled','--disable-infobars'],
                    **launch_opts,
                    **context_opts
                )
                return None, context
            except Exception as e:
                log(f"⚠️ Persistent context failed: {str(e)}. Falling back.")
        
        browser = playwright.chromium.launch(
            args=['--incognito', '--disable-blink-features=AutomationControlled','--disable-infobars'],
            **launch_opts
        )
        context = browser.new_context(**context_opts)
        return browser, context

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

