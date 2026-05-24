import sys
import os

# --- উইন্ডোজ ARM64 ভার্চুয়াল এনভায়রনমেন্টের জন্য পাথ হ্যাক ---
# (ম্যাকবুকে থাকলে এই কন্ডিশনটা নিজে থেকেই স্কিপ হয়ে যাবে, কোনো এরর দেবে না)
venv_path = os.path.join(os.path.dirname(__file__), '.venv', 'Lib', 'site-packages')
if os.path.exists(venv_path):
    sys.path.append(venv_path)

import flet as ft
import datetime
import threading
import time
import sqlite3
from supabase import create_client, Client

# --- নতুন পেজ এবং ডাটাবেজ ইমপোর্ট ---
from pages.ProfitReportPage import ProfitReportPage 

def get_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

from database import (
    init_db, get_inventory_items, get_dashboard_stats,
    get_recent_sales, get_app_password, 
    update_app_password,
)

# ==================== SUPABASE CONFIGURATION ====================
SUPABASE_URL = "https://poynesakhmzcguvrihul.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveW5lc2FraG16Y2d1dnJpaHVsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTI4NTAwOCwiZXhwIjoyMDk0ODYxMDA4fQ.6i6uMdNOPeRBs4JXT8-20dYI5wdNVHj8zn0X4ymOzAY"
# ================================================================

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase connection established successfully!")
except Exception as e:
    print(f"Failed to connect to Supabase: {e}")

def get_local_db():
    # check_same_thread=False এবং timeout=30.0 দিলে UI ও ব্যাকগ্রাউন্ড থ্রেড একসাথে ডেটাবেজ নিয়ে জ্যাম ছাড়া কাজ করবে
    return sqlite3.connect("inventory.db", check_same_thread=False, timeout=30.0)

def sync_inventory():
    global supabase
    conn = get_local_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, brand, die_no, name, color, thick, total_in, unit_in, buy_price, sell_price, unit_type, current_stock 
            FROM inventory WHERE is_synced = 0
        """)
        rows = cursor.fetchall()
        if not rows:
            return
        
        print(f"Syncing {len(rows)} inventory items to cloud...")
        for row in rows:
            data = {
                "id": row[0], "brand": row[1], "die_no": row[2], "name": row[3],
                "color": row[4], "thick": row[5], "total_in": row[6], "unit_in": row[7],
                "buy_price": row[8], "sell_price": row[9], "unit_type": row[10], "current_stock": row[11]
            }
            try:
                try:
                    # প্রথমবার ট্রাই করা
                    supabase.table("inventory").upsert(data).execute()
                except Exception as conn_err:
                    # যদি HTTP/2 বা ConnectionTerminated এরর দেয়, সাথে সাথে ক্লায়েন্ট রিনিউ করে আবার ডেটা পাঠানো
                    print("Connection terminated during inventory sync. Re-establishing Supabase client...")
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    supabase.table("inventory").upsert(data).execute()
                
                # ক্লাউডে ডেটা সাকসেসফুলি যাওয়ার পরই কেবল লোকাল ফ্ল্যাগ আপডেট এবং কমিট হবে
                cursor.execute("UPDATE inventory SET is_synced = 1 WHERE id = ?", (row[0],))
                conn.commit()
            except Exception as e:
                print(f"Error syncing inventory ID {row[0]}: {e}")
    except Exception as e:
        print(f"Database error in sync_inventory: {e}")
    finally:
        cursor.close()
        conn.close()

def sync_sales():
    global supabase
    conn = get_local_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, order_id, sale_date, sale_time, customer_name, customer_phone, customer_address,
                   profile_name, color, spec, die_no, quantity, price, total, discount, paid_amount, due_amount, profit 
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
                "paid_amount": row[15], "due_amount": row[16], "profit": row[17]
            }
            try:
                try:
                    supabase.table("sales").upsert(data).execute()
                except Exception as conn_err:
                    print("Connection terminated during sales sync. Re-establishing Supabase client...")
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    supabase.table("sales").upsert(data).execute()
                
                cursor.execute("UPDATE sales SET is_synced = 1 WHERE id = ?", (row[0],))
                conn.commit()
            except Exception as e:
                print(f"Error syncing sale ID {row[0]}: {e}")
    except Exception as e:
        print(f"Database error in sync_sales: {e}")
    finally:
        cursor.close()
        conn.close()

def sync_audit_logs():
    global supabase
    # 🌟 প্যাক করার পর ডাটাবেজ খুঁজে পাওয়ার জন্য get_path ব্যবহার করুন
    db_path = get_path("inventory.db")
    conn = sqlite3.connect(db_path, timeout=20) # এখানে পরিবর্তন হয়েছে
    cursor = conn.cursor()
    try:
        # ... আপনার বাকি সব কোড আগের মতোই থাকবে ...
        cursor.execute("""
            SELECT id, timestamp, action_type, product_name, brand, die_code, 
                   color, unit_length, old_stock, new_stock, details, user 
            FROM audit_logs 
            WHERE is_synced = 0
        """)
        rows = cursor.fetchall()
        if not rows:
            return
            
        print(f"Syncing {len(rows)} audit logs to Supabase...")
        for row in rows:
            # 🌟 সুপাবেস কলামের নামের সাথে হুবহু মিল (user_name)
            data = {
                "id":           row[0],   
                "timestamp":    row[1],   
                "action_type":  row[2],  
                "product_name": row[3],   
                "brand":        row[4],   
                "die_code":     row[5],   
                "color":        row[6],   
                "unit_length":  row[7],   
                "old_stock":    row[8],   
                "new_stock":    row[9],   
                "details":      row[10],  
                "user_name":    row[11]   # 🌟 এখানে user_name ব্যবহার করা হয়েছে
            }
            try:
                try:
                    supabase.table("audit_logs").upsert(data).execute()
                except Exception:
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    supabase.table("audit_logs").upsert(data).execute()
                
                cursor.execute("UPDATE audit_logs SET is_synced = 1 WHERE id = ?", (row[0],))
                conn.commit()
            except Exception as e:
                print(f"Error syncing log ID {row[0]}: {e}")
    except Exception as e:
        print(f"Database error in sync_audit_logs: {e}")
    finally:
        cursor.close()
        conn.close()

# এই ফাংশনটি থ্রেডের মাধ্যমে ব্যাকগ্রাউন্ডে অনবরত চলবে
def start_sync_worker(interval_seconds=5):
    print(f"Sync worker started. Monitoring local database every {interval_seconds} seconds...")
    while True:
        try:
            sync_inventory()
            sync_sales()
            sync_audit_logs()
        except Exception as e:
            print(f"Sync worker encountered an error: {e}")
        time.sleep(interval_seconds)
#######################################
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from pages.billing_page import billing_page
from database import (
    init_db, get_inventory_items, get_dashboard_stats,
    get_recent_sales, init_settings_db, get_app_password, update_app_password
)
from pages.inventory import inventory_page
from pages.pos import pos_page
from pages.sales_report import sales_report_page
from pages.stock_report import stock_report_page
from pages.history import history_page
from pages.due_management import DueManagementPage

init_db()
APP_PASSWORD = get_app_password()

MASTER_PIN = "tarek"


# --- স্টক ফরম্যাট ---
def format_stock_simple(total_val, unit_size, unit_type):
    if total_val <= 0:
        return "Out of Stock"
    if unit_type == "piece":
        return f"{int(total_val)} Pcs"
    if unit_type == "sft":
        return f"{total_val:.2f} SFT"
    if unit_type == "wool":
        return f"{int(total_val // 12)}' {total_val % 12:.0f}\""
    pcs   = int(total_val // unit_size)
    rem   = total_val % unit_size
    ft_v  = int(rem // 12)
    in_v  = rem % 12
    res   = []
    if pcs  > 0: res.append(f"{pcs}P")
    if ft_v > 0: res.append(f"{ft_v}'")
    if in_v > 0: res.append(f'{in_v:.0f}"')
    return " ".join(res) if res else '0"'
######################################################

def main(page: ft.Page):
    # --- ফাংশন দুটি main এর ভেতরে রাখুন ---
    def create_card(title, value, color, icon, on_click=None):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, color=color, size=40),
                ft.Text(title, color="white60"),
                ft.Text(value, size=22, weight="bold"),
            ]),
            bgcolor="#1e2b5e", padding=25, border_radius=15,
            col={"sm": 12, "md": 6, "lg": 3},
            on_click=on_click,
            ink=True,
        )

    def show_pin_dialog(page):
        pin_input = ft.TextField(label="Enter Master PIN", password=True, can_reveal_password=True, autofocus=True)
        
        def verify_and_go(e):
            if pin_input.value == MASTER_PIN:
                page.close(dlg)
                # clear করলে সাইডবার চলে যায়, তাই শুধু কন্টেন্ট আপডেট করুন
                content_area.content = ProfitReportPage(page)
                page.update()
            else:
                pin_input.error_text = "Incorrect PIN!"
                page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Master Access Required"),
            content=pin_input,
            actions=[ft.ElevatedButton("Verify", on_click=verify_and_go)]
        )
        page.open(dlg)
    init_db()
    page.title   = "MD TAREK POS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f111a"
    page.padding = 0

    main_layout  = ft.Container(expand=True)
    content_area = ft.Container(expand=True)
    clock_text   = ft.Text(size=16, color="white60", weight="bold")

    # --- ঘড়ি ---
    def update_clock():
        while True:
            now = datetime.datetime.now()
            clock_text.value = now.strftime("%d %B %Y | %I:%M:%S %p")
            try:
                page.update()
            except Exception:
                break
            time.sleep(1)

    # ================================================================
    # NAVIGATE
    # ================================================================
    def navigate(target):
        page._navigate = navigate   # ✅ billing_page back button এর জন্য
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
            print("SESSION CART:", page.session.get("cart_items"))
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

        # --- ফ্লেট অ্যাপের লাইভ রিফ্রেশ ও সেফটি চেক লজিক ---
        try:
            # যদি অ্যাপ অলরেডি ড্যাশবোর্ডে ঢুকে থাকে, তাহলে কন্টেন্ট এরিয়া লাইভ রিফ্রেশ হবে (স্টক/ইনভেস্টমেন্ট আপডেট দেখাবে)
            content_area.update()
        except Exception:
            # প্রথমবার লগইনের সময় যেহেতু কন্টেন্ট এরিয়া স্ক্রিনে থাকে না, তাই এই এরর এড়াতে স্কিপ করবে
            pass

        page.update()
   # ================================================================
    # DASHBOARD BUILD (১০০% ক্লিন ও ডাটাবেজ ডিপেন্ডেন্ট)
    # ================================================================
    def _build_dashboard():
        try:
            # সরাসরি ডাটাবেজ থেকে নিখুঁত হিসাবগুলো চলে আসবে
            stats             = get_dashboard_stats()
            recent_sales_data = get_recent_sales(5)   # (profile_name, quantity, total, sale_date, sale_time)
            items             = get_inventory_items()
        except Exception as e:
            print(f"Dashboard load error: {e}")
            stats             = {"investment": 0, "items": 0, "sales": 0, "profit": 0, "due": 0}
            recent_sales_data = []
            items             = []

        # লো-স্টক অ্যালার্টের হিসাব (এটি আগের মতোই থাকবে)
        low_stock_items = []
        for i in items:
            try:
                stock_val = float(i[6] or 0) # i[6] এখানে perfectly current_stock
                u_size    = float(i[7] or 120)
                u_type    = i[10] if len(i) > 10 else "alum"
                threshold = 50 * u_size if u_type == "alum" else 50
                if stock_val < threshold:
                    low_stock_items.append(i)
            except Exception:
                pass

        # রিসেন্ট সেলস রো বিল্ড (আগের মতোই থাকবে)
        sale_rows = []
        for s in recent_sales_data:
            try:
                name  = str(s[0] or "—")[:20]
                total = float(s[2] or 0)
                time_ = str(s[4] or s[3] or "—")
                sale_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(name)),
                        ft.DataCell(ft.Text(f"{total:,.0f}")),
                        ft.DataCell(ft.Text(time_)),
                    ])
                )
            except Exception:
                pass

        # লো-স্টক রো বিল্ড (আগের মতোই থাকবে)
        low_rows = []
        for item in low_stock_items[:5]:
            try:
                low_rows.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.WARNING_ROUNDED, color="red"),
                        title=ft.Text(item[3], size=14),
                        subtitle=ft.Text(
                            format_stock_simple(float(item[6]), float(item[7]), item[10]),
                            color="red200"
                        ),
                    )
                )
            except Exception:
                pass

        # মূল ড্যাশবোর্ড UI কন্টেইনার
        content_area.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Business Overview", size=35, weight="bold"),
                    ft.Container(expand=True),
                    clock_text,
                ], alignment="spaceBetween"),

                ft.Container(height=20),

                # এখানে সরাসরি stats.get() দিয়ে ডাটাবেজের ভ্যালুগুলো কার্ডে বসে যাচ্ছে
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
                                    ft.DataColumn(ft.Text("Item")),
                                    ft.DataColumn(ft.Text("Total Bill")),
                                    ft.DataColumn(ft.Text("Time")),
                                ],
                                rows=sale_rows if sale_rows else [
                                    ft.DataRow(cells=[
                                        ft.DataCell(ft.Text("No sales yet")),
                                        ft.DataCell(ft.Text("—")),
                                        ft.DataCell(ft.Text("—")),
                                    ])
                                ]
                            ),
                        ]),
                        bgcolor="#1e2b5e", padding=25, border_radius=15, expand=2,
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Low Stock Alert", size=22, weight="bold", color="red400"),
                            ft.Divider(color="white10"),
                            ft.Column(
                                low_rows if low_rows else [ft.Text("সব স্টক ঠিকঠাক আছে ✅", color="green300")],
                                scroll=ft.ScrollMode.AUTO
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

    # ================================================================
    # CARD & SIDEBAR
    # ================================================================
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
            content=ft.Row([ft.Icon(icon, color="white"), ft.Text(label, size=18, weight="bold")], spacing=20),
            padding=ft.padding.symmetric(vertical=15, horizontal=25),
            on_click=lambda _: navigate(target),
            border_radius=10,
            on_hover=lambda e: (
                setattr(e.control, "bgcolor", "#2c3e50" if e.data == "true" else None) or e.control.update()
            ),
        )

    page.sidebar_container = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.STORE, size=50, color="orange"),
                    ft.Text("CITY GLASS\n ART& THY ALUMINIUM", size=25, weight="bold"),
                ]),
                padding=ft.padding.only(top=40, bottom=20),
            ),
            ft.Divider(height=1, color="white10"),
            sidebar_btn(ft.Icons.DASHBOARD,      "Dashboard",  "dashboard"),
            sidebar_btn(ft.Icons.INVENTORY,      "Inventory",  "inventory"),
            sidebar_btn(ft.Icons.SHOPPING_CART,  "Sales (POS)","sales"),
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
            ft.Container(expand=True),
            sidebar_btn(ft.Icons.LOGOUT,   "Logout",   "logout"),
        ]),
        width=280, bgcolor="#1e2b5e", padding=20, visible=True,
    )

    # ================================================================
    # MASTER RECOVERY
    # ================================================================
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
            new_pass = ft.TextField(label="Enter New Password", password=True, can_reveal_password=True)

            def save_new_pass(e):
                global APP_PASSWORD
                if new_pass.value:
                    APP_PASSWORD = new_pass.value
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

    # ================================================================
    # LOGIN
    # ================================================================
    def load_dashboard():
        main_layout.content = ft.Row(
            [page.sidebar_container, content_area], expand=True, spacing=0
        )
        navigate("dashboard")
        threading.Thread(target=update_clock, daemon=True).start()
        page.update()

    # আপনার লগইন ফাইলের handle_login ফাংশনটি দেখতে এমন হতে পারে:
    def handle_login(e):
       global APP_PASSWORD
    # লোকাল স্টোরেজে সেটিংস থেকে কোনো নতুন পাসওয়ার্ড সেভ করা আছে কিনা তা চেক করা
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


# if __name__ == "__main__":
#     import os
#     # সার্ভার থেকে পোর্ট নম্বর নেওয়া, না থাকলে ডিফল্ট ৮০৮০ বা ৮৫০২
#     port = int(os.getenv("PORT", 8080)) 
    
#     ft.app(
#         target=main,
#         assets_dir="assets",
#         # হোস্টিংয়ের সময় view=None রাখা ভালো, এতে সার্ভার মোড কাজ করে
#         view=None, 
#         port=port
# #     )
# if __name__ == "__main__":
#     # Flet অ্যাপ চালু হওয়ার ঠিক আগে ব্যাকগ্রাউন্ড থ্রেডটি ৫ সেকেন্ড ইন্টারভ্যাল দিয়ে স্টার্ট করা
#     sync_thread = threading.Thread(target=start_sync_worker, args=(5,), daemon=True)
#     sync_thread.start()
    
#     # আপনার মেইন Flet অ্যাপ রান করা (আগের প্যারামিটারগুলোসহ)
#     ft.app(
#         target=main, 
#         assets_dir="assets",
#         view=ft.AppView.WEB_BROWSER  # এটি দিলে সরাসরি ব্রাউজারে খুলবে
#     )

if __name__ == "__main__":
    sync_thread = threading.Thread(
        target=start_sync_worker,
        args=(5,),
        daemon=True
    )
    sync_thread.start()

    ft.app(target=main, assets_dir="assets")