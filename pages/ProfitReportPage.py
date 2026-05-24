import flet as ft
from database import get_profit_sum 

def ProfitReportPage(page):
    # --- স্টেট এবং ডাটাবেজ লজিক ---
    profit_display = ft.Text("0.00 TK", size=45, weight="bold", color="greenaccent")
    total_sales_display = ft.Text("Total Sales: 0.00 TK", size=18, color="white70")
    
    def refresh_profit(period="today"):
        # ডাটাবেজ থেকে আসল ডেটা আনা হচ্ছে
        p, s = get_profit_sum(period)
        
        # UI আপডেট করা
        profit_display.value = f"{p:,.2f} TK"
        total_sales_display.value = f"Total Sales in this period: {s:,.2f} TK"
        page.update()

    # --- ফিল্টার বাটন লজিক ---
    def filter_clicked(e):
        for btn in filter_row.controls:
            btn.bgcolor = ft.Colors.BLUE_GREY_800
        e.control.bgcolor = ft.Colors.BLUE_700
        
        # বাটনের data প্রপার্টি অনুযায়ী ডাটাবেজে রিকোয়েস্ট পাঠানো
        refresh_profit(e.control.data)
        page.update()

    # ফিল্টার রো
    filter_row = ft.Row([
        ft.Container(content=ft.Text("Today"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_700, data="today", on_click=filter_clicked),
        ft.Container(content=ft.Text("This Month"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800, data="month", on_click=filter_clicked),
        ft.Container(content=ft.Text("This Year"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800, data="year", on_click=filter_clicked),
        ft.Container(content=ft.Text("All Time"), padding=10, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800, data="all", on_click=filter_clicked),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    # --- পেজ লেআউট ---
    content = ft.Column([
        ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK_IOS_NEW, icon_color="white", on_click=lambda _: page.go("/")),
            ft.Text("Profit Analysis Report", size=24, weight="bold", color="white"),
        ], alignment=ft.MainAxisAlignment.START),
        
        ft.Divider(height=20, color="transparent"),
        
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.MONETIZATION_ON_OUTLINED, size=50, color="greenaccent"),
                ft.Text("Net Profit Amount", size=16, color="white60"),
                profit_display,
                total_sales_display,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=40,
            bgcolor="#1A233A",
            border_radius=20,
            alignment=ft.alignment.center,
            width=600,
        ),
        
        ft.Divider(height=30, color="transparent"),
        
        ft.Text("Select Time Period", size=16, color="white70"),
        filter_row,
        
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # শুরুতে আজকের প্রফিট অটো লোড হবে
    refresh_profit("today")

    return ft.Container(
        content=content,
        padding=30,
        expand=True,
        bgcolor="#0F172A"
    )