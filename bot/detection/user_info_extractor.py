"""
User information extraction - Extract username and karma from Reddit pages
"""
import time
import re
from typing import Tuple, Optional, Callable


def extract_user_info(page, log_callback: Optional[Callable] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract username and karma from Reddit page, even when account is locked/reset.
    
    Args:
        page: Playwright page object
        log_callback: Optional logging function
        
    Returns:
        Tuple of (username, karma) - both can be None
    """
    username = None
    karma = None
    log = log_callback or (lambda x: None)
    
    try:
        # Method 1: Try to extract from current URL first (fastest, works even with banners)
        current_url = page.url
        if '/user/' in current_url:
            username = current_url.split('/user/')[-1].split('/')[0].strip()
            if username and len(username) > 0:
                # Found username from URL, try to get karma from current page
                try:
                    page_content = page.content()
                    # Look for karma in HTML even with banners
                    # IMPORTANT: Exclude numbers that are part of the username
                    username_numeric_part = None
                    # Extract any trailing numbers from username (e.g., "1901" from "Same_Mountain_1901")
                    username_match = re.search(r'(\d+)$', username)
                    if username_match:
                        username_numeric_part = username_match.group(1)
                    
                    karma_patterns = [
                        r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)\s*(?:post|comment)?\s*karma',
                        r'karma[^>]*>(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)',
                        r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)\s*karma',
                    ]
                    for pattern in karma_patterns:
                        match = re.search(pattern, page_content, re.IGNORECASE)
                        if match:
                            potential_karma = match.group(1)
                            # Check if this karma value is actually part of the username
                            karma_numeric = potential_karma.replace(',', '').replace('.', '').replace('k', '').replace('m', '').lower()
                            # Skip if it matches the numeric part of username
                            if username_numeric_part and karma_numeric == username_numeric_part:
                                continue
                            # Also check if it's a substring of username (but not standalone karma)
                            if username_numeric_part and username_numeric_part in karma_numeric and len(karma_numeric) > len(username_numeric_part):
                                # This might be a larger number containing username digits, be more careful
                                # Only accept if it's clearly karma (has k/m suffix or is much larger)
                                if 'k' in potential_karma.lower() or 'm' in potential_karma.lower():
                                    karma = potential_karma
                                    break
                                continue
                            karma = potential_karma
                            break
                except:
                    pass
        
        # Method 2: Try selectors (works when logged in normally)
        if not username:
            username_selectors = [
                'button[aria-label*="User"]',
                'a[href*="/user/"]',
                '[data-testid="user-menu"]',
                'button:has-text("/u/")',
                'a[href^="/user/"]',
                'a[href*="user/"]',
                '[data-testid="user-name"]',
                'span[data-testid="user-name"]'
            ]
            
            for selector in username_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem:
                        text = elem.inner_text() or elem.get_attribute('href') or ""
                        if '/u/' in text:
                            username = text.split('/u/')[-1].split()[0].strip().split('/')[0]
                        elif text.startswith('u/'):
                            username = text.split('u/')[-1].split()[0].strip().split('/')[0]
                        elif '/user/' in text:
                            username = text.split('/user/')[-1].split()[0].strip().split('/')[0]
                        else:
                            username = text.strip()
                        if username and len(username) > 0:
                            break
                except:
                    continue
        
        # Method 3: Try clicking user menu to get profile link
        if not username:
            try:
                user_menu = page.query_selector('button[aria-label*="User"], [data-testid="user-menu"], button:has-text("/u/")')
                if user_menu:
                    user_menu.click()
                    time.sleep(0.3)  # Reduced wait
                    profile_link = page.query_selector('a[href*="/user/"]')
                    if profile_link:
                        profile_url = profile_link.get_attribute('href')
                        if profile_url:
                            if not profile_url.startswith('http'):
                                profile_url = 'https://www.reddit.com' + profile_url
                            if '/user/' in profile_url:
                                username = profile_url.split('/user/')[-1].split('/')[0].strip()
            except:
                pass
        
        # Method 4: Navigate to /user/me if we're logged in but don't have username
        if not username:
            try:
                # Try navigating to /user/me endpoint - Reddit redirects to actual username
                page.goto('https://www.reddit.com/user/me', timeout=10000)
                time.sleep(1)  # Wait for redirect
                # Wait for navigation to complete
                try:
                    page.wait_for_load_state('domcontentloaded', timeout=3000)
                except:
                    pass
                current_url = page.url
                if '/user/' in current_url and '/user/me' not in current_url:
                    username = current_url.split('/user/')[-1].split('/')[0].strip()
                    # If we got username from redirect, try to get karma from this page
                    if username:
                        try:
                            page_content = page.content()
                            # Extract any trailing numbers from username to exclude from karma
                            username_numeric_part = None
                            username_match = re.search(r'(\d+)$', username)
                            if username_match:
                                username_numeric_part = username_match.group(1)
                            
                            karma_patterns = [
                                r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)\s*(?:post|comment)?\s*karma',
                                r'karma[^>]*>(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)',
                                r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)\s*karma',
                            ]
                            for pattern in karma_patterns:
                                match = re.search(pattern, page_content, re.IGNORECASE)
                                if match:
                                    potential_karma = match.group(1)
                                    # Check if this karma value is actually part of the username
                                    karma_numeric = potential_karma.replace(',', '').replace('.', '').replace('k', '').replace('m', '').lower()
                                    if username_numeric_part and karma_numeric == username_numeric_part:
                                        continue
                                    karma = potential_karma
                                    break
                        except:
                            pass
            except:
                pass
        
        # Extract karma - try multiple methods
        if username:
            try:
                # Navigate to profile if not already there
                profile_url = f'https://www.reddit.com/user/{username}'
                if '/user/' not in page.url or username not in page.url:
                    page.goto(profile_url, timeout=10000)
                    time.sleep(0.5)  # Reduced wait
                
                # Method 1: Try selectors
                karma_selectors = [
                    '[data-testid="karma"]',
                    '.karma',
                    'span:has-text("karma")',
                    'div:has-text("karma")',
                    '[id*="karma"]',
                    '[class*="karma"]'
                ]
                
                for selector in karma_selectors:
                    try:
                        karma_elem = page.query_selector(selector)
                        if karma_elem:
                            karma_text = karma_elem.inner_text()
                            numbers = re.findall(r'[\d,\.]+[km]?', karma_text)
                            if numbers:
                                karma = numbers[0]
                                break
                    except:
                        continue
                
                # Method 2: Search HTML content for karma patterns (works even with banners)
                if not karma:
                    try:
                        page_content = page.content()
                        # More comprehensive karma patterns - but exclude username patterns
                        # First, get username to exclude it from karma matches
                        username_to_exclude = username if username else ""
                        
                        # More comprehensive karma patterns
                        karma_patterns = [
                            r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)\s*(?:post|comment)?\s*karma',
                            r'karma[^>]*>(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)',
                            r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)\s*karma',
                            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:post|comment)\s*karma',
                        ]
                        for pattern in karma_patterns:
                            matches = re.findall(pattern, page_content, re.IGNORECASE)
                            if matches:
                                # Filter out matches that are part of username
                                for match in matches:
                                    # Check if this number appears in the username
                                    if username_to_exclude and match.replace(',', '').replace('.', '').replace('k', '').replace('m', '') in username_to_exclude:
                                        continue
                                    # Also check if it's in URL patterns that might be username
                                    if f'/user/{username_to_exclude}' in page_content and match in f'/user/{username_to_exclude}':
                                        continue
                                    karma = match
                                    break
                                if karma:
                                    break
                    except:
                        pass
                
                # Method 3: Try extracting from page text
                if not karma:
                    try:
                        page_text = page.inner_text('body') if page.query_selector('body') else ""
                        karma_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?[km]?)\s*karma', page_text, re.IGNORECASE)
                        if karma_match:
                            karma = karma_match.group(1)
                    except:
                        pass
            except Exception as e:
                # Even if extraction fails, we might have username
                pass
    
    except Exception as e:
        log(f"Warning: Error extracting user info: {e}")
    
    return (username, karma)

