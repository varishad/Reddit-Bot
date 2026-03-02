"""
Navigation module - URL navigation utilities.
"""
from typing import Any, Optional
from config import BROWSER_TIMEOUT


def navigate_via_address_bar(page: Any, url: str, timeout: Optional[int] = None) -> bool:
    """
    Navigate to a URL by opening a fresh tab and using Playwright's native goto.
    
    Args:
        page: Playwright page object
        url: URL to navigate to
        timeout: Navigation timeout (defaults to BROWSER_TIMEOUT)
        
    Returns:
        True if navigation succeeded, False otherwise
    """
    if timeout is None:
        timeout = BROWSER_TIMEOUT
    
    try:
        page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception:
            pass
        return True
    except Exception:
        try:
            page.goto(url, timeout=timeout)
            return True
        except Exception:
            return False

