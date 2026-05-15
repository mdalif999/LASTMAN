import flet as ft
from datetime import datetime
from database import get_only_due_reports, collect_due_payment

def DueManagementPage(page):
    # --- তারিখ ফরম্যাট করার ফাংশন ---
    def format_date_time(date_str):
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            return dt.strftime('%d %b, %y  |  %I:%M %p')
        except:
            return date_str

    # --- ডাটা রিফ্রেশ এবং ফিল্টার লজিক ---
    def refresh_data(filter_type="all"):
        try:
            search_query = search_field.value.lower()
            start_d = start_date_btn.text
            end_d = end_date_btn.text
        except:
            search_query = ""
            start_d = "Start Date"
            end_d = "End Date"
        
        data_list = get_only_due_reports()
        due_table.rows.clear()
        
        t_due_sum = 0
        now = datetime.now()

        for row in data_list:
            c_name_raw = row['customer_name'] if row['customer_name'] else "Cash"
            c_name = str(c_name_raw).lower()
            phone_val = str(row['customer_phone'] or "").lower()
            
            sale_date_str = str(row['sale_date'])
            try:
                sale_dt = datetime.strptime(sale_date_str, '%Y-%m-%d %H:%M:%S')
                sale_date_only = sale_date_str.split()[0]
            except:
                continue

            # ফিল্টার কন্ডিশন
            is_in_filter = False
            if filter_type == "today":
                is_in_filter = sale_dt.date() == now.date()
            elif filter_type == "month":
                is_in_filter = sale_dt.month == now.month and sale_dt.year == now.year
            elif filter_type == "year": # এই বছরের ফিল্টার
                is_in_filter = sale_dt.year == now.year
            elif filter_type == "all":
                is_in_filter = True

            # ডেট পিকার ফিল্টার
            if start_d != "Start Date" and end_d != "End Date":
                is_in_filter = start_d <= sale_date_only <= end_d

            # সার্চ ফিল্টার
            is_in_search = search_query in c_name or search_query in phone_val

            if is_in_filter and is_in_search:
                s_id = row['id']
                total = float(row['total_price'] or 0)
                paid = float(row['paid_amount'] or 0)
                due = total - paid

                if due > 0:
                    t_due_sum += due
                    due_table.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Container(
                                    content=ft.Text(format_date_time(sale_date_str), size=11), 
                                    padding=ft.padding.only(left=5), 
                                    border=ft.border.only(left=ft.BorderSide(2, ft.Colors.ORANGE))
                                )),
                                ft.DataCell(ft.Column([
                                    ft.Text(c_name_raw, weight="bold", size=14),
                                    ft.Text(row['customer_phone'] or "No Number", size=11, color="white60")
                                ], tight=True, spacing=0)),
                                ft.DataCell(ft.Text(f"{total:,.2f}")),
                                ft.DataCell(ft.Text(f"{paid:,.2f}", color="green")),
                                ft.DataCell(ft.Text(f"{due:,.2f}", color="red", weight="bold")),
                                ft.DataCell(
                                    ft.IconButton(
                                        icon=ft.Icons.PAYMENTS_OUTLINED,
                                        icon_color="orange",
                                        on_click=lambda e, s=s_id, d=due, n=c_name_raw: show_pay_dialog(s, d, n)
                                    )
                                ),
                            ]
                        )
                    )
        
        due_summary_text.value = f"{t_due_sum:,.2f} TK"
        page.update()

    # --- UI Components ---
    start_date_btn = ft.TextButton("Start Date") 
    end_date_btn = ft.TextButton("End Date")

    search_field = ft.TextField(
        label="নাম বা নম্বর দিয়ে খুঁজুন",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda _: refresh_data(),
        expand=True, bgcolor="white10", border_radius=10, height=45, text_size=14
    )

    due_summary_text = ft.Text("0.00 TK", size=25, weight="bold", color="red")

    # এখানে 'This Year' অপশনটি যোগ করা হয়েছে
    filter_menu = ft.PopupMenuButton(
        icon=ft.Icons.FILTER_ALT_ROUNDED,
        icon_color="orange",
        items=[
            ft.PopupMenuItem(text="Today's Due", on_click=lambda _: refresh_data("today")),
            ft.PopupMenuItem(text="This Month", on_click=lambda _: refresh_data("month")),
            ft.PopupMenuItem(text="This Year", on_click=lambda _: refresh_data("year")),
            ft.PopupMenuItem(text="All Time Due", on_click=lambda _: refresh_data("all")),
        ]
    )

    due_table = ft.DataTable(
        heading_row_color=ft.Colors.BLUE_GREY_900,
        columns=[
            ft.DataColumn(ft.Text("সময় ও তারিখ")),
            ft.DataColumn(ft.Text("কাস্টমার")),
            ft.DataColumn(ft.Text("মোট বিল")),
            ft.DataColumn(ft.Text("পেইড")),
            ft.DataColumn(ft.Text("বাকি")),
            ft.DataColumn(ft.Text("জমা নিন")),
        ]
    )

    def show_pay_dialog(sale_id, current_due, customer_name):
        pay_input = ft.TextField(label="জমার পরিমাণ", value=str(current_due), keyboard_type=ft.KeyboardType.NUMBER)
        def save_payment(e):
            amount = float(pay_input.value or 0)
            if 0 < amount <= current_due:
                collect_due_payment(sale_id, amount)
                page.close(dialog)
                refresh_data()
                page.snack_bar = ft.SnackBar(ft.Text(f"{amount} TK Received"), bgcolor="green")
                page.snack_bar.open = True
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text(f"বকেয়া জমা: {customer_name}"),
            content=pay_input,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.close(dialog)),
                ft.ElevatedButton("Confirm", on_click=save_payment, bgcolor="orange", color="white")
            ]
        )
        page.open(dialog)

    refresh_data()

    return ft.Container(
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, on_click=lambda _: page.go("/"), icon_size=18),
                    ft.Text("Due Management", size=28, weight="bold"),
                ]),
                filter_menu
            ], alignment="spaceBetween"),
            ft.Container(
                content=ft.Row([
                    ft.Column([ft.Text("Total Outstanding Due", size=14), due_summary_text], expand=True),
                    ft.Icon(ft.Icons.MONETIZATION_ON, size=40, color="red300")
                ]),
                padding=20, bgcolor="#1e2b5e", border_radius=15
            ),
            ft.Divider(height=10, color="transparent"),
            ft.Row([search_field]),
            ft.Container(
                content=ft.ListView([ft.Row([due_table], scroll="always")], expand=True),
                expand=True, bgcolor="#0f111a", padding=10, border_radius=15
            )
        ], expand=True)
    )