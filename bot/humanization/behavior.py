"""
Behavior module - Human-like behaviors (pauses, mouse movements, scrolling).
"""
import time
import random as _random
from playwright.sync_api import Page
from config import HUMAN_STEP_WAIT_MIN_S, HUMAN_STEP_WAIT_MAX_S


def human_pause(natural: bool = True) -> None:
    """Small random pause between steps. If natural=True, uses a Gaussian distribution."""
    try:
        if natural:
            # Gaussian (Normal) distribution mirrors human hesitation better
            # centered between min and max
            mu = (HUMAN_STEP_WAIT_MIN_S + HUMAN_STEP_WAIT_MAX_S) / 2
            sigma = (HUMAN_STEP_WAIT_MAX_S - HUMAN_STEP_WAIT_MIN_S) / 4
            wait = _random.gauss(mu, sigma)
            # Boundary clamp
            wait = max(HUMAN_STEP_WAIT_MIN_S, min(wait, HUMAN_STEP_WAIT_MAX_S))
            time.sleep(wait)
        else:
            time.sleep(_random.uniform(HUMAN_STEP_WAIT_MIN_S, HUMAN_STEP_WAIT_MAX_S))
    except Exception:
        pass


def mouse_jitter(page: Page) -> None:
    """
    Perform realistic random mouse movements across the viewport to simulate human presence.
    
    Args:
        page: Playwright page object
    """
    try:
        viewport = page.viewport_size or {'width': 1280, 'height': 720}
        width = viewport['width']
        height = viewport['height']

        # Industrial Grade: Randomize across full viewport
        for _ in range(_random.randint(2, 5)):
            x = _random.randint(10, width - 10)
            y = _random.randint(10, height - 10)
            
            # Vary steps and speed for each movement
            steps = _random.randint(10, 40)
            page.mouse.move(x, y, steps=steps)
            
            # Natural micro-pause after movement
            if _random.random() > 0.7:
                time.sleep(_random.uniform(0.1, 0.4))
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

