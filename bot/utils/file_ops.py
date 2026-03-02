"""
File operations utilities
"""
from typing import Optional


def prune_credentials_entry(file_path: str, email: str, password: str, log_callback=None):
    """
    Remove a single 'email:password' token from the credentials source file if present.
    Parsing is by whitespace tokens (matching parse_credentials).
    
    Args:
        file_path: Path to credentials file
        email: Email to remove
        password: Password to remove
        log_callback: Optional logging function
    """
    try:
        from config import FILE_PRUNING_ENABLED
    except Exception:
        FILE_PRUNING_ENABLED = False
    
    if not FILE_PRUNING_ENABLED:
        return
    
    log = log_callback or (lambda x: None)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            return
        tokens = content.split()
        target = f"{email}:{password}"
        new_tokens = []
        removed = False
        for t in tokens:
            if not removed and t.strip() == target:
                removed = True
                continue
            new_tokens.append(t)
        if removed:
            new_content = "\n".join(new_tokens) if '\n' in content else " ".join(new_tokens)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
    except Exception as e:
        log(f"File pruning error: {str(e)}")

