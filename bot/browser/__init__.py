"""
Browser module - Browser lifecycle management, navigation, and page utilities.
"""
from bot.browser.browser_manager import (
    launch_browser_and_context, close_context_browser,
    launch_browser_and_context_sync, close_context_browser_sync
)
from bot.browser.navigation import navigate_via_address_bar
from bot.browser.page_utils import get_or_create_page, close_extra_pages, ensure_page_ready

__all__ = [
    'launch_browser_and_context',
    'close_context_browser',
    'launch_browser_and_context_sync',
    'close_context_browser_sync',
    'navigate_via_address_bar',
    'get_or_create_page',
    'close_extra_pages',
    'ensure_page_ready',
]
