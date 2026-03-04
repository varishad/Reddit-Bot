"""
Form utilities - Form field operations, clearing, and validation.
"""
from typing import Optional, List
from playwright.sync_api import Page, Locator
from bot.humanization.typing import clear_input as clear_input_util, type_human as type_human_util
from config import HUMANIZE_INPUT


def clear_form_fields(page: Page, log_callback: Optional[callable] = None) -> bool:
    """
    Clear username and password fields in the login form.
    """
    log = log_callback or (lambda msg: None)
    
    try:
        # Use Locators for reliability
        username_selectors = [
            'faceplate-text-input[type="text"]',
            'faceplate-text-input[name="username"]',
            'input[name="username"]',
            'input[id*="username"]'
        ]
        username_cleared = False
        for selector in username_selectors:
            try:
                field = page.locator(selector).first
                if field.is_visible():
                    if 'faceplate' in selector.lower():
                        inner = field.locator('input')
                        inner.fill("")
                    else:
                        field.fill("")
                    username_cleared = True
                    break
            except:
                continue
        
        password_selectors = [
            'faceplate-text-input[type="password"]',
            'input[type="password"]'
        ]
        for selector in password_selectors:
            try:
                field = page.locator(selector).first
                if field.is_visible():
                    if 'faceplate' in selector.lower():
                        field.locator('input').fill("")
                    else:
                        field.fill("")
                    break
            except:
                continue
        
        if username_cleared:
            log("♻️ Cleared form fields for next account")
            return True
        return False
    except Exception:
        return False


def is_form_visible(page: Page) -> bool:
    """Check if login form is visible."""
    try:
        return page.locator('form, input[name="username"], input[type="password"]').first.is_visible()
    except:
        return False


def ensure_form_ready(page: Page, timeout: int = 4000) -> bool:
    """Ensure login form is ready and visible."""
    try:
        page.wait_for_selector('form, input[name="username"], input[type="password"]', timeout=timeout)
        return True
    except:
        return False


def fill_username_field(
    page: Page,
    email: str,
    log_callback: Optional[callable] = None
) -> Optional[Locator]:
    """Fill the username/email field using Locators."""
    log = log_callback or (lambda msg: None)
    
    email_selectors = [
        'faceplate-text-input[type="text"]',
        'faceplate-text-input[name="username"]',
        'input[name="username"]',
        'input[type="text"]',
        '#loginUsername',
        '#username'
    ]
    
    for selector in email_selectors:
        try:
            field = page.locator(selector).first
            if field.is_visible():
                field.click()
                target = field
                if 'faceplate' in selector.lower():
                    target = field.locator('input')
                
                log("Entering username...")
                try:
                    clear_input_util(target)
                except:
                    target.fill("")
                
                if HUMANIZE_INPUT:
                    type_human_util(target, email)
                else:
                    target.fill(email)
                return field
        except:
            continue
    return None


def fill_password_field(
    page: Page,
    password: str,
    log_callback: Optional[callable] = None
) -> Optional[Locator]:
    """Fill the password field using Locators."""
    log = log_callback or (lambda msg: None)
    
    password_selectors = [
        'faceplate-text-input[type="password"]',
        'input[type="password"]',
        'input[name="password"]'
    ]
    
    for selector in password_selectors:
        try:
            field = page.locator(selector).first
            if field.is_visible():
                target = field
                if 'faceplate' in selector.lower():
                    target = field.locator('input')
                
                log("Entering password...")
                try:
                    clear_input_util(target)
                except:
                    target.fill("")
                
                if HUMANIZE_INPUT:
                    type_human_util(target, password)
                else:
                    target.fill(password)
                return field
        except:
            continue
    return None


def submit_form(page: Page, password_field: Optional[Locator] = None, log_callback: Optional[callable] = None) -> bool:
    """
    Submit the login form.
    
    Args:
        page: Playwright page object
        password_field: Optional password field locator (for Enter key submission)
        log_callback: Optional logging function
        
    Returns:
        True if form was submitted, False otherwise
    """
    log = log_callback or (lambda msg: None)
    
    form_submitted = False
    
    try:
        from config import INSTANT_FILL_ENABLED
        if HUMANIZE_INPUT and not INSTANT_FILL_ENABLED:
            from bot.humanization.behavior import human_pause as human_pause_util
            human_pause_util()
        
        # Use Enter key (fastest), with slight delay
        if password_field:
            if not INSTANT_FILL_ENABLED:
                password_field.press('Enter')
            else:
                # Truly instant
                password_field.press('Enter', delay=0)
            form_submitted = True
    except:
        pass
    
    # Fallback to button click if Enter didn't work
    if not form_submitted:
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Log In")',
            'button:has-text("Sign In")',
            'input[type="submit"]'
        ]
        
        for selector in submit_selectors:
            try:
                submit_button = page.locator(selector).first
                if submit_button.is_visible():
                    submit_button.click()
                    form_submitted = True
                    break
            except:
                continue
    
    return form_submitted

