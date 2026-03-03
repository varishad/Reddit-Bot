from config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client
from datetime import datetime, timedelta, timezone

def populate_user_fields():
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Define sample data
        license_key = "REDDIT-CAWX-C1J5-KNHK"
        machine_id = "TEST-PC-7788-X99"
        
        # Times in ISO format with UTC timezone
        now = datetime.now(timezone.utc)
        plan_start = now
        plan_end = now + timedelta(days=30)
        
        print(f"Updating user with license: {license_key}")
        print(f"Machine ID: {machine_id}")
        print(f"Start: {plan_start.isoformat()}")
        print(f"End: {plan_end.isoformat()}")
        
        # Perform update
        response = client.table('users').update({
            'machine_id': machine_id,
            'plan_start_date': plan_start.isoformat(),
            'plan_end_date': plan_end.isoformat(),
            'is_active': True # Ensure user is active
        }).eq('license_key', license_key).execute()
        
        if response.data:
            print("✅ Successfully updated user fields")
            print(f"Updated data: {response.data}")
        else:
            print("❌ User not found or no changes made")
            
    except Exception as e:
        print(f"❌ Error during update: {e}")

if __name__ == "__main__":
    populate_user_fields()
