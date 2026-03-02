"""
Stealth module - Browser fingerprinting evasion and automation detection prevention.
"""
from typing import Optional
from playwright.sync_api import Page


def apply_basic_stealth(page: Page) -> None:
    """
    Enhanced stealth: patch navigator.webdriver, plugins, languages, WebGL, chrome runtime, permissions, and more.
    
    Args:
        page: Playwright page object to apply stealth to
    """
    js = """
() => {
  try {
    // Hide webdriver property
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    
    // Ensure languages are set
    if (!navigator.languages || navigator.languages.length === 0) {
      Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    }
    
    // Fake plugins if missing
    const origPlugins = navigator.plugins;
    if (!origPlugins || origPlugins.length === 0) {
      const fakePluginArray = { length: 3, 0: {}, 1: {}, 2: {} };
      Object.setPrototypeOf(fakePluginArray, PluginArray.prototype);
      Object.defineProperty(navigator, 'plugins', { get: () => fakePluginArray });
    }
    
    // Ensure chrome object exists
    if (!window.chrome) {
      window.chrome = { runtime: {} };
    }
    
    // Patch WebGL fingerprinting
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
      const UNMASKED_VENDOR_WEBGL = 0x9245;
      const UNMASKED_RENDERER_WEBGL = 0x9246;
      if (parameter === UNMASKED_VENDOR_WEBGL) return 'Google Inc.';
      if (parameter === UNMASKED_RENDERER_WEBGL) return 'ANGLE (Intel, Intel(R) UHD Graphics, Direct3D 11)';
      return getParameter.call(this, parameter);
    };
    
    // Hide automation indicators
    Object.defineProperty(navigator, 'permissions', {
      get: () => ({
        query: () => Promise.resolve({ state: 'granted' })
      })
    });
    
    // Override notification permission
    const originalQuery = window.Notification?.permission;
    Object.defineProperty(window, 'Notification', {
      get: () => ({
        permission: 'default'
      })
    });
    
    // Remove automation flags from window
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    
    // Override toString to hide automation
    const originalToString = Function.prototype.toString;
    Function.prototype.toString = function() {
      if (this === navigator.webdriver || this === window.chrome) {
        return 'function () { [native code] }';
      }
      return originalToString.call(this);
    };
  } catch (e) {}
}
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
    if stealth_module:
        try:
            stealth_module(page)
        except Exception:
            pass
    
    # Always apply basic stealth
    apply_basic_stealth(page)

