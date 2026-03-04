from database import Database
db = Database()

users = db.client.table('users').select('*').execute().data
acts = db.client.table('activations').select('*').execute().data

target_key = 'REDDIT-CAWX-C1J5-KNHK'
target_users = [u for u in users if u['license_key'] == target_key]
target_acts = [a for a in acts if a['license_key'] == target_key]

print(f"Total Users: {len(users)}")
print(f"Total Activations: {len(acts)}")
print(f"Found {target_key} in Users: {bool(target_users)}")
print(f"Found {target_key} in Activations: {bool(target_acts)}")

if target_acts:
    print(f"Status of target activation: {target_acts[0]}")

# Let's also create the new admin credential requested
new_key = "REDDIT-CAWX-C1J6-KNHK"
new_pw = "password123"
new_act = "UVSSORNGJ1NZ"

# clean up just in case
db.client.table('activations').delete().eq('license_key', new_key).execute()
db.client.table('users').delete().eq('license_key', new_key).execute()

db.create_user('Admin2', new_key, new_pw, 'Admin', 'Premium', 365)
db.client.table('activations').insert({
    'license_key': new_key, 
    'activation_code': new_act, 
    'is_used': False, 
    'activation_ip': '127.0.0.1'
}).execute()

print(f"\nCREATED NEW ADMIN CREDENTIAL:\nLicense Key: {new_key}\nPassword: {new_pw}\nActivation Code: {new_act}")
