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
    
    Args:
        page: Playwright page object
        log_callback: Optional logging function
        
    Returns:
        True if fields were cleared, False otherwise
    """
    log = log_callback or (lambda msg: None)
    
    try:
        # Try multiple selectors for username field (including faceplate)
        username_selectors = [
            'faceplate-text-input[type="text"]',
            'faceplate-text-input[name="username"]',
            'faceplate-text-input',
            'input[name="username"]',
            'input[id*="username"]',
            'input[type="text"]'
        ]
        username_cleared = False
        for selector in username_selectors:
            try:
                username_field = page.query_selector(selector)
                if username_field and username_field.is_visible():
                    # For faceplate, get inner input
                    if 'faceplate' in selector.lower():
                        inner_input = username_field.query_selector('input')
                        if inner_input:
                            inner_input.fill("")
                            username_cleared = True
                            break
                    else:
                        username_field.fill("")
                        username_cleared = True
                        break
            except:
                continue
        
        # Clear password field (including faceplate inputs)
        password_selectors = [
            'faceplate-text-input[type="password"]',
            'faceplate-text-input[name="password"]',
            'faceplate-text-input',
            'input[type="password"]',
            'input[name="password"]',
            'input[id*="password"]'
        ]
        for selector in password_selectors:
            try:
                password_field = page.query_selector(selector)
                if password_field and password_field.is_visible():
                    # For faceplate, get inner input
                    if 'faceplate' in selector.lower():
                        inner_input = password_field.query_selector('input')
                        if inner_input:
                            inner_input.fill("")
                            break
                    else:
                        password_field.fill("")
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
    """
    Check if login form is visible on the page.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if form is visible, False otherwise
    """
    try:
        login_form = page.query_selector('form, input[name="username"], input[type="password"]')
        return login_form is not None
    except Exception:
        return False


def ensure_form_ready(page: Page, timeout: int = 4000) -> bool:
    """
    Ensure login form is ready and visible.
    
    Args:
        page: Playwright page object
        timeout: Timeout in milliseconds
        
    Returns:
        True if form is ready, False otherwise
    """
    try:
        page.wait_for_selector('form, input[name="username"], input[type="password"]', timeout=timeout)
        return True
    except Exception:
        return False


def fill_username_field(
    page: Page,
    email: str,
    log_callback: Optional[callable] = None
) -> Optional[Locator]:
    """
    Fill the username/email field in the login form.
    
    Args:
        page: Playwright page object
        email: Email/username to fill
        log_callback: Optional logging function
        
    Returns:
        The filled field locator if successful, None otherwise
    """
    log = log_callback or (lambda msg: None)
    
    email_selectors = [
        'faceplate-text-input[type="text"]',  # Reddit's new UI - fastest
        'faceplate-text-input[name="username"]',
        'faceplate-text-input',  # Fallback for new UI
        'input[name="username"]',  # Old UI fallback
        'input[name="user"]',
        'input[type="text"]',
        'input[id*="username"]',
        'input[id*="user"]',
        'input[placeholder*="username" i]',
        'input[placeholder*="email" i]',
        'input[autocomplete="username"]',
        'form input[type="text"]:first-of-type',
        '#loginUsername',
        '#username'
    ]
    
    email_filled = False
    email_field = None
    
    for selector in email_selectors:
        try:
            email_field = page.query_selector(selector)
            if email_field and email_field.is_visible():
                email_field.click()
                # For faceplate-text-input, need to find inner input
                if 'faceplate' in selector.lower():
                    inner_input = email_field.query_selector('input')
                    if inner_input:
                        log("Entering username...")
                        # Clear previous value
                        try:
                            clear_input_util(inner_input)
                        except Exception:
                            try:
                                inner_input.fill("")
                            except Exception:
                                pass
                        if HUMANIZE_INPUT:
                            type_human_util(inner_input, email)
                        else:
                            inner_input.fill(email)
                    else:
                        try:
                            clear_input_util(email_field)
                        except Exception:
                            try:
                                email_field.fill("")
                            except Exception:
                                pass
                        if HUMANIZE_INPUT:
                            type_human_util(email_field, email)
                        else:
                            email_field.fill(email)
                else:
                    try:
                        clear_input_util(email_field)
                    except Exception:
                        try:
                            email_field.fill("")
                        except Exception:
                            pass
                    if HUMANIZE_INPUT:
                        type_human_util(email_field, email)
                    else:
                        email_field.fill(email)
                email_filled = True
                break
        except:
            continue
    
    if not email_filled:
        try:
            # Try faceplate-text-input first (new UI)
            faceplate_inputs = page.query_selector_all('faceplate-text-input[type="text"]')
            if faceplate_inputs:
                email_field = faceplate_inputs[0]
                if email_field.is_visible():
                    email_field.click()
                    log("Entering username...")
                    inner_input = email_field.query_selector('input')
                    if inner_input:
                        try:
                            clear_input_util(inner_input)
                        except Exception:
                            try:
                                inner_input.fill("")
                            except Exception:
                                pass
                        if HUMANIZE_INPUT:
                            type_human_util(inner_input, email)
                        else:
                            inner_input.fill(email)
                    else:
                        try:
                            clear_input_util(email_field)
                        except Exception:
                            try:
                                email_field.fill("")
                            except Exception:
                                pass
                        if HUMANIZE_INPUT:
                            type_human_util(email_field, email)
                        else:
                            email_field.fill(email)
                    email_filled = True
            else:
                text_inputs = page.query_selector_all('form input[type="text"]')
                if text_inputs:
                    email_field = text_inputs[0]
                    if email_field.is_visible():
                        email_field.click()
                        log("Entering username...")
                        try:
                            clear_input_util(email_field)
                        except Exception:
                            try:
                                email_field.fill("")
                            except Exception:
                                pass
                        if HUMANIZE_INPUT:
                            type_human_util(email_field, email)
                        else:
                            email_field.fill(email)
                        email_filled = True
        except:
            pass
    
    return email_field if email_filled else None


def fill_password_field(
    page: Page,
    password: str,
    log_callback: Optional[callable] = None
) -> Optional[Locator]:
    """
    Fill the password field in the login form.
    
    Args:
        page: Playwright page object
        password: Password to fill
        log_callback: Optional logging function
        
    Returns:
        The filled password field locator if successful, None otherwise
    """
    log = log_callback or (lambda msg: None)
    
    password_selectors = [
        'faceplate-text-input[type="password"]',  # Reddit's new UI - fastest
        'faceplate-text-input[name="password"]',
        'faceplate-text-input',  # Fallback for new UI
        'input[name="password"]',  # Old UI fallback
        'input[type="password"]',
        'input[id*="password"]'
    ]
    
    password_filled = False
    password_field = None
    
    for selector in password_selectors:
        try:
            password_field = page.query_selector(selector)
            if password_field and password_field.is_visible():
                # For faceplate-text-input, need to find inner input
                if 'faceplate' in selector.lower():
                    inner_input = password_field.query_selector('input')
                    if inner_input:
                        log("Entering password...")
                        try:
                            clear_input_util(inner_input)
                        except Exception:
                            try:
                                inner_input.fill("")
                            except Exception:
                                pass
                        if HUMANIZE_INPUT:
                            type_human_util(inner_input, password)
                        else:
                            inner_input.fill(password)
                    else:
                        try:
                            clear_input_util(password_field)
                        except Exception:
                            try:
                                password_field.fill("")
                            except Exception:
                                pass
                        if HUMANIZE_INPUT:
                            type_human_util(password_field, password)
                        else:
                            password_field.fill(password)
                else:
                    try:
                        clear_input_util(password_field)
                    except Exception:
                        try:
                            password_field.fill("")
                        except Exception:
                            pass
                    if HUMANIZE_INPUT:
                        type_human_util(password_field, password)
                    else:
                        password_field.fill(password)
                password_filled = True
                break
        except:
            continue
    
    return password_field if password_filled else None


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
        if HUMANIZE_INPUT:
            from bot.humanization.behavior import human_pause as human_pause_util
            human_pause_util()
        
        # Use Enter key (fastest), with slight delay
        if password_field:
            log("Submitted form via Enter key")
            password_field.press('Enter')
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
                submit_button = page.query_selector(selector)
                if submit_button:
                    submit_button.click()
                    form_submitted = True
                    break
            except:
                continue
    
    return form_submitted

