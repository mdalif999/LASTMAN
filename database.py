import sqlite3
from datetime import datetime


# ========== CONNECTION ==========
def get_db_connection():
    return sqlite3.connect("inventory.db")


# ========== INIT ==========
def init_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    # ১. ইনভেন্টরি টেবিল
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            brand       TEXT,
            die_no      TEXT,
            name        TEXT,
            color       TEXT,
            thick       TEXT,
            total_in    REAL DEFAULT 0,
            unit_in     REAL DEFAULT 120,
            buy_price   REAL DEFAULT 0,
            sell_price  REAL DEFAULT 0,
            unit_type   TEXT DEFAULT 'alum'
        )
    """)

    # ২. সেলস টেবিল  ← সব column এখানেই আছে, কোনো ALTER দরকার নেই
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id         TEXT,
            sale_date        TEXT,
            sale_time        TEXT,
            customer_name    TEXT DEFAULT 'Cash',
            customer_phone   TEXT DEFAULT '',
            customer_address TEXT DEFAULT '',
            profile_name     TEXT,
            color            TEXT,
            spec             TEXT,
            die_no           TEXT,
            quantity         REAL DEFAULT 0,
            price            REAL DEFAULT 0,
            total            REAL DEFAULT 0,
            discount         REAL DEFAULT 0,
            paid_amount      REAL DEFAULT 0,
            due_amount       REAL DEFAULT 0,
            profit           REAL DEFAULT 0
        )
    """)

    # ৩. অডিট লগ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT DEFAULT CURRENT_TIMESTAMP,
            action_type  TEXT,
            product_name TEXT,
            details      TEXT,
            user         TEXT DEFAULT 'Admin'
        )
    """)

    # ৪. ব্র্যান্ড
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO brands (name) VALUES ('Altech'), ('Chunghua')")

    # ৫. সেটিংস
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('app_password', '123')")

    # ৬. বিজনেস প্রোফাইল
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_profile (
            id         INTEGER PRIMARY KEY,
            owner_name TEXT,
            shop_name  TEXT,
            address    TEXT,
            phone      TEXT,
            logo_path  TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM business_profile")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO business_profile (owner_name, shop_name, address, phone, logo_path)
            VALUES (?, ?, ?, ?, ?)
        """, ("আলিফ", "আমার দোকান", "ঠিকানা এখানে", "০১৭...", ""))

    # ৭. পুরনো sales টেবিল থেকে নতুন column যোগ (যদি DB আগের হয়)
    _safe_add_columns(cursor, "sales", [
        ("order_id",         "TEXT"),
        ("sale_time",        "TEXT"),
        ("customer_address", "TEXT"),
        ("quantity",         "REAL DEFAULT 0"),
        ("price",            "REAL DEFAULT 0"),
        ("total",            "REAL DEFAULT 0"),
        ("discount",         "REAL DEFAULT 0"),
        ("due_amount",       "REAL DEFAULT 0"),
        ("profit",           "REAL DEFAULT 0"),
    ])

    # ৮. inventory unit_type column
    _safe_add_columns(cursor, "inventory", [
        ("unit_type", "TEXT DEFAULT 'alum'"),
    ])

    conn.commit()
    conn.close()
    _sync_database_names()


def _safe_add_columns(cursor, table, columns):
    """কলাম না থাকলে যোগ করে, থাকলে চুপ থাকে।"""
    for col, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass


def _sync_database_names():
    """পুরনো action_type ভ্যালু নতুনে আপডেট করে।"""
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
        if cursor.fetchone():
            cursor.execute("UPDATE audit_logs SET action_type='STOCK_UPDATE' WHERE action_type='Stock Update'")
            cursor.execute("UPDATE audit_logs SET action_type='NEW_ITEM'     WHERE action_type='New Item'")
            conn.commit()
    except Exception as e:
        print(f"Sync warning: {e}")
    finally:
        conn.close()


# ========== SETTINGS ==========
def init_settings_db():
    init_db()  # init_db তেই সব করা হয়েছে


def get_app_password():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='app_password'")
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "123"


def update_app_password(new_pw):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value=? WHERE key='app_password'", (new_pw,))
    conn.commit()
    conn.close()


# ========== BRANDS ==========
def get_brands():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM brands ORDER BY name ASC")
    brands = [row[0] for row in cursor.fetchall()]
    conn.close()
    return brands


def add_new_brand(brand_name):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO brands (name) VALUES (?)", (brand_name.strip(),))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ========== INVENTORY ==========
def add_inventory_item(brand, die_no, name, color, thick, total_in, unit_in, buy, sell, unit_type='alum'):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    if unit_type not in ['alum', 'wool']:
        unit_in = 1.0
    try:
        cursor.execute("""
            INSERT INTO inventory (brand, die_no, name, color, thick, total_in, unit_in, buy_price, sell_price, unit_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (brand, die_no, name, color, thick, total_in, unit_in, buy, sell, unit_type))
        cursor.execute("""
            INSERT INTO audit_logs (action_type, product_name, details, user)
            VALUES (?, ?, ?, ?)
        """, ("Opening Stock", name, f"Brand:{brand} Die:{die_no} Color:{color} Qty:{total_in}", "Admin"))
        conn.commit()
    except Exception as e:
        print(f"add_inventory_item error: {e}")
    finally:
        conn.close()


def get_inventory_items():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, brand, die_no, name, color, thick,
                   total_in, unit_in, buy_price, sell_price, unit_type
            FROM inventory ORDER BY id DESC
        """)
        items = cursor.fetchall()
        result = []
        for item in items:
            row = list(item)
            row[6] = float(row[6] or 0)    # total_in
            row[7] = float(row[7] or 120)  # unit_in
            result.append(tuple(row))
        return result
    except sqlite3.OperationalError as e:
        print(f"get_inventory_items error: {e}")
        return []
    finally:
        conn.close()


def update_inventory_item(item_id, brand, die_no, name, color, thick, buy, sell, total_in=None):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT buy_price, sell_price, total_in FROM inventory WHERE id=?", (item_id,))
    row = cursor.fetchone()
    old_buy, old_sell, old_stock = row if row else (0, 0, 0)

    if total_in is not None:
        cursor.execute("""
            UPDATE inventory SET brand=?, die_no=?, name=?, color=?, thick=?, buy_price=?, sell_price=?, total_in=?
            WHERE id=?
        """, (brand, die_no, name, color, thick, buy, sell, total_in, item_id))
        diff = total_in - old_stock
        if diff != 0:
            action = "Stock Added" if diff > 0 else "Stock Removed"
            cursor.execute("""
                INSERT INTO audit_logs (action_type, product_name, details, user)
                VALUES (?, ?, ?, ?)
            """, (action, name, f"Qty Change: {abs(diff)}", "Admin"))
    else:
        cursor.execute("""
            UPDATE inventory SET brand=?, die_no=?, name=?, color=?, thick=?, buy_price=?, sell_price=?
            WHERE id=?
        """, (brand, die_no, name, color, thick, buy, sell, item_id))

    if float(buy) != float(old_buy) or float(sell) != float(old_sell):
        details = f"Old Buy:{old_buy} New:{buy} | Old Sell:{old_sell} New:{sell}"
        cursor.execute("""
            INSERT INTO audit_logs (action_type, product_name, details, user)
            VALUES (?, ?, ?, ?)
        """, ("Price Changed", name, details, "Admin"))

    conn.commit()
    conn.close()


def delete_inventory_item(item_id):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# ========== SALES ==========
def process_sale(item_id, sold_qty, total_bill, profile_name,
                 die_no="", color="", spec="", cust_name="Cash",
                 cust_phone="", cust_address="", disc_amt=0, paid_amt=0,
                 total_items_in_cart=1):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT total_in, unit_in, buy_price, unit_type FROM inventory WHERE id=?
        """, (item_id,))
        item = cursor.fetchone()
        if not item:
            return False

        current_stock, unit_in, buy_price_full, unit_type = item
        new_stock = round(float(current_stock) - float(sold_qty), 2)
        cursor.execute("UPDATE inventory SET total_in=? WHERE id=?", (new_stock, item_id))

        cost_rate = (float(buy_price_full) / float(unit_in)) if (unit_type in ["alum", "wool"] and float(unit_in) > 0) else float(buy_price_full)
        cost_price = cost_rate * float(sold_qty)

        distributed_disc = float(disc_amt or 0) / max(int(total_items_in_cart), 1)
        actual_sale = float(total_bill) - distributed_disc
        profit     = round(actual_sale - cost_price, 2)
        due_amount = round(actual_sale - float(paid_amt or 0), 2)

        now        = datetime.now()
        sale_date  = now.strftime("%Y-%m-%d")
        sale_time  = now.strftime("%I:%M %p")
        order_id   = now.strftime("ORD%Y%m%d%H%M%S")

        cursor.execute("""
            INSERT INTO sales (
                order_id, sale_date, sale_time,
                customer_name, customer_phone, customer_address,
                profile_name, color, spec, die_no,
                quantity, price, total,
                discount, paid_amount, due_amount, profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, sale_date, sale_time,
            cust_name, cust_phone, cust_address,
            profile_name, color, spec, die_no,
            sold_qty, total_bill, total_bill,
            distributed_disc, paid_amt, due_amount, profit
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"process_sale error: {e}")
        return False
    finally:
        conn.close()


# ========== DASHBOARD ==========
def get_dashboard_stats():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    # ইনভেস্টমেন্ট
    cursor.execute("SELECT total_in, unit_in, buy_price, unit_type FROM inventory")
    total_inv = 0.0
    for total_in, unit_in, buy_price, u_type in cursor.fetchall():
        s = float(total_in or 0)
        u = float(unit_in or 1)
        b = float(buy_price or 0)
        if u_type == "alum" and u > 0:
            total_inv += (s / u) * b
        else:
            total_inv += s * b

    # টোটাল প্রোডাক্ট
    cursor.execute("SELECT COUNT(*) FROM inventory")
    total_items = cursor.fetchone()[0] or 0

    # আজকের সেলস ও প্রফিট
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        cursor.execute("""
            SELECT SUM(total - discount), SUM(profit)
            FROM sales
            WHERE sale_date = ?
        """, (today,))
        row = cursor.fetchone()
        today_sales  = float(row[0] or 0)
        today_profit = float(row[1] or 0)
    except Exception:
        today_sales = today_profit = 0.0

    # মোট বাকি
    try:
        cursor.execute("SELECT SUM(due_amount) FROM sales WHERE due_amount > 0")
        total_due = float(cursor.fetchone()[0] or 0)
    except Exception:
        total_due = 0.0

    conn.close()
    return {
        "investment": total_inv,
        "items":      total_items,
        "sales":      today_sales,
        "profit":     today_profit,
        "due":        total_due,
    }


def get_recent_sales(limit=5):
    """
    Returns: [(profile_name, quantity, total, sale_date, sale_time), ...]
    Dashboard এ s[0]=profile_name, s[2]=total, s[3]=sale_date দেখায়।
    """
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT profile_name, quantity, total, sale_date, sale_time
            FROM sales
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"get_recent_sales error: {e}")
        return []
    finally:
        conn.close()


# ========== REPORTS ==========
def get_all_sales_report():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                id,
                sale_date,
                customer_name,
                customer_phone,
                profile_name,
                discount,
                (total - discount) AS net_bill,
                paid_amount,
                due_amount
            FROM sales
            ORDER BY id DESC
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"get_all_sales_report error: {e}")
        return []
    finally:
        conn.close()


def get_filtered_sales_report(filter_type="today"):
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if filter_type == "today":
        query = "SELECT * FROM sales WHERE date(sale_date) = date('now','localtime')"
    elif filter_type == "month":
        query = "SELECT * FROM sales WHERE strftime('%m-%Y', sale_date) = strftime('%m-%Y', 'now','localtime')"
    elif filter_type == "year":
        query = "SELECT * FROM sales WHERE strftime('%Y', sale_date) = strftime('%Y', 'now','localtime')"
    else:
        query = "SELECT * FROM sales"

    query += " ORDER BY id DESC"
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"get_filtered_sales_report error: {e}")
        return []
    finally:
        conn.close()


def get_only_due_reports():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM sales
            WHERE due_amount > 0
            ORDER BY id DESC
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"get_only_due_reports error: {e}")
        return []
    finally:
        conn.close()


def collect_due_payment(sale_id, payment_amount):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT paid_amount, due_amount FROM sales WHERE id=?", (sale_id,))
        row = cursor.fetchone()
        if row:
            new_paid = float(row[0] or 0) + float(payment_amount)
            new_due  = float(row[1] or 0) - float(payment_amount)
            cursor.execute("""
                UPDATE sales SET paid_amount=?, due_amount=?
                WHERE id=?
            """, (new_paid, new_due, sale_id))
            conn.commit()
    except Exception as e:
        print(f"collect_due_payment error: {e}")
    finally:
        conn.close()


def cancel_sale(sale_id, item_name, qty_to_return):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE inventory SET total_in = total_in + ? WHERE name=?",
            (qty_to_return, item_name)
        )
        cursor.execute("DELETE FROM sales WHERE id=?", (sale_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"cancel_sale error: {e}")
        return False
    finally:
        conn.close()


# ========== INVOICE ==========
def get_sale_invoice_details(sale_id):
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                s.id, s.order_id,
                s.sale_date, s.sale_time,
                s.customer_name, s.customer_phone, s.customer_address,
                s.profile_name, s.color, s.spec, s.die_no,
                s.quantity, s.price, s.total,
                s.discount, s.paid_amount, s.due_amount,
                i.brand, i.die_no AS inv_die_no
            FROM sales s
            LEFT JOIN inventory i
                ON s.profile_name = i.name AND s.die_no = i.die_no
            WHERE s.id=?
        """, (sale_id,))
        return cursor.fetchone()
    except Exception as e:
        print(f"get_sale_invoice_details error: {e}")
        return None
    finally:
        conn.close()


# ========== AUDIT LOGS ==========
def add_audit_log(action_type, product_name, details, user="Admin"):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    try:
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, action_type, product_name, details, user)
            VALUES (?, ?, ?, ?, ?)
        """, (now, action_type, product_name, details, user))
        conn.commit()
    except Exception as e:
        print(f"add_audit_log error: {e}")
    finally:
        conn.close()


def get_audit_logs(action_type="All", limit=50):
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        if action_type != "All":
            cursor.execute("""
                SELECT timestamp, action_type, product_name, details
                FROM audit_logs
                WHERE action_type=?
                ORDER BY id DESC LIMIT ?
            """, (action_type, limit))
        else:
            cursor.execute("""
                SELECT timestamp, action_type, product_name, details
                FROM audit_logs
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"get_audit_logs error: {e}")
        return []
    finally:
        conn.close()


# ========== COLORS (pos_database.db) ==========
def get_colors():
    conn = sqlite3.connect("pos_database.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS colors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    cursor.execute("SELECT name FROM colors")
    colors = [row[0] for row in cursor.fetchall()]
    conn.close()
    return colors


def add_new_color(name):
    conn = sqlite3.connect("pos_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO colors (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


# ========== BUSINESS PROFILE ==========
def get_profile_data():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM business_profile WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    return row


# ========== HELPERS ==========
def format_inches_to_feet(total_inches):
    try:
        total = float(total_inches)
        feet  = int(total // 12)
        inches = round(total % 12, 1)
        if feet > 0:
            return f"{feet}' {inches}\""
        return f"{inches}\""
    except Exception:
        return str(total_inches)


# ========== AUTO RUN ==========
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")


def get_invoice_items(order_id):
    """একটি order_id এর সব items + inventory থেকে unit_in, unit_type আনে।"""
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                s.id, s.order_id, s.profile_name, s.die_no,
                s.color, s.spec, s.quantity,
                s.price, s.total, s.discount,
                i.unit_in, i.unit_type, i.brand
            FROM sales s
            LEFT JOIN inventory i ON s.die_no = i.die_no
            WHERE s.order_id = ?
            ORDER BY s.id ASC
        """, (str(order_id),))
        return cursor.fetchall()
    except Exception as e:
        print(f"get_invoice_items error: {e}")
        return []
    finally:
        conn.close()