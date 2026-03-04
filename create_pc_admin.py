import requests
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

license_key = "REDDIT-CAWX-C1J5-KNHK"
password = "password123"
activation_code = "UVSSORNGJ1NY"
password_hash = hashlib.sha256(password.encode()).hexdigest()

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# Update existing user to be Admin
user_data = {
    "password_hash": password_hash,
    "notes": "PC Admin User",
    "role": "Admin"
}

response = requests.patch(
    f"{SUPABASE_URL}/rest/v1/users?license_key=eq.{license_key}",
    headers=headers,
    json=user_data
)

print(f"User update: {response.status_code}")
if response.status_code == 200 or response.status_code == 204:
    print("User updated to Admin role!")
    
    # Check if activation exists
    check = requests.get(
        f"{SUPABASE_URL}/rest/v1/activations?license_key=eq.{license_key}",
        headers=headers
    )
    
    if check.json():
        # Update activation
        act_response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/activations?license_key=eq.{license_key}",
            headers=headers,
            json={"activation_code": activation_code}
        )
        print(f"Activation updated: {act_response.status_code}")
    else:
        # Get user ID
        user_resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?license_key=eq.{license_key}",
            headers=headers
        )
        user_id = user_resp.json()[0]['id']
        
        # Create activation
        activation_data = {
            "license_key": license_key,
            "activation_code": activation_code,
            "activation_ip": "0.0.0.0",
            "user_id": user_id
        }
        
        act_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/activations",
            headers=headers,
            json=activation_data
        )
        print(f"Activation created: {act_response.status_code}")
else:
    print(f"Error: {response.status_code} - {response.text}")

print("")
print("PC Admin Credentials:")
print(f"  License Key: {license_key}")
print(f"  Password: {password}")
print(f"  Activation Code: {activation_code}")
print(f"  Role: Admin")
