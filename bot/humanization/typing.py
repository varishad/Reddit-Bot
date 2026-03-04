"""
Typing module - Human-like typing simulation and input field management.
"""
import random as _random
from playwright.sync_api import Locator
from config import HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS, INSTANT_FILL_ENABLED


def type_human(element: Locator, text: str) -> None:
    """
    Type with per-character delay to simulate human typing, 
    or use instant fill if configured.
    Each keystroke gets a unique random delay for realistic variation.
    """
    if INSTANT_FILL_ENABLED:
        fill_instant(element, text)
        return

    import time
    try:
        element.click()
        for char in text:
            delay = _random.uniform(HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS) / 1000.0
            element.press(char)
            time.sleep(delay)
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

