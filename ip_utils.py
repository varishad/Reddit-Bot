"""
IP and Location Utilities - Get IP address and country information
"""
import requests
from typing import Optional, Tuple
from typing import Dict, Any
from logger import setup_logger

logger = setup_logger("ip_utils")

def get_ip_info() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get current IP address, country, and location.
    Returns: (ip_address, country, location_string)
    """
    try:
        # Try ipapi.co first (free, no API key needed)
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            ip = data.get('ip', '')
            country = data.get('country_name', '')
            city = data.get('city', '')
            region = data.get('region', '')
            
            # Build location string
            location_parts = []
            if city:
                location_parts.append(city)
            if region:
                location_parts.append(region)
            if country:
                location_parts.append(country)
            
            location = ', '.join(location_parts) if location_parts else country or 'Unknown'
            
            return ip, country, location
    except Exception as e:
        logger.warning(f"Failed to get IP info from ipapi.co: {str(e)}")
    
    try:
        # Fallback to ipify + ip-api
        ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if ip_response.status_code == 200:
            ip = ip_response.json().get('ip', '')
            
            # Get country from ip-api
            try:
                geo_response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
                if geo_response.status_code == 200:
                    geo_data = geo_response.json()
                    country = geo_data.get('country', '')
                    city = geo_data.get('city', '')
                    region = geo_data.get('regionName', '')
                    
                    location_parts = []
                    if city:
                        location_parts.append(city)
                    if region:
                        location_parts.append(region)
                    if country:
                        location_parts.append(country)
                    
                    location = ', '.join(location_parts) if location_parts else country or 'Unknown'
                    
                    return ip, country, location
            except Exception as e:
                logger.warning(f"Failed to get geo info for IP {ip}: {str(e)}")
            
            # If geo lookup fails, just return IP
            return ip, None, None
    except Exception as e:
        logger.warning(f"Failed to get fallback IP info: {str(e)}")
    
    return None, None, None

def get_ip_address() -> Optional[str]:
    """Get current IP address (simple version)."""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        logger.warning(f"Failed to get simple IP address: {str(e)}")
    return None

def get_geo_profile() -> Dict[str, Any]:
    """
    Return geolocation profile for aligning browser context:
    {
      'ip': str|None,
      'country': str|None,
      'location': str|None,
      'timezone': str|None,
      'locale': str|None,         # e.g., 'en-US'
      'latitude': float|None,
      'longitude': float|None
    }
    """
    profile: Dict[str, Any] = {
        "ip": None,
        "country": None,
        "location": None,
        "timezone": None,
        "locale": None,
        "latitude": None,
        "longitude": None
    }
    try:
        r = requests.get('https://ipapi.co/json/', timeout=5)
        if r.status_code == 200:
            data = r.json()
            profile["ip"] = data.get("ip")
            profile["country"] = data.get("country_name")
            city = data.get("city", "")
            region = data.get("region", "")
            parts = [p for p in [city, region, profile["country"]] if p]
            profile["location"] = ', '.join(parts) if parts else profile["country"]
            profile["timezone"] = data.get("timezone")
            # languages comes like 'en-US,en;q=0.9'; pick the first tag if present
            languages = (data.get("languages") or "").split(",")
            locale = languages[0].strip() if languages and languages[0].strip() else None
            # Normalize to dash format (already is), fallback to en-US
            profile["locale"] = locale or "en-US"
            profile["latitude"] = data.get("latitude")
            profile["longitude"] = data.get("longitude")
            return profile
    except Exception as e:
        logger.warning(f"Failed to get geo profile from ipapi.co: {str(e)}")

    # Fallback: best effort using ip-api.com
    try:
        ip_resp = requests.get('https://api.ipify.org?format=json', timeout=5)
        if ip_resp.status_code == 200:
            ip = ip_resp.json().get("ip")
            geo_resp = requests.get(f'http://ip-api.com/json/{ip}?fields=status,country,city,regionName,lat,lon,timezone', timeout=5)
            if geo_resp.status_code == 200:
                g = geo_resp.json()
                if g.get("status") == "success":
                    profile["ip"] = ip
                    profile["country"] = g.get("country")
                    city = g.get("city", "")
                    region = g.get("regionName", "")
                    parts = [p for p in [city, region, profile["country"]] if p]
                    profile["location"] = ', '.join(parts) if parts else profile["country"]
                    profile["timezone"] = g.get("timezone")
                    # Best guess for locale from country (very rough)
                    # Could be improved with a mapping; default en-US
                    profile["locale"] = "en-US"
                    profile["latitude"] = g.get("lat")
                    profile["longitude"] = g.get("lon")
    except Exception as e:
        logger.warning(f"Failed to get geo profile fallback: {str(e)}")

    return profile

