import flet as ft
import datetime
import sqlite3
import os
import platform
import subprocess


# ============================================================
# PDF OPEN (cross-platform)
# ============================================================
def open_pdf(path):
    try:
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", path])
        elif system == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"PDF open error: {e}")


# ============================================================
# PDF GENERATOR
# ============================================================
def save_pdf_invoice(order_no, customer_name, cart_items, totals, extra_info):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm

        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_path, exist_ok=True)
        file_path = os.path.join(downloads_path, f"Invoice_{order_no}.pdf")

        doc = SimpleDocTemplate(
            file_path, pagesize=A4,
            leftMargin=20*mm, rightMargin=20*mm,
            topMargin=12*mm, bottomMargin=12*mm,
        )

        normal  = ParagraphStyle("normal", fontSize=9,  leading=12)
        bold    = ParagraphStyle("bold",   fontSize=9,  leading=12, fontName="Helvetica-Bold")
        small   = ParagraphStyle("small",  fontSize=8,  leading=10)
        small_r = ParagraphStyle("small_r",fontSize=8,  leading=10, alignment=2)
        bold_r  = ParagraphStyle("bold_r", fontSize=9,  leading=12, fontName="Helvetica-Bold", alignment=2)
        bold_h  = ParagraphStyle("bold_h", fontSize=8,  leading=10, fontName="Helvetica-Bold")
        bold_hr = ParagraphStyle("bold_hr",fontSize=8,  leading=10, fontName="Helvetica-Bold", alignment=2)

        # A4 width=210mm, margin 20×2=40mm, available=170mm
        PAGE_W = 170 * mm

        elements = []

        # ── Shop Header ──────────────────────────────────────
        elements.append(Paragraph(
            "<b>CITY GLASS ART &amp; THY ALUMINIUM</b>",
            ParagraphStyle("h1", fontSize=20, leading=24, alignment=1, fontName="Helvetica-Bold")
        ))
        elements.append(Paragraph(
            "Park Road, Ghorapotti, Sutrapur, Bogura",
            ParagraphStyle("h2", fontSize=10, leading=13, alignment=1)
        ))
        elements.append(Paragraph(
            "Mob: 01719-252128, 01712954722, 01716205160",
            ParagraphStyle("h3", fontSize=10, leading=13, alignment=1)
        ))
        elements.append(Paragraph(
            "Email: tarekkamruzzaman@gmail.com",
            ParagraphStyle("h4", fontSize=10, leading=13, alignment=1)
        ))
        elements.append(Spacer(1, 4*mm))

        # ── Customer Info ────────────────────────────────────
        info_data = [[
            Paragraph(f"<b>Customer :</b> {customer_name}", normal),
            Paragraph(f"<b>Order No :</b> {order_no}", bold),
        ],[
            Paragraph(f"<b>Contact  :</b> {extra_info.get('cust_phone', '')}", normal),
            Paragraph(f"<b>Date :</b> {datetime.date.today().strftime('%d/%m/%Y')}", normal),
        ],[
            Paragraph(f"<b>Address  :</b> {extra_info.get('cust_address', '')}", normal),
            Paragraph(f"<b>Time :</b> {datetime.datetime.now().strftime('%I:%M %p')}", normal),
        ]]
        info_table = Table(info_data, colWidths=[PAGE_W * 0.55, PAGE_W * 0.45])
        info_table.setStyle(TableStyle([
            ("ALIGN",         (0,0), (0,-1), "LEFT"),
            ("ALIGN",         (1,0), (1,-1), "RIGHT"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 4*mm))

        # ── Items Table ──────────────────────────────────────
        col_widths = [
            8*mm,   # SN
            18*mm,  # Die No
            42*mm,  # Profile Name
            26*mm,  # Brand
            22*mm,  # Spec
            18*mm,  # Color
            14*mm,  # Qty
            14*mm,  # Price
            14*mm,  # Total
        ]
        # মোট = 170mm = PAGE_W

        header = [
            Paragraph("<b>SN</b>",           bold_h),
            Paragraph("<b>Die No</b>",        bold_h),
            Paragraph("<b>Profile Name</b>",  bold_h),
            Paragraph("<b>Brand</b>",         bold_h),
            Paragraph("<b>Spec</b>",          bold_h),
            Paragraph("<b>Color</b>",         bold_h),
            Paragraph("<b>Qty</b>",           bold_h),
            Paragraph("<b>Price</b>",         bold_hr),
            Paragraph("<b>Total</b>",         bold_hr),
        ]

        table_data = [header]

        for i, item in enumerate(cart_items or [], 1):
            raw_profile   = str(item.get("profile", ""))
            clean_profile = raw_profile.split('(')[0].strip()

            table_data.append([
                Paragraph(str(i),                              small),
                Paragraph(str(item.get("die_no",  "")),        small),
                Paragraph(clean_profile,                        small),
                Paragraph(str(item.get("brand",   "")),        small),
                Paragraph(str(item.get("spec",    "")),        small),
                Paragraph(str(item.get("color",   "")),        small),
                Paragraph(str(item.get("qty",     "0")),       small),
                Paragraph(f"{float(item.get('price',0)):.0f}", small_r),
                Paragraph(f"{float(item.get('total',0)):.0f}", small_r),
            ])

        items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        items_table.setStyle(TableStyle([
            ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),  (-1,0),  8),
            ("LINEBELOW",     (0,0),  (-1,0),  1.2, colors.black),
            ("LINEABOVE",     (0,0),  (-1,0),  1.2, colors.black),
            ("FONTSIZE",      (0,1),  (-1,-1), 8),
            ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),  (-1,-1), 3),
            ("BOTTOMPADDING", (0,0),  (-1,-1), 3),
            ("GRID",          (0,0),  (-1,-1), 0.3, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, colors.HexColor("#f9f9f9")]),
            ("ALIGN",         (7,0),  (-1,-1), "RIGHT"),
            ("ALIGN",         (0,0),  (0,-1),  "CENTER"),
        ]))

        elements.append(items_table)
        elements.append(Spacer(1, 5*mm))

        # ── Totals ───────────────────────────────────────────
        gross    = float(totals.get("gross",       0))
        disc_per = totals.get("discount_per", 0)
        disc_tk  = float(totals.get("discount_tk", 0))
        net      = float(totals.get("net",         0))
        paid     = float(totals.get("paid_amount", 0))
        due      = float(totals.get("due_amount",  0))

        totals_data = [
            [Paragraph("Gross Total :",  normal), Paragraph(f"{gross:,.2f}",         bold_r)],
            [Paragraph(f"Discount ({disc_per}%) :", normal), Paragraph(f"- {disc_tk:,.2f}", bold_r)],
            [Paragraph("<b>NET PAYABLE :</b>", bold), Paragraph(f"<b>{net:,.2f} TK</b>", bold_r)],
            [Paragraph("Paid Amount :",  normal), Paragraph(f"{paid:,.2f}",           bold_r)],
        ]
        if due > 0.01:
            totals_data.append([
                Paragraph("<b>Due Amount :</b>", bold),
                Paragraph(f"<b>{due:,.2f}</b>",  bold_r)
            ])

        totals_table = Table(totals_data, colWidths=[PAGE_W * 0.70, PAGE_W * 0.30])
        totals_table.setStyle(TableStyle([
            ("ALIGN",         (1,0),  (1,-1),  "RIGHT"),
            ("LINEABOVE",     (0,2),  (-1,2),  0.8, colors.black),
            ("LINEBELOW",     (0,2),  (-1,2),  0.8, colors.black),
            ("TOPPADDING",    (0,0),  (-1,-1), 2),
            ("BOTTOMPADDING", (0,0),  (-1,-1), 2),
        ]))
        elements.append(totals_table)

        doc.build(elements)
        return file_path

    except Exception as e:
        print(f"PDF Error: {e}")
        import traceback; traceback.print_exc()
        return None


# ============================================================
# ORDER NO
# ============================================================
def get_billing_data():
    conn   = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    shop_info = {
        "shop_name":    "CITY GLASS ART & THY ALUMINIUM",
        "shop_address": "Park Road, Ghorapotti, Sutrapur, Bogura",
        "shop_email":   "tarekkamruzzaman@gmail.com",
        "shop_phone1":  "01719-252128",
        "shop_phone2":  "01712954722",
        "shop_phone3":  "01716205160",
    }
    order_no = 1001
    try:
        cursor.execute("SELECT MAX(CAST(order_id AS INTEGER)) FROM sales")
        res = cursor.fetchone()[0]
        if res:
            order_no = int(res) + 1
    except Exception:
        pass
    finally:
        conn.close()
    return shop_info, order_no


# ============================================================
# BILLING PAGE
# ============================================================
def billing_page(page, cart_items=None, totals=None):
    shop_settings, order_no = get_billing_data()

    if not totals:
        totals = {"gross": 0, "discount_tk": 0, "discount_per": 0, "net": 0}

    totals.setdefault("discount_per", 0)
    totals.setdefault("discount_tk",  0)
    net_val = float(totals.get("net", 0))
    totals["paid_amount"] = net_val
    totals["due_amount"]  = 0.0

    num_filter = ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string="")

    def clear_on_focus(e):
        e.control.value = ""
        e.control.update()

    def restore_if_empty(e):
        if e.control.value.strip() == "":
            e.control.value = "0"
            e.control.update()
        sync_calc(None)

    disp_name    = ft.Text("........................", size=15, weight="bold", color="black")
    disp_phone   = ft.Text("........................", size=14, color="black")
    disp_address = ft.Text("........................", size=14, color="black")
    disp_disc_text = ft.Text("- 0.00 TK",         size=15, color="red",   weight="bold")
    disp_net_text  = ft.Text(f"{net_val:,.2f} TK", size=22, weight="bold", color="black")
    disp_paid_text = ft.Text(f"{net_val:,.2f} TK", size=16, color="green", weight="bold")
    disp_due_text  = ft.Text("0.00 TK",            size=16, color="red",   weight="bold")

    c_name = ft.TextField(
        label="Customer Name", hint_text="Cash / Walk-in",
        width=220, border_color="black", text_size=13, bgcolor="white",
        label_style=ft.TextStyle(color="black", weight="bold"),
        text_style=ft.TextStyle(color="black"),
    )
    c_phone = ft.TextField(
        label="Contact No", width=175, border_color="black",
        text_size=13, bgcolor="white",
        keyboard_type=ft.KeyboardType.PHONE,
        label_style=ft.TextStyle(color="black", weight="bold"),
        text_style=ft.TextStyle(color="black"),
    )
    c_address = ft.TextField(
        label="Address", width=220, border_color="black",
        text_size=13, bgcolor="white",
        label_style=ft.TextStyle(color="black", weight="bold"),
        text_style=ft.TextStyle(color="black"),
    )

    c_discount_per = ft.TextField(
        label="Disc %", value="0", width=100,
        text_align="right", suffix_text="%",
        border_color="black", border_radius=5, bgcolor="white",
        input_filter=num_filter,
        suffix_style=ft.TextStyle(color="black", weight="bold"),
        label_style=ft.TextStyle(color="black", weight="bold"),
        text_style=ft.TextStyle(color="black", weight="bold"),
        on_focus=clear_on_focus, on_blur=restore_if_empty,
    )
    c_paid = ft.TextField(
        value=f"{net_val:.2f}", width=155,
        text_align="right", text_size=15, bgcolor="white",
        border_color="black", border_radius=5,
        input_filter=num_filter,
        prefix_text="৳ ",
        prefix_style=ft.TextStyle(color="black"),
        text_style=ft.TextStyle(color="black", weight="bold"),
        on_focus=clear_on_focus, on_blur=restore_if_empty,
    )

    def sync_calc(e):
        try:
            gross    = float(totals.get("gross", 0))
            disc_pct = float(c_discount_per.value or 0)
            disc_tk  = (gross * disc_pct) / 100
            new_net  = gross - disc_tk

            if e and hasattr(e, "control") and e.control == c_discount_per:
                c_paid.value = f"{new_net:.2f}"

            paid_amt = float(c_paid.value or 0)
            due_amt  = max(0.0, new_net - paid_amt)

            disp_disc_text.value = f"- {disc_tk:,.2f} TK"
            disp_net_text.value  = f"{new_net:,.2f} TK"
            disp_paid_text.value = f"{paid_amt:,.2f} TK"
            disp_due_text.value  = f"{due_amt:,.2f} TK"
            disp_due_text.color  = "red" if due_amt > 0 else "green"

            totals["discount_per"] = disc_pct
            totals["discount_tk"]  = disc_tk
            totals["net"]          = new_net
            totals["paid_amount"]  = paid_amt
            totals["due_amount"]   = due_amt
        except Exception as ex:
            print(f"sync_calc error: {ex}")

        disp_name.value    = c_name.value    or "........................"
        disp_phone.value   = c_phone.value   or "........................"
        disp_address.value = c_address.value or "........................"
        page.update()

    c_name.on_change         = sync_calc
    c_phone.on_change        = sync_calc
    c_address.on_change      = sync_calc
    c_discount_per.on_change = sync_calc
    c_paid.on_change         = sync_calc

    def confirm_sell_to_db():
        try:
            conn   = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            now           = datetime.datetime.now()
            sale_date     = now.strftime("%Y-%m-%d")
            sale_time     = now.strftime("%I:%M %p")
            total_items   = len(cart_items or [])
            final_paid    = round(float(totals.get("paid_amount", 0)), 2)
            final_due     = round(float(totals.get("due_amount",  0)), 2)

            # customer discount percent (billing page এ যা দেওয়া হয়েছে)
            try:
                customer_disc_pct = float(c_discount_per.value or 0)
            except Exception:
                customer_disc_pct = float(totals.get("discount_per", 0))

            # due floating point fix
            if abs(final_due) < 0.01:
                final_due = 0.0

            for item in (cart_items or []):
                item_id = item.get("item_id")
                die_no  = item.get("die_no", "")
                color   = item.get("color", "")
                raw_qty = float(item.get("raw_qty", 0))

                res = None

                # 1. item_id দিয়ে exact match
                if item_id:
                    cursor.execute(
                        "SELECT current_stock, sell_price, unit_in, unit_type, discount_percent "
                        "FROM inventory WHERE id=?",
                        (item_id,)
                    )
                    res = cursor.fetchone()

                # 2. die_no + color দিয়ে match
                if not res and die_no:
                    cursor.execute(
                        "SELECT current_stock, sell_price, unit_in, unit_type, discount_percent "
                        "FROM inventory WHERE die_no=? AND color=? LIMIT 1",
                        (die_no, color)
                    )
                    res = cursor.fetchone()

                    if not res:
                        cursor.execute(
                            "SELECT current_stock, sell_price, unit_in, unit_type, discount_percent "
                            "FROM inventory WHERE die_no=? LIMIT 1",
                            (die_no,)
                        )
                        res = cursor.fetchone()

                if res:
                    current_stock    = float(res[0] or 0)
                    sell_price_full  = float(res[1] or 0)   # company listed price
                    piece_len        = float(res[2] or 120)
                    u_type           = res[3] or "alum"
                    company_disc_pct = float(res[4] or 0)   # company আমাকে যত % দিল

                    # stock update
                    new_stock = round(current_stock - raw_qty, 2)
                    if item_id:
                        cursor.execute(
                            "UPDATE inventory SET current_stock=?, is_synced=0 WHERE id=?",
                            (new_stock, item_id)
                        )
                    else:
                        cursor.execute(
                           "UPDATE inventory SET current_stock=?, is_synced=0 "
        "WHERE die_no=? AND color=? AND ABS(unit_in - ?) < 1",
        (new_stock, die_no, color, float(res[2] or 252))
                        )

                    # ── profit calculation ──────────────────────────────
                    # sell_price_full  = company listed price (e.g. 100)
                    # company_disc_pct = company আমাকে দিল (e.g. 20%) → buy_cost = 80
                    # customer_disc_pct= আমি customer কে দিলাম (e.g. 15%) → net_sell = 85
                    # profit = net_sell - buy_cost = 85 - 80 = 5

                    item_total = float(item.get("total", 0))

                    if u_type == "alum" and piece_len > 0:
                        price_per_inch = sell_price_full / piece_len
                        gross_sell     = price_per_inch * raw_qty
                    else:
                        gross_sell     = sell_price_full * raw_qty

                    buy_cost      = round(gross_sell * (1 - company_disc_pct  / 100), 2)
                    net_sell      = round(gross_sell * (1 - customer_disc_pct / 100), 2)
                    item_profit   = round(net_sell - buy_cost, 2)
                    item_discount = round(gross_sell * (customer_disc_pct / 100), 2)
                    print(f"DEBUG → gross={gross_sell} buy={buy_cost} net_sell={net_sell} profit={item_profit} disc={item_discount} raw_qty={raw_qty} piece_len={piece_len}")

                    cursor.execute("""
                        INSERT INTO sales (
                            order_id, sale_date, sale_time,
                            customer_name, customer_phone, customer_address,
                            die_no, profile_name, spec, color,
                            quantity, price, total,
                            discount, paid_amount, due_amount, profit, is_synced,brand,unit_in, inventory_id
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?)
                    """, (
                        str(order_no), sale_date, sale_time,
                        c_name.value or "Cash", c_phone.value or "",
                        c_address.value or "",
                        die_no, item.get("profile", ""), item.get("spec", ""), color,
                        raw_qty, float(item.get("price", 0)), item_total,
                        item_discount,
                        final_paid, final_due, item_profit,item.get("brand", ""),
                        float(res[2] or 252),item_id or 0,  # unit_in
                    ))
                else:
                    print(f"Warning: item not found! id={item_id} die={die_no} color={color}")

            conn.commit()
            conn.close()
            return True
        except Exception as ex:
            print(f"DB Error: {ex}")
            import traceback; traceback.print_exc()
            return False
    def handle_confirm(e):
        page.close(confirm_dlg)
        success = confirm_sell_to_db()

        if success:
            extra = {
                "phone":        shop_settings["shop_phone1"],
                "cust_phone":   c_phone.value or "",
                "cust_address": c_address.value or "",
            }
            pdf_path = save_pdf_invoice(
                order_no, c_name.value or "Walking Customer",
                cart_items, totals, extra
            )

            page.session.set("selected_items", {})
            page.session.set("cart_items",     [])
            page.session.set("bill_totals",    {})

            if pdf_path:
                open_pdf(pdf_path)
                msg = f"✅ Order #{order_no} Sell Successful! PDF opening... (Ctrl+P to print)"
                bg  = "green"
            else:
                msg = f"✅ Order #{order_no} Sell Successful! (PDF save failed — check console)"
                bg  = "orange"

            page.snack_bar = ft.SnackBar(
                ft.Text(msg, color="white"), bgcolor=bg, duration=5000
            )
            page.snack_bar.open = True
            page.update()

            nav = getattr(page, "_navigate", None)
            if nav:
                nav("sales")

        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("❌ Sell Failed! Check console for details.", color="white"),
                bgcolor="red"
            )
            page.snack_bar.open = True
            page.update()

    confirm_dlg = ft.AlertDialog(
        modal=True, bgcolor="white",
        shape=ft.RoundedRectangleBorder(radius=12),
        title=ft.Row([
            ft.Icon(ft.Icons.SHOPPING_BAG, color="blue", size=26),
            ft.Text("Confirm Order", size=20, weight="bold", color="black"),
        ]),
        content=ft.Container(
            width=380,
            content=ft.Column([
                ft.Text(f"Order No    : #{order_no}", size=15, color="black", weight="bold"),
                ft.Text(f"Items       : {len(cart_items or [])}", size=13, color="black"),
                ft.Text(f"Net Payable : {float(totals.get('net', 0)):,.2f} TK",
                        size=17, color="blue", weight="bold"),
                ft.Divider(color="black12"),
                ft.Text("✔ Stock will be updated", size=12, color="grey", italic=True),
                ft.Text("✔ PDF will open automatically for printing", size=12, color="grey", italic=True),
            ], spacing=8, tight=True),
            padding=10,
        ),
        actions=[
            ft.TextButton("Cancel", style=ft.ButtonStyle(color="red"),
                          on_click=lambda _: page.close(confirm_dlg)),
            ft.ElevatedButton(
                "Confirm Sell & Update Stock",
                icon=ft.Icons.CHECK_CIRCLE,
                bgcolor="blue_800", color="white",
                on_click=handle_confirm,
            ),
        ],
    )

    invoice_ui = ft.Column([

        # ── Shop header ───────────────────────────────────────
        ft.Container(
            content=ft.Column([
                ft.Text(shop_settings["shop_name"].upper(),
                        size=46, weight="bold", color="black", text_align="center"),
                ft.Text(shop_settings["shop_address"],
                        size=16, color="black", weight="w500", text_align="center"),
                ft.Text(
                    f"Mob: {shop_settings['shop_phone1']}, {shop_settings['shop_phone2']}, {shop_settings['shop_phone3']}",
                    size=13, color="black", text_align="center"
                ),
                ft.Text(
                    f"Email: {shop_settings['shop_email']}",
                    size=13, color="black", text_align="center"
                ),
            ], horizontal_alignment="center", spacing=2),
            margin=ft.Margin(left=0, right=0, top=0, bottom=10),
        ),
        ft.Divider(height=2, color="black"),

        # ── Customer inputs ──────────────────────────────────
        ft.Container(
            bgcolor="#f7f9ff",
            border=ft.border.all(1, "black12"),
            border_radius=10,
            padding=ft.Padding(left=20, right=20, top=14, bottom=14),
            content=ft.Row([
                ft.Column([
                    c_name,
                    ft.Container(height=6),
                    ft.Row([c_phone, ft.Container(width=10), c_address]),
                ], spacing=0),
                ft.Column([
                    ft.Text(f"Order No : {order_no}", size=16, weight="bold", color="black"),
                    ft.Text(f"Date     : {datetime.date.today().strftime('%d/%m/%Y')}", size=14, color="black"),
                    ft.Text(f"Time     : {datetime.datetime.now().strftime('%I:%M %p')}", size=14, color="black"),
                ], horizontal_alignment="end", spacing=5),
            ], alignment="spaceBetween", vertical_alignment="center"),
        ),

        ft.Container(height=8),

        # ── Live preview ──────────────────────────────────────
        ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("Customer : ", weight="bold", color="black", size=14), disp_name]),
                ft.Row([ft.Text("Contact  : ", weight="bold", color="black", size=13), disp_phone]),
                ft.Row([ft.Text("Address  : ", weight="bold", color="black", size=13), disp_address]),
            ], spacing=3),
            padding=ft.Padding(left=0, right=0, top=0, bottom=10),
        ),

        # ── Items table ───────────────────────────────────────
        ft.DataTable(
            border=ft.border.all(1.5, "black"),
            heading_row_color="#f0f0f0",
            horizontal_lines=ft.BorderSide(1, "black"),
            vertical_lines=ft.BorderSide(0.5, "black26"),
            column_spacing=14,
            columns=[
                ft.DataColumn(ft.Text("SN",           color="black", weight="bold")),
                ft.DataColumn(ft.Text("Die No",       color="black", weight="bold")),
                ft.DataColumn(ft.Text("Profile Name", color="black", weight="bold")),
                ft.DataColumn(ft.Text("Brand",        color="black", weight="bold")),
                ft.DataColumn(ft.Text("Spec",         color="black", weight="bold")),
                ft.DataColumn(ft.Text("Color",        color="black", weight="bold")),
                ft.DataColumn(ft.Text("Qty",          color="black", weight="bold")),
                ft.DataColumn(ft.Text("Price",        color="black", weight="bold")),
                ft.DataColumn(ft.Text("Total",        color="black", weight="bold")),
            ],
            rows=[
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(i + 1),                            color="black")),
                    ft.DataCell(ft.Text(str(item.get("die_no",  "")),          color="black")),
                    ft.DataCell(ft.Text(str(item.get("profile", "")),          color="black")),
                    ft.DataCell(ft.Text(str(item.get("brand",   "")),          color="black")),
                    ft.DataCell(ft.Text(str(item.get("spec",    "")),          color="black")),
                    ft.DataCell(ft.Text(str(item.get("color",   "")),          color="black")),
                    ft.DataCell(ft.Text(str(item.get("qty",     "0")),         color="black")),
                    ft.DataCell(ft.Text(f"{float(item.get('price',0)):,.2f}", color="black")),
                    ft.DataCell(ft.Text(f"{float(item.get('total',0)):,.2f}", color="black", weight="bold")),
                ])
                for i, item in enumerate(cart_items or [])
            ],
            width=1100,
        ),

        ft.Container(height=12),

        # ── Payment + Totals ──────────────────────────────────
        ft.Row([
            ft.Container(
                bgcolor="#f7f9ff",
                border=ft.border.all(1, "black12"),
                border_radius=10,
                padding=20,
                content=ft.Column([
                    ft.Text("Payment Details", size=15, weight="bold", color="black"),
                    ft.Divider(color="black12", height=8),
                    ft.Row([
                        ft.Column([
                            ft.Text("Discount %",  size=13, color="black", weight="bold"),
                            c_discount_per,
                        ]),
                        ft.Column([
                            ft.Text("Paid Amount", size=13, color="black", weight="bold"),
                            c_paid,
                        ]),
                        ft.Column([
                            ft.Text("Due Amount",  size=13, color="black", weight="bold"),
                            ft.Container(
                                content=disp_due_text,
                                padding=ft.Padding(left=12, right=12, top=9, bottom=9),
                                border=ft.border.all(1, "black26"),
                                border_radius=5, width=140, bgcolor="white",
                            ),
                        ]),
                    ], spacing=18),
                ], spacing=6),
                width=460,
            ),

            ft.Container(expand=True),

            ft.Column([
                ft.Row([
                    ft.Text("Gross Total :", size=16, color="black"),
                    ft.Text(f"{float(totals.get('gross',0)):,.2f} TK",
                            size=16, weight="bold", color="black"),
                ], alignment="end", spacing=25),
                ft.Row([
                    ft.Text("Discount    :", size=15, color="red"),
                    disp_disc_text,
                ], alignment="end", spacing=25),
                ft.Divider(color="black26"),
                ft.Row([
                    ft.Text("NET PAYABLE :", size=20, weight="bold", color="black"),
                    disp_net_text,
                ], alignment="end", spacing=25),
                ft.Row([
                    ft.Text("Paid Amount :", size=15, color="green"),
                    disp_paid_text,
                ], alignment="end", spacing=25),
            ], horizontal_alignment="end", spacing=8),
        ], alignment="spaceBetween", vertical_alignment="start"),

        ft.Container(height=20),

        # ── Confirm button ─────────────────────────────────────
        ft.Row([
            ft.ElevatedButton(
                "CONFIRM SELL & UPDATE STOCK",
                icon=ft.Icons.CHECK_CIRCLE,
                bgcolor="blue_800", color="white",
                height=52, width=340,
                on_click=lambda _: page.open(confirm_dlg),
            ),
        ], alignment="end"),

        ft.Container(height=30),
    ])

    def go_back(e):
        nav = getattr(page, "_navigate", None)
        if nav:
            nav("sales")
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text("Use sidebar → Sales (POS) to go back.", color="white"),
                bgcolor="orange"
            )
            page.snack_bar.open = True
            page.update()

    return ft.Container(
        expand=True, bgcolor="white",
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color="black",
                                  tooltip="Back to Sales", on_click=go_back),
                    ft.Text("Generate Invoice", size=20, weight="bold", color="black"),
                ], spacing=10),
                padding=ft.Padding(left=15, right=15, top=8, bottom=8),
                bgcolor="#f5f5f5",
                border=ft.Border(left=None, right=None, top=None, bottom=ft.BorderSide(1, "black12")),
            ),
            ft.Container(
                content=invoice_ui,
                bgcolor="white", padding=40,
                border=ft.border.all(1, "black12"),
                margin=ft.Margin(left=10, right=10, top=10, bottom=10),
                alignment=ft.alignment.top_center,
            ),
        ], scroll=ft.ScrollMode.AUTO),
    )


