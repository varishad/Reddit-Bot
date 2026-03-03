"""
Browser Manager - Browser lifecycle management (launch, close, context management).
"""
import random as _random
import pathlib as _pathlib
from typing import Tuple, Optional
from playwright.async_api import Playwright, Browser, BrowserContext
from config import (
    BROWSER_TYPE, HEADLESS, PERSISTENT_CONTEXT, PERSISTENT_PROFILE_DIR,
    VIEWPORT_BASE_WIDTH, VIEWPORT_BASE_HEIGHT, VIEWPORT_VARIATION,
    USER_AGENT_POOL, PROXY_ENABLED, PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS
)
from ip_utils import get_geo_profile


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
    
    # Launch browser based on config
    if BROWSER_TYPE.lower() == "firefox":
        log("✅ Firefox driver setup without proxy")
        if geo.get('latitude') and geo.get('longitude'):
            context_opts['geolocation'] = {'latitude': float(geo['latitude']), 'longitude': float(geo['longitude'])}
            context_opts['permissions'] = ['geolocation']
        
        # Add Proxy support
        if PROXY_ENABLED and PROXY_HOST and PROXY_PORT:
            proxy_opts = {
                "server": f"{PROXY_HOST}:{PROXY_PORT}"
            }
            if PROXY_USER and PROXY_PASS:
                proxy_opts["username"] = PROXY_USER
                proxy_opts["password"] = PROXY_PASS
            
            log(f"🌐 [PROXY] Routing via {PROXY_HOST}:{PROXY_PORT}...")
            browser = await playwright.firefox.launch(
                headless=HEADLESS,
                proxy=proxy_opts
            )
        else:
            browser = await playwright.firefox.launch(
                headless=HEADLESS
            )
            
        context = await browser.new_context(**context_opts)
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
        if geo.get('latitude') and geo.get('longitude'):
            context_opts['geolocation'] = {'latitude': float(geo['latitude']), 'longitude': float(geo['longitude'])}
            context_opts['permissions'] = ['geolocation']

        # Proxy configuration for Chromium
        proxy_opts = None
        if PROXY_ENABLED and PROXY_HOST and PROXY_PORT:
            proxy_opts = {
                "server": f"{PROXY_HOST}:{PROXY_PORT}"
            }
            if PROXY_USER and PROXY_PASS:
                proxy_opts["username"] = PROXY_USER
                proxy_opts["password"] = PROXY_PASS
            log(f"🌐 [PROXY] Routing via {PROXY_HOST}:{PROXY_PORT}...")

        context = None
        browser = None
        if PERSISTENT_CONTEXT:
            try:
                _pathlib.Path(PERSISTENT_PROFILE_DIR).mkdir(parents=True, exist_ok=True)
                # Persistent context only for Chromium
                context = await playwright.chromium.launch_persistent_context(
                    PERSISTENT_PROFILE_DIR,
                    headless=HEADLESS,
                    args=['--disable-blink-features=AutomationControlled','--disable-infobars'],
                    proxy=proxy_opts,
                    **context_opts
                )
                browser = None  # Managed by persistent context
            except Exception as e:
                log(f"⚠️  Persistent context failed: {str(e)}. Falling back to ephemeral context.")
        
        if context is None:
            try:
                browser = await playwright.chromium.launch(
                    headless=HEADLESS,
                    args=['--incognito', '--disable-blink-features=AutomationControlled','--disable-infobars'],
                    proxy=proxy_opts
                )
                context = await browser.new_context(**context_opts)
            except Exception as e:
                # Re-raise with clearer message
                raise RuntimeError(f"Chromium context launch failed: {str(e)}")
    return browser, context


async def close_context_browser(
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
                        await p.close()
                    except:
                        pass
            except:
                pass
            try:
                await context.close()
            except:
                pass
    except:
        pass
    try:
        if browser:
            try:
                await browser.close()
            except:
                pass
    except:
        pass

