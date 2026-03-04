"""
Advanced Browser Fingerprint Generator

Generates realistic, matching sets of User-Agents, Client Hints, and Hardware Concurrency
to bypass advanced anti-bot network security systems.
"""
import random

def generate_fingerprint():
    """Generates a consistent set of browser fingerprint attributes."""
    
    profiles = [
        # Chrome 122 Windows
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "ch_mobile": "?0",
            "ch_platform": '"Windows"',
            "platform": "Win32",
            "vendor": "Google Inc.",
            "renderer": "Google SwiftShader",
        },
        # Chrome 121 Windows
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "ch_ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "ch_mobile": "?0",
            "ch_platform": '"Windows"',
            "platform": "Win32",
            "vendor": "Google Inc.",
            "renderer": "ANGLE (Intel, Intel(R) UHD Graphics, Direct3D 11 vs_5_0 ps_5_0)",
        },
        # Edge 122 Windows
        {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
            "ch_mobile": "?0",
            "ch_platform": '"Windows"',
            "platform": "Win32",
            "vendor": "Google Inc.",
            "renderer": "ANGLE (AMD, AMD Radeon(TM) Graphics, Direct3D 11 vs_5_0 ps_5_0)",
        },
        # Chrome 122 macOS
        {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "ch_ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "ch_mobile": "?0",
            "ch_platform": '"macOS"',
            "platform": "MacIntel",
            "vendor": "Apple Inc.",
            "renderer": "Apple M1",
        },
        # Chrome 121 macOS
        {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "ch_ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            "ch_mobile": "?0",
            "ch_platform": '"macOS"',
            "platform": "MacIntel",
            "vendor": "Apple Inc.",
            "renderer": "Apple M2",
        }
    ]
    
    base_profile = random.choice(profiles)
    
    # 2. Hardware specs
    hardware_concurrency = random.choice([4, 6, 8, 12, 16])
    device_memory = random.choice([4, 8, 16, 32])
    
    # 3. Screen 
    screen_depth = random.choice([24, 32])
    
    return {
        **base_profile,
        "hardware_concurrency": hardware_concurrency,
        "device_memory": device_memory,
        "screen_depth": screen_depth
    }
