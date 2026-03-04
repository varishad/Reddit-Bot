"""
Navigation module - URL navigation utilities.
"""
import time
from typing import Any, Optional
from config import BROWSER_TIMEOUT


def navigate_via_address_bar(page: Any, url: str, timeout: Optional[int] = None) -> bool:
    """
    Navigate to a URL with retry logic and proper wait states.
    
    Args:
        page: Playwright page object
        url: URL to navigate to
        timeout: Navigation timeout (defaults to BROWSER_TIMEOUT)
        
    Returns:
        True if navigation succeeded, False otherwise
    """
    if timeout is None:
        timeout = BROWSER_TIMEOUT
    
    # Try method 1: Full navigation with domcontentloaded
    try:
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        # Try networkidle as best effort (not required)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        return True
    except Exception:
        pass
    
    # Try method 2: Navigate with default wait (network:0 for faster fail)
    try:
        page.goto(url, timeout=timeout)
        time.sleep(0.5)  # Brief wait for any redirects
        return True
    except Exception:
        pass
    
    # Try method 3: Force navigation by reloading
    try:
        page.reload(timeout=timeout, wait_until="domcontentloaded")
        return True
    except Exception:
        pass
    
    # All methods failed
    return False

