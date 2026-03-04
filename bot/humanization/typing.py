"""
Typing module - Human-like typing simulation and input field management.
"""
import random as _random
from playwright.sync_api import Locator
from config import HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS, INSTANT_FILL_ENABLED


def type_human(element: Locator, text: str) -> None:
    """
    Type with sophisticated human-like simulation:
    - Variable character delays based on a rhythmic distribution.
    - Occasional typos followed by backspace corrections.
    - Thinking pauses before starting and after finishing.
    - Longer delays between words.
    """
    from config import HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS, HUMAN_TYPO_CHANCE, INSTANT_FILL_ENABLED
    
    if INSTANT_FILL_ENABLED:
        fill_instant(element, text)
        return

    try:
        import time
        element.click()
        
        # Initial "thinking" pause before starting to type
        time.sleep(_random.uniform(0.3, 0.8))
        
        # Keyboard adjacent characters for realistic typos
        adjacents = {
            'a': 'sqwz', 'b': 'vghn', 'c': 'xvdfg', 'd': 'serfcx', 'e': 'rdswf',
            'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb', 'i': 'ujko89', 'j': 'hukmny',
            'k': 'jilmo', 'l': 'kop;.', 'm': 'njk,', 'n': 'bhjm', 'o': 'iklp90',
            'p': 'olp[0-', 'q': 'wa12s', 'r': 'edft45', 's': 'awdezx', 't': 'rfgy56',
            'u': 'yhji78', 'v': 'cfgb', 'w': 'qeas23', 'x': 'zsdc', 'y': 'tghu67',
            'z': 'asx', '1': '2q', '2': '13qw', '3': '24we', '4': '35er', '5': '46rt',
            '6': '57ty', '7': '68yu', '8': '79io', '9': '80op', '0': '9-p'
        }

        for i, char in enumerate(text):
            # 1. Base delay per character
            delay_ms = _random.uniform(HUMAN_TYPING_DELAY_MIN_MS, HUMAN_TYPING_DELAY_MAX_MS)
            
            # 2. Rhythmic variation: occasional micro-pauses or "bursts"
            if _random.random() < 0.1:  # 10% chance of a "thinking" pause
                delay_ms += _random.uniform(100, 300)
            
            # 3. Longer pause after spaces (end of word)
            if i > 0 and text[i-1] == ' ':
                delay_ms += _random.uniform(50, 150)

            # 4. Typo and Correction logic
            if char.lower() in adjacents and _random.random() < HUMAN_TYPO_CHANCE:
                typo_char = _random.choice(adjacents[char.lower()])
                # Shift if original was upper
                if char.isupper():
                    typo_char = typo_char.upper()
                
                # Type the wrong char
                time.sleep(delay_ms / 1000.0)
                element.press_sequentially(typo_char)
                
                # Realize mistake pause
                time.sleep(_random.uniform(0.2, 0.5))
                element.press("Backspace")
                
                # Correction delay
                time.sleep(_random.uniform(0.1, 0.2))

            # 5. Type the actual character
            time.sleep(delay_ms / 1000.0)
            element.press_sequentially(char)
            
        # Final pause after finishing field
        time.sleep(_random.uniform(0.2, 0.4))
            
    except Exception:
        try:
            # Fallback for ElementHandle or other issues
            if hasattr(element, "fill"):
                element.fill(text)
        except Exception:
            pass


def fill_instant(element: Locator, text: str) -> None:
    """Standard automated filling (no delay)."""
    try:
        element.fill(text)
    except Exception:
        try:
            if hasattr(element, "type"):
                element.type(text)
        except Exception:
            pass


def clear_input(element: Locator) -> None:
    """Clear an input field robustly."""
    try:
        if hasattr(element, "click"):
            element.click()
        
        # Try locator-based press first
        try:
            if hasattr(element, "press"):
                element.press("Control+A")
                element.press("Backspace")
                return
        except:
            pass
            
        # Fallback to fill
        if hasattr(element, "fill"):
            element.fill("")
    except Exception:
        pass

