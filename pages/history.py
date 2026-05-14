import flet as ft
from database import get_audit_logs # নিশ্চিত করুন এই ফাংশনটি টাইপ ও লিমিট প্যারামিটার নিতে পারে

def history_page(page: ft.Page):
    # ১. ফিট-ইঞ্চি ফরম্যাট করার ছোট ইন্টারনাল ফাংশন
    def format_history_details(text):
        import re
        if "নতুন স্টক:" in text:
            # টেক্সট থেকে সংখ্যাটি খুঁজে বের করা
            match = re.search(r"(\d+\.\d+|\d+)", text)
            if match:
                total_inches = float(match.group(1))
                # ইঞ্চি থেকে ফিট-ইঞ্চি ক্যালকুলেশন
                feet = int(total_inches // 12)
                inches = round(total_inches % 12, 1)
                
                # নতুন ফরম্যাট তৈরি
                formatted_unit = f"{feet}' {inches}\""
                return text.replace(match.group(1), formatted_unit)
        return text

    # ডাটা আপডেট করার ফাংশন
    def update_table(e=None):
        selected_type = filter_dropdown.value
        logs = get_audit_logs(action_type=selected_type, limit=50) 
        
        history_table.rows.clear()
        if logs:
            for l in logs:
                # এখানে format_history_details(l[3]) ব্যবহার করা হয়েছে
                history_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(l[0]))), # Timestamp
                        ft.DataCell(ft.Text(l[1], color=action_colors.get(l[1], "white"))),
                        ft.DataCell(ft.Text(l[2])), # Product Name
                        ft.DataCell(ft.Text(format_history_details(l[3]))), # Details ফিক্সড
                    ])
                )
        page.update()
    action_colors = {
        "PRICE_CHANGE": "orange",
        "STOCK_IN": "green",
        "STOCK_OUT": "red",
        "UPDATE": "blue"
    }

    # ফিল্টার অপশন (ড্রপডাউন)
    filter_dropdown = ft.Dropdown(
        label="কাজের ধরন অনুযায়ী দেখুন",
        width=300,
        options=[
            ft.dropdown.Option("All"),
            ft.dropdown.Option("PRICE_CHANGE", "Price Change"),
            ft.dropdown.Option("STOCK_UPDATE", "Stock Update"), # এখানে STOCK_UPDATE দিন
            ft.dropdown.Option("NEW_ITEM", "New Item"),         # এখানে NEW_ITEM দিন
            ft.dropdown.Option("DELETE_ITEM", "Delete Item"),
        ],
        value="All",
        on_change=update_table
    )
    history_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("সময়")),
            ft.DataColumn(ft.Text("কাজের ধরন")),
            ft.DataColumn(ft.Text("প্রোডাক্ট")),
            ft.DataColumn(ft.Text("বিস্তারিত")),
        ],
        rows=[]
    )

    # শুরুতে একবার টেবিল লোড করা
    update_table()

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HISTORY, color="orange", size=30),
                ft.Text("Inventory & Price History", size=25, weight="bold")
            ]),
            ft.Divider(height=20, color="white10"),
            filter_dropdown, # ফিল্টার ড্রপডাউন উপরে থাকলো
            ft.Container(height=10),
            ft.Container(
                content=ft.ListView(
                    controls=[history_table],
                    expand=True,
                ),
                expand=True,
                border=ft.border.all(1, "white10"),
                border_radius=10,
            )
        ]),
        padding=30,
        expand=True
    )