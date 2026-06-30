import sqlite3
from datetime import datetime
import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB = os.path.join(BASE_DIR, "inventory.db")


def _conn():
    return sqlite3.connect(DB, timeout=15)


def get_db_connection():
    return _conn()


def init_db():
    conn   = _conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            brand            TEXT,
            die_no           TEXT,
            name             TEXT,
            color            TEXT,
            thick            TEXT,
            total_in         REAL DEFAULT 0,
            unit_in          REAL DEFAULT 120,
            buy_price        REAL DEFAULT 0,
            sell_price       REAL DEFAULT 0,
            unit_type        TEXT DEFAULT 'alum',
            current_stock    REAL DEFAULT 0,
            is_synced        INTEGER DEFAULT 0,
            discount_percent REAL DEFAULT 0.0
        )
    """)

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
            profit           REAL DEFAULT 0,
            is_synced        INTEGER DEFAULT 0,
            brand       TEXT DEFAULT '',
            unit_in REAL DEFAULT 252,
            inventory_id     INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT DEFAULT CURRENT_TIMESTAMP,
            action_type  TEXT,
            product_name TEXT,
            brand        TEXT,
            die_code     TEXT,
            color        TEXT,
            unit_length  REAL DEFAULT 120.0,
            old_stock    REAL DEFAULT 0.0,
            new_stock    REAL DEFAULT 0.0,
            details      TEXT,
            user         TEXT DEFAULT 'Admin',
            is_synced    INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO brands (name) VALUES ('Altech'), ('Chunghua')")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colors (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('app_password', '123')")

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

    # ── deleted_inventory: Supabase delete queue ──────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deleted_inventory (
            id          INTEGER PRIMARY KEY,
            deleted_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            is_synced   INTEGER DEFAULT 0
        )
    """)

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
        ("is_synced",        "INTEGER DEFAULT 0"),
    ])
    _safe_add_columns(cursor, "inventory", [
        ("unit_type",        "TEXT DEFAULT 'alum'"),
        ("current_stock",    "REAL DEFAULT 0"),
        ("is_synced",        "INTEGER DEFAULT 0"),
        ("discount_percent", "REAL DEFAULT 0.0"),
    ])
    _safe_add_columns(cursor, "audit_logs", [
        ("is_synced",   "INTEGER DEFAULT 0"),
        ("brand",       "TEXT"),
        ("die_code",    "TEXT"),
        ("color",       "TEXT"),
        ("unit_length", "REAL DEFAULT 120.0"),
        ("old_stock",   "REAL DEFAULT 0.0"),
        ("new_stock",   "REAL DEFAULT 0.0"),
    ])

    cursor.execute("""
        UPDATE inventory SET current_stock = total_in
        WHERE current_stock = 0 AND total_in > 0
    """)

    conn.commit()
    conn.close()
    _sync_database_names()
    _populate_brands_from_inventory()


def _safe_add_columns(cursor, table, columns):
    for col, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass


def _sync_database_names():
    conn   = _conn()
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


def _populate_brands_from_inventory():
    """inventory table এ যত distinct brand/color আছে সব local tables এ save।"""
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT brand FROM inventory WHERE brand IS NOT NULL AND brand != ''")
        for (b,) in cursor.fetchall():
            try:
                cursor.execute("INSERT OR IGNORE INTO brands (name) VALUES (?)", (b,))
            except Exception:
                pass

        cursor.execute("SELECT DISTINCT color FROM inventory WHERE color IS NOT NULL AND color != ''")
        for (c,) in cursor.fetchall():
            try:
                cursor.execute("INSERT OR IGNORE INTO colors (name) VALUES (?)", (c,))
            except Exception:
                pass
        conn.commit()
    except Exception as e:
        print(f"_populate_brands_from_inventory error: {e}")
    finally:
        conn.close()


# ========== SETTINGS ==========


def get_app_password():
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key='app_password'")
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "123"

def update_app_password(new_pw):
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value=? WHERE key='app_password'", (new_pw,))
    conn.commit()
    conn.close()


# ========== BRANDS ==========
def get_brands():
    conn = _conn()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM brands ORDER BY name ASC")
    brands = [row[0] for row in cursor.fetchall()]
    conn.close()
    return brands

def add_new_brand(brand_name):
    conn = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO brands (name) VALUES (?)", (brand_name.strip(),))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ========== COLORS ==========
def get_colors():
    conn = sqlite3.connect(DB, timeout=15)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS colors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    cursor.execute("SELECT name FROM colors")
    colors = [row[0] for row in cursor.fetchall()]
    conn.close()
    return colors

def add_new_color(name):
    conn = sqlite3.connect(DB, timeout=15)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO colors (name) VALUES (?)", (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


# ========== AUDIT LOG ==========
def add_audit_log(action_type, product_name, details="", user="Admin",
                  brand="", die_code="", color="",
                  unit_length=120.0, old_stock=0.0, new_stock=0.0):
    conn   = _conn()
    cursor = conn.cursor()
    now    = datetime.now().strftime("%d %b %Y, %I:%M %p")
    try:
        cursor.execute("""
            INSERT INTO audit_logs
                (timestamp, action_type, product_name, brand, die_code,
                 color, unit_length, old_stock, new_stock, details, user, is_synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (now, action_type, product_name, str(brand), str(die_code),
              str(color), float(unit_length), float(old_stock),
              float(new_stock), details, user))
        conn.commit()
    except Exception as e:
        print(f"add_audit_log error: {e}")
    finally:
        conn.close()


def get_audit_logs(action_type="All", limit=99999):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        base = """
            SELECT timestamp, action_type, product_name, brand, die_code,
                   color, unit_length, old_stock, new_stock, details
            FROM audit_logs
        """
        if action_type != "All":
            cursor.execute(base + " WHERE action_type=? ORDER BY id DESC LIMIT ?",
                           (action_type, limit))
        else:
            cursor.execute(base + " ORDER BY id DESC LIMIT ?", (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"get_audit_logs error: {e}")
        return []
    finally:
        conn.close()


# ========== INVENTORY ==========
def add_inventory_item(brand, die_no, name, color, thick,
                       total_in, unit_in, buy,
                       unit_type='alum', discount=0.0):
    conn   = _conn()
    cursor = conn.cursor()
    if unit_type not in ['alum', 'wool']:
        unit_in = 1.0
    
    sell_price = float(buy or 0)
    buy_price  = round(sell_price * (1 - float(discount or 0) / 100), 2)
    
    try:
        cursor.execute("""
            INSERT INTO inventory
                (brand, die_no, name, color, thick,
                 total_in, unit_in, buy_price, sell_price,
                 unit_type, current_stock, is_synced, discount_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        """, (brand, die_no, name, color, thick,
              total_in, unit_in, buy_price, sell_price,
              unit_type, total_in, discount))
        conn.commit()
        _populate_brands_from_inventory()
    except Exception as e:
        print(f"add_inventory_item error: {e}")
    finally:
        conn.close()

def get_inventory_items(limit=1000, offset=0):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, brand, die_no, name, color, thick,
                   current_stock, unit_in, buy_price, sell_price,
                   unit_type, discount_percent
            FROM inventory ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        result = []
        for item in cursor.fetchall():
            row     = list(item)
            row[6]  = float(row[6]  or 0)
            row[7]  = float(row[7]  or 252)
            row[11] = float(row[11] or 0.0)
            result.append(tuple(row))
        return result
    except sqlite3.OperationalError as e:
        print(f"get_inventory_items error: {e}")
        return []
    finally:
        conn.close()


def get_inventory_total_count():
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM inventory")
        return cursor.fetchone()[0] or 0
    except Exception:
        return 0
    finally:
        conn.close()


def update_inventory_item(item_id, brand, die_no, name, color, thick,
                          buy, total_in=None, discount=0.0):
    conn   = _conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT buy_price, sell_price, current_stock, discount_percent, unit_in "
        "FROM inventory WHERE id=?", (item_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    old_buy, old_sell, old_stock, old_disc, db_unit_in = row
    old_stock  = float(old_stock  or 0.0)
    db_unit_in = float(db_unit_in or 120.0)
    final_total = total_in if total_in is not None else old_stock

    sell_price = float(buy or 0)
    buy_price  = round(sell_price * (1 - float(discount or 0) / 100), 2)

    cursor.execute("""
        UPDATE inventory
        SET brand=?, die_no=?, name=?, color=?, thick=?,
            buy_price=?, sell_price=?, total_in=?, current_stock=?,
            discount_percent=?, is_synced=0
        WHERE id=?
    """, (brand, die_no, name, color, thick,
          buy_price, sell_price, final_total, final_total, discount, item_id))
    conn.commit()
    conn.close()

    if float(buy) != float(old_sell or 0):
        add_audit_log(
            action_type="Price Changed", product_name=name,
            details=f"Old Price: {old_sell} → New Price: {buy}",
            user="Admin", brand=brand, die_code=die_no, color=color,
            unit_length=db_unit_in, old_stock=old_stock, new_stock=old_stock,
        )
    if float(discount) != float(old_disc or 0.0):
        add_audit_log(
            action_type="Discount Changed", product_name=name,
            details=f"Old Discount: {old_disc}% → New: {discount}%",
            user="Admin", brand=brand, die_code=die_no, color=color,
            unit_length=db_unit_in, old_stock=old_stock, new_stock=old_stock,
        )
def delete_inventory_item(item_id):
    """
    Local এ delete করে AND deleted_inventory table এ ID রাখে।
    main.py এর sync worker এই table দেখে Supabase থেকেও delete করে।
    """
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT name, die_no, brand, color, current_stock, unit_in "
            "FROM inventory WHERE id=?", (item_id,)
        )
        item = cursor.fetchone()

        # ── deleted_inventory queue তে রাখো ──
        cursor.execute(
            "INSERT OR IGNORE INTO deleted_inventory (id, is_synced) VALUES (?, 0)",
            (item_id,)
        )

        cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        conn.commit()
    except Exception as e:
        print(f"delete_inventory_item error: {e}")
        conn.rollback()
        item = None
    finally:
        conn.close()

    if item:
        p_name, die_no, brand, clr, last_stk, unit_len = item
        add_audit_log(
            action_type="Stock Removed", product_name=str(p_name),
            details=f"Product Code: {die_no} permanently deleted.",
            user="Admin", brand=str(brand or ""), die_code=str(die_no or ""),
            color=str(clr or ""), unit_length=float(unit_len or 120.0),
            old_stock=float(last_stk or 0.0), new_stock=0.0,
        )


def get_pending_deletes():
    """Supabase থেকে delete করার জন্য pending ID গুলো।"""
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM deleted_inventory WHERE is_synced=0")
        return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def mark_delete_synced(item_id):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE deleted_inventory SET is_synced=1 WHERE id=?", (item_id,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


# ========== SALES ==========
def process_sale(item_id, sold_qty, total_bill, profile_name,
                 die_no="", color="", spec="", cust_name="Cash",
                 cust_phone="", cust_address="", disc_amt=0, paid_amt=0,
                 total_items_in_cart=1):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT current_stock, unit_in, buy_price, unit_type FROM inventory WHERE id=?",
            (item_id,)
        )
        item = cursor.fetchone()
        if not item: return False

        current_stock, unit_in, buy_price_full, unit_type = item
        new_stock  = round(float(current_stock) - float(sold_qty), 2)
        cursor.execute(
            "UPDATE inventory SET current_stock=?, is_synced=0 WHERE id=?",
            (new_stock, item_id)
        )
        cost_rate  = (float(buy_price_full) / float(unit_in)
                      if unit_type in ["alum", "wool"] and float(unit_in) > 0
                      else float(buy_price_full))
        cost_price = cost_rate * float(sold_qty)
        dist_disc  = float(disc_amt or 0) / max(int(total_items_in_cart), 1)
        actual     = float(total_bill) - dist_disc
        profit     = round(actual - cost_price, 2)
        due        = round(actual - float(paid_amt or 0), 2)
        now        = datetime.now()

        cursor.execute("""
            INSERT INTO sales (
                order_id, sale_date, sale_time,
                customer_name, customer_phone, customer_address,
                profile_name, color, spec, die_no,
                quantity, price, total,
                discount, paid_amount, due_amount, profit, is_synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            now.strftime("ORD%Y%m%d%H%M%S"),
            now.strftime("%Y-%m-%d"), now.strftime("%I:%M %p"),
            cust_name, cust_phone, cust_address,
            profile_name, color, spec, die_no,
            sold_qty, total_bill, total_bill,
            dist_disc, paid_amt, due, profit,
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
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT current_stock, unit_in, buy_price, unit_type FROM inventory")
        total_inv = 0.0
        for cs, ui, bp, ut in cursor.fetchall():
            s = float(cs or 0); u = float(ui or 120); b = float(bp or 0)
            total_inv += (s/u)*b if str(ut).strip().lower()=="alum" and u>0 else s*b

        cursor.execute("SELECT COUNT(*) FROM inventory WHERE current_stock > 0")
        total_items = cursor.fetchone()[0] or 0

        today = datetime.now().strftime("%Y-%m-%d")
        try:
            cursor.execute(
                "SELECT SUM(total-discount), SUM(profit) FROM sales WHERE sale_date=?", (today,))
            row = cursor.fetchone()
            today_sales  = float(row[0] or 0)
            today_profit = float(row[1] or 0)
        except Exception:
            today_sales = today_profit = 0.0

        try:
            cursor.execute("""
                SELECT SUM(due_amount) FROM (
                    SELECT MAX(due_amount) as due_amount 
                    FROM sales 
                    WHERE due_amount > 0.05
                    GROUP BY order_id
                )
            """)
            total_due = float(cursor.fetchone()[0] or 0)
        except Exception:
            total_due = 0.0

        return {"investment": round(total_inv, 2), "items": total_items,
                "sales": today_sales, "profit": today_profit, "due": total_due}

    except Exception as e:
        print(f"get_dashboard_stats error: {e}")
        return {"investment": 0, "items": 0, "sales": 0, "profit": 0, "due": 0}
    finally:
        conn.close()
def get_recent_sales(limit=5):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT profile_name, quantity, total, sale_date, sale_time "
            "FROM sales ORDER BY id DESC LIMIT ?", (limit,))
        return cursor.fetchall()
    except Exception as e:
        print(f"get_recent_sales error: {e}")
        return []
    finally:
        conn.close()


# ========== REPORTS ==========
def get_all_sales_report():
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, sale_date, customer_name, customer_phone,
                   profile_name, discount,
                   (total - discount) AS net_bill,
                   paid_amount, due_amount
            FROM sales ORDER BY id DESC
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"get_all_sales_report error: {e}")
        return []
    finally:
        conn.close()


def get_filtered_sales_report(filter_type="today"):
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if filter_type == "today":
        q = "SELECT * FROM sales WHERE date(sale_date)=date('now','localtime')"
    elif filter_type == "month":
        q = "SELECT * FROM sales WHERE strftime('%m-%Y',sale_date)=strftime('%m-%Y','now','localtime')"
    elif filter_type == "year":
        q = "SELECT * FROM sales WHERE strftime('%Y',sale_date)=strftime('%Y','now','localtime')"
    else:
        q = "SELECT * FROM sales"
    try:
        cursor.execute(q + " ORDER BY id DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"get_filtered_sales_report error: {e}")
        return []
    finally:
        conn.close()


def get_grouped_sales_report(filter_type="all"):
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    where = {
        "today": "WHERE date(sale_date)=date('now','localtime')",
        "month": "WHERE strftime('%m-%Y',sale_date)=strftime('%m-%Y','now','localtime')",
        "year":  "WHERE strftime('%Y',sale_date)=strftime('%Y','now','localtime')",
    }.get(filter_type, "")
    try:
        cursor.execute(f"""
            SELECT order_id, sale_date, sale_time,
                   customer_name, customer_phone,
                   SUM(total)          AS gross,
                   SUM(discount)       AS discount,
                   SUM(total-discount) AS net,
                   MAX(paid_amount)    AS paid_amount,
                   MAX(due_amount)     AS due_amount,
                   SUM(profit)         AS profit,
                   COUNT(*)            AS item_count
            FROM sales {where}
            GROUP BY order_id ORDER BY MIN(id) DESC
        """)
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"get_grouped_sales_report error: {e}")
        return []
    finally:
        conn.close()


def get_only_due_reports():
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM sales WHERE due_amount>0 ORDER BY id DESC")
        return cursor.fetchall()
    except Exception as e:
        print(f"get_only_due_reports error: {e}")
        return []
    finally:
        conn.close()


def collect_due_payment(sale_id, payment_amount):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        # আগে order_id বের করো
        cursor.execute("SELECT order_id, paid_amount, due_amount FROM sales WHERE id=?", (sale_id,))
        row = cursor.fetchone()
        if row:
            order_id   = row[0]
            new_paid   = float(row[1] or 0) + float(payment_amount)
            new_due    = float(row[2] or 0) - float(payment_amount)
            if new_due < 0: new_due = 0.0

            # ওই order_id এর সব rows update করো
            cursor.execute("""
                UPDATE sales 
                SET paid_amount=?, due_amount=?, is_synced=0 
                WHERE order_id=?
            """, (new_paid, new_due, order_id))
            conn.commit()
    except Exception as e:
        print(f"collect_due_payment error: {e}")
    finally:
        conn.close()


def cancel_sale(sale_id, item_name, qty_to_return):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE inventory SET current_stock=current_stock+?, is_synced=0 WHERE name=?",
            (qty_to_return, item_name))
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
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT s.id, s.order_id, s.sale_date, s.sale_time,
                   s.customer_name, s.customer_phone, s.customer_address,
                   s.profile_name, s.color, s.spec, s.die_no,
                   s.quantity, s.price, s.total,
                   s.discount, s.paid_amount, s.due_amount,
                   i.brand, i.die_no AS inv_die_no
            FROM sales s
            LEFT JOIN inventory i ON s.profile_name=i.name AND s.die_no=i.die_no
            WHERE s.id=?
        """, (sale_id,))
        return cursor.fetchone()
    except Exception as e:
        print(f"get_sale_invoice_details error: {e}")
        return None
    finally:
        conn.close()


def get_invoice_items(order_id):
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        
        cursor.execute("""
    SELECT 
        s.id, s.order_id, s.profile_name, s.die_no,
        s.color, s.spec, s.quantity,
        s.price, s.total, s.discount,
        s.customer_name, s.customer_phone,
        s.paid_amount, s.due_amount,
        s.brand,
        COALESCE(i.unit_in, 120) as unit_in,
        COALESCE(i.unit_type, 'alum') as unit_type
    FROM sales s
    LEFT JOIN (
        SELECT die_no, color, unit_in, unit_type
        FROM inventory
        GROUP BY die_no, color
    ) i ON s.die_no = i.die_no AND s.color = i.color
    WHERE s.order_id=? ORDER BY s.id ASC
        """, (str(order_id),))
        return cursor.fetchall()
    except Exception as e:
        print(f"get_invoice_items error: {e}")
        return []
    finally:
        conn.close()


# ========== PROFILE ==========
def get_profile_data():
    conn   = _conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM business_profile WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    return row


# ========== HELPERS ==========
def format_inches_to_feet(total_inches):
    try:
        total  = float(total_inches)
        feet   = int(total // 12)
        inches = round(total % 12, 1)
        return f"{feet}' {inches}\"" if feet > 0 else f"{inches}\""
    except Exception:
        return str(total_inches)


def get_profit_sum(filter_type="today"):
    conn   = _conn()
    cursor = conn.cursor()
    q = "SELECT SUM(profit), SUM(total) FROM sales"
    if filter_type == "today":
        q += " WHERE DATE(sale_date)=DATE('now')"
    elif filter_type == "month":
        q += " WHERE strftime('%m',sale_date)=strftime('%m','now') AND strftime('%Y',sale_date)=strftime('%Y','now')"
    elif filter_type == "year":
        q += " WHERE strftime('%Y',sale_date)=strftime('%Y','now')"
    cursor.execute(q)
    result = cursor.fetchone()
    conn.close()
    return (result[0] if result and result[0] else 0.0,
            result[1] if result and result[1] else 0.0)

def get_brand_profit_summary(filter_type="today"):
    conn   = _conn()
    cursor = conn.cursor()

    date_filter = ""
    if filter_type == "today":
        date_filter = "WHERE DATE(s.sale_date)=DATE('now')"
    elif filter_type == "month":
        date_filter = "WHERE strftime('%m',s.sale_date)=strftime('%m','now') AND strftime('%Y',s.sale_date)=strftime('%Y','now')"
    elif filter_type == "year":
        date_filter = "WHERE strftime('%Y',s.sale_date)=strftime('%Y','now')"

    cursor.execute(f"""
    SELECT 
        s.brand,
        SUM(s.total)              AS gross,
        SUM(s.total - s.discount) AS net,
        SUM(s.discount)           AS total_discount,
        SUM(s.profit)             AS profit
    FROM sales s
    {date_filter}
    GROUP BY s.brand
    HAVING s.brand != ''
    ORDER BY profit DESC
""")

    rows = cursor.fetchall()
    conn.close()
    return rows


def get_product_unit_in(product_name):
    conn   = _conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT unit_in, unit_type FROM inventory WHERE name=? LIMIT 1",
            (product_name,))
        row = cursor.fetchone()
        if row:
            return float(row[0] or 120.0), str(row[1] or "alum")
        cursor.execute(
            "SELECT unit_length FROM audit_logs "
            "WHERE product_name LIKE ? AND unit_length IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (f"%{product_name}%",))
        log_row = cursor.fetchone()
        if log_row:
            return float(log_row[0] or 120.0), "alum"
        return 120.0, "alum"
    except Exception as e:
        print(f"get_product_unit_in error: {e}")
        return 120.0, "alum"
    finally:
        conn.close()

def get_recent_grouped_sales(limit=5):
    """Dashboard এর জন্য invoice-level summary।"""
    conn = _conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT order_id, sale_date, sale_time,
                   customer_name, customer_phone,
                   SUM(total)          AS gross,
                   SUM(discount)       AS discount,
                   SUM(total-discount) AS net,
                   MAX(paid_amount)    AS paid_amount,
                   MAX(due_amount)     AS due_amount
            FROM sales
            GROUP BY order_id
            ORDER BY MAX(id) DESC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        print(f"get_recent_grouped_sales error: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")

