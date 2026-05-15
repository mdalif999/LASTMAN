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

    # ── Main data refresh ───────────────────────────────────
    def refresh_data(filter_type="all"):
        try:
            search_query = (search_field.value or "").lower().strip()
            start_d = start_date_btn.text
            end_d   = end_date_btn.text
        except Exception:
            search_query = ""
            start_d = "Start Date"
            end_d   = "End Date"

        try:
            data_list = get_only_due_reports()
        except Exception as ex:
            print(f"get_only_due_reports error: {ex}")
            data_list = []

        due_table.rows.clear()
        t_due_sum = 0.0
        now = datetime.now()

        for row in data_list:
            try:
                # ── নতুন schema: total, paid_amount, due_amount ──
                # row is sqlite3.Row so access by key
                c_name_raw  = row["customer_name"] or "Cash"
                c_phone_raw = row["customer_phone"] or ""
                sale_date_str = str(row["sale_date"] or "")

                # total এবং paid — নতুন column নাম
                total = float(row["total"]       or 0)
                paid  = float(row["paid_amount"] or 0)
                due   = float(row["due_amount"]  or 0)

                # due_amount সরাসরি না থাকলে calculate করি
                if due <= 0:
                    due = round(total - paid, 2)
                if due <= 0:
                    continue

                # ── date filter ──────────────────────────────
                date_only = get_date_only(sale_date_str)
                try:
                    sale_dt = datetime.strptime(date_only, "%Y-%m-%d")
                except ValueError:
                    sale_dt = None

                if filter_type == "today":
                    if not sale_dt or sale_dt.date() != now.date():
                        continue
                elif filter_type == "month":
                    if not sale_dt or (sale_dt.month != now.month or sale_dt.year != now.year):
                        continue
                elif filter_type == "year":
                    if not sale_dt or sale_dt.year != now.year:
                        continue
                # "all" → কোনো filter নেই

                # ── date picker filter ────────────────────────
                if start_d != "Start Date" and end_d != "End Date":
                    if not (start_d <= date_only <= end_d):
                        continue

                # ── search filter ─────────────────────────────
                if search_query:
                    if search_query not in c_name_raw.lower() and search_query not in c_phone_raw.lower():
                        continue

                t_due_sum += due
                s_id = row["id"]

                inv_no = str(row["order_id"] or "—")
                due_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(inv_no, size=12, color="cyan200", weight="bold")),
                        ft.DataCell(ft.Container(
                            content=ft.Text(format_date(sale_date_str), size=11, color="white70"),
                            padding=ft.padding.only(left=6),
                            border=ft.border.only(left=ft.BorderSide(3, ft.Colors.ORANGE)),
                        )),
                        ft.DataCell(ft.Column([
                            ft.Text(c_name_raw,   weight="bold", size=14, color="white"),
                            ft.Text(c_phone_raw or "No Number", size=11, color="white60"),
                        ], tight=True, spacing=0)),
                        ft.DataCell(ft.Text(f"{total:,.2f}", color="white")),
                        ft.DataCell(ft.Text(f"{paid:,.2f}",  color="green")),
                        ft.DataCell(ft.Text(f"{due:,.2f}",   color="red", weight="bold")),
                        ft.DataCell(
                            ft.ElevatedButton(
                                "জমা নিন",
                                icon=ft.Icons.PAYMENTS_OUTLINED,
                                bgcolor="orange",
                                color="white",
                                height=36,
                                on_click=lambda e, sid=s_id, d=due, n=c_name_raw:
                                    show_pay_dialog(sid, d, n)
                            )
                        ),
                    ])
                )

            except Exception as ex:
                print(f"Due row error: {ex}")
                continue

        due_summary_text.value = f"{t_due_sum:,.2f} TK"

        if not due_table.rows:
            due_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("কোনো বাকি নেই ✅", color="green300", size=14)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
            ]))

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