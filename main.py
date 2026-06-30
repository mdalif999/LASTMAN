import sys
import os
from database import get_pending_deletes, mark_delete_synced

venv_path = os.path.join(os.path.dirname(__file__), '.venv', 'Lib', 'site-packages')
if os.path.exists(venv_path):
    sys.path.append(venv_path)

import socket


import flet as ft
import datetime
import threading
import time
import sqlite3
from supabase import create_client, Client

from pages.ProfitReportPage import ProfitReportPage

def get_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

from database import (
    init_db,get_recent_grouped_sales, get_inventory_items, get_dashboard_stats,
    get_recent_sales, get_app_password,
    update_app_password, DB,
)
init_db()


# ==================== SUPABASE CONFIGURATION ====================
SUPABASE_URL = "https://poynesakhmzcguvrihul.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveW5lc2FraG16Y2d1dnJpaHVsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTI4NTAwOCwiZXhwIjoyMDk0ODYxMDA4fQ.6i6uMdNOPeRBs4JXT8-20dYI5wdNVHj8zn0X4ymOzAY"
# ================================================================

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase connection established successfully!")
except Exception as e:
    print(f"Failed to connect to Supabase: {e}")
    supabase = None


def get_local_db():
    return sqlite3.connect(DB, check_same_thread=False, timeout=30.0)


# ════════════════════════════════════════════════════════════════
#  SUPABASE → LOCAL PULL  (নতুন install এ একবার চলে)
# ════════════════════════════════════════════════════════════════
def pull_from_supabase_if_empty():
    """
    Local inventory table যদি empty থাকে (নতুন install),
    Supabase থেকে সব data এনে local এ save করে।
    50টা করে batch এ load করে — memory safe।
    """
    if not supabase:
        print("Supabase not connected — skipping pull.")
        return

    conn   = get_local_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM inventory")
    local_count = cursor.fetchone()[0]
    conn.close()

    if local_count > 0:
        print(f"Local DB has {local_count} items — skipping pull from Supabase.")
        return

    print("Local DB is empty. Pulling data from Supabase...")

    # ── inventory ────────────────────────────────────────────
    try:
        BATCH = 50
        offset = 0
        total_pulled = 0

        while True:
            try:
                result = (supabase.table("inventory")
                          .select("*")
                          .range(offset, offset + BATCH - 1)
                          .execute())
            except Exception:
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
                result = (supabase_client.table("inventory")
                          .select("*")
                          .range(offset, offset + BATCH - 1)
                          .execute())

            rows = result.data or []
            if not rows:
                break

            conn   = get_local_db()
            cursor = conn.cursor()
            for row in rows:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO inventory
                            (id, brand, die_no, name, color, thick,
                             total_in, unit_in, buy_price, sell_price,
                             unit_type, current_stock, is_synced, discount_percent)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """, (
                        row.get("id"),
                        row.get("brand", ""),
                        row.get("die_no", ""),
                        row.get("name", ""),
                        row.get("color", ""),
                        row.get("thick", ""),
                        row.get("total_in", 0),
                        row.get("unit_in", 120),
                        row.get("buy_price", 0),
                        row.get("sell_price", 0),   # DB তে রাখা হচ্ছে, UI তে দেখাবে না
                        row.get("unit_type", "alum"),
                        row.get("current_stock", 0),
                        row.get("discount_percent", 0.0),
                    ))
                except Exception as ex:
                    print(f"  Inventory row insert error: {ex}")
            conn.commit()
            conn.close()

            total_pulled += len(rows)
            print(f"  Pulled {total_pulled} inventory items so far...")
            offset += BATCH

            if len(rows) < BATCH:
                break

        print(f"Inventory pull complete: {total_pulled} items.")

    except Exception as e:
        print(f"pull_from_supabase inventory error: {e}")

    # ── brands populate from pulled inventory ─────────────────
    try:
        from database import _populate_brands_from_inventory
        _populate_brands_from_inventory()
        print("Brands & colors populated from pulled inventory.")
    except Exception as e:
        print(f"populate brands error: {e}")

    # ── sales ─────────────────────────────────────────────────
    try:
        BATCH  = 50
        offset = 0
        total_pulled = 0

        while True:
            try:
                result = (supabase.table("sales")
                          .select("*")
                          .range(offset, offset + BATCH - 1)
                          .execute())
            except Exception:
                supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
                result = (supabase_client.table("sales")
                          .select("*")
                          .range(offset, offset + BATCH - 1)
                          .execute())

            rows = result.data or []
            if not rows:
                break

            conn   = get_local_db()
            cursor = conn.cursor()
            for row in rows:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO sales
                            (id, order_id, sale_date, sale_time,
                             customer_name, customer_phone, customer_address,
                             profile_name, color, spec, die_no,
                             quantity, price, total, discount,
                             paid_amount, due_amount, profit, is_synced,brand, unit_in)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)
                    """, (
                        row.get("id"),
                        row.get("order_id", ""),
                        row.get("sale_date", ""),
                        row.get("sale_time", ""),
                        row.get("customer_name", "Cash"),
                        row.get("customer_phone", ""),
                        row.get("customer_address", ""),
                        row.get("profile_name", ""),
                        row.get("color", ""),
                        row.get("spec", ""),
                        row.get("die_no", ""),
                        row.get("quantity", 0),
                        row.get("price", 0),
                        row.get("total", 0),
                        row.get("discount", 0),
                        row.get("paid_amount", 0),
                        row.get("due_amount", 0),
                        row.get("profit", 0),
                        row.get("brand", ""),
                        row.get("unit_in", 252),
                    ))
                except Exception as ex:
                    print(f"  Sales row insert error: {ex}")
            conn.commit()
            conn.close()

            total_pulled += len(rows)
            print(f"  Pulled {total_pulled} sales records so far...")
            offset += BATCH

            if len(rows) < BATCH:
                break

        print(f"Sales pull complete: {total_pulled} records.")

    except Exception as e:
        print(f"pull_from_supabase sales error: {e}")

    print("Initial Supabase pull finished!")


# ════════════════════════════════════════════════════════════════
#  LOCAL → SUPABASE PUSH  (background sync)
# ════════════════════════════════════════════════════════════════
def sync_inventory():
    global supabase
    conn   = get_local_db()
    cursor = conn.cursor()
    try:
        # ── Upsert sync ──
        cursor.execute("""
            SELECT id, brand, die_no, name, color, thick, total_in, unit_in,
                   buy_price, sell_price, unit_type, current_stock, discount_percent
            FROM inventory WHERE is_synced = 0
        """)
        rows = cursor.fetchall()
        if rows:
            print(f"Syncing {len(rows)} inventory items to cloud...")
            for row in rows:
                data = {
                    "id": row[0], "brand": row[1], "die_no": row[2], "name": row[3],
                    "color": row[4], "thick": row[5], "total_in": row[6], "unit_in": row[7],
                    "buy_price": row[8], "sell_price": row[9],
                    "unit_type": row[10], "current_stock": row[11],
                    "discount_percent": row[12],
                }
                try:
                    try:
                        supabase.table("inventory").upsert(data).execute()
                    except Exception:
                        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                        supabase.table("inventory").upsert(data).execute()
                    cursor.execute("UPDATE inventory SET is_synced=1 WHERE id=?", (row[0],))
                    conn.commit()
                except Exception as e:
                    print(f"Error syncing inventory ID {row[0]}: {e}")

        # ── Delete sync ──
        pending = get_pending_deletes()
        for item_id in pending:
            try:
                supabase.table("inventory").delete().eq("id", item_id).execute()
                mark_delete_synced(item_id)
                print(f"Deleted item {item_id} from Supabase")
            except Exception as e:
                print(f"Error deleting item {item_id} from Supabase: {e}")

    except Exception as e:
        print(f"Database error in sync_inventory: {e}")
    finally:
        cursor.close()
        conn.close()

def sync_sales():
    global supabase
    conn   = get_local_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, order_id, sale_date, sale_time, customer_name, customer_phone,
                   customer_address, profile_name, color, spec, die_no,
                   quantity, price, total, discount, paid_amount, due_amount, profit, brand,inventory_id
            FROM sales WHERE is_synced = 0
        """)
        rows = cursor.fetchall()
        if not rows:
            return
        print(f"Syncing {len(rows)} sales records to cloud...")
        for row in rows:
            data = {
                "id": row[0], "order_id": row[1], "sale_date": row[2], "sale_time": row[3],
                "customer_name": row[4], "customer_phone": row[5], "customer_address": row[6],
                "profile_name": row[7], "color": row[8], "spec": row[9], "die_no": row[10],
                "quantity": row[11], "price": row[12], "total": row[13], "discount": row[14],
                "paid_amount": row[15], "due_amount": row[16], "profit": row[17],"brand": row[18] or "",
                 "inventory_id": row[19] or 0,
            }
            try:
                try:
                    supabase.table("sales").upsert(data).execute()
                except Exception:
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    supabase.table("sales").upsert(data).execute()
                cursor.execute("UPDATE sales SET is_synced=1 WHERE id=?", (row[0],))
                conn.commit()
            except Exception as e:
                print(f"Error syncing sale ID {row[0]}: {e}")
    except Exception as e:
        print(f"Database error in sync_sales: {e}")
    finally:
        cursor.close(); conn.close()


def sync_audit_logs():
    global supabase
    conn   = get_local_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, timestamp, action_type, product_name, brand, die_code,
                   color, unit_length, old_stock, new_stock, details, user
            FROM audit_logs WHERE is_synced = 0
        """)
        rows = cursor.fetchall()
        if not rows:
            return
        print(f"Syncing {len(rows)} audit logs to Supabase...")
        for row in rows:
            data = {
                "id": row[0], "timestamp": row[1], "action_type": row[2],
                "product_name": row[3], "brand": row[4], "die_code": row[5],
                "color": row[6], "unit_length": row[7], "old_stock": row[8],
                "new_stock": row[9], "details": row[10], "user_name": row[11],
            }
            try:
                try:
                    supabase.table("audit_logs").upsert(data).execute()
                except Exception:
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    supabase.table("audit_logs").upsert(data).execute()
                cursor.execute("UPDATE audit_logs SET is_synced=1 WHERE id=?", (row[0],))
                conn.commit()
            except Exception as e:
                print(f"Error syncing log ID {row[0]}: {e}")
    except Exception as e:
        print(f"Database error in sync_audit_logs: {e}")
    finally:
        cursor.close(); conn.close()


def reset_sync_if_needed():
    if not supabase:
        return
    try:
        result       = supabase.table("inventory").select("id", count="exact").execute()
        supabase_cnt = result.count or 0
        conn         = get_local_db()
        c            = conn.cursor()
        c.execute("SELECT COUNT(*) FROM inventory")
        local_cnt = c.fetchone()[0]
        conn.close()
        if supabase_cnt < local_cnt:
            conn = get_local_db()
            c    = conn.cursor()
            c.execute("UPDATE inventory  SET is_synced=0")
            c.execute("UPDATE sales      SET is_synced=0")
            c.execute("UPDATE audit_logs SET is_synced=0")
            conn.commit()
            conn.close()
            print("Sync reset done!")
    except Exception as e:
        print(f"Sync check error: {e}")
    
def pull_audit_logs_from_supabase():
    if not supabase:
        return
    try:
        conn = get_local_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM audit_logs")
        local_count = c.fetchone()[0]
        conn.close()

        if local_count > 0:
            print(f"Audit logs already exist locally ({local_count}) — skipping.")
            return

        print("Pulling audit logs from Supabase...")
        BATCH = 50
        offset = 0
        total = 0

        while True:
            result = (supabase.table("audit_logs")
                      .select("*")
                      .range(offset, offset + BATCH - 1)
                      .execute())
            rows = result.data or []
            if not rows:
                break

            conn = get_local_db()
            c = conn.cursor()
            for row in rows:
                try:
                    c.execute("""
                        INSERT OR REPLACE INTO audit_logs
                            (id, timestamp, action_type, product_name, brand,
                             die_code, color, unit_length, old_stock, new_stock,
                             details, user, is_synced)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)
                    """, (
                        row.get("id"),
                        row.get("timestamp", ""),
                        row.get("action_type", ""),
                        row.get("product_name", ""),
                        row.get("brand", ""),
                        row.get("die_code", ""),
                        row.get("color", ""),
                        row.get("unit_length", 120.0),
                        row.get("old_stock", 0.0),
                        row.get("new_stock", 0.0),
                        row.get("details", ""),
                        row.get("user_name", "Admin"),
                    ))
                except Exception as ex:
                    print(f"Audit log insert error: {ex}")
            conn.commit()
            conn.close()

            total += len(rows)
            offset += BATCH
            if len(rows) < BATCH:
                break

        print(f"Audit logs pull complete: {total} records.")
    except Exception as e:
        print(f"pull_audit_logs error: {e}")

        
def has_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False

def start_sync_worker(interval_seconds=5):
    print(f"Sync worker started. Interval: {interval_seconds}s")
    pull_from_supabase_if_empty()
    pull_audit_logs_from_supabase()
    reset_sync_if_needed()
    while True:
        try:
            # ✅ net না থাকলে কিছুই করবে না
            if not has_internet():
                time.sleep(interval_seconds)
                continue

            # প্রতি loop এ check — net না থাকলে আগে pull হয়নি
            conn = get_local_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM inventory")
            count = c.fetchone()[0]
            conn.close()
            if count == 0:
                pull_from_supabase_if_empty()
                pull_audit_logs_from_supabase()

            sync_inventory()
            sync_sales()
            sync_audit_logs()
        except Exception as e:
            print(f"Sync worker error: {e}")
        time.sleep(interval_seconds)

# ════════════════════════════════════════════════════════════════
#  REPORTS
# ════════════════════════════════════════════════════════════════
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from pages.billing_page import billing_page
from database import (
    init_db, get_inventory_items, get_dashboard_stats,
    get_recent_sales, get_app_password, update_app_password,
)
from pages.inventory import inventory_page
from pages.pos import pos_page
from pages.sales_report import sales_report_page
from pages.stock_report import stock_report_page
from pages.history import history_page
from pages.due_management import DueManagementPage

APP_PASSWORD = get_app_password()
MASTER_PIN   = "tarek"


def format_stock_simple(total_val, unit_size, unit_type):
    if total_val <= 0:
        return "Out of Stock"
    if unit_type == "piece":
        return f"{int(total_val)} Pcs"
    if unit_type == "sft":
        return f"{total_val:.2f} SFT"
    if unit_type == "wool":
        return f"{int(total_val // 12)}' {total_val % 12:.0f}\""
    pcs  = int(total_val // unit_size)
    rem  = total_val % unit_size
    ft_v = int(rem // 12)
    in_v = rem % 12
    res  = []
    if pcs  > 0: res.append(f"{pcs}P")
    if ft_v > 0: res.append(f"{ft_v}'")
    if in_v > 0: res.append(f'{in_v:.0f}"')
    return " ".join(res) if res else '0"'


def main(page: ft.Page):

    def show_pin_dialog(page):
        pin_input = ft.TextField(label="Enter Master PIN", password=True,
                                 can_reveal_password=True, autofocus=True)

        def verify_and_go(e):
            if pin_input.value == MASTER_PIN:
                page.close(dlg)
                content_area.content = ProfitReportPage(page)
                page.update()
            else:
                pin_input.error_text = "Incorrect PIN!"
                page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Master Access Required"),
            content=pin_input,
            actions=[ft.ElevatedButton("Verify", on_click=verify_and_go)],
        )
        page.open(dlg)

    page.title      = "MD TAREK POS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0f111a"
    page.padding    = 0

    main_layout  = ft.Container(expand=True)
    content_area = ft.Container(expand=True)
    clock_text   = ft.Text(size=16, color="white60", weight="bold")

    def update_clock():
        while True:
            now = datetime.datetime.now()
            clock_text.value = now.strftime("%d %B %Y | %I:%M:%S %p")
            try:
                page.update()
            except Exception:
                break
            time.sleep(1)

    # ════════════════════════════════════════════════════════
    #  NAVIGATE
    # ════════════════════════════════════════════════════════
    def navigate(target):
        page._navigate    = navigate
        content_area.content = None

        if target == "dashboard":
            _build_dashboard()
        elif target == "inventory":
            content_area.content = inventory_page(page)
        elif target == "sales":
            try:
                content_area.content = pos_page(page, navigate)
            except TypeError:
                content_area.content = pos_page(page)
        elif target == "sales_report":
            content_area.content = sales_report_page(page)
        elif target == "generate_bill":
            content_area.content = billing_page(
                page,
                cart_items=page.session.get("cart_items"),
                totals=page.session.get("bill_totals"),
            )
        elif target == "stock_report":
            content_area.content = stock_report_page(page)
        elif target == "/due_management":
            content_area.content = DueManagementPage(page)
        elif target == "history":
            content_area.content = history_page(page)
        elif target == "settings":
            from pages.settings_page import settings_view
            content_area.content = settings_view(page)
        elif target == "logout":
            pass_input.value      = ""
            pass_input.error_text = None
            main_layout.content   = login_screen

        try:
            content_area.update()
        except Exception:
            pass
        page.update()

    # ════════════════════════════════════════════════════════
    #  DASHBOARD
    # ════════════════════════════════════════════════════════
    def _build_dashboard():
        try:
            stats             = get_dashboard_stats()
            recent_sales_data = get_recent_grouped_sales(5)
            items             = get_inventory_items(99999)
        except Exception as e:
            print(f"Dashboard load error: {e}")
            stats             = {"investment": 0, "items": 0, "sales": 0, "profit": 0, "due": 0}
            recent_sales_data = []
            items             = []

        low_stock_items = []
        for i in items:
            try:
                stock_val = float(i[6] or 0)
                u_size    = float(i[7] or 120)
                u_type    = i[10] if len(i) > 10 else "alum"
                threshold = 50 * u_size if u_type == "alum" else 50
                if stock_val < threshold:
                    low_stock_items.append(i)
            except Exception:
                pass

        sale_rows = []
        for s in recent_sales_data:
            try:
                order_id = str(s.get("order_id") or "—")
                cust     = str(s.get("customer_name") or "Cash")[:15]
                net      = float(s.get("net", 0) or 0)
                paid     = float(s.get("paid_amount", 0) or 0)
                due      = float(s.get("due_amount", 0) or 0)
                time_    = str(s.get("sale_time") or "—")

                sale_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(order_id, color="cyan200", weight="bold")),
                        ft.DataCell(ft.Text(cust)),
                        ft.DataCell(ft.Text(f"{net:,.0f}")),
                        ft.DataCell(ft.Text(f"{paid:,.0f}", color="green")),
                        ft.DataCell(ft.Text(f"{due:,.0f}", color="red" if due>0 else "green")),
                        ft.DataCell(ft.Text(time_)),
                    ])
                )
            except Exception:
                pass

        low_rows = []
        for item in sorted(low_stock_items, key=lambda x: float(x[6] or 0))[:5]:
            try:
                low_rows.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.WARNING_ROUNDED, color="red"),
                        title=ft.Text(item[3], size=14),
                        subtitle=ft.Text(
                            format_stock_simple(float(item[6]), float(item[7]), item[10]),
                            color="red200",
                        ),
                    )
                )
            except Exception:
                pass

        content_area.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Business Overview", size=35, weight="bold"),
                    ft.Container(expand=True),
                    clock_text,
                ], alignment="spaceBetween"),
                ft.Container(height=20),
                ft.ResponsiveRow([
                    create_card("Total Investment",
                                f"{stats.get('investment', 0):,.2f} TK",
                                "orange", ft.Icons.PAYMENTS),
                    create_card("Total Products",
                                str(stats.get('items', 0)),
                                "blue", ft.Icons.INVENTORY_2),
                    create_card("Today's Sales",
                                f"{stats.get('sales', 0):,.2f} TK",
                                "green", ft.Icons.TRENDING_UP,
                                on_click=lambda e: show_pin_dialog(page)),
                    create_card("Total Due",
                                f"{stats.get('due', 0):,.2f} TK",
                                "red", ft.Icons.REPORT_GMAILERRORRED,
                                on_click=lambda _: navigate("/due_management")),
                ], spacing=20),
                ft.Container(height=30),
                ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Recent Sales", size=22, weight="bold"),
                            ft.Divider(color="white10"),
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text("Invoice")),
                                    ft.DataColumn(ft.Text("Customer")),
                                    ft.DataColumn(ft.Text("Net")),
                                    ft.DataColumn(ft.Text("Paid")),
                                    ft.DataColumn(ft.Text("Due")),
                                    ft.DataColumn(ft.Text("Time")),
                                ],
                                rows=sale_rows if sale_rows else [
                                    ft.DataRow(cells=[
                                        ft.DataCell(ft.Text("No sales yet")),
                                        ft.DataCell(ft.Text("—")),
                                        ft.DataCell(ft.Text("—")),
                                    ])
                                ],
                            ),
                        ]),
                        bgcolor="#1e2b5e", padding=25, border_radius=15, expand=2,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Low Stock Alert", size=22, weight="bold", color="red400"),
                            ft.Divider(color="white10"),
                            ft.Column(
                                low_rows if low_rows else [
                                    ft.Text("সব স্টক ঠিকঠাক আছে ✅", color="green300")
                                ],
                                scroll=ft.ScrollMode.AUTO,
                            ),
                        ]),
                        bgcolor="#1e2b5e", padding=25, border_radius=15, expand=1,
                    ),
                ], spacing=20),
                ft.Container(height=30),
                ft.Text("Quick Actions", size=25, weight="bold"),
                ft.Row([
                    ft.ElevatedButton("New Sale", icon=ft.Icons.ADD_SHOPPING_CART,
                                      on_click=lambda _: navigate("sales"),
                                      bgcolor="orange", color="white"),
                    ft.ElevatedButton("View Inventory", icon=ft.Icons.LIST_ALT,
                                      on_click=lambda _: navigate("inventory")),
                ], spacing=15),
            ], scroll=ft.ScrollMode.AUTO),
            padding=40,
        )

    # ════════════════════════════════════════════════════════
    #  CARD & SIDEBAR
    # ════════════════════════════════════════════════════════
    def create_card(title, val, color, icon, on_click=None):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, color=color, size=40),
                ft.Text(title, color="white60"),
                ft.Text(val, size=22, weight="bold"),
            ]),
            bgcolor="#1e2b5e", padding=25, border_radius=15,
            col={"sm": 12, "md": 6, "lg": 3},
            on_click=on_click, ink=True,
        )

    def sidebar_btn(icon, label, target):
        return ft.Container(
            content=ft.Row(
                [ft.Icon(icon, color="white"), ft.Text(label, size=18, weight="bold")],
                spacing=20,
            ),
            padding=ft.Padding(left=25, right=25, top=15, bottom=15),
            on_click=lambda _: navigate(target),
            border_radius=10,
            on_hover=lambda e: (
                setattr(e.control, "bgcolor", "#2c3e50" if e.data == "true" else None)
                or e.control.update()
            ),
        )

    page.sidebar_container = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.STORE, size=50, color="orange"),
                    ft.Text("CITY GLASS\n ART& THY ALUMINIUM", size=25, weight="bold"),
                ]),
                padding=ft.Padding(top=40, bottom=20, left=0, right=0),
            ),
            ft.Divider(height=1, color="white10"),
            ft.Column([
                sidebar_btn(ft.Icons.DASHBOARD,     "Dashboard",  "dashboard"),
                sidebar_btn(ft.Icons.INVENTORY,     "Inventory",  "inventory"),
                sidebar_btn(ft.Icons.SHOPPING_CART, "Sales (POS)","sales"),
                ft.ExpansionTile(
                    title=ft.Text("Reports", size=18, weight="bold", color="white"),
                    leading=ft.Icon(ft.Icons.INSERT_CHART, color="white"),
                    collapsed_icon_color="white",
                    icon_color="orange",
                    controls=[
                        ft.ListTile(title=ft.Text("Sales Report"),
                                    leading=ft.Icon(ft.Icons.POINT_OF_SALE, size=20),
                                    on_click=lambda _: navigate("sales_report")),
                        ft.ListTile(title=ft.Text("Stock Report"),
                                    leading=ft.Icon(ft.Icons.INVENTORY_2, size=20),
                                    on_click=lambda _: navigate("stock_report")),
                    ],
                ),
                sidebar_btn(ft.Icons.HISTORY,  "History",  "history"),
                sidebar_btn(ft.Icons.SETTINGS, "Settings", "settings"),
            ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=5),
            ft.Divider(height=1, color="white10"),
            sidebar_btn(ft.Icons.LOGOUT, "Logout", "logout"),
        ]),
        width=280, bgcolor="#1e2b5e", padding=20, visible=True,
    )

    # ════════════════════════════════════════════════════════
    #  MASTER RECOVERY
    # ════════════════════════════════════════════════════════
    def open_master_recovery(e):
        master_pw = ft.TextField(
            label="Master Security PIN", password=True,
            can_reveal_password=True, text_align="center", autofocus=True,
        )

        def verify_master(e):
            if master_pw.value == MASTER_PIN:
                page.close(master_dlg)
                show_reset_dialog()
            else:
                master_pw.error_text = "Incorrect Master PIN!"
                page.update()

        def show_reset_dialog():
            new_pass = ft.TextField(label="Enter New Password", password=True,
                                    can_reveal_password=True)

            def save_new_pass(e):
                global APP_PASSWORD
                if new_pass.value:
                    APP_PASSWORD = new_pass.value
                    page.client_storage.set("app_pin", new_pass.value)
                    update_app_password(new_pass.value)
                    page.close(reset_dlg)
                    page.snack_bar = ft.SnackBar(ft.Text("PIN Reset Successful!"), bgcolor="green")
                    page.snack_bar.open = True
                    load_dashboard()
                else:
                    new_pass.error_text = "Cannot be empty!"
                    page.update()

            reset_dlg = ft.AlertDialog(
                title=ft.Text("Reset App PIN"),
                content=new_pass,
                actions=[ft.ElevatedButton("Save & Login", on_click=save_new_pass,
                                           bgcolor="orange", color="white")],
            )
            page.open(reset_dlg)

        master_dlg = ft.AlertDialog(
            title=ft.Text("Emergency Master Unlock"),
            content=ft.Column([ft.Text("Enter master code to reset PIN:"), master_pw], tight=True),
            actions=[
                ft.TextButton("Cancel",  on_click=lambda _: page.close(master_dlg)),
                ft.ElevatedButton("Verify", on_click=verify_master, bgcolor="blue", color="white"),
            ],
        )
        page.open(master_dlg)

    # ════════════════════════════════════════════════════════
    #  LOGIN
    # ════════════════════════════════════════════════════════
    def load_dashboard():
        main_layout.content = ft.Row(
            [page.sidebar_container, content_area], expand=True, spacing=0,
        )
        navigate("dashboard")
        threading.Thread(target=update_clock, daemon=True).start()
        page.update()

    def handle_login(e):
        global APP_PASSWORD
        saved_pin = page.client_storage.get("app_pin") or APP_PASSWORD
        if pass_input.value == saved_pin:
            load_dashboard()
        else:
            pass_input.error_text = "ভুল পাসওয়ার্ড! আবার চেষ্টা করুন।"
            page.update()

    def on_pass_change(e):
        if pass_input.error_text:
            pass_input.error_text = None
            page.update()

    pass_input = ft.TextField(
        label="Enter Password", width=350,
        password=True, can_reveal_password=True,
        on_submit=handle_login, on_change=on_pass_change,
        text_align="center", border_color="orange",
    )

    login_screen = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.LOCK_PERSON, size=80, color="orange"),
            ft.Text("CITY GLASS ART & THY ALUMINIUM", size=30, weight="bold"),
            pass_input,
            ft.ElevatedButton("Unlock Dashboard", on_click=handle_login,
                              width=350, bgcolor="orange", color="white"),
            ft.TextButton("Forget PIN? Reset with Master PIN",
                          on_click=open_master_recovery,
                          style=ft.ButtonStyle(color="white54")),
        ], alignment="center", horizontal_alignment="center", spacing=20),
        expand=True, alignment=ft.alignment.center,
    )

    main_layout.content = login_screen
    page.add(main_layout)


if __name__ == "__main__":
    sync_thread = threading.Thread(
        target=start_sync_worker,
        args=(5,),
        daemon=True,
    )
    sync_thread.start()

    ft.app(target=main, assets_dir="assets")