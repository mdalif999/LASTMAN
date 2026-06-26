import flet as ft
import sqlite3
import datetime
import os
from database import get_filtered_sales_report, get_invoice_items


# ============================================================
# QTY FORMAT
# ============================================================
def format_qty(raw_qty, unit_in, unit_type):
    try:
        q  = float(raw_qty  or 0)
        ui = float(unit_in  or 120)
        ut = str(unit_type or "alum").lower()
        if ut == "piece": return f"{int(q)} pcs"
        if ut == "sft":   return f"{q:.2f} sft"
        parts = []
        if ut in ("alum", "wool") and ui > 0:
            pcs    = int(q // ui)
            remain = q % ui
        else:
            pcs = 0; remain = q
        ft_val = int(remain // 12)
        in_val = round(remain % 12, 1)
        if pcs   > 0: parts.append(f"{pcs} pcs")
        if ft_val > 0: parts.append(f"{ft_val} ft")
        if in_val > 0: parts.append(f"{in_val} inc")
        return " ".join(parts) if parts else "0"
    except Exception:
        return str(raw_qty)


# ============================================================
# CUSTOMER LEDGER PDF
# ============================================================
def generate_ledger_pdf(customer_name, customer_phone, rows, date_from, date_to):
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm

        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_path, exist_ok=True)
        safe_name = (customer_phone or customer_name or "customer").replace("/", "-")
        file_path = os.path.join(downloads_path, f"Ledger_{safe_name}.pdf")

        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(A4),
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=12*mm, bottomMargin=12*mm,
        )

        normal = ParagraphStyle("normal", fontSize=8, leading=10)
        bold   = ParagraphStyle("bold",   fontSize=8, leading=10, fontName="Helvetica-Bold")
        small  = ParagraphStyle("small",  fontSize=7, leading=9)
        small_r = ParagraphStyle("small_r", fontSize=7, leading=9, alignment=2)
        bold_r  = ParagraphStyle("bold_r",  fontSize=8, leading=10, fontName="Helvetica-Bold", alignment=2)

        elements = []

        # ── Header ──────────────────────────────────────────
        elements.append(Paragraph(
            "<b>CITY GLASS ART &amp; THY ALUMINIUM</b>",
            ParagraphStyle("h1", fontSize=16, leading=20, alignment=1, fontName="Helvetica-Bold")
        ))
        elements.append(Paragraph(
            "Park Road, Ghorapotti, Sutrapur, Bogura | 01719-252128",
            ParagraphStyle("h2", fontSize=9, leading=12, alignment=1)
        ))
        elements.append(Spacer(1, 3*mm))

        # ── Customer Info ────────────────────────────────────
        info_data = [[
            Paragraph(f"<b>Customer:</b> {customer_name or '—'}", normal),
            Paragraph(f"<b>Phone:</b> {customer_phone or '—'}", normal),
            Paragraph(f"<b>Period:</b> {date_from or 'All'} → {date_to or 'All'}", normal),
            Paragraph(f"<b>Printed:</b> {datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')}", normal),
        ]]
        info_table = Table(info_data, colWidths=["25%", "25%", "25%", "25%"])
        elements.append(info_table)
        elements.append(Spacer(1, 3*mm))

        # ── Column widths ────────────────────────────────────
        col_widths = [
            10*mm,  # SN
            18*mm,  # Invoice
            22*mm,  # Date
            60*mm,  # Profile Name
            22*mm,  # Spec
            18*mm,  # Color
            13*mm,  # Qty
            18*mm,  # Price
            20*mm,  # Total
            17*mm,  # Disc%
            20*mm,  # Net
            20*mm,  # Paid  ← merge হবে
            17*mm,  # Due   ← merge হবে
        ]

        header = [
            Paragraph("<b>SN</b>",          bold),
            Paragraph("<b>Invoice</b>",      bold),
            Paragraph("<b>Date</b>",         bold),
            Paragraph("<b>Profile Name</b>", bold),
            Paragraph("<b>Spec</b>",         bold),
            Paragraph("<b>Color</b>",        bold),
            Paragraph("<b>Qty</b>",          bold),
            Paragraph("<b>Price</b>",        bold_r),
            Paragraph("<b>Total</b>",        bold_r),
            Paragraph("<b>Disc%</b>",        bold_r),
            Paragraph("<b>Net</b>",          bold_r),
            Paragraph("<b>Paid</b>",         bold_r),
            Paragraph("<b>Due</b>",          bold_r),
        ]

        table_data = [header]

        # ── Invoice grouping ─────────────────────────────────
        # invoice wise group করি
        from collections import OrderedDict
        invoice_groups = OrderedDict()
        for r in rows:
            inv_id = str(r.get("order_id") or "—")
            if inv_id not in invoice_groups:
                invoice_groups[inv_id] = []
            invoice_groups[inv_id].append(r)

        span_commands = []  # ROWSPAN commands
        row_idx = 1  # header is row 0
        sn = 0

        t_total = t_disc = t_net = 0.0
        t_paid  = t_due  = 0.0
        seen_invoices = set()

        for inv_id, inv_rows in invoice_groups.items():
            inv_count = len(inv_rows)

            for local_i, r in enumerate(inv_rows):
                sn += 1
                total     = float(r.get("total",       0) or 0)
                disc      = float(r.get("discount",    0) or 0)
                disc_pct  = (disc / total * 100) if total > 0 else 0.0
                net       = total - disc
                paid      = float(r.get("paid_amount", 0) or 0)
                due       = float(r.get("due_amount",  0) or 0)
                price     = float(r.get("price",       0) or 0)
                qty       = float(r.get("quantity",    0) or 0)
                unit_in   = float(r.get("unit_in",   120) or 120)
                unit_type = str(r.get("unit_type", "alum") or "alum")
                date_     = str(r.get("sale_date",    "") or "")[:10]
                profile   = str(r.get("profile_name", "") or "—")
                spec      = str(r.get("spec",         "") or "—")
                color     = str(r.get("color",        "") or "—")

                # qty format
                if unit_type == "alum" and unit_in > 1:
                    pcs = int(qty // unit_in)
                    rem = qty % unit_in
                    ft_ = int(rem // 12)
                    inc = round(rem % 12, 1)
                    parts = []
                    if pcs > 0: parts.append(f"{pcs}p")
                    if ft_  > 0: parts.append(f"{ft_}ft")
                    if inc  > 0: parts.append(f'{inc:.0f}"')
                    qty_str = " ".join(parts) if parts else "0"
                else:
                    qty_str = f"{int(qty)}"

                t_total += total
                t_disc  += disc
                t_net   += net

                # paid/due শুধু প্রথম row তে, বাকিগুলো খালি
                if local_i == 0:
                    due_color = "red" if due > 0 else "green"
                    paid_cell = Paragraph(f"{paid:,.0f}", small_r)
                    due_cell  = Paragraph(
                        f"<font color='{due_color}'>{due:,.0f}</font>", small_r
                    )
                    # invoice wise unique paid/due
                    if inv_id not in seen_invoices:
                        seen_invoices.add(inv_id)
                        t_paid += paid
                        t_due  += due
                else:
                    paid_cell = Paragraph("", small)
                    due_cell  = Paragraph("", small)

                table_data.append([
                    Paragraph(str(sn),              small),
                    Paragraph(inv_id,               small),
                    Paragraph(date_,                small),
                    Paragraph(profile,              small),
                    Paragraph(spec,                 small),
                    Paragraph(color,                small),
                    Paragraph(qty_str,              small),
                    Paragraph(f"{price:,.0f}",      small_r),
                    Paragraph(f"{total:,.0f}",      small_r),
                    Paragraph(f"{disc_pct:.1f}%",   small_r),
                    Paragraph(f"{net:,.0f}",        small_r),
                    paid_cell,
                    due_cell,
                ])

                row_idx += 1

            # ROWSPAN — paid/due merge
            if inv_count > 1:
                span_commands.append(("SPAN", (11, row_idx - inv_count), (11, row_idx - 1)))
                span_commands.append(("SPAN", (12, row_idx - inv_count), (12, row_idx - 1)))

            # invoice border
            span_commands.append((
                "LINEBELOW",
                (0, row_idx - 1), (-1, row_idx - 1),
                0.8, colors.HexColor("#999999")
            ))

        # ── Total row ────────────────────────────────────────
        table_data.append([
            Paragraph(f"<b>TOTAL ({sn} items)</b>", bold),
            "", "", "", "", "", "",
            "",
            Paragraph(f"<b>{t_total:,.2f}</b>", bold_r),
            Paragraph(f"<b>{t_disc:,.2f}</b>",  bold_r),
            Paragraph(f"<b>{t_net:,.2f}</b>",   bold_r),
            Paragraph(f"<b>{t_paid:,.2f}</b>",  bold_r),
            Paragraph(f"<b><font color='red'>{t_due:,.2f}</font></b>", bold_r),
        ])

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_cmds = [
            # Header
            ("BACKGROUND",    (0,0),  (-1,0),  colors.white),
            ("TEXTCOLOR",     (0,0),  (-1,0),  colors.black),
            ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),  (-1,0),  8),
            ("LINEBELOW",     (0,0),  (-1,0),  1.2, colors.black),
            ("LINEABOVE",     (0,0),  (-1,0),  1.2, colors.black),

            # All cells
            ("FONTSIZE",      (0,1),  (-1,-1), 7),
            ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),  (-1,-1), 3),
            ("BOTTOMPADDING", (0,0),  (-1,-1), 3),
            ("GRID",          (0,0),  (-1,-1), 0.3, colors.HexColor("#dddddd")),
            ("ROWBACKGROUNDS",(0,1),  (-1,-2), [colors.white, colors.HexColor("#f9f9f9")]),

            # Total row
            ("BACKGROUND",    (0,-1), (-1,-1), colors.HexColor("#e8eaf6")),
            ("FONTNAME",      (0,-1), (-1,-1), "Helvetica-Bold"),
            ("LINEABOVE",     (0,-1), (-1,-1), 1.2, colors.black),
            ("SPAN",          (0,-1), (7,-1)),

            # Right align numbers
            ("ALIGN", (7,0),  (-1,-1), "RIGHT"),
            ("ALIGN", (0,0),  (0,-1),  "CENTER"),
        ] + span_commands

        table.setStyle(TableStyle(style_cmds))
        elements.append(table)
        doc.build(elements)
        return file_path

    except Exception as e:
        print(f"Ledger PDF error: {e}")
        import traceback; traceback.print_exc()
        return None


# ============================================================
# SALES REPORT PAGE
# ============================================================
def sales_report_page(page):

    all_rows = []

    sales_card_text = ft.Text("0.00 TK", size=22, weight="bold", color="green")
    due_card_text   = ft.Text("0.00 TK", size=22, weight="bold", color="red")
    row_count_text  = ft.Text("0 records", size=13, color="white54")

    search_field = ft.TextField(
        label="Invoice No বা Customer নামে সার্চ করুন...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True, height=45, border_radius=10,
        label_style=ft.TextStyle(color="white54"),
        text_style=ft.TextStyle(color="white"),
        border_color="white24",
        on_change=lambda e: apply_search(e.control.value),
    )

    report_table = ft.DataTable(
        show_checkbox_column=False,
        heading_row_color=ft.Colors.BLUE_GREY_900,
        border=ft.border.all(1, "white10"),
        horizontal_lines=ft.BorderSide(1, "white10"),
        column_spacing=18,
        columns=[
            ft.DataColumn(ft.Text("SN",          color="white",  weight="bold")),
            ft.DataColumn(ft.Text("Invoice No",  color="cyan200",weight="bold")),
            ft.DataColumn(ft.Text("Date & Time", color="white",  weight="bold")),
            ft.DataColumn(ft.Text("Customer",    color="white",  weight="bold")),
            ft.DataColumn(ft.Text("Phone",       color="white",  weight="bold")),
            ft.DataColumn(ft.Text("Net",         color="white",  weight="bold")),
            ft.DataColumn(ft.Text("Paid",        color="green",  weight="bold")),
            ft.DataColumn(ft.Text("Due",         color="red",    weight="bold")),
        ],
    )

    # ── invoice popup ──────────────────────────────────────
    def show_invoice_details(order_id):
        items = get_invoice_items(order_id)
        if not items:
            page.snack_bar = ft.SnackBar(
                ft.Text("Invoice data পাওয়া যায়নি।", color="white"), bgcolor="red")
            page.snack_bar.open = True; page.update(); return

        product_rows = []
        grand_total = total_disc = 0.0

        for i, item in enumerate(items):
            total     = float(item["total"]    or 0)
            price     = float(item["price"]    or 0)
            disc      = float(item["discount"] or 0)
            unit_in   = float(item["unit_in"]  or 120)
            unit_type = item["unit_type"] or "alum"
            raw_qty   = float(item["quantity"] or 0)
            qty_str   = format_qty(raw_qty, unit_in, unit_type)
            grand_total += total; total_disc += disc

            product_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(i+1),                       color="black")),
                ft.DataCell(ft.Text(str(item["die_no"]    or "—"),  color="black")),
                ft.DataCell(ft.Text(str(item["profile_name"] or "—"),color="black", weight="bold")),
                ft.DataCell(ft.Text(str(item["brand"]     or "—"),  color="black")),
                ft.DataCell(ft.Text(str(item["color"]     or "—"),  color="black")),
                ft.DataCell(ft.Text(str(item["spec"]      or "—"),  color="black")),
                ft.DataCell(ft.Text(qty_str,                        color="blue", weight="bold")),
                ft.DataCell(ft.Text(f"{price:,.2f}",                color="black")),
                ft.DataCell(ft.Text(f"{total:,.2f}",                color="black", weight="bold")),
            ]))

        net_after_disc = grand_total - total_disc
        first      = dict(items[0])
        cust_name  = first.get("customer_name",  "") or ""
        cust_phone = first.get("customer_phone", "") or ""
        paid       = float(first.get("paid_amount", 0) or 0)
        due        = float(first.get("due_amount",  0) or 0)

        invoice_dialog = ft.AlertDialog(
            modal=True, bgcolor="white",
            shape=ft.RoundedRectangleBorder(radius=14),
            title=ft.Container(
                bgcolor="#1a237e",
                border_radius=ft.border_radius.only(top_left=14, top_right=14),
                padding=ft.Padding(left=20, right=20, top=14, bottom=14),
                content=ft.Row([
                    ft.Icon(ft.Icons.RECEIPT_LONG, color="white", size=26),
                    ft.Column([
                        ft.Text(f"Invoice #{order_id}", size=20, weight="bold", color="white"),
                        ft.Text(f"{cust_name}  {cust_phone}", size=13, color="white70"),
                    ], spacing=2, tight=True),
                ], spacing=12),
            ),
            content=ft.Container(
                width=1000, bgcolor="white",
                content=ft.Column([
                    ft.Container(
                        content=ft.ListView([ft.DataTable(
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
                        )]),
                        border=ft.border.all(1, "black12"), border_radius=8, padding=5,
                    ),
                    ft.Container(height=12),
                    ft.Container(
                        bgcolor="#f7f9ff",
                        border=ft.border.all(1, "black12"), border_radius=10,
                        padding=ft.Padding(left=20, right=20, top=14, bottom=14),
                        content=ft.Row([
                            ft.Text(f"Total Items : {len(items)}", size=14, color="black"),
                            ft.Column([
                                ft.Row([ft.Text("Gross Total :", size=14, color="black"),
                                        ft.Text(f"{grand_total:,.2f} TK", size=14, weight="bold", color="black")], spacing=20),
                                ft.Row([ft.Text("Discount    :", size=13, color="red"),
                                        ft.Text(f"- {total_disc:,.2f} TK", size=13, color="red", weight="bold")], spacing=20),
                                ft.Divider(color="black12", height=6),
                                ft.Row([ft.Text("NET PAYABLE :", size=16, weight="bold", color="black"),
                                        ft.Text(f"{net_after_disc:,.2f} TK", size=16, weight="bold", color="black")], spacing=20),
                                ft.Row([ft.Text("Paid Amount :", size=14, color="green"),
                                        ft.Text(f"{paid:,.2f} TK", size=14, color="green", weight="bold")], spacing=20),
                                ft.Row([ft.Text("Due Amount  :", size=14, color="red" if due>0 else "green"),
                                        ft.Text(f"{due:,.2f} TK", size=14, weight="bold", color="red" if due>0 else "green")], spacing=20),
                            ], horizontal_alignment="end"),
                        ], alignment="spaceBetween"),
                    ),
                ], scroll=ft.ScrollMode.AUTO),
                padding=ft.Padding(left=16, right=16, top=16, bottom=8),
            ),
            actions=[
                ft.TextButton("Close", style=ft.ButtonStyle(color="black"),
                              on_click=lambda _: page.close(invoice_dialog)),
            ],
        )
        page.open(invoice_dialog)

    # ── render rows ────────────────────────────────────────
    def render_rows(data):
        report_table.rows.clear()
        t_sales = t_due = 0.0
        for index, row in enumerate(data):
            try:
                r          = dict(row)
                net_total  = float(r.get("total",0) or 0) - float(r.get("discount",0) or 0)
                paid       = float(r.get("paid_amount",0) or 0)
                due        = float(r.get("due_amount", 0) or 0)
                order_id   = r.get("order_id")   or "—"
                sale_date  = r.get("sale_date")  or ""
                sale_time  = r.get("sale_time")  or ""
                cust_name  = r.get("customer_name")  or "Cash"
                cust_phone = r.get("customer_phone") or "—"
                t_sales += net_total; t_due += due

                report_table.rows.append(ft.DataRow(
                    on_select_changed=lambda e, oid=order_id: show_invoice_details(oid),
                    cells=[
                        ft.DataCell(ft.Text(str(index+1), color="white54", size=12)),
                        ft.DataCell(ft.Text(f"{order_id}", color="cyan200", weight="bold")),
                        ft.DataCell(ft.Text(f"{sale_date}  {sale_time}", size=12, color="white70")),
                        ft.DataCell(ft.Text(cust_name,  color="white", weight="bold")),
                        ft.DataCell(ft.Text(cust_phone, color="white60", size=12)),
                        ft.DataCell(ft.Text(f"{net_total:,.2f}", color="white", weight="bold")),
                        ft.DataCell(ft.Text(f"{paid:,.2f}",      color="green")),
                        ft.DataCell(ft.Text(f"{due:,.2f}", color="red" if due>0 else "green")),
                    ],
                ))
            except Exception as row_err:
                print(f"Row Error: {row_err}")

        sales_card_text.value = f"{t_sales:,.2f} TK"
        due_card_text.value   = f"{t_due:,.2f} TK"
        row_count_text.value  = f"{len(data)} records"
        page.update()

    # ── search filter ──────────────────────────────────────
    def apply_search(query):
        q = (query or "").lower().strip()
        if not q: render_rows(all_rows); return
        filtered = [
            r for r in all_rows
            if q in str(r.get("order_id","")      or "").lower()
            or q in str(r.get("customer_name","") or "").lower()
            or q in str(r.get("customer_phone","")or "").lower()
        ]
        render_rows(filtered)

    # ── load from DB ───────────────────────────────────────
    def load_report_data(filter_type="today"):
        nonlocal all_rows
        try:
            raw_data = list(get_filtered_sales_report(filter_type))
            grouped  = {}
            for row in raw_data:
                r   = dict(row)
                oid = r.get("order_id")
                if oid not in grouped:
                    grouped[oid] = {
                        "order_id":      oid,
                        "sale_date":     r.get("sale_date"),
                        "sale_time":     r.get("sale_time"),
                        "customer_name": r.get("customer_name"),
                        "customer_phone":r.get("customer_phone"),
                        "total":    0.0, "discount": 0.0,
                        "paid_amount": r.get("paid_amount"),
                        "due_amount":  r.get("due_amount"),
                    }
                grouped[oid]["total"]    += float(r.get("total")    or 0)
                grouped[oid]["discount"] += float(r.get("discount") or 0)
            all_rows = list(grouped.values())
            search_field.value = ""
            render_rows(all_rows)
        except Exception as e:
            print(f"Loading Error: {e}")

# ============================================================
    # CUSTOMER LEDGER DIALOG  (replace the entire function)
    # ============================================================
    def open_customer_ledger(e):
        phone_tf = ft.TextField(
            label="Customer Phone", prefix_icon=ft.Icons.PHONE,
            border_color="orange", text_style=ft.TextStyle(color="white"),
            label_style=ft.TextStyle(color="white60"),
            keyboard_type=ft.KeyboardType.PHONE,
            expand=True,
        )

        # ── date fields (type করা যাবে অথবা picker থেকে বেছে নেওয়া যাবে) ──
        date_from_tf = ft.TextField(
            label="From", hint_text="YYYY-MM-DD",
            border_color="orange", width=160,
            text_style=ft.TextStyle(color="white"),
            label_style=ft.TextStyle(color="white60"),
            hint_style=ft.TextStyle(color="white30"),
        )
        date_to_tf = ft.TextField(
            label="To", hint_text="YYYY-MM-DD",
            border_color="orange", width=160,
            text_style=ft.TextStyle(color="white"),
            label_style=ft.TextStyle(color="white60"),
            hint_style=ft.TextStyle(color="white30"),
        )

        def pick_from(ev):
            def on_pick(e):
                if e.control.value:
                    date_from_tf.value = e.control.value.strftime("%Y-%m-%d")
                    page.update()
            page.open(ft.DatePicker(on_change=on_pick))

        def pick_to(ev):
            def on_pick(e):
                if e.control.value:
                    date_to_tf.value = e.control.value.strftime("%Y-%m-%d")
                    page.update()
            page.open(ft.DatePicker(on_change=on_pick))

        # ── item-level detail table (invoice এর ভেতরে কী কী বিক্রি হয়েছে) ──
        detail_table = ft.DataTable(
            bgcolor="#1e2b5e",
            heading_row_color=ft.Colors.BLUE_GREY_900,
            border=ft.border.all(1, "white10"),
            horizontal_lines=ft.BorderSide(1, "white10"),
            vertical_lines=ft.BorderSide(0.5, "white10"),
            column_spacing=14,
            columns=[
                ft.DataColumn(ft.Text("SN",          color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Invoice No",  color="cyan200",weight="bold", size=12)),
                ft.DataColumn(ft.Text("Date",        color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Profile",     color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Spec",        color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Color",       color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Qty",         color="cyan",   weight="bold", size=12)),
                ft.DataColumn(ft.Text("Price",       color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Total",       color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Discount",    color="orange", weight="bold", size=12)),
                ft.DataColumn(ft.Text("Net",         color="white",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Paid",        color="green",  weight="bold", size=12)),
                ft.DataColumn(ft.Text("Due",         color="red",    weight="bold", size=12)),
            ],
        )

        summary_text    = ft.Text("", color="white70", size=13)
        ledger_rows_cache = []

        def do_search(ev=None):
            nonlocal ledger_rows_cache
            phone     = (phone_tf.value     or "").strip()
            date_from = (date_from_tf.value or "").strip()
            date_to   = (date_to_tf.value   or "").strip()

            if not phone:
                phone_tf.error_text = "Phone number দিন"
                page.update()
                return
            phone_tf.error_text = None

            try:
                from database import DB
                conn = sqlite3.connect(DB)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Item-level query — প্রতিটি product আলাদা row এ আসবে
                query = """
    SELECT
        s.order_id, s.sale_date, s.sale_time,
        s.customer_name, s.customer_phone,
        s.profile_name, s.spec, s.color,
        s.quantity, s.price, s.total,
        s.discount, s.paid_amount, s.due_amount,
        COALESCE((
            SELECT unit_in FROM inventory
            WHERE die_no = s.die_no 
            AND color = s.color
            AND sell_price = s.price
            LIMIT 1
        ), 120) as unit_in,
        COALESCE((
            SELECT unit_type FROM inventory
            WHERE die_no = s.die_no
            AND color = s.color
            AND sell_price = s.price
            LIMIT 1
        ), 'alum') as unit_type
    FROM sales s
    WHERE s.customer_phone LIKE ?
"""
                params = [f"%{phone}%"]

                if date_from:
                    query  += " AND s.sale_date >= ?"
                    params.append(date_from)
                if date_to:
                    query  += " AND s.sale_date <= ?"
                    params.append(date_to)

                query += " ORDER BY s.id DESC"
                cursor.execute(query, params)
                rows = [dict(r) for r in cursor.fetchall()]
                conn.close()

                ledger_rows_cache = rows
                detail_table.rows.clear()

                t_total = t_disc = t_net = t_paid = t_due = 0.0

                for i, r in enumerate(rows, 1):
                    total  = float(r.get("total",        0) or 0)
                    disc   = float(r.get("discount",     0) or 0)
                    disc_pct = (disc / total * 100) if total > 0 else 0.0
                    net    = total - disc
                    paid   = float(r.get("paid_amount",  0) or 0)
                    due    = float(r.get("due_amount",   0) or 0)
                    price  = float(r.get("price",        0) or 0)
                    qty    = float(r.get("quantity",     0) or 0)
                    unit_in   = float(r.get("unit_in",  120) or 120)
                    unit_type = str(r.get("unit_type", "alum") or "alum")

                    qty_str = format_qty(qty, unit_in, unit_type)

                    t_total += total
                    t_disc  += disc
                    t_net   += net
                    t_paid  += paid
                    t_due   += due

                    detail_table.rows.append(ft.DataRow(
                        on_select_changed=lambda e, oid=r.get("order_id"): show_invoice_details(oid),
                        cells=[
                            ft.DataCell(ft.Text(str(i),                          color="white54", size=12)),
                            ft.DataCell(ft.Text(str(r.get("order_id") or "—"),   color="cyan200", weight="bold", size=12)),
                            ft.DataCell(ft.Text(str(r.get("sale_date") or "")[:10], color="white70", size=12)),
                            ft.DataCell(ft.Text(str(r.get("profile_name") or "—"), color="white",  weight="bold", size=12)),
                            ft.DataCell(ft.Text(str(r.get("spec")  or "—"),      color="white70", size=12)),
                            ft.DataCell(ft.Text(str(r.get("color") or "—"),      color="white70", size=12)),
                            ft.DataCell(ft.Text(qty_str,                          color="cyan",    weight="bold", size=12)),
                            ft.DataCell(ft.Text(f"{price:,.2f}",                  color="white",   size=12)),
                            ft.DataCell(ft.Text(f"{total:,.2f}",                  color="white",   weight="bold", size=12)),
                            ft.DataCell(ft.Text(f"{disc_pct:.1f}%", color="orange", size=12)),
                            ft.DataCell(ft.Text(f"{net:,.2f}",                    color="white",   weight="bold", size=12)),
                            ft.DataCell(ft.Text(f"{paid:,.2f}",                   color="green",   size=12)),
                            ft.DataCell(ft.Text(f"{due:,.2f}",
                                                color="red" if due > 0 else "green",
                                                weight="bold" if due > 0 else "normal",
                                                size=12)),
                        ],
                    ))

                summary_text.value = (
                    f"{len(rows)} items  |  "
                    f"Total: {t_total:,.2f}  Disc: {t_disc:,.2f}  "
                    f"Net: {t_net:,.2f}  Paid: {t_paid:,.2f}  Due: {t_due:,.2f} TK"
                )
                page.update()

            except Exception as ex:
                print(f"Ledger search error: {ex}")
                import traceback; traceback.print_exc()

        def do_print(ev=None):
            if not ledger_rows_cache:
                page.snack_bar = ft.SnackBar(
                    ft.Text("প্রথমে Search করুন!", color="white"), bgcolor="red")
                page.snack_bar.open = True
                page.update()
                return

            cust_name  = ledger_rows_cache[0].get("customer_name", "") or ""
            cust_phone = (phone_tf.value or "").strip()
            pdf_path   = generate_ledger_pdf(
                cust_name, cust_phone, ledger_rows_cache,
                date_from_tf.value, date_to_tf.value,
            )
            if pdf_path:
                import platform, subprocess
                try:
                    sys_name = platform.system()
                    if sys_name == "Darwin":    subprocess.Popen(["open", pdf_path])
                    elif sys_name == "Windows": os.startfile(pdf_path)
                    else:                       subprocess.Popen(["xdg-open", pdf_path])
                except Exception:
                    pass
                page.snack_bar = ft.SnackBar(
                    ft.Text("✅ PDF saved & opening...", color="white"), bgcolor="green")
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("PDF generate failed!", color="white"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

        ledger_dlg = ft.AlertDialog(
            modal=True, bgcolor="#0f111a",
            shape=ft.RoundedRectangleBorder(radius=14),
            title=ft.Row([
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color="orange", size=24),
                ft.Text("Customer Ledger", size=20, weight="bold", color="white"),
            ], spacing=10),
            content=ft.Container(
                width=1100,
                content=ft.Column([
                    # ── input row ──────────────────────────────────────
                    ft.Row([
                        phone_tf,
                        ft.Row([
                            date_from_tf,
                            ft.IconButton(
                                ft.Icons.CALENDAR_TODAY,
                                icon_color="orange", tooltip="From তারিখ বেছে নিন",
                                on_click=pick_from,
                            ),
                        ], spacing=2),
                        ft.Row([
                            date_to_tf,
                            ft.IconButton(
                                ft.Icons.CALENDAR_MONTH,
                                icon_color="orange", tooltip="To তারিখ বেছে নিন",
                                on_click=pick_to,
                            ),
                        ], spacing=2),
                    ], spacing=10),

                    ft.Container(height=4),

                    # ── detail table ───────────────────────────────────
                    ft.Container(
                        content=ft.ListView(
                            [ft.Row([detail_table], scroll=ft.ScrollMode.ALWAYS)],
                            expand=True,
                        ),
                        height=360,
                        border=ft.border.all(1, "white10"),
                        border_radius=8, padding=4,
                    ),

                    ft.Container(height=4),
                    summary_text,
                ], spacing=8, scroll=ft.ScrollMode.AUTO),
                padding=ft.padding.all(16),
            ),
            actions=[
                ft.TextButton("Close", style=ft.ButtonStyle(color="white54"),
                              on_click=lambda _: page.close(ledger_dlg)),
                ft.ElevatedButton("Search",    icon=ft.Icons.SEARCH,
                                  bgcolor="orange",    color="white", on_click=do_search),
                ft.ElevatedButton("Print PDF", icon=ft.Icons.PRINT,
                                  bgcolor="blue_800",  color="white", on_click=do_print),
            ],
        )
        page.open(ledger_dlg)

    # ── filter button ──────────────────────────────────────
    def filter_btn(label, ftype):
        return ft.ElevatedButton(
            label, bgcolor="white10", color="white", height=36,
            on_click=lambda _: load_report_data(ftype),
        )

    load_report_data("today")

    # ── UI ─────────────────────────────────────────────────
    return ft.Container(
        padding=20, expand=True,
        content=ft.Column([
            ft.Text("Sales Report", size=25, weight="bold"),
            ft.Container(height=5),

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

            ft.Row([
                filter_btn("Today",      "today"),
                filter_btn("This Month", "month"),
                filter_btn("This Year",  "year"),
                filter_btn("All Time",   "all"),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Customer Ledger",
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                    bgcolor="orange", color="white", height=36,
                    on_click=open_customer_ledger,
                ),
                row_count_text,
            ], spacing=8),

            ft.Container(height=6),
            ft.Row([search_field]),
            ft.Divider(height=10, color="white10"),

            ft.Container(
                expand=True,
                content=ft.ListView([
                    ft.Row([report_table], scroll=ft.ScrollMode.ALWAYS)
                ], expand=True),
                border=ft.border.all(1, "white10"),
                border_radius=10, padding=5,
            ),
        ]),
    )