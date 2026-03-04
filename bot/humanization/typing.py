"""
Typing module - Human-like typing simulation and input field management.
"""
import random as _random
from playwright.sync_api import Locator
from config import HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS, INSTANT_FILL_ENABLED


def type_human(element: Locator, text: str) -> None:
    """
    Type with per-character variable delay to simulate realistic human typing.
    Each character gets a unique random delay, with occasional micro-pauses
    to simulate thinking/hesitation.
    """
    if INSTANT_FILL_ENABLED:
        fill_instant(element, text)
        return

    try:
        import time
        element.click()
        for i, char in enumerate(text):
            # Base delay: random per character (30-80ms)
            delay_ms = _random.uniform(HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS)
            
            # Occasional micro-pause to simulate hesitation (~15% chance)
            if _random.random() < 0.15 and i > 0:
                delay_ms += _random.uniform(80, 200)
            
            # Slight speed burst on common characters (space, @, .)
            if char in (' ', '@', '.'):
                delay_ms *= _random.uniform(0.6, 0.9)
            
            time.sleep(delay_ms / 1000.0)
            element.press_sequentially(char)
    except Exception:
        try:
            element.fill(text)
        except Exception:
            pass


def fill_instant(element: Locator, text: str) -> None:
    """
    Standard automated filling (no delay).
    """
    try:
        element.fill(text)
    except Exception:
        try:
            element.type(text)
        except Exception:
            pass


def clear_input(element: Locator) -> None:
    """
    Clear an input field robustly without reloading/closing.
    
    Args:
        element: Playwright locator for the input element
    """
    try:
        element.click()
        # Select all and delete
        try:
            element.press("Control+A")
        except Exception:
            try:
                element.press("Meta+A")
            except Exception:
                pass
        element.press("Backspace")
    except Exception:
        try:
            element.fill("")
        except Exception:
            pass

