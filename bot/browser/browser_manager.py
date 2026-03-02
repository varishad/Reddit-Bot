"""
Browser Manager - Browser lifecycle management (launch, close, context management).
"""
import random as _random
import pathlib as _pathlib
from typing import Tuple, Optional
from playwright.sync_api import Playwright, Browser, BrowserContext
from config import (
    BROWSER_TYPE, HEADLESS, PERSISTENT_CONTEXT, PERSISTENT_PROFILE_DIR,
    VIEWPORT_BASE_WIDTH, VIEWPORT_BASE_HEIGHT, VIEWPORT_VARIATION,
    USER_AGENT_POOL
)
from ip_utils import get_geo_profile


def launch_browser_and_context(
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
    
    # Launch browser based on config
    if BROWSER_TYPE.lower() == "firefox":
        log("✅ Firefox driver setup without proxy")
        browser = playwright.firefox.launch(
            headless=HEADLESS
        )
        geo = {}
        try:
            geo = get_geo_profile() or {}
        except:
            geo = {}
        # Randomize viewport slightly
        viewport_width = VIEWPORT_BASE_WIDTH + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
        viewport_height = VIEWPORT_BASE_HEIGHT + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
        # Select random user agent
        user_agent = _random.choice(USER_AGENT_POOL) if USER_AGENT_POOL else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        context_opts = {
            'viewport': {'width': viewport_width, 'height': viewport_height},
            'user_agent': user_agent
        }
        if geo.get('timezone'):
            context_opts['timezone_id'] = geo['timezone']
        if geo.get('locale'):
            context_opts['locale'] = geo['locale']
        lat = geo.get('latitude')
        lon = geo.get('longitude')
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            context_opts['geolocation'] = {'latitude': float(lat), 'longitude': float(lon)}
            context_opts['permissions'] = ['geolocation']
        context = browser.new_context(**context_opts)
    else:
        log("✅ Chromium driver setup without proxy")
        # Prefer persistent context for Chromium if enabled
        geo = {}
        try:
            geo = get_geo_profile() or {}
        except:
            geo = {}
        # Randomize viewport slightly
        viewport_width = VIEWPORT_BASE_WIDTH + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
        viewport_height = VIEWPORT_BASE_HEIGHT + _random.randint(-VIEWPORT_VARIATION, VIEWPORT_VARIATION)
        # Select random user agent from pool
        user_agent = _random.choice(USER_AGENT_POOL) if USER_AGENT_POOL else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        context_opts = {
            'viewport': {'width': viewport_width, 'height': viewport_height},
            'user_agent': user_agent
        }
        if geo.get('timezone'):
            context_opts['timezone_id'] = geo['timezone']
        if geo.get('locale'):
            context_opts['locale'] = geo['locale']
        lat = geo.get('latitude')
        lon = geo.get('longitude')
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            context_opts['geolocation'] = {'latitude': float(lat), 'longitude': float(lon)}
            context_opts['permissions'] = ['geolocation']

        context = None
        browser = None
        if PERSISTENT_CONTEXT:
            try:
                _pathlib.Path(PERSISTENT_PROFILE_DIR).mkdir(parents=True, exist_ok=True)
                # Persistent context only for Chromium
                context = playwright.chromium.launch_persistent_context(
                    PERSISTENT_PROFILE_DIR,
                    headless=HEADLESS,
                    args=['--disable-blink-features=AutomationControlled','--disable-infobars'],
                    **context_opts
                )
                browser = None  # Managed by persistent context
            except Exception as e:
                log(f"⚠️  Persistent context failed: {str(e)}. Falling back to ephemeral context.")
        if context is None:
            try:
                browser = playwright.chromium.launch(
                    headless=HEADLESS,
                    args=['--incognito', '--disable-blink-features=AutomationControlled','--disable-infobars']
                )
                context = browser.new_context(**context_opts)
            except Exception as e:
                # Re-raise with clearer message
                raise RuntimeError(f"Chromium context launch failed: {str(e)}")
    return browser, context


def close_context_browser(
    browser: Optional[Browser],
    context: Optional[BrowserContext]
) -> None:
    """
    Close all pages, then context and browser safely.
    
    Args:
        browser: Browser instance to close (may be None for persistent contexts)
        context: Browser context to close
    """
    try:
        if context:
            try:
                for p in getattr(context, "pages", []) or []:
                    try:
                        p.close()
                    except:
                        pass
            except:
                pass
            try:
                context.close()
            except:
                pass
    except:
        pass
    try:
        if browser:
            try:
                browser.close()
            except:
                pass
    except:
        pass

