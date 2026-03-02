"""
Status detection and user info extraction
"""

from bot.detection.status_detector import detect_status
from bot.detection.user_info_extractor import extract_user_info
from bot.detection.error_normalizer import normalize_login_error

__all__ = [
    'detect_status',
    'extract_user_info',
    'normalize_login_error',
]
