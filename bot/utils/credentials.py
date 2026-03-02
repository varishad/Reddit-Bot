"""
Credential parsing utilities
"""
from typing import List, Tuple


def parse_credentials(file_path: str, log_callback=None) -> List[Tuple[str, str]]:
    """
    Parse credentials from file.
    
    Args:
        file_path: Path to credentials file
        log_callback: Optional logging function
        
    Returns:
        List of (email, password) tuples
    """
    credentials = []
    log = log_callback or (lambda x: None)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                log("Warning: credentials file is empty")
                return credentials
            
            entries = content.split()
            for entry in entries:
                entry = entry.strip()
                if not entry:
                    continue
                
                if ':' not in entry:
                    log(f"Warning: Skipping malformed entry: {entry}")
                    continue
                
                parts = entry.split(':', 1)
                if len(parts) == 2:
                    email, password = parts
                    credentials.append((email.strip(), password.strip()))
    except Exception as e:
        log(f"Error reading credentials file: {e}")
    
    return credentials

