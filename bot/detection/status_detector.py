"""
Status detection - Detect login status from Reddit pages
"""
import time
from typing import Tuple, Optional, Callable
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from bot.detection.error_normalizer import normalize_login_error
from bot.detection.user_info_extractor import extract_user_info


def detect_status(page, log_callback: Optional[Callable] = None) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """
    Detect login status and extract user information with specific error detection.
    
    Args:
        page: Playwright page object
        log_callback: Optional logging function
        
    Returns:
        Tuple of (status, username, karma, error_message)
        status: 'success', 'invalid', 'banned', 'locked', or 'error'
    """
    try:
        # Minimal wait for faster detection (like other bot: 1-2s)
        try:
            page.wait_for_load_state('domcontentloaded', timeout=2000)
        except:
            pass
        time.sleep(0.3)  # Reduced to 0.3s for faster detection
        
        current_url = page.url
        page_content = page.content().lower()
        page_text = page.inner_text('body').lower() if page.query_selector('body') else ""
        
        # Check for specific error messages first (most specific to least specific)
        
        # 1. Check for rate limiting / too many requests
        rate_limit_indicators = ['too many requests', 'rate limit', 'try again later', 'slow down', '429']
        if any(indicator in page_text for indicator in rate_limit_indicators):
            return ('error', None, None, 'Rate limited - Too many login attempts. Please wait and try again later.')
        
        # 2. Check for 2FA / verification required
        two_fa_indicators = ['two-factor', '2fa', 'verification code', 'enter code', 'authenticator', 'verify']
        if any(indicator in page_text for indicator in two_fa_indicators):
            return ('error', None, None, 'Two-factor authentication (2FA) required - Account has 2FA enabled')
        
        # 3. Check for account locked / temporarily locked / password reset required
        # Covers banners like: "we've locked your account after detecting some unusual activity... reset your password"
        locked_indicators = [
            'account locked',
            'temporarily locked',
            'locked for security',
            'suspicious activity',
            'locked your account',
            'unusual activity',
            'reset your password'
        ]
        if any(indicator in page_text for indicator in locked_indicators):
            # Prefer precise wording when reset is required
            if 'reset your password' in page_text:
                return ('error', None, None, 'Account locked due to unusual activity - Password reset required')
            return ('error', None, None, 'Account temporarily locked due to unusual activity')
        
        # 4. Check for banned/suspended (specific messages)
        banned_selectors = [
            'div[role="alert"]',
            '.AnimatedForm__errorMessage',
            '[data-testid="login-error"]',
            '.error',
            'div:has-text("suspended")',
            'div:has-text("banned")',
            'div:has-text("permanently")',
            'h1:has-text("suspended")',
            'h1:has-text("banned")'
        ]
        
        for selector in banned_selectors:
            try:
                error_elem = page.query_selector(selector)
                if error_elem:
                    error_text = error_elem.inner_text().strip()
                    error_lower = error_text.lower()
                    if 'suspended' in error_lower or 'banned' in error_lower:
                        # Return the actual error message
                        if error_text:
                            return ('banned', None, None, error_text)
            except:
                continue
        
        # Check page content for banned/suspended keywords
        if 'suspended' in page_text or 'banned' in page_text:
            # Try to get more specific message
            try:
                # Look for common Reddit suspension messages
                if 'permanently suspended' in page_text:
                    return ('banned', None, None, 'Account permanently suspended by Reddit')
                elif 'temporarily suspended' in page_text:
                    return ('banned', None, None, 'Account temporarily suspended by Reddit')
                elif 'banned' in page_text:
                    return ('banned', None, None, 'Account banned by Reddit')
                elif 'suspended' in page_text:
                    return ('banned', None, None, 'Account suspended by Reddit')
            except:
                pass
            return ('banned', None, None, 'Account appears to be suspended or banned')
        
        # 5. Check if still on login page (invalid credentials or other login errors)
        if 'login' in current_url.lower() or '/login' in current_url:
            # Look for specific error messages
            error_selectors = [
                'div[role="alert"]',
                '.AnimatedForm__errorMessage',
                '[data-testid="login-error"]',
                '.error',
                'div:has-text("incorrect")',
                'div:has-text("wrong")',
                'div:has-text("invalid")',
                'div:has-text("password")',
                'div:has-text("username")',
                'div:has-text("email")'
            ]
            
            for selector in error_selectors:
                try:
                    error_elem = page.query_selector(selector)
                    if error_elem and error_elem.is_visible():
                        error_text = (error_elem.inner_text() or "").strip()
                        if error_text:
                            error_lower = error_text.lower()
                            # Try multilingual normalization first
                            norm = normalize_login_error(error_lower)
                            if norm:
                                return norm
                            # Map common phrases to precise reasons
                            # Check for browser/extension errors first (should be retried, not marked invalid)
                            if 'an error occurred' in error_lower or 'disable any extensions' in error_lower or 'try using a different web browser' in error_lower:
                                return ('error', None, None, error_text)
                            if 'invalid email or password' in error_lower:
                                return ('invalid', None, None, 'Invalid email or password.')
                            if 'something went wrong logging in' in error_lower:
                                return ('error', None, None, 'Something went wrong logging in. Please try again.')
                            if any(k in error_lower for k in ['too many', 'rate limit', 'try again later']):
                                return ('error', None, None, 'Rate limited - Too many requests. Please wait and try again.')
                            # Generic invalid cases
                            if any(word in error_lower for word in ['incorrect', 'wrong']) and any(w in error_lower for w in ['password','username','email','credentials']):
                                return ('invalid', None, None, 'Invalid email or password.')
                            if any(word in error_lower for word in ['invalid','credentials']) and any(w in error_lower for w in ['password','username','email']):
                                return ('invalid', None, None, 'Invalid email or password.')
                            # Check for other login errors
                            elif 'error' in error_lower or 'failed' in error_lower:
                                return ('error', None, None, error_text)
                except:
                    continue
            
            # If still on login page but no error message found, check if form is still visible
            try:
                login_form = page.query_selector('form, input[name="username"], input[type="password"]')
                if login_form:
                    # Form still visible means login failed
                    return ('invalid', None, None, 'Invalid email or password.')
            except:
                pass
            
            # Default invalid message
            return ('invalid', None, None, 'Invalid email or password.')
        
        # 6. Check for success (redirected away from login page)
        if 'login' not in current_url.lower() and '/login' not in current_url:
            # Check if we're on a Reddit page (not an error page)
            if 'reddit.com' in current_url or current_url.startswith('/'):
                # Extract user info first - wait a bit more for page to fully load
                try:
                    page.wait_for_load_state('networkidle', timeout=3000)
                except:
                    pass
                time.sleep(0.5)  # Give page time to render
                username, karma = extract_user_info(page, log_callback=log_callback)
                
                # NOW check for lock banner AFTER extracting user info (banners appear on logged-in pages)
                lock_message = None
                try:
                    # Refresh page_text after extraction to catch any banners
                    page_text_updated = page.inner_text('body').lower() if page.query_selector('body') else ""
                    page_content_updated = page.content().lower()
                    
                    # Check for lock/reset banners with more specific patterns
                    lock_indicators = [
                        ('reset your password', 'For your security, we\'ve locked your account after detecting some unusual activity. To keep using Reddit, reset your password.'),
                        ('locked your account', 'Account locked due to unusual activity - Password reset required'),
                        ('unusual activity', 'Account locked due to unusual activity - Password reset required'),
                        ('we\'ve locked', 'Account locked due to unusual activity - Password reset required'),
                        ('for your security', 'Account locked due to unusual activity - Password reset required')
                    ]
                    
                    for indicator, default_msg in lock_indicators:
                        if indicator in page_text_updated or indicator in page_content_updated:
                            # Try to extract the actual banner message
                            try:
                                # Look for the banner element
                                banner_selectors = [
                                    '[role="alert"]',
                                    '.banner',
                                    '[class*="banner"]',
                                    '[class*="alert"]',
                                    'div:has-text("locked")',
                                    'div:has-text("reset")',
                                    'div:has-text("unusual activity")'
                                ]
                                for banner_sel in banner_selectors:
                                    banner_elem = page.query_selector(banner_sel)
                                    if banner_elem:
                                        banner_text = banner_elem.inner_text().strip()
                                        if any(ind in banner_text.lower() for ind in ['locked', 'reset', 'unusual']):
                                            lock_message = banner_text
                                            break
                            except:
                                pass
                            
                            if not lock_message:
                                lock_message = default_msg
                            break
                except:
                    pass
                
                # If lock banner detected, return 'locked' status with user info
                if lock_message:
                    return ('locked', username, karma, lock_message)
                
                # No lock banner - normal success
                if username and username != "Unknown":
                    return ('success', username, karma, None)
                elif username == "Unknown":
                    # Try one more time with navigation to /user/me
                    try:
                        page.goto('https://www.reddit.com/user/me', timeout=10000)
                        time.sleep(1)
                        # Re-check for lock banners after navigation
                        page_text_after_nav = page.inner_text('body').lower() if page.query_selector('body') else ""
                        if any(ind in page_text_after_nav for ind in ['reset your password', 'locked your account', 'unusual activity']):
                            username, karma = extract_user_info(page, log_callback=log_callback)
                            return ('locked', username, karma, 'Account locked due to unusual activity - Password reset required')
                        username, karma = extract_user_info(page, log_callback=log_callback)
                        if username and username != "Unknown":
                            return ('success', username, karma, None)
                    except:
                        pass
                    return ('success', 'Unknown', None, 'Logged in successfully but could not extract user info')
                else:
                    # Logged in but couldn't extract info - might be a different page
                    return ('success', 'Unknown', None, 'Logged in successfully but could not extract user info')
            else:
                # Not on Reddit domain - might be an error
                return ('error', None, None, f'Unexpected redirect to: {current_url}')
        
        # 7. Check for CAPTCHA
        captcha_indicators = ['captcha', 'verify you', 'human', 'robot', 'i\'m not a robot', 'recaptcha']
        if any(indicator in page_text for indicator in captcha_indicators):
            return ('error', None, None, 'CAPTCHA required - Manual intervention needed')
        
        # 8. Check for network/connection errors
        network_indicators = ['network error', 'connection error', 'timeout', 'failed to load', 'no internet']
        if any(indicator in page_text for indicator in network_indicators):
            return ('error', None, None, 'Network error - Connection issue detected')
        
        # 9. Check for Reddit maintenance/outage
        maintenance_indicators = ['maintenance', 'down for maintenance', 'temporarily unavailable', 'service unavailable', '503']
        if any(indicator in page_text for indicator in maintenance_indicators):
            return ('error', None, None, 'Reddit service unavailable - Maintenance or outage')
        
        # 10. Check URL for clues
        if 'error' in current_url.lower() or 'fail' in current_url.lower():
            return ('error', None, None, f'Error page detected - URL: {current_url}')
        
        # 11. Check for empty page or loading state
        if not page_text or len(page_text.strip()) < 50:
            # Page might still be loading
            try:
                page.wait_for_load_state('networkidle', timeout=3000)
                page_text = page.inner_text('body').lower() if page.query_selector('body') else ""
                if not page_text or len(page_text.strip()) < 50:
                    return ('error', None, None, 'Empty or incomplete page - Possible loading issue')
            except:
                return ('error', None, None, 'Page loading timeout - Content not loaded')
        
        # 12. Default error with more context
        return ('error', None, None, f'Unable to determine login status - URL: {current_url[:100]}, Page length: {len(page_text)} chars')
    
    except PlaywrightTimeoutError:
        return ('error', None, None, 'Timeout waiting for page to load - Page took too long to respond')
    except Exception as e:
        return ('error', None, None, f'Error detecting status: {str(e)}')

