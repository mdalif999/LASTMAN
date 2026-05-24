import time
import sqlite3
from supabase import create_client, Client

# ==================== CONFIGURATION ====================
# এখানে আপনার সুপাবেজের আসল URL এবং API Key বসিয়ে দিন
SUPABASE_URL = "https://poynesakhmzcguvrihul.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveW5lc2FraG16Y2d1dnJpaHVsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTI4NTAwOCwiZXhwIjoyMDk0ODYxMDA4fQ.6i6uMdNOPeRBs4JXT8-20dYI5wdNVHj8zn0X4ymOzAY"
# =======================================================

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase connection established successfully!")
except Exception as e:
    print(f"Failed to connect to Supabase: {e}")
    exit(1)

def get_local_db():
    return sqlite3.connect("inventory.db")

def sync_inventory():
    conn = get_local_db()
    cursor = conn.cursor()
    
    # যে মালামালগুলো এখনো সিঙ্ক হয়নি (is_synced = 0) সেগুলো তুলবো
    cursor.execute("""
        SELECT id, brand, die_no, name, color, thick, total_in, unit_in, buy_price, sell_price, unit_type, current_stock 
        FROM inventory WHERE is_synced = 0
    """)
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return

    print(f"Syncing {len(rows)} inventory items to cloud...")
    for row in rows:
        data = {
            "id": row[0], "brand": row[1], "die_no": row[2], "name": row[3],
            "color": row[4], "thick": row[5], "total_in": row[6], "unit_in": row[7],
            "buy_price": row[8], "sell_price": row[9], "unit_type": row[10], "current_stock": row[11]
        }
        try:
            # সুপাবেজে আপসার্ট (Upsert) করবো - থাকলে আপডেট হবে, না থাকলে নতুন ঢুকবে
            supabase.table("inventory").upsert(data).execute()
            # সিঙ্ক সফল হলে লোকাল ডাটাবেজে ফ্ল্যাগ ১ করে দেবো
            cursor.execute("UPDATE inventory SET is_synced = 1 WHERE id = ?", (row[0],))
            conn.commit()
        except Exception as e:
            print(f"Error syncing inventory ID {row[0]}: {e}")
            
    conn.close()

def sync_sales():
    conn = get_local_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, order_id, sale_date, sale_time, customer_name, customer_phone, customer_address,
               profile_name, color, spec, die_no, quantity, price, total, discount, paid_amount, due_amount, profit 
        FROM sales WHERE is_synced = 0
    """)
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return

    print(f"Syncing {len(rows)} sales records to cloud...")
    for row in rows:
        data = {
            "id": row[0], "order_id": row[1], "sale_date": row[2], "sale_time": row[3],
            "customer_name": row[4], "customer_phone": row[5], "customer_address": row[6],
            "profile_name": row[7], "color": row[8], "spec": row[9], "die_no": row[10],
            "quantity": row[11], "price": row[12], "total": row[13], "discount": row[14],
            "paid_amount": row[15], "due_amount": row[16], "profit": row[17]
        }
        try:
            supabase.table("sales").upsert(data).execute()
            cursor.execute("UPDATE sales SET is_synced = 1 WHERE id = ?", (row[0],))
            conn.commit()
        except Exception as e:
            print(f"Error syncing sale ID {row[0]}: {e}")
            
    conn.close()

def sync_audit_logs():
    conn = get_local_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, timestamp, action_type, product_name, details, user 
        FROM audit_logs WHERE is_synced = 0
    """)
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return

    print(f"Syncing {len(rows)} audit logs to cloud...")
    for row in rows:
        data = {
            "id": row[0], "timestamp": row[1], "action_type": row[2],
            "product_name": row[3], "details": row[4], "user_name": row[5] # সুপাবেজের কলাম নামের সাথে ম্যাচ করা হলো
        }
        try:
            supabase.table("audit_logs").upsert(data).execute()
            cursor.execute("UPDATE audit_logs SET is_synced = 1 WHERE id = ?", (row[0],))
            conn.commit()
        except Exception as e:
            print(f"Error syncing log ID {row[0]}: {e}")
            
    conn.close()

def start_sync_loop(interval_seconds=10):
    """নির্দিষ্ট সময় পরপর ব্যাকগ্রাউন্ডে ডেটা সিঙ্ক করার লুপ"""
    print(f"Sync worker started. Monitoring local database every {interval_seconds} seconds...")
    while True:
        try:
            sync_inventory()
            sync_sales()
            sync_audit_logs()
        except Exception as e:
            print(f"Sync worker encountered an error: {e}")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    # টেস্ট করার জন্য স্ক্রিপ্টটি সরাসরি রান করা যাবে
    start_sync_loop(interval_seconds=5)