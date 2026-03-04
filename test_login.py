import sys
from database import Database

db = Database()
success, msg, user = db.authenticate_user("REDDIT-CAWX-C1J5-KNHK", "password123")
print(f"Success: {success}")
print(f"Message: {msg}")
if user:
    print(f"User: {user['username']}")
