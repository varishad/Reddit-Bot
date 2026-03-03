"""
Local logging utility - Appends results to text files for competitive parity.
"""
import os
from datetime import datetime
from config import LOCAL_LOGGING_ENABLED

def append_to_local_log(status: str, email: str, password: str, username: str = None, karma: str = None):
    """
    Append credential results to local .txt files categorized by status.
    Format: email:password | username: {username} | karma: {karma} | time: {timestamp}
    """
    if not LOCAL_LOGGING_ENABLED:
        return

    # Ensure results directory exists
    results_dir = "results"
    if not os.path.exists(results_dir):
        try:
            os.makedirs(results_dir)
        except Exception:
            # Fallback to current directory if can't create
            results_dir = "."

    # Map status to filename
    status_map = {
        "success": "good_account.txt",
        "invalid": "wrong_pass.txt",
        "banned": "banned.txt",
        "locked": "locked.txt",
        "error": "error.txt"
    }
    
    filename = status_map.get(status.lower(), "unclear_account.txt")
    file_path = os.path.join(results_dir, filename)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{email}:{password}"
    
    details = []
    if username and username != "Unknown":
        details.append(f"username: {username}")
    if karma:
        details.append(f"karma: {karma}")
    details.append(f"time: {timestamp}")
    
    if details:
        log_entry += " | " + " | ".join(details)
    
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        # Silent fail or print to console if needed, but don't crash the bot
        print(f"⚠️ Failed to write local log: {str(e)}")
