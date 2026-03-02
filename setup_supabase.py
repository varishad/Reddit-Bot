"""
Script to help setup Supabase database schema
This will guide you through the setup process
"""
import os

def main():
    print("=" * 70)
    print("Reddit Bot - Supabase Database Setup")
    print("=" * 70)
    print("\nThis script will help you set up your Supabase database.")
    print("\nSteps:")
    print("1. Open your Supabase project")
    print("2. Go to SQL Editor")
    print("3. Run the schema SQL")
    print("\n" + "=" * 70)
    
    # Read the clean schema
    schema_path = "database/schema_clean.sql"
    if os.path.exists(schema_path):
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        print("\n✅ Schema file found!")
        print(f"\nFile location: {os.path.abspath(schema_path)}")
        
        # Ask if user wants to see the SQL
        show_sql = input("\nDo you want to see the SQL? (y/n): ").strip().lower()
        if show_sql == 'y':
            print("\n" + "=" * 70)
            print("SQL SCHEMA:")
            print("=" * 70)
            print(schema_sql)
            print("=" * 70)
        
        print("\n" + "=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print("\n1. Go to: https://supabase.com/dashboard/project/nszfjvbxrbsnnbixnboc/")
        print("2. Click on 'SQL Editor' in the left sidebar")
        print("3. Click 'New Query'")
        print("4. Copy the entire contents of 'database/schema_clean.sql'")
        print("5. Paste into the SQL Editor")
        print("6. Click 'Run' (or press Ctrl+Enter)")
        print("7. Wait for 'Success' message")
        print("\nAfter running the SQL, come back and we'll test the setup!")
        print("=" * 70)
        
        # Option to open file
        open_file = input("\nOpen schema file in default editor? (y/n): ").strip().lower()
        if open_file == 'y':
            os.startfile(os.path.abspath(schema_path))
    else:
        print(f"\n❌ Schema file not found: {schema_path}")
        print("Please make sure the file exists.")

if __name__ == "__main__":
    main()


