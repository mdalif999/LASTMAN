import flet as ft
from database import get_inventory_items

def stock_report_page(page: ft.Page):
    items = get_inventory_items()
    
    def format_stock_display(total_qty, unit_size, u_type):
        qty = float(total_qty or 0)
        u_size = float(unit_size or 120)
        u_type = str(u_type).lower()

        if u_type == "alum":
            pcs = int(qty // u_size)
            remaining_inches = qty % u_size
            feet = int(remaining_inches // 12)
            inches = remaining_inches % 12
            res = []
            if pcs > 0: res.append(f"{pcs} Pcs")
            if feet > 0 or inches > 0:
                res.append(f"{feet}' {inches:.1f}\"")
            return " ".join(res) if res else "0 Pcs"
        elif u_type == "sft":
            return f"{qty:.2f} SFT"
        elif u_type == "piece" or u_type == "hardware":
            return f"{int(qty)} Pcs"
        elif u_type == "wool":
            feet = int(qty // 12)
            inches = qty % 12
            return f"{feet}' {inches:.1f}\""
        return f"{qty:.2f}"

    def get_stock_summary():
        total_items = len(items)
        low_stock_count = 0
        out_of_stock_count = 0
        total_investment = 0
        
        for i in items:
            stock_qty = float(i[6] or 0)
            unit_size = float(i[7] or 1)
            buy_p = float(i[8] or 0)
            u_type = str(i[10]).lower()

            if u_type == "alum" and unit_size > 0:
                item_inv = (stock_qty / unit_size) * buy_p
            else:
                item_inv = stock_qty * buy_p
            
            total_investment += item_inv
            if stock_qty <= 0:
                out_of_stock_count += 1
            elif (u_type == "alum" and stock_qty < unit_size) or (u_type != "alum" and stock_qty < 10):
                low_stock_count += 1
        
        return total_items, low_stock_count, out_of_stock_count, total_investment

    t_items, l_stock, o_stock, t_invest = get_stock_summary()

    stock_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("প্রোডাক্টের নাম")),
            ft.DataColumn(ft.Text("বর্তমান স্টক")),
            ft.DataColumn(ft.Text("অবস্থা")),
            ft.DataColumn(ft.Text("ইনভেস্টমেন্ট")),
        ],
        heading_row_color="#22ffffff", # হালকা সাদা ব্যাকগ্রাউন্ড যা সব ভার্সনে কাজ করবে
    )

    for i in items:
        stock_val = float(i[6] or 0)
        unit_size = float(i[7] or 1)
        buy_price = float(i[8] or 0)
        u_type = str(i[10]).lower()

        status = "In Stock"
        status_color = "green400" # স্ট্রিং হিসেবে কালার দিলাম
        if stock_val <= 0:
            status = "Out of Stock"
            status_color = "red400"
        elif (u_type == "alum" and stock_val < unit_size) or (u_type != "alum" and stock_val < 10):
            status = "Low Stock"
            status_color = "orange400"

        if u_type == "alum":
            row_inv = (stock_val / unit_size) * buy_price
        else:
            row_inv = stock_val * buy_price

        stock_table.rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(f"{i[3]} ({i[2]})")),
                ft.DataCell(ft.Text(format_stock_display(stock_val, unit_size, u_type))), 
                ft.DataCell(ft.Text(status, color=status_color)),
                ft.DataCell(ft.Text(f"{row_inv:,.2f} TK")),
            ])
        )

    return ft.Container(
        content=ft.Column([
            ft.Text("Inventory Stock Report", size=30, weight="bold"),
            ft.Divider(height=20, color="white10"),
            ft.Row([
                ft.Container(content=ft.Column([ft.Text("Total Items"), ft.Text(str(t_items), size=20, weight="bold")]), bgcolor="#1e2b5e", padding=20, border_radius=10, expand=True),
                ft.Container(content=ft.Column([ft.Text("Low Stock", color="orange"), ft.Text(str(l_stock), size=20, weight="bold")]), bgcolor="#1e2b5e", padding=20, border_radius=10, expand=True),
                ft.Container(content=ft.Column([ft.Text("Out of Stock", color="red"), ft.Text(str(o_stock), size=20, weight="bold")]), bgcolor="#1e2b5e", padding=20, border_radius=10, expand=True),
                ft.Container(content=ft.Column([ft.Text("Total Investment", color="green"), ft.Text(f"{t_invest:,.2f} TK", size=20, weight="bold")]), bgcolor="#1e2b5e", padding=20, border_radius=10, expand=True),
            ], spacing=20),
            ft.Container(height=20),
            ft.Text("Detailed Stock List", size=22, weight="bold"),
            ft.Container(content=ft.ListView(controls=[stock_table], expand=True), expand=True)
        ], scroll=ft.ScrollMode.AUTO),
        padding=40, expand=True
    )