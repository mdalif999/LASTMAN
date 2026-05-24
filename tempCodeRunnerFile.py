import sqlite3

def wipe_all_data():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    # সবগুলো টেবিল খালি করে দেওয়া
    tables = ['sales', 'inventory', 'audit_logs']
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Table '{table}' cleared.")
        except Exception as e:
            print(f"Error clearing {table}: {e}")
    
    conn.commit()
    conn.close()
    print("Database wiped successfully! Restart the app now.")

if __name__ == "__main__":
    confirm = input("ARE YOU SURE? This will delete EVERYTHING (inventory, sales, logs). (yes/no): ")
    if confirm.lower() == 'yes':
        wipe_all_data()