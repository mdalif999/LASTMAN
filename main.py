import flet as ft
import datetime
import threading
import time
import os

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

MASTER_PIN = "9988"


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


def main(page: ft.Page):
    init_db()
    page.title   = "Khondakar Traders POS"
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

        page.update()

    # ================================================================
    # DASHBOARD BUILD
    # ================================================================
    def _build_dashboard():
        try:
            stats            = get_dashboard_stats()
            recent_sales_data = get_recent_sales(5)   # (profile_name, quantity, total, sale_date, sale_time)
            items            = get_inventory_items()
        except Exception as e:
            print(f"Dashboard load error: {e}")
            stats            = {"investment": 0, "items": 0, "sales": 0, "profit": 0, "due": 0}
            recent_sales_data = []
            items            = []

        # লো-স্টক
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

        # রিসেন্ট সেলস রো বিল্ড
        # get_recent_sales → (profile_name[0], quantity[1], total[2], sale_date[3], sale_time[4])
        sale_rows = []
        for s in recent_sales_data:
            try:
                name  = str(s[0] or "—")[:20]
                total = float(s[2] or 0)
                time_ = str(s[4] or s[3] or "—")   # sale_time পাওয়া গেলে সেটা, নাহলে date
                sale_rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(name)),
                        ft.DataCell(ft.Text(f"{total:,.0f}")),
                        ft.DataCell(ft.Text(time_)),
                    ])
                )
            except Exception:
                pass

        # লো-স্টক রো বিল্ড
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
                                "green", ft.Icons.TRENDING_UP),
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
                    ft.Text("Khondakar\nTraders", size=25, weight="bold"),
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

    def handle_login(e):
        global APP_PASSWORD
        if pass_input.value == APP_PASSWORD:
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
            ft.Text("Khondakar Traders", size=30, weight="bold"),
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
    ft.app(
        target=main,
        assets_dir="assets",
        view=ft.AppView.WEB_BROWSER,
    )


# ================================================================
# PDF INVOICE GENERATOR
# ================================================================
def generate_invoice_pdf(order_id, customer_name, cart_items, total_amount):
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    file_path      = os.path.join(downloads_path, f"Invoice_{order_id}.pdf")

    c      = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 50, "KHONDAKAR TRADERS")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 65, "Stadium Lane, Bogura")
    c.drawCentredString(width / 2, height - 78, "Contact: 01787-203830")
    c.line(50, height - 90, 545, height - 90)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, f"Order No: {order_id}")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 140, f"Customer: {customer_name}")

    c.line(50, height - 160, 545, height - 160)
    c.drawString(55,  height - 175, "Item Name")
    c.drawString(300, height - 175, "Qty")
    c.drawString(400, height - 175, "Price")
    c.drawString(480, height - 175, "Total")
    c.line(50, height - 185, 545, height - 185)

    y = height - 205
    for item in cart_items:
        c.drawString(55,  y, str(item.get('profile', '')))
        c.drawString(305, y, str(item.get('qty', '')))
        c.drawString(405, y, f"{item.get('price', 0):.2f}")
        c.drawString(485, y, f"{item.get('total', 0):.2f}")
        y -= 20

    c.line(50, y, 545, y)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(400, y - 30, f"Net Payable: {total_amount:.2f} TK")
    c.save()
    return file_path