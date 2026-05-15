import flet as ft
import re
from database import get_audit_logs


def history_page(page: ft.Page):

    # ── action type → color & label ────────────────────────
    ACTION_COLORS = {
        "Opening Stock":  "cyan",
        "Stock Added":    "green",
        "Stock Removed":  "red",
        "Price Changed":  "orange",
        "STOCK_UPDATE":   "green",
        "NEW_ITEM":       "cyan",
        "DELETE_ITEM":    "red400",
    }

    ACTION_LABELS = {
        "Opening Stock": "Opening Stock",
        "Stock Added":   "Stock Added",
        "Stock Removed": "Stock Removed",
        "Price Changed": "Price Changed",
        "STOCK_UPDATE":  "Stock Update",
        "NEW_ITEM":      "New Item",
        "DELETE_ITEM":   "Delete Item",
    }

    # ── details text format ────────────────────────────────
    def format_details(text):
        """ইঞ্চি সংখ্যাকে ফিট-ইঞ্চিতে দেখায় যদি 'Qty' থাকে।"""
        if not text:
            return "—"
        try:
            def replace_inches(m):
                val = float(m.group(1))
                if val >= 12:
                    ft_val  = int(val // 12)
                    in_val  = round(val % 12, 1)
                    return f"{ft_val}' {in_val}\""
                return m.group(0)
            # শুধু Qty: বা নতুন স্টক: এর পাশের সংখ্যায় apply করব
            return re.sub(r"Qty[:\s]+([\d.]+)", lambda m: f"Qty: {replace_inches(m)}", text)
        except Exception:
            return text

    # ── table ──────────────────────────────────────────────
    history_table = ft.DataTable(
        heading_row_color=ft.Colors.BLUE_GREY_900,
        border=ft.border.all(1, "white10"),
        horizontal_lines=ft.BorderSide(1, "white10"),
        column_spacing=20,
        columns=[
            ft.DataColumn(ft.Text("সময়",        color="white", weight="bold")),
            ft.DataColumn(ft.Text("কাজের ধরন",  color="white", weight="bold")),
            ft.DataColumn(ft.Text("প্রোডাক্ট",  color="white", weight="bold")),
            ft.DataColumn(ft.Text("বিস্তারিত",  color="white", weight="bold")),
        ],
        rows=[],
    )

    # ── filter dropdown ────────────────────────────────────
    filter_dropdown = ft.Dropdown(
        label="কাজের ধরন অনুযায়ী ফিল্টার করুন",
        width=300,
        text_style=ft.TextStyle(color="white"),
        label_style=ft.TextStyle(color="white60"),
        border_color="white24",
        options=[
            ft.dropdown.Option("All",           "সব দেখুন"),
            ft.dropdown.Option("Opening Stock", "Opening Stock"),
            ft.dropdown.Option("Stock Added",   "Stock Added"),
            ft.dropdown.Option("Stock Removed", "Stock Removed"),
            ft.dropdown.Option("Price Changed", "Price Changed"),
            ft.dropdown.Option("STOCK_UPDATE",  "Stock Update (পুরনো)"),
            ft.dropdown.Option("NEW_ITEM",      "New Item (পুরনো)"),
        ],
        value="All",
        on_change=lambda e: update_table(),
    )

    # ── update table ───────────────────────────────────────
    def update_table():
        selected = filter_dropdown.value or "All"
        try:
            logs = get_audit_logs(action_type=selected, limit=100)
        except Exception as ex:
            print(f"get_audit_logs error: {ex}")
            logs = []

        history_table.rows.clear()

        if not logs:
            history_table.rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text("কোনো ইতিহাস নেই", color="white54", size=14)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text("")),
            ]))
            page.update()
            return

        for log in logs:
            try:
                # get_audit_logs returns tuples: (timestamp, action_type, product_name, details)
                timestamp   = str(log[0] or "—")
                action_type = str(log[1] or "—")
                product     = str(log[2] or "—")
                details     = format_details(str(log[3] or "—"))

                color = ACTION_COLORS.get(action_type, "white70")
                label = ACTION_LABELS.get(action_type, action_type)

                history_table.rows.append(ft.DataRow(cells=[
                    ft.DataCell(ft.Text(timestamp, size=12, color="white60")),
                    ft.DataCell(ft.Container(
                        content=ft.Text(label, size=13, weight="bold", color=color),
                        padding=ft.padding.only(left=6),
                        border=ft.border.only(left=ft.BorderSide(3, color)),
                    )),
                    ft.DataCell(ft.Text(product, size=13, color="white")),
                    ft.DataCell(ft.Text(details, size=12, color="white70")),
                ]))
            except Exception as ex:
                print(f"History row error: {ex}")
                continue

        page.update()

    # ── initial load ───────────────────────────────────────
    update_table()

    # ── UI ─────────────────────────────────────────────────
    return ft.Container(
        padding=30,
        expand=True,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HISTORY, color="orange", size=30),
                ft.Text("Inventory & Price History", size=25, weight="bold"),
            ]),
            ft.Divider(height=15, color="white10"),
            ft.Row([
                filter_dropdown,
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Refresh",
                    icon=ft.Icons.REFRESH,
                    bgcolor="white10",
                    color="white",
                    on_click=lambda _: update_table(),
                ),
            ]),
            ft.Container(height=10),
            ft.Container(
                content=ft.ListView(
                    controls=[history_table],
                    expand=True,
                ),
                expand=True,
                border=ft.border.all(1, "white10"),
                border_radius=10,
                padding=5,
            ),
        ]),
    )