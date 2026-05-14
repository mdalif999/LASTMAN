import flet as ft
from database import get_admin_sales_report, get_investment_details

def admin_panel_page(page):
    # লাভসহ সেলস টেবিল
    sales_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("তারিখ")),
            ft.DataColumn(ft.Text("কাস্টমার")),
            ft.DataColumn(ft.Text("আইটেম")),
            ft.DataColumn(ft.Text("নেট বিল")),
            ft.DataColumn(ft.Text("লাভ (Profit)", color="orange", weight="bold")),
        ],
        rows=[],
        heading_row_color=ft.Colors.BLUE_GREY_900,
        column_spacing=20,
    )

    # ইনভেস্টমেন্ট টেবিল
    invest_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("মালের নাম")),
            ft.DataColumn(ft.Text("ব্র্যান্ড")),
            ft.DataColumn(ft.Text("স্টক")),
            ft.DataColumn(ft.Text("কেনা দাম")),
            ft.DataColumn(ft.Text("মোট ইনভেস্ট")),
        ],
        rows=[],
        heading_row_color=ft.Colors.INDIGO_900,
    )

    profit_card_text = ft.Text("0 TK", size=28, weight="bold", color="orange")
    invest_card_text = ft.Text("0 TK", size=28, weight="bold", color="cyan")

    def load_data():
        try:
            # ১. প্রফিট ডাটা লোড
            s_data = get_admin_sales_report()
            sales_table.rows.clear()
            total_p = 0
            for r in s_data:
                # ইন্ডেক্সিং ডাটাবেস কোয়েরি অনুযায়ী (r[7] হলো লাভ)
                p = float(r[7] or 0)
                total_p += p
                sales_table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(r[0])[:10])),
                    ft.DataCell(ft.Text(str(r[1]))),
                    ft.DataCell(ft.Text(str(r[3]))),
                    ft.DataCell(ft.Text(f"{r[4]:,.2f}")),
                    ft.DataCell(ft.Text(f"{p:,.2f}", color="orange", weight="bold")),
                ]))
            
            # ২. ইনভেস্টমেন্ট ডাটা লোড
            i_data = get_investment_details()
            invest_table.rows.clear()
            total_i = 0
            for r in i_data:
                val = float(r[4] or 0)
                total_i += val
                invest_table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(r[0]))),
                    ft.DataCell(ft.Text(str(r[1]))),
                    ft.DataCell(ft.Text(str(r[2]))),
                    ft.DataCell(ft.Text(f"{r[3]:,.2f}")),
                    ft.DataCell(ft.Text(f"{val:,.2f}")),
                ]))
            
            profit_card_text.value = f"{total_p:,.0f} TK"
            invest_card_text.value = f"{total_i:,.0f} TK"
            page.update()
        except Exception as e:
            print(f"Admin Load Error: {e}")

    load_data()

    # মেইন কন্টেইনার রিটার্ন
    return ft.Container(
        content=ft.Column([
            ft.Text("Owner Control Panel", size=32, weight="bold", color="blue"),
            
            # উপরের সামারি কার্ডগুলো
            ft.Row([
                ft.Container(
                    content=ft.Column([ft.Text("Net Profit (Total)"), profit_card_text]), 
                    padding=20, bgcolor="#2e1a05", border_radius=15, expand=True
                ),
                ft.Container(
                    content=ft.Column([ft.Text("Stock Investment"), invest_card_text]), 
                    padding=20, bgcolor="#051a2e", border_radius=15, expand=True
                ),
            ], spacing=20),

            # ট্যাব ভিউ (পাইথন ৩.৯ এ এরর এড়াতে আইকন ছাড়া)
            ft.Tabs(
                selected_index=0,
                expand=True,
                tabs=[
                    ft.Tab(
                        text="Sales & Profit History", 
                        content=ft.Container(
                            content=ft.Column([ft.Row([sales_table], scroll="always")], scroll="always"),
                            padding=10
                        )
                    ),
                    ft.Tab(
                        text="Product-wise Investment", 
                        content=ft.Container(
                            content=ft.Column([ft.Row([invest_table], scroll="always")], scroll="always"),
                            padding=10
                        )
                    ),
                ],
            )
        ], expand=True),
        padding=20
    )