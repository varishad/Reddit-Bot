"""
Stealth module - Browser fingerprinting evasion and automation detection prevention.
"""
from typing import Optional
from playwright.sync_api import Page


def apply_basic_stealth(page: Page, fingerprint: Optional[dict] = None, skip_webdriver: bool = False) -> None:
    """
    Enhanced stealth: patch navigator.webdriver, plugins, languages, WebGL, chrome runtime, permissions, and more.
    Dynamically injects fingerprint parameters if provided.
    
    Args:
        page: Playwright page object to apply stealth to
        fingerprint: Optional hardware/device profile to inject
        skip_webdriver: If True, do not patch navigator.webdriver (avoids double-patching)
    """
    
    # Default values if no fingerprint provided
    fp = fingerprint or {}
    hw_concurrency = fp.get("hardware_concurrency", 8)
    device_memory = fp.get("device_memory", 8)
    platform = fp.get("platform", "Win32")
    vendor = fp.get("vendor", "Google Inc.")
    renderer = fp.get("renderer", "ANGLE (Intel, Intel(R) UHD Graphics, Direct3D 11)")
    screen_depth = fp.get("screen_depth", 24)

    webdriver_patch = ""
    if not skip_webdriver:
        webdriver_patch = "Object.defineProperty(navigator, 'webdriver', { get: () => false });"

    js = f"""
() => {{
  try {{
    // Hide webdriver property (if requested)
    {webdriver_patch}
    
    // Inject hardware fingerprint
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hw_concurrency} }});
    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {device_memory} }});
    Object.defineProperty(navigator, 'platform', {{ get: () => '{platform}' }});
    
    // Spoof Screen Depth
    Object.defineProperty(screen, 'colorDepth', {{ get: () => {screen_depth} }});
    Object.defineProperty(screen, 'pixelDepth', {{ get: () => {screen_depth} }});
    
    // Ensure languages are set
    if (!navigator.languages || navigator.languages.length === 0) {{
      Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'] }});
    }}
    
    // Fake plugins if missing
    const origPlugins = navigator.plugins;
    if (!origPlugins || origPlugins.length === 0) {{
      const fakePluginArray = {{ length: 3, 0: {{}}, 1: {{}}, 2: {{}} }};
      Object.setPrototypeOf(fakePluginArray, PluginArray.prototype);
      Object.defineProperty(navigator, 'plugins', {{ get: () => fakePluginArray }});
    }}
    
    // Ensure chrome object exists
    if (!window.chrome) {{
      window.chrome = {{ runtime: {{}} }};
    }}
    
    // Patch WebGL fingerprinting
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
      const UNMASKED_VENDOR_WEBGL = 0x9245;
      const UNMASKED_RENDERER_WEBGL = 0x9246;
      if (parameter === UNMASKED_VENDOR_WEBGL) return '{vendor}';
      if (parameter === UNMASKED_RENDERER_WEBGL) return '{renderer}';
      return getParameter.call(this, parameter);
    }};
    
    // Hide automation indicators
    Object.defineProperty(navigator, 'permissions', {{
      get: () => ({{
        query: () => Promise.resolve({{ state: 'granted' }})
      }})
    }});
    
    // Override notification permission
    const originalQuery = window.Notification?.permission;
    Object.defineProperty(window, 'Notification', {{
      get: () => ({{
        permission: 'default'
      }})
    }});
    
    // Remove automation flags from window
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    
    // Override toString to hide automation
    const originalToString = Function.prototype.toString;
    Function.prototype.toString = function() {{
      if (this === navigator.webdriver || this === window.chrome) {{
        return 'function () {{ [native code] }}';
      }}
      return originalToString.call(this);
    }};
  }} catch (e) {{}}
}}
"""
    try:
        page.add_init_script(js)
    except Exception:
        pass


def apply_stealth(page: Page, stealth_module: Optional[object] = None) -> None:
    """
    Apply stealth patches to a page, using external stealth module if available.
    
    Args:
        page: Playwright page object
        stealth_module: Optional playwright_stealth module (stealth_sync function)
    """
    is_stealth_module_ok = False
    if stealth_module:
        try:
            stealth_module(page)
            is_stealth_module_ok = True
        except Exception:
            pass
    
    # Extract fingerprint created by browser_manager
    fingerprint = getattr(page.context, '_fingerprint', None)
    
    # Apply basic stealth, skipping webdriver if playwright-stealth handled it
    apply_basic_stealth(page, fingerprint, skip_webdriver=is_stealth_module_ok)

