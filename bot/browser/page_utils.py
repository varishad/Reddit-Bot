"""
Page utilities - Page creation, reuse, and management.
"""
from typing import Optional
from playwright.sync_api import BrowserContext, Page


def get_or_create_page(context: BrowserContext, prefer_existing: bool = True) -> Page:
    """
    Get existing page from context or create a new one.
    
    Args:
        context: Browser context
        prefer_existing: If True, prefer existing first page over creating new
        
    Returns:
        Page object
    """
    if prefer_existing:
        try:
            pages = getattr(context, "pages", [])
            if pages:
                return pages[0]
        except Exception:
            pass
    return context.new_page()


def close_extra_pages(context: BrowserContext, keep_first: bool = True) -> None:
    """
    Close extra pages in context, optionally keeping the first one.
    
    Args:
        context: Browser context
        keep_first: If True, keep the first page and close the rest
    """
    try:
        pages = getattr(context, "pages", [])
        if not pages:
            return
        
        if keep_first and len(pages) > 1:
            # Close all except the first page
            for p in pages[1:]:
                try:
                    p.close()
                except:
                    pass
        elif not keep_first:
            # Close all pages
            for p in pages:
                try:
                    p.close()
                except:
                    pass
    except Exception:
        pass


def ensure_page_ready(page: Page, timeout: int = 2000) -> bool:
    """
    Ensure page is ready by waiting for load state.
    
    Args:
        page: Page object
        timeout: Timeout in milliseconds
        
    Returns:
        True if page is ready, False otherwise
    """
    try:
        page.wait_for_load_state('domcontentloaded', timeout=timeout)
        return True
    except:
        return False

