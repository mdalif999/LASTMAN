import sqlite3

def check_database():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    # database-e ki ki table ache tar nam ber kora
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("--- Database Tables and Columns ---")
    for table in tables:
        table_name = table[0]
        if table_name != 'sqlite_sequence': # auto-increment record bad deyar jonno
            print(f"\nTable Name: {table_name}")
            
            # Protita table-er column er nam o type ber kora
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - Column: {col[1]} ({col[2]})")
                
    conn.close()

if __name__ == "__main__":
    check_database()