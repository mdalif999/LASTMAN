import flet as ft
from database import get_profit_sum, get_brand_profit_summary


def ProfitReportPage(page):

    profit_display     = ft.Text("0.00 TK", size=45, weight="bold", color="greenaccent")
    total_sales_display = ft.Text("", size=16, color="white70")
    brand_table_rows   = []

    brand_table = ft.DataTable(
        bgcolor="#1A233A",
        border=ft.border.all(1, "#2A3A5A"),
        horizontal_lines=ft.BorderSide(1, "#2A3A5A"),
        vertical_lines=ft.BorderSide(1, "#2A3A5A"),
        heading_row_color="#0F172A",
        column_spacing=30,
        columns=[
            ft.DataColumn(ft.Text("Brand",    color="white70", weight="bold")),
            ft.DataColumn(ft.Text("Gross",    color="white70", weight="bold"), numeric=True),
            ft.DataColumn(ft.Text("Discount", color="orange",  weight="bold"), numeric=True),
            ft.DataColumn(ft.Text("Net",      color="white70", weight="bold"), numeric=True),
            ft.DataColumn(ft.Text("Profit",   color="greenaccent", weight="bold"), numeric=True),
        ],
        rows=brand_table_rows,
    )

    def refresh(period="today"):
        # overall profit
        p, s = get_profit_sum(period)
        profit_display.value      = f"{p:,.2f} TK"
        profit_display.color      = "greenaccent" if p >= 0 else "red"
        total_sales_display.value = f"Gross Sale: {s:,.2f} TK"

        # brand wise table
        brand_table.rows.clear()
        rows = get_brand_profit_summary(period)

        for brand, gross, net, discount, profit in rows:
            profit  = profit  or 0.0
            gross   = gross   or 0.0
            net     = net     or 0.0
            discount = discount or 0.0

            brand_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(brand or "Unknown"), color="white")),
                ft.DataCell(ft.Text(f"{gross:,.2f}",   color="white")),
                ft.DataCell(ft.Text(f"{discount:,.2f}", color="orange")),
                ft.DataCell(ft.Text(f"{net:,.2f}",     color="white")),
                ft.DataCell(ft.Text(
                    f"{profit:,.2f}",
                    color="greenaccent" if profit >= 0 else "red",
                    weight="bold"
                )),
            ]))

        page.update()

    def filter_clicked(e):
        for btn in filter_row.controls:
            btn.bgcolor = ft.Colors.BLUE_GREY_800
        e.control.bgcolor = ft.Colors.BLUE_700
        refresh(e.control.data)
        page.update()

    filter_row = ft.Row([
        ft.Container(content=ft.Text("Today",      color="white"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_700,      data="today", on_click=filter_clicked),
        ft.Container(content=ft.Text("This Month", color="white"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800, data="month", on_click=filter_clicked),
        ft.Container(content=ft.Text("This Year",  color="white"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800, data="year",  on_click=filter_clicked),
        ft.Container(content=ft.Text("All Time",   color="white"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800, data="all",   on_click=filter_clicked),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    content = ft.Column([
        ft.Row([
            ft.Text("Profit Analysis Report", size=24, weight="bold", color="white"),
        ]),

        ft.Divider(height=15, color="transparent"),

        # top summary card
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.MONETIZATION_ON_OUTLINED, size=45, color="greenaccent"),
                ft.Text("Net Profit", size=15, color="white60"),
                profit_display,
                total_sales_display,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=35,
            bgcolor="#1A233A",
            border_radius=20,
            alignment=ft.alignment.center,
            width=500,
        ),

        ft.Divider(height=20, color="transparent"),

        ft.Text("Filter by Period", size=15, color="white70"),
        filter_row,

        ft.Divider(height=25, color="transparent"),

        ft.Text("Brand-wise Breakdown", size=17, weight="bold", color="white"),
        ft.Divider(height=6, color="transparent"),

        ft.Container(
            content=ft.ListView([brand_table], expand=True),
            border=ft.border.all(1, "#2A3A5A"),
            border_radius=12,
            expand=True,
        ),

    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    refresh("today")

    return ft.Container(
        content=content,
        padding=30,
        expand=True,
        bgcolor="#0F172A"
    )