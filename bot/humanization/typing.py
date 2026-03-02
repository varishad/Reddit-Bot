"""
Typing module - Human-like typing simulation and input field management.
"""
import random as _random
from playwright.sync_api import Locator
from config import HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS


def type_human(element: Locator, text: str) -> None:
    """
    Type with per-character delay to simulate human typing.
    
    Args:
        element: Playwright locator for the input element
        text: Text to type
    """
    try:
        delay = lambda: _random.uniform(HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS)
        # Playwright element.type supports delay per char
        element.type(text, delay=delay())
    except Exception:
        try:
            element.fill(text)
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

