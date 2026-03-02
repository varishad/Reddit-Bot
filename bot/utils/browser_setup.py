"""
Browser setup utilities - Playwright browser installation and checking
"""
import sys
import subprocess
import os
import tempfile


def ensure_playwright_browsers():
    """Ensure Playwright browsers are installed. Check by trying to launch."""
    try:
        from playwright.sync_api import sync_playwright
        from config import BROWSER_TYPE
        with sync_playwright() as p:
            try:
                # Try to launch browser based on config
                if BROWSER_TYPE.lower() == "firefox":
                    browser = p.firefox.launch(headless=True)
                else:
                    browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                return False
    except Exception:
        return False


def install_playwright_browsers(log_callback=None):
    """Install Playwright browsers using Playwright's installation API."""
    try:
        log = log_callback or print
        
        log("Downloading Playwright browsers (this may take a few minutes)...")
        log("Please wait, this is a one-time setup...")
        
        # Method 1: Try using Playwright's installation API directly
        try:
            from playwright._impl._driver import install_browsers
            from config import BROWSER_TYPE
            browser_name = "firefox" if BROWSER_TYPE.lower() == "firefox" else "chromium"
            log(f"Installing {browser_name} browser...")
            install_browsers([browser_name])
            log("Browsers installed successfully!")
            return True
        except ImportError:
            log("Direct API not available, trying subprocess method...")
        except Exception as e:
            log(f"Direct installation failed: {str(e)[:100]}")
        
        # Method 2: Use subprocess to run playwright install
        try:
            # For .exe, we need to extract Python from the bundle or use a different approach
            if getattr(sys, 'frozen', False):
                # Running from .exe - try to use the bundled Python
                # The .exe contains Python, so we can try to run playwright install
                # Create a temporary script to install browsers
                script_content = """
import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    pass  # This triggers browser download
"""
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(script_content)
                    script_path = f.name
                
                try:
                    # Try to run the script using the bundled Python
                    result = subprocess.run(
                        [sys.executable, script_path],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )
                    os.unlink(script_path)
                    
                    if result.returncode == 0:
                        log("Browsers installed successfully!")
                        return True
                except:
                    try:
                        os.unlink(script_path)
                    except:
                        pass
            
            # Fallback: Try standard method
            from config import BROWSER_TYPE
            browser_name = "firefox" if BROWSER_TYPE.lower() == "firefox" else "chromium"
            python_exe = sys.executable
            result = subprocess.run(
                [python_exe, "-m", "playwright", "install", browser_name],
                capture_output=True,
                text=True,
                timeout=600,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if result.returncode == 0:
                log("Browsers downloaded successfully!")
                return True
            else:
                error_msg = result.stderr or result.stdout
                log(f"Installation error: {error_msg[:200]}")
                return False
                
        except Exception as e:
            log(f"Subprocess installation failed: {str(e)[:100]}")
            return False
            
    except Exception as e:
        if log_callback:
            log_callback(f"Error installing browsers: {str(e)}")
        return False

