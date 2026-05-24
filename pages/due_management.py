import flet as ft
from datetime import datetime
from database import get_only_due_reports, collect_due_payment


def DueManagementPage(page):

    # ── তারিখ ফরম্যাট ─────────────────────────────────────
    def format_date(date_str):
        """যেকোনো date string কে সুন্দর করে দেখায়।"""
        if not date_str:
            return "—"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d %b %Y, %I:%M %p"):
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                return dt.strftime("%d %b %Y  |  %I:%M %p")
            except ValueError:
                continue
        return str(date_str)

    def get_date_only(date_str):
        """YYYY-MM-DD অংশটুকু বের করে।"""
        if not date_str:
            return ""
        s = str(date_str).strip()
        return s[:10] if len(s) >= 10 else s

    # ── UI refs (আগে declare করতে হবে refresh_data এর আগে) ──
    search_field    = ft.TextField(
        label="নাম বা নম্বর দিয়ে খুঁজুন",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda _: refresh_data(),
        expand=True, bgcolor="white10",
        border_radius=10, height=45, text_size=14,
    )
    start_date_btn  = ft.TextButton("Start Date")
    end_date_btn    = ft.TextButton("End Date")
    due_summary_text = ft.Text("0.00 TK", size=25, weight="bold", color="red")

    due_table = ft.DataTable(
        heading_row_color=ft.Colors.BLUE_GREY_900,
        columns=[
            ft.DataColumn(ft.Text("Invoice No",    color="cyan200", weight="bold")),
            ft.DataColumn(ft.Text("তারিখ ও সময়",  color="white", weight="bold")),
            ft.DataColumn(ft.Text("কাস্টমার",      color="white", weight="bold")),
            ft.DataColumn(ft.Text("মোট বিল",       color="white", weight="bold")),
            ft.DataColumn(ft.Text("পেইড",           color="white", weight="bold")),
            ft.DataColumn(ft.Text("বাকি",           color="orange", weight="bold")),
            ft.DataColumn(ft.Text("জমা নিন",        color="white", weight="bold")),
        ],
    )

    # ── Payment dialog ──────────────────────────────────────
    def show_pay_dialog(sale_id, current_due, customer_name):
        pay_input = ft.TextField(
            label="জমার পরিমাণ (TK)",
            value=f"{current_due:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_color="orange",
            text_style=ft.TextStyle(color="white"),
            label_style=ft.TextStyle(color="white60"),
        )

        def save_payment(e):
            try:
                amount = float(pay_input.value or 0)
            except ValueError:
                pay_input.error_text = "সঠিক পরিমাণ দিন"
                page.update()
                return

            if amount <= 0:
                pay_input.error_text = "০ এর বেশি দিন"
                page.update()
                return
            if amount > current_due:
                pay_input.error_text = f"বাকির চেয়ে বেশি দেওয়া যাবে না ({current_due:.2f})"
                page.update()
                return

            collect_due_payment(sale_id, amount)
            page.close(dialog)
            refresh_data()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ {amount:,.2f} TK received from {customer_name}", color="white"),
                bgcolor="green"
            )
            page.snack_bar.open = True
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            bgcolor="#1e2b5e",
            shape=ft.RoundedRectangleBorder(radius=12),
            title=ft.Row([
                ft.Icon(ft.Icons.PAYMENTS, color="orange"),
                ft.Text(f"বকেয়া জমা — {customer_name}", color="white", size=18),
            ]),
            content=ft.Container(
                width=360,
                content=ft.Column([
                    ft.Text(f"বর্তমান বাকি: {current_due:,.2f} TK",
                            color="red300", size=15, weight="bold"),
                    ft.Container(height=8),
                    pay_input,
                ], tight=True),
                padding=10,
            ),
            actions=[
                ft.TextButton("Cancel",
                              style=ft.ButtonStyle(color="white54"),
                              on_click=lambda _: page.close(dialog)),
                ft.ElevatedButton("Confirm Receive",
                                  icon=ft.Icons.CHECK_CIRCLE,
                                  bgcolor="orange", color="white",
                                  on_click=save_payment),
            ],
        )
        page.open(dialog)

 # ── Main data refresh (Full Fixed & Clean) ───────────
    def refresh_data(filter_type="all"):
        try:
            search_query = (search_field.value or "").lower().strip()
            start_d = start_date_btn.text
            end_d   = end_date_btn.text
        except:
            search_query = ""; start_d = "Start Date"; end_d = "End Date"

        try:
            # ডাটাবেজ থেকে ডেটা আনা
            raw_data = get_only_due_reports()
        except:
            raw_data = []

        due_table.rows.clear()
        t_due_sum = 0.0
        now = datetime.now()

        # ১. ইনভয়েস অনুযায়ী গ্রুপ করা (যাতে মাল্টিপল রো না আসে)
        grouped = {}
        for row in raw_data:
            oid = str(row["order_id"])
            if oid not in grouped:
                grouped[oid] = {
                    "id": row["id"],
                    "order_id": oid,
                    "sale_date": row["sale_date"],
                    "customer_name": row["customer_name"],
                    "customer_phone": row["customer_phone"],
                    "total": 0.0,
                    "paid_amount": float(row["paid_amount"] or 0),
                    "due_amount": float(row["due_amount"] or 0)
                }
            grouped[oid]["total"] += float(row["total"] or 0)

        # ২. লুপ চালানো এবং ফিল্টার করা
        for oid, r in grouped.items():
            # ডিউ অ্যামাউন্ট রাউন্ড করা এবং দশমিকের সমস্যা দূর করা
            due = round(float(r["due_amount"] or 0), 2)
            
            # 💡 এখানে মূল ফিল্টার: ০.০৫ এর কম হলে সেটাকে শূন্য ধরে লিস্ট থেকে বাদ দিন
            if due < 0.05:
                continue

            try:
                total = r["total"]
                paid = r["paid_amount"]
                
                # ── Date Filter ──
                date_only = get_date_only(str(r["sale_date"] or ""))
                # ... (আপনার আগের date filter logic গুলো এখানে থাকবে) ...

                # ── Search Filter ──
                c_name = str(r["customer_name"]).lower()
                c_phone = str(r["customer_phone"]).lower()
                if search_query and (search_query not in c_name and search_query not in c_phone):
                    continue

                t_due_sum += due
                
                due_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(oid, size=12, color="cyan200", weight="bold")),
                        ft.DataCell(ft.Text(format_date(r["sale_date"]), size=11, color="white70")),
                        ft.DataCell(ft.Column([
                            ft.Text(r["customer_name"] or "Cash", weight="bold", size=14, color="white"),
                            ft.Text(r["customer_phone"] or "No Number", size=11, color="white60"),
                        ], tight=True, spacing=0)),
                        ft.DataCell(ft.Text(f"{total:,.2f}", color="white")),
                        ft.DataCell(ft.Text(f"{paid:,.2f}",  color="green")),
                        ft.DataCell(ft.Text(f"{due:,.2f}",   color="red", weight="bold")),
                        ft.DataCell(
                            ft.ElevatedButton(
                                "জমা নিন", icon=ft.Icons.PAYMENTS_OUTLINED, bgcolor="orange",
                                color="white", height=36,
                                on_click=lambda e, sid=r["id"], d=due, n=r["customer_name"]: show_pay_dialog(sid, d, n)
                            )
                        ),
                    ])
                )
            except Exception as ex:
                print(f"Row error: {ex}")
                continue

        due_summary_text.value = f"{t_due_sum:,.2f} TK"
        
        # নো-ডেটা মেসেজ
        if not due_table.rows:
            due_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("কোনো বাকি নেই ✅", color="green300")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))]))

        page.update()

    # ── Filter menu ─────────────────────────────────────────
    filter_menu = ft.PopupMenuButton(
        icon=ft.Icons.FILTER_ALT_ROUNDED,
        icon_color="orange",
        items=[
            ft.PopupMenuItem(text="Today's Due",  on_click=lambda _: refresh_data("today")),
            ft.PopupMenuItem(text="This Month",   on_click=lambda _: refresh_data("month")),
            ft.PopupMenuItem(text="This Year",    on_click=lambda _: refresh_data("year")),
            ft.PopupMenuItem(text="All Time Due", on_click=lambda _: refresh_data("all")),
        ],
    )

    # ── Back button ─────────────────────────────────────────
    def go_back(e):
        nav = getattr(page, "_navigate", None)
        if nav:
            nav("dashboard")
        else:
            page.update()

    # ── Initial load ────────────────────────────────────────
    refresh_data()

    # ── Return UI ───────────────────────────────────────────
    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column([
            # Header
            ft.Row([
                ft.Row([
                    ft.IconButton(
                        ft.Icons.ARROW_BACK_IOS_NEW,
                        icon_color="white",
                        on_click=go_back,
                        icon_size=18,
                        tooltip="Back to Dashboard",
                    ),
                    ft.Text("Due Management", size=28, weight="bold"),
                ]),
                filter_menu,
            ], alignment="spaceBetween"),

            # Summary card
            ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text("Total Outstanding Due", size=14, color="white60"),
                        due_summary_text,
                    ], expand=True),
                    ft.Icon(ft.Icons.MONETIZATION_ON, size=45, color="red300"),
                ]),
                padding=20, bgcolor="#1e2b5e", border_radius=15,
            ),

            ft.Divider(height=10, color="transparent"),

            # Search
            ft.Row([search_field]),

            # Table
            ft.Container(
                content=ft.ListView(
                    [ft.Row([due_table], scroll=ft.ScrollMode.ALWAYS)],
                    expand=True,
                ),
                expand=True,
                bgcolor="#0f111a",
                padding=10,
                border_radius=15,
            ),
        ], expand=True),
    )