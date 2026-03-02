"""
Humanization module - Human-like behavior simulation for browser automation.
"""
from bot.humanization.stealth import apply_stealth, apply_basic_stealth
from bot.humanization.typing import type_human, clear_input
from bot.humanization.behavior import human_pause, mouse_jitter, gentle_scroll

__all__ = [
    'apply_stealth',
    'apply_basic_stealth',
    'type_human',
    'clear_input',
    'human_pause',
    'mouse_jitter',
    'gentle_scroll',
]
