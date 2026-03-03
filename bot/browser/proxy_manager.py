"""
Proxy Manager - Handles loading and rotating proxies from a list file.
"""
import os
import random
from typing import Optional, List, Dict
from config import PROXY_LIST_FILE, PROXY_ROTATION_STRATEGY


class ProxyManager:
    def __init__(self, log_callback=None):
        self.log = log_callback or (lambda msg: None)
        self.proxies: List[Dict[str, str]] = []
        self.current_index = 0
        self.load_proxies()

    def load_proxies(self):
        """Load proxies from the file specified in config."""
        if not os.path.exists(PROXY_LIST_FILE):
            self.log(f"⚠️ [PROXY] Proxy list file not found: {PROXY_LIST_FILE}")
            return

        try:
            with open(PROXY_LIST_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 2:
                        proxy = {
                            "host": parts[0],
                            "port": parts[1],
                            "user": parts[2] if len(parts) >= 4 else "",
                            "pass": parts[3] if len(parts) >= 4 else ""
                        }
                        self.proxies.append(proxy)
            
            if self.proxies:
                self.log(f"✅ [PROXY] Loaded {len(self.proxies)} proxy(ies) from {PROXY_LIST_FILE}")
            else:
                self.log(f"⚠️ [PROXY] No valid proxies found in {PROXY_LIST_FILE}")
        except Exception as e:
            self.log(f"❌ [PROXY] Error loading proxies: {str(e)}")

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy based on the rotation strategy."""
        if not self.proxies:
            return None

        if PROXY_ROTATION_STRATEGY.lower() == "random":
            return random.choice(self.proxies)
        else:
            # Sequential (Round Robin)
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy

    def get_proxy_string(self, proxy: Dict[str, str]) -> str:
        """Format proxy dict as a string for logging."""
        return f"{proxy['host']}:{proxy['port']}"
