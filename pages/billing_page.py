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
    """PDF টা automatically open করে — যেকোনো OS এ।"""
    try:
        system = platform.system()
        if system == "Darwin":       # macOS
            subprocess.Popen(["open", path])
        elif system == "Windows":
            os.startfile(path)
        else:                        # Linux
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"PDF open error: {e}")


# ============================================================
# PDF GENERATOR (FIXED BRAND REPETITION)
# ============================================================
def save_pdf_invoice(order_no, customer_name, cart_items, totals, extra_info):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as rl_canvas

        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_path, exist_ok=True)
        file_path = os.path.join(downloads_path, f"Invoice_{order_no}.pdf")
        c = rl_canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(width / 2, height - 48, "CITY GLASS ART & THY ALUMINIUM")
        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2, height - 63, "Park Road, Ghorapotti, Sutrapur, Bogura")
        c.drawCentredString(width / 2, height - 76,
            f"Mob: {extra_info.get('phone', '')} | Email: khondakartraders@gmail.com")
        c.line(50, height - 88, 545, height - 88)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(50,  height - 108, f"Customer : {customer_name}")
        c.drawRightString(545, height - 108, f"Order No : {order_no}")
        c.setFont("Helvetica", 10)
        c.drawString(50,  height - 123, f"Contact  : {extra_info.get('cust_phone', '')}")
        c.drawRightString(545, height - 123, f"Date : {datetime.date.today().strftime('%d/%m/%Y')}")
        c.drawString(50,  height - 138, f"Address  : {extra_info.get('cust_address', '')}")
        c.drawRightString(545, height - 138, f"Time : {datetime.datetime.now().strftime('%I:%M %p')}")

        y = height - 165
        c.setFont("Helvetica-Bold", 9)
        c.line(50, y + 8, 545, y + 8)
        c.drawString(55,  y, "SN")
        c.drawString(75,  y, "Die No")
        c.drawString(125, y, "Profile Name")
        c.drawString(235, y, "Brand")
        c.drawString(285, y, "Spec")
        c.drawString(345, y, "Color")
        c.drawString(400, y, "Qty")
        c.drawString(440, y, "Price")
        c.drawString(495, y, "Total")
        c.line(50, y - 4, 545, y - 4)

        y -= 18
        c.setFont("Helvetica", 9)
        for i, item in enumerate(cart_items or []):
            # ── প্রোফাইল নাম থেকে ব্র্যাকেটের ভেতরের ব্র্যান্ড বাদ দেওয়ার লজিক ──
            raw_profile = str(item.get("profile", ""))
            clean_profile = raw_profile.split('(')[0].strip()

            c.drawString(55,  y, str(i + 1))
            c.drawString(75,  y, str(item.get("die_no",  ""))[:10])
            c.drawString(125, y, clean_profile[:16]) # 👈 এখানে এখন ব্র্যান্ড ছাড়া ক্লিন নাম প্রিন্ট হবে
            c.drawString(235, y, str(item.get("brand",   ""))[:10])
            c.drawString(285, y, str(item.get("spec",    ""))[:10])
            c.drawString(345, y, str(item.get("color",   ""))[:9])
            c.drawString(400, y, str(item.get("qty",     "0")))
            c.drawString(440, y, f"{float(item.get('price', 0)):.0f}")
            c.drawString(495, y, f"{float(item.get('total', 0)):.0f}")
            y -= 16

        y -= 8
        c.line(50, y, 545, y)
        y -= 16

        c.setFont("Helvetica", 11)
        c.drawRightString(465, y, "Gross Total :")
        c.drawRightString(545, y, f"{float(totals.get('gross', 0)):,.2f}")
        y -= 14
        disc_per = totals.get("discount_per", 0)
        disc_tk  = float(totals.get("discount_tk", 0))
        c.drawRightString(465, y, f"Discount ({disc_per}%) :")
        c.drawRightString(545, y, f"- {disc_tk:,.2f}")
        y -= 18
        c.setFont("Helvetica-Bold", 13)
        c.drawRightString(465, y, "NET PAYABLE :")
        c.drawRightString(545, y, f"{float(totals.get('net', 0)):,.2f} TK")
        y -= 16
        c.setFont("Helvetica", 11)
        paid = float(totals.get("paid_amount", 0))
        due  = float(totals.get("due_amount",  0))
        c.drawRightString(465, y, "Paid Amount :")
        c.drawRightString(545, y, f"{paid:,.2f}")
        if due > 0.01:
            y -= 14
            c.setFont("Helvetica-Bold", 11)
            c.drawRightString(465, y, "Due Amount :")
            c.drawRightString(545, y, f"{due:,.2f}")

        c.save()
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
        "shop_email":   "khondakartraders@gmail.com",
        "shop_phone1":  "01719-252128",
        "shop_phone2":  "01641-513276",
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

    # ── display texts ──────────────────────────────────────
    disp_name    = ft.Text("........................", size=15, weight="bold", color="black")
    disp_phone   = ft.Text("........................", size=14, color="black")
    disp_address = ft.Text("........................", size=14, color="black")
    disp_disc_text = ft.Text("- 0.00 TK",         size=15, color="red",   weight="bold")
    disp_net_text  = ft.Text(f"{net_val:,.2f} TK", size=22, weight="bold", color="black")
    disp_paid_text = ft.Text(f"{net_val:,.2f} TK", size=16, color="green", weight="bold")
    disp_due_text  = ft.Text("0.00 TK",            size=16, color="red",   weight="bold")

    # ── customer inputs ────────────────────────────────────
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

    # ── discount & paid ────────────────────────────────────
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

    # ── sync ──────────────────────────────────────────────
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

    # ============================================================
    # DB SAVE (সংশোধিত ও লাইভ স্টক ফিক্সড)
    # ============================================================
    def confirm_sell_to_db():
        try:
            conn   = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            now         = datetime.datetime.now()
            sale_date   = now.strftime("%Y-%m-%d")
            sale_time   = now.strftime("%I:%M %p")
            total_items = len(cart_items or [])
            disc_tk     = float(totals.get("discount_tk", 0))
            disc_per_item = disc_tk / total_items if total_items > 0 else 0
            final_paid  = float(totals.get("paid_amount", 0))
            final_due   = float(totals.get("due_amount",  0))

            for item in (cart_items or []):
                die_no  = item.get("die_no", "")
                raw_qty = float(item.get("raw_qty", 0))

                # ✅ ফিক্সড: current_stock কলামটি কুয়েরিতে নিয়ে আসা হলো
                cursor.execute(
                    "SELECT current_stock, buy_price, unit_in, unit_type FROM inventory WHERE die_no=?",
                    (die_no,)
                )
                res = cursor.fetchone()
                if res:
                    current_stock = float(res[0] or 0)  # এখন সরাসরি current_stock রিড হবে
                    buy_price     = float(res[1] or 0)
                    piece_len     = float(res[2] or 120)
                    u_type        = res[3] or "alum"
                    
                    # নতুন স্টক হিসাব
                    new_stock     = round(current_stock - raw_qty, 2)
                    
                    # ✅ জাদুকরী ফিক্স: total_in এর বদলে current_stock কলাম আপডেট করা হলো
                    cursor.execute("UPDATE inventory SET current_stock=? WHERE die_no=?", (new_stock, die_no))

                    item_cost   = (raw_qty / piece_len) * buy_price if (u_type == "alum" and piece_len > 0) else raw_qty * buy_price
                    item_total  = float(item.get("total", 0))
                    item_profit = (item_total - disc_per_item) - item_cost

                    cursor.execute("""
                        INSERT INTO sales (
                            order_id, sale_date, sale_time,
                            customer_name, customer_phone, customer_address,
                            die_no, profile_name, spec, color,
                            quantity, price, total,
                            discount, profit, paid_amount, due_amount, is_synced
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                    """, (
                        str(order_no), sale_date, sale_time,
                        c_name.value or "Cash", c_phone.value or "", c_address.value or "",
                        die_no, item.get("profile",""), item.get("spec",""), item.get("color",""),
                        raw_qty, float(item.get("price",0)), item_total,
                        round(disc_per_item,2), round(item_profit,2),
                        final_paid, final_due,
                    ))
                else:
                    print(f"Warning: Die No '{die_no}' not found!")

            conn.commit()
            conn.close()
            return True
        except Exception as ex:
            print(f"DB Error: {ex}")
            import traceback; traceback.print_exc()
            return False

    # ============================================================
    # CONFIRM DIALOG
    # ============================================================
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

            # cart clear
            page.session.set("selected_items", {})
            page.session.set("cart_items",     [])
            page.session.set("bill_totals",    {})

            if pdf_path:
                # ✅ PDF automatically open — সেখান থেকে Ctrl+P দিয়ে print
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

            # ✅ sales page এ ফিরে যাও
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

    # ============================================================
    # INVOICE UI
    # ============================================================
    invoice_ui = ft.Column([

        # ── Shop header ───────────────────────────────────────
        ft.Container(
            content=ft.Column([
                ft.Text(shop_settings["shop_name"].upper(),
                        size=46, weight="bold", color="black", text_align="center"),
                ft.Text(shop_settings["shop_address"],
                        size=16, color="black", weight="w500", text_align="center"),
                ft.Text(
                    f"Mob: {shop_settings['shop_phone1']}, {shop_settings['shop_phone2']}"
                    f" | Email: {shop_settings['shop_email']}",
                    size=13, color="black", text_align="center"
                ),
            ], horizontal_alignment="center", spacing=2),
            margin=ft.Margin(left=0, right=0, top=0, bottom=10),

        ),
        ft.Divider(height=2, color="black"),

        # ── Customer inputs below header ──────────────────────
        ft.Container(
            bgcolor="#f7f9ff",
            border=ft.border.all(1, "black12"),
            border_radius=10,
            #padding=ft.padding.symmetric(horizontal=20, vertical=14),
            # ✅ এটা দাও
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
                                #padding=ft.padding.symmetric(vertical=9, horizontal=12),
                                 # ✅ এটা দাও
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

    # ── Back ──────────────────────────────────────────────────
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
                # padding=ft.padding.symmetric(horizontal=15, vertical=8),
                    # ✅ এটা দাও
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