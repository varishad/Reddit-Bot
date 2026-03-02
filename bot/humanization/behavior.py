"""
Behavior module - Human-like behaviors (pauses, mouse movements, scrolling).
"""
import time
import random as _random
from playwright.sync_api import Page
from config import HUMAN_STEP_WAIT_MIN_S, HUMAN_STEP_WAIT_MAX_S


def human_pause() -> None:
    """Small random pause between steps."""
    try:
        time.sleep(_random.uniform(HUMAN_STEP_WAIT_MIN_S, HUMAN_STEP_WAIT_MAX_S))
    except Exception:
        pass


def mouse_jitter(page: Page) -> None:
    """
    Perform small random mouse movements to simulate human presence.
    
    Args:
        page: Playwright page object
    """
    try:
        # More realistic mouse movements - multiple small movements
        for _ in range(_random.randint(2, 4)):
            x = _random.randint(50, 300)
            y = _random.randint(50, 300)
            page.mouse.move(x, y, steps=_random.randint(5, 15))
            time.sleep(_random.uniform(0.1, 0.3))
    except Exception:
        pass


def gentle_scroll(page: Page) -> None:
    """
    Perform a small gentle scroll to mimic reading.
    
    Args:
        page: Playwright page object
    """
    try:
        page.mouse.wheel(0, _random.randint(100, 300))
        human_pause()
        page.mouse.wheel(0, -_random.randint(50, 150))
    except Exception:
        pass

