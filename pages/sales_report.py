import flet as ft
from database import get_filtered_sales_report, get_invoice_items


# ============================================================
# QTY FORMAT  (inches → pcs/ft/inc depending on unit_type)
# ============================================================
def format_qty(raw_qty, unit_in, unit_type):
    """
    raw_qty  = inches stored in DB
    unit_in  = piece length in inches (e.g. 120 for 10ft bar)
    unit_type = 'alum' | 'wool' | 'piece' | 'sft'
    """
    try:
        q  = float(raw_qty  or 0)
        ui = float(unit_in  or 120)
        ut = str(unit_type or "alum").lower()

        if ut == "piece":
            return f"{int(q)} pcs"
        if ut == "sft":
            return f"{q:.2f} sft"

        # alum / wool → break into pcs + ft + inc
        parts = []
        if ut in ("alum", "wool") and ui > 0:
            pcs    = int(q // ui)
            remain = q % ui
        else:
            pcs    = 0
            remain = q

        ft_val  = int(remain // 12)
        in_val  = round(remain % 12, 1)

        if pcs   > 0: parts.append(f"{pcs} pcs")
        if ft_val > 0: parts.append(f"{ft_val} ft")
        if in_val > 0: parts.append(f"{in_val} inc")
        return " ".join(parts) if parts else "0"
    except Exception:
        return str(raw_qty)


# ============================================================
# SALES REPORT PAGE
# ============================================================
def sales_report_page(page):

    all_rows = []   # সব data cache করা হবে — search filter এর জন্য

    # ── summary texts ──────────────────────────────────────
    sales_card_text = ft.Text("0.00 TK", size=22, weight="bold", color="green")
    due_card_text   = ft.Text("0.00 TK", size=22, weight="bold", color="red")
    row_count_text  = ft.Text("0 records", size=13, color="white54")

    # ── search ────────────────────────────────────────────
    search_field = ft.TextField(
        label="Invoice No বা Customer নামে সার্চ করুন...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True, height=45, border_radius=10,
        label_style=ft.TextStyle(color="white54"),
        text_style=ft.TextStyle(color="white"),
        border_color="white24",
        on_change=lambda e: apply_search(e.control.value),
    )

    # ── table ─────────────────────────────────────────────
    report_table = ft.DataTable(
        show_checkbox_column=False,
        heading_row_color=ft.Colors.BLUE_GREY_900,
        border=ft.border.all(1, "white10"),
        horizontal_lines=ft.BorderSide(1, "white10"),
        column_spacing=18,
        columns=[
            ft.DataColumn(ft.Text("SN",           color="white", weight="bold")),
            ft.DataColumn(ft.Text("Invoice No",   color="cyan200", weight="bold")),
            ft.DataColumn(ft.Text("Date & Time",  color="white", weight="bold")),
            ft.DataColumn(ft.Text("Customer",     color="white", weight="bold")),
            ft.DataColumn(ft.Text("Phone",        color="white", weight="bold")),
            ft.DataColumn(ft.Text("Net",          color="white", weight="bold")),
            ft.DataColumn(ft.Text("Paid",         color="green", weight="bold")),
            ft.DataColumn(ft.Text("Due",          color="red",   weight="bold")),
        ],
    )

    # ── invoice popup ──────────────────────────────────────
    def show_invoice_details(order_id):
        items = get_invoice_items(order_id)
        if not items:
            page.snack_bar = ft.SnackBar(
                ft.Text("Invoice data পাওয়া যায়নি।", color="white"), bgcolor="red"
            )
            page.snack_bar.open = True
            page.update()
            return

        product_rows = []
        grand_total  = 0.0
        total_disc   = 0.0

        for i, item in enumerate(items):
            total      = float(item["total"]    or 0)
            price      = float(item["price"]    or 0)
            disc       = float(item["discount"] or 0)
            unit_in    = float(item["unit_in"]  or 120)
            unit_type  = item["unit_type"] or "alum"
            raw_qty    = float(item["quantity"] or 0)

            qty_str    = format_qty(raw_qty, unit_in, unit_type)
            grand_total += total
            total_disc  += disc

            product_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(i + 1),                    color="black")),
                ft.DataCell(ft.Text(str(item["die_no"]    or "—"), color="black")),
                ft.DataCell(ft.Text(str(item["profile_name"] or "—"), color="black", weight="bold")),
                ft.DataCell(ft.Text(str(item["brand"]     or "—"), color="black")),
                ft.DataCell(ft.Text(str(item["color"]     or "—"), color="black")),
                ft.DataCell(ft.Text(str(item["spec"]      or "—"), color="black")),
                ft.DataCell(ft.Text(qty_str,                       color="blue_900", weight="bold")),
                ft.DataCell(ft.Text(f"{price:,.2f}",               color="black")),
                ft.DataCell(ft.Text(f"{total:,.2f}",               color="black", weight="bold")),
            ]))

        net_after_disc = grand_total - total_disc

        # ── first row এর customer info ────────────────────
        first = dict(items[0])
        cust_name  = first.get("customer_name",  "") or ""
        cust_phone = first.get("customer_phone", "") or ""

        # paid/due — sales table থেকে (order_id দিয়ে group করা নেই, তাই first row নিচ্ছি)
        # আসলে প্রতিটা row তে same paid/due থাকে (billing level এ set হয়)
        paid = float(first.get("paid_amount", 0) or 0)
        due  = float(first.get("due_amount",  0) or 0)

        # ── popup ──────────────────────────────────────────
        invoice_dialog = ft.AlertDialog(
            modal=True,
            bgcolor="white",
            shape=ft.RoundedRectangleBorder(radius=14),
            title=ft.Container(
                bgcolor="#1a237e",
                border_radius=ft.border_radius.only(top_left=14, top_right=14),
                padding=ft.padding.symmetric(horizontal=20, vertical=14),
                content=ft.Row([
                    ft.Icon(ft.Icons.RECEIPT_LONG, color="white", size=26),
                    ft.Column([
                        ft.Text(f"Invoice  #{order_id}",
                                size=20, weight="bold", color="white"),
                        ft.Text(f"{cust_name}  {cust_phone}",
                                size=13, color="white70"),
                    ], spacing=2, tight=True),
                ], spacing=12),
            ),
            content=ft.Container(
                width=1000,
                bgcolor="white",
                content=ft.Column([
                    # items table
                    ft.Container(
                        content=ft.ListView([
                            ft.DataTable(
                                bgcolor="white",
                                border=ft.border.all(1, "black12"),
                                heading_row_color="#f0f4ff",
                                horizontal_lines=ft.BorderSide(1, "black12"),
                                vertical_lines=ft.BorderSide(0.5, "black12"),
                                column_spacing=16,
                                columns=[
                                    ft.DataColumn(ft.Text("SN",      color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Die No",  color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Profile", color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Brand",   color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Color",   color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Spec",    color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Qty",     color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Price",   color="black", weight="bold")),
                                    ft.DataColumn(ft.Text("Total",   color="black", weight="bold")),
                                ],
                                rows=product_rows,
                            )
                        ]),
                        border=ft.border.all(1, "black12"),
                        border_radius=8,
                        padding=5,
                    ),

                    ft.Container(height=12),

                    # summary
                    ft.Container(
                        bgcolor="#f7f9ff",
                        border=ft.border.all(1, "black12"),
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=20, vertical=14),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"Total Items : {len(items)}",
                                        size=14, color="black"),
                            ]),
                            ft.Column([
                                ft.Row([
                                    ft.Text("Gross Total :",  size=14, color="black"),
                                    ft.Text(f"{grand_total:,.2f} TK",
                                            size=14, weight="bold", color="black"),
                                ], spacing=20),
                                ft.Row([
                                    ft.Text("Discount    :",  size=13, color="red"),
                                    ft.Text(f"- {total_disc:,.2f} TK",
                                            size=13, color="red", weight="bold"),
                                ], spacing=20),
                                ft.Divider(color="black12", height=6),
                                ft.Row([
                                    ft.Text("NET PAYABLE :", size=16, weight="bold", color="black"),
                                    ft.Text(f"{net_after_disc:,.2f} TK",
                                            size=16, weight="bold", color="black"),
                                ], spacing=20),
                                ft.Row([
                                    ft.Text("Paid Amount :", size=14, color="green"),
                                    ft.Text(f"{paid:,.2f} TK",
                                            size=14, color="green", weight="bold"),
                                ], spacing=20),
                                ft.Row([
                                    ft.Text("Due Amount  :", size=14,
                                            color="red" if due > 0 else "green"),
                                    ft.Text(f"{due:,.2f} TK",
                                            size=14, weight="bold",
                                            color="red" if due > 0 else "green"),
                                ], spacing=20),
                            ], horizontal_alignment="end"),
                        ], alignment="spaceBetween"),
                    ),
                ], scroll=ft.ScrollMode.AUTO),
                padding=ft.padding.only(left=16, right=16, top=16, bottom=8),
            ),
            actions=[
                ft.TextButton(
                    "Close",
                    style=ft.ButtonStyle(color="black"),
                    on_click=lambda _: page.close(invoice_dialog),
                )
            ],
        )

        page.open(invoice_dialog)

    # ── render rows ────────────────────────────────────────
    def render_rows(data):
        report_table.rows.clear()
        t_sales = 0.0
        t_due   = 0.0

        for index, row in enumerate(data):
            try:
                r          = dict(row)
                net_total  = float(r.get("total",        0) or 0) - float(r.get("discount", 0) or 0)
                paid       = float(r.get("paid_amount",  0) or 0)
                due        = float(r.get("due_amount",   0) or 0)
                order_id   = r.get("order_id") or "—"
                sale_date  = r.get("sale_date")  or ""
                sale_time  = r.get("sale_time")  or ""
                cust_name  = r.get("customer_name")  or "Cash"
                cust_phone = r.get("customer_phone") or "—"

                t_sales += net_total
                t_due   += due

                report_table.rows.append(ft.DataRow(
                    on_select_changed=lambda e, oid=order_id: show_invoice_details(oid),
                    cells=[
                        ft.DataCell(ft.Text(str(index + 1), color="white54", size=12)),
                        ft.DataCell(ft.Text(f"{order_id}", color="cyan200", weight="bold")),
                        ft.DataCell(ft.Text(f"{sale_date}  {sale_time}", size=12, color="white70")),
                        ft.DataCell(ft.Text(cust_name,  color="white", weight="bold")),
                        ft.DataCell(ft.Text(cust_phone, color="white60", size=12)),
                        ft.DataCell(ft.Text(f"{net_total:,.2f}", color="white",  weight="bold")),
                        ft.DataCell(ft.Text(f"{paid:,.2f}",      color="green")),
                        ft.DataCell(ft.Text(f"{due:,.2f}",
                                            color="red" if due > 0 else "green")),
                    ],
                ))
            except Exception as row_err:
                print(f"Row Error: {row_err}")

        sales_card_text.value = f"{t_sales:,.2f} TK"
        due_card_text.value   = f"{t_due:,.2f}   TK"
        row_count_text.value  = f"{len(data)} records"
        page.update()

    # ── search filter ──────────────────────────────────────
    def apply_search(query):
        q = (query or "").lower().strip()
        if not q:
            render_rows(all_rows)
            return
        filtered = [
            r for r in all_rows
            if q in str(r["order_id"]       or "").lower()
            or q in str(r["customer_name"]  or "").lower()
            or q in str(r["customer_phone"] or "").lower()
        ]
        render_rows(filtered)

    # ── load from DB (সংশোধিত) ───────────────────────────────
    def load_report_data(filter_type="today"):
        nonlocal all_rows
        try:
            raw_data = list(get_filtered_sales_report(filter_type))
            
            # ডেটা গ্রুপ করার ম্যাজিক: একই order_id এর আইটেমগুলো যোগ করে ফেলা
            grouped = {}
            for row in raw_data:
                r = dict(row)
                oid = r.get("order_id")
                if oid not in grouped:
                    grouped[oid] = {
                        "order_id": oid,
                        "sale_date": r.get("sale_date"),
                        "sale_time": r.get("sale_time"),
                        "customer_name": r.get("customer_name"),
                        "customer_phone": r.get("customer_phone"),
                        "total": 0.0,
                        "discount": 0.0,
                        "paid_amount": r.get("paid_amount"),
                        "due_amount": r.get("due_amount")
                    }
                grouped[oid]["total"]    += float(r.get("total") or 0)
                grouped[oid]["discount"] += float(r.get("discount") or 0)
            
            # গ্রুপ করা ডেটাগুলো লিস্টে নিয়ে আসা
            all_rows = list(grouped.values())
            
            search_field.value = ""
            render_rows(all_rows)
        except Exception as e:
            print(f"Loading Error: {e}")

    # ── filter buttons ─────────────────────────────────────
    def filter_btn(label, ftype):
        return ft.ElevatedButton(
            label,
            bgcolor="white10", color="white",
            height=36,
            on_click=lambda _: load_report_data(ftype),
        )

    # initial load
    load_report_data("today")

    # ── UI ─────────────────────────────────────────────────
    return ft.Container(
        padding=20, expand=True,
        content=ft.Column([

            ft.Text("Sales Report", size=25, weight="bold"),
            ft.Container(height=5),

            # summary cards
            ft.Row([
                ft.Container(
                    expand=1, bgcolor="#1a237e", padding=15, border_radius=10,
                    content=ft.Column([
                        ft.Text("Total Sales", color="white60", size=13),
                        sales_card_text,
                    ]),
                ),
                ft.Container(
                    expand=1, bgcolor="#1a237e", padding=15, border_radius=10,
                    content=ft.Column([
                        ft.Text("Total Due", color="white60", size=13),
                        due_card_text,
                    ]),
                ),
            ], spacing=15),

            ft.Container(height=8),

            # filter buttons
            ft.Row([
                filter_btn("Today",     "today"),
                filter_btn("This Month","month"),
                filter_btn("This Year", "year"),
                filter_btn("All Time",  "all"),
                ft.Container(expand=True),
                row_count_text,
            ], spacing=8),

            ft.Container(height=6),

            # search
            ft.Row([search_field]),

            ft.Divider(height=10, color="white10"),

            # table
            ft.Container(
                expand=True,
                content=ft.ListView([
                    ft.Row([report_table], scroll=ft.ScrollMode.ALWAYS)
                ], expand=True),
                border=ft.border.all(1, "white10"),
                border_radius=10,
                padding=5,
            ),
        ]),
    ) 