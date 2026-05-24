# cat > /mnt/user-data/outputs/inventory.py << 'PYEOF'
import flet as ft
from database import (
    add_inventory_item, get_inventory_items, get_brands,
    add_new_brand, update_inventory_item, delete_inventory_item,
    get_colors, add_new_color, add_audit_log,
)


def inventory_page(page):
    editing_id     = None
    inventory_list = ft.Column(spacing=0, scroll="auto", expand=True)

    def is_mobile():
        try:    return (page.width or 800) < 700
        except: return False

    num_filter = ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string="")

    def ibox(label, value="", width=None, expand=None):
        _orig = str(value)
        tf = ft.TextField(
            label=label, value=_orig,
            width=width, expand=expand,
            input_filter=num_filter,
            text_align=ft.TextAlign.CENTER,
            border_color="#1565C0", border_width=2, border_radius=8,
            bgcolor="#EEF4FF", color="black",
            label_style=ft.TextStyle(color="#1565C0", size=11, weight="bold"),
            text_style=ft.TextStyle(color="black", weight="bold", size=14),
            content_padding=ft.padding.symmetric(horizontal=6, vertical=8),
            height=56,
        )
        def on_focus(e):
            if tf.value == _orig: tf.value = ""; tf.update()
        def on_blur(e):
            if (tf.value or "").strip() == "": tf.value = _orig; tf.update()
        tf.on_focus = on_focus
        tf.on_blur  = on_blur
        return tf

    brand_filter_dd = ft.Dropdown(
        label="Brand", value="All", color="black",
        text_size=13, content_padding=8,
        label_style=ft.TextStyle(color="black"),
    )
    search_tf = ft.TextField(
        label="Search", expand=True, prefix_icon=ft.Icons.SEARCH,
        color="black", label_style=ft.TextStyle(color="black"),
        text_style=ft.TextStyle(color="black"),
        border_color="black", height=44,
    )
    new_brand_dd = ft.Dropdown(label="Select Brand", expand=True, color="black",
                               label_style=ft.TextStyle(color="black"))
    new_color_dd = ft.Dropdown(label="Select Color", expand=True, color="black",
                               label_style=ft.TextStyle(color="black"))

    def load_dropdowns():
        brands = get_brands()
        brand_filter_dd.options = (
            [ft.dropdown.Option("All")] + [ft.dropdown.Option(b) for b in brands]
        )
        if not brand_filter_dd.value: brand_filter_dd.value = "All"
        new_brand_dd.options = [ft.dropdown.Option(b) for b in brands]
        new_color_dd.options = [ft.dropdown.Option(c) for c in get_colors()]
        page.update()

    def open_add_brand(e):
        f = ft.TextField(label="Brand Name", autofocus=True, border_color="blue", color="black")
        def save(ev):
            if f.value.strip(): add_new_brand(f.value.strip()); load_dropdowns(); page.close(d)
        d = ft.AlertDialog(bgcolor="white",
            title=ft.Text("Add Brand", weight="bold", color="black"), content=f,
            actions=[ft.ElevatedButton("Save", on_click=save, bgcolor="blue", color="white")])
        page.open(d)

    def open_add_color(e):
        f = ft.TextField(label="Color Name", autofocus=True, border_color="blue", color="black")
        def save(ev):
            if f.value.strip(): add_new_color(f.value.strip()); load_dropdowns(); page.close(d)
        d = ft.AlertDialog(bgcolor="white",
            title=ft.Text("Add Color", weight="bold", color="black"), content=f,
            actions=[ft.ElevatedButton("Save", on_click=save, bgcolor="blue", color="white")])
        page.open(d)

    def delete_confirm(item_id, item_name):
        def do_delete(e):
            # delete_inventory_item নিজেই log করে (database.py তে)
            delete_inventory_item(item_id)
            refresh_list()
        d = ft.AlertDialog(bgcolor="white",
            title=ft.Text(f"Delete '{item_name}'?", color="black"),
            content=ft.Text("Permanently delete this product?", color="black"),
            actions=[
                ft.TextButton("Cancel", style=ft.ButtonStyle(color="black"),
                              on_click=lambda _: page.close(d)),
                ft.ElevatedButton("Delete",
                                  on_click=lambda e: [page.close(d), do_delete(e)],
                                  bgcolor="red", color="white"),
            ])
        page.open(d)

    def toggle_edit(item_id):
        nonlocal editing_id
        editing_id = item_id
        refresh_list()

    # ================================================================
    # REFRESH LIST
    # ================================================================
    def refresh_list(e=None):
        nonlocal editing_id
        inventory_list.controls.clear()
        items    = get_inventory_items()
        mobile   = is_mobile()
        b_filter = brand_filter_dd.value or "All"
        s_filter = (search_tf.value or "").lower().strip()

        filtered = []
        for item in items:
            if b_filter != "All" and b_filter != str(item[1]).strip(): continue
            if s_filter and (
                s_filter not in str(item[3] or "").lower() and
                s_filter not in str(item[2] or "").lower() and
                s_filter not in str(item[1] or "").lower()
            ): continue
            filtered.append(item)

        if not mobile:
            inventory_list.controls.append(ft.Container(
                bgcolor="#e8eaf6",
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border=ft.border.only(bottom=ft.BorderSide(2, "black26")),
                content=ft.Row([
                    ft.Text("SL",                   width=38,  weight="bold", color="black", size=13),
                    ft.Text("Code",                 width=85,  weight="bold", color="black", size=13),
                    ft.Text("Product Name (Brand)", width=240, weight="bold", color="black", size=13),
                    ft.Text("Spec",                 width=130, weight="bold", color="black", size=13),
                    ft.Text("Color",                width=90,  weight="bold", color="black", size=13),
                    ft.Text("Stock",                width=175, weight="bold", color="black", size=13),
                    ft.Text("Buy",                  width=80,  weight="bold", color="black", size=13),
                    ft.Text("Sell",                 width=80,  weight="bold", color="black", size=13),
                    ft.Text("Disc%",                width=65,  weight="bold", color="red",   size=13),
                    ft.Text("Action",               width=90,  weight="bold", color="black", size=13),
                ]),
            ))

        for idx, item in enumerate(filtered, 1):
            total_in   = float(item[6]  or 0)
            unit_in    = float(item[7]  or 120)
            u_type     = str(item[10]   or "alum").strip().lower()
            mm_val     = str(item[5]    or "").strip()
            buy_price  = float(item[8]  or 0)
            sell_price = float(item[9]  or 0)
            try:    disc_pct = float(item[11] or 0)
            except: disc_pct = 0.0

            if u_type == "alum":
                u_ft = int(unit_in//12); u_in = int(unit_in%12)
                spec_display = f"{u_ft}' {u_in}\""
                if mm_val: spec_display += f" ({mm_val}mm)"
            else:
                spec_display = "PCS"

            if u_type == "alum":
                pcs_c = int(total_in//unit_in); rem = total_in%unit_in
                stock_str = f"{pcs_c} Pcs"
                if rem > 0: stock_str += f" +{int(rem//12)}' {round(rem%12,1)}\""
            else:
                stock_str = f"{int(total_in)} Pcs"

            s_color = ("red"    if total_in<=0
                       else "orange" if (u_type=="alum" and total_in<unit_in)
                                        or (u_type!="alum" and total_in<10)
                       else "blue")

            # ── MOBILE CARD ─────────────────────────────────────
            if mobile:
                if editing_id == item[0]:
                    buy_f  = ibox("Buy",   buy_price,  expand=1)
                    sell_f = ibox("Sell",  sell_price, expand=1)
                    disc_f = ibox("Disc%", disc_pct,   expand=1)

                    if u_type == "alum":
                        in_p = ibox("Pcs", 0,               expand=1)
                        in_f = ibox("Ft",  int(unit_in//12), expand=1)
                        in_i = ibox("In",  int(unit_in%12),  expand=1)

                        def save_m(e, i=item, b=buy_f, s=sell_f,
                                   p=in_p, f=in_f, inc=in_i, d=disc_f,
                                   bp=buy_price, sp=sell_price, dp=disc_pct):
                            try:
                                per_pc  = (float(f.value or 0)*12) + float(inc.value or 0)
                                added   = float(p.value or 0) * per_pc
                                old_stk = float(i[6] or 0.0)
                                new_stk = old_stk + added

                                # ✅ Stock Added log — এখানে একবারই
                                if added > 0:
                                    add_audit_log(
                                        action_type  = "Stock Added",
                                        product_name = str(i[3]),
                                        details      = f"Added {float(p.value or 0):.0f} pcs",
                                        brand        = str(i[1]),
                                        die_code     = str(i[2]),
                                        color        = str(i[4]),
                                        unit_length  = per_pc if per_pc > 0 else float(i[7] or 120),
                                        old_stock    = old_stk,
                                        new_stock    = new_stk,
                                    )

                                # ✅ update_inventory_item — Price/Discount log ওখানে হবে
                                update_inventory_item(
                                    i[0], i[1], i[2], i[3], i[4], i[5],
                                    float(b.value or bp), float(s.value or sp),
                                    new_stk if added > 0 else None,
                                    float(d.value or dp),
                                )
                                nonlocal editing_id; editing_id=None; refresh_list()
                            except Exception as ex: print(ex)

                        qty_row = ft.Row([in_p, in_f, in_i], spacing=6)
                        save_fn = save_m

                    else:
                        in_qty = ibox("Add Qty", 0, expand=1)

                        def save_pcs_m(e, i=item, b=buy_f, s=sell_f, q=in_qty, d=disc_f,
                                       bp=buy_price, sp=sell_price, dp=disc_pct):
                            try:
                                change_qty = float(q.value or 0)
                                old_stk    = float(i[6] or 0.0)
                                new_stk    = old_stk + change_qty

                                if change_qty > 0:
                                    add_audit_log(
                                        action_type  = "Stock Added",
                                        product_name = str(i[3]),
                                        details      = f"Added {change_qty:.0f} Pcs",
                                        brand        = str(i[1]),
                                        die_code     = str(i[2]),
                                        color        = str(i[4]),
                                        unit_length  = 1.0,
                                        old_stock    = old_stk,
                                        new_stock    = new_stk,
                                    )

                                update_inventory_item(
                                    i[0], i[1], i[2], i[3], i[4], i[5],
                                    float(b.value or bp), float(s.value or sp),
                                    new_stk if change_qty > 0 else None,
                                    float(d.value or dp),
                                )
                                nonlocal editing_id; editing_id=None; refresh_list()
                            except Exception as ex: print(ex)

                        qty_row = in_qty
                        save_fn = save_pcs_m

                    card = ft.Container(
                        bgcolor="white", border_radius=12, padding=14,
                        border=ft.border.all(2, "#1565C0"),
                        margin=ft.margin.only(bottom=10),
                        content=ft.Column([
                            ft.Text(f"{item[3]}  ({item[1]})", weight="bold", color="black", size=15),
                            ft.Text(f"Code: {item[2]}  •  Color: {item[4]}  •  {spec_display}",
                                    size=12, color="black54"),
                            ft.Divider(color="black12"),
                            ft.Text("Add Stock:", size=12, color="#1565C0", weight="bold"),
                            qty_row,
                            ft.Divider(color="black12"),
                            ft.Row([buy_f, sell_f, disc_f], spacing=8),
                            ft.Row([
                                ft.ElevatedButton("Save", icon=ft.Icons.CHECK,
                                                  bgcolor="green", color="white",
                                                  on_click=save_fn, height=40),
                                ft.OutlinedButton("Cancel",
                                                  on_click=lambda _: toggle_edit(None), height=40),
                            ], spacing=8),
                        ], spacing=8),
                    )
                else:
                    card = ft.Container(
                        bgcolor="white", border_radius=10, padding=12,
                        border=ft.border.all(1, "black12"),
                        margin=ft.margin.only(bottom=8),
                        content=ft.Column([
                            ft.Row([
                                ft.Column([
                                    ft.Text(f"{item[3]}", weight="bold", color="black", size=15),
                                    ft.Text(f"{item[1]}  |  Code: {item[2]}", size=12, color="black54"),
                                ], expand=True, spacing=2),
                                ft.Row([
                                    ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color="blue",
                                                  icon_size=20,
                                                  on_click=lambda e, iid=item[0]: toggle_edit(iid)),
                                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red",
                                                  icon_size=20,
                                                  on_click=lambda e, iid=item[0], n=item[3]:
                                                      delete_confirm(iid, n)),
                                ], spacing=0),
                            ]),
                            ft.Row([
                                ft.Text(f"Spec: {spec_display}", size=12, color="black54"),
                                ft.Text(f"Color: {item[4]}",     size=12, color="black54"),
                            ], spacing=12),
                            ft.Row([
                                ft.Text(f"Stock: {stock_str}", size=13, color=s_color, weight="bold"),
                                ft.Container(expand=True),
                                ft.Column([
                                    ft.Text(f"Buy: {buy_price:,.0f}",   size=12, color="black54"),
                                    ft.Text(f"Sell: {sell_price:,.0f}", size=13, color="black",
                                            weight="bold"),
                                    ft.Text(f"Disc: {disc_pct}%", size=12, color="red"),
                                ], horizontal_alignment="end", spacing=2),
                            ]),
                        ], spacing=6),
                    )
                inventory_list.controls.append(card)

            # ── DESKTOP ROW ──────────────────────────────────────
            else:
                if editing_id != item[0]:
                    inventory_list.controls.append(ft.Container(
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border=ft.border.only(bottom=ft.BorderSide(1, "black12")),
                        content=ft.Row([
                            ft.Text(str(idx),                  width=38,  color="black",  size=13),
                            ft.Text(str(item[2] or ""),        width=85,  color="black",  size=13),
                            ft.Text(f"{item[3]}  ({item[1]})", width=240, color="black",
                                    weight="bold", size=14),
                            ft.Text(spec_display,               width=130, color="black",  size=13),
                            ft.Text(str(item[4] or ""),         width=90,  color="black",  size=13),
                            ft.Text(stock_str,                  width=175, color=s_color,
                                    weight="bold", size=13),
                            ft.Text(f"{buy_price:,.0f}",        width=80,  color="black",  size=13),
                            ft.Text(f"{sell_price:,.0f}",       width=80,  color="black",  size=13),
                            ft.Text(f"{disc_pct}%",             width=65,  color="red",    size=13),
                            ft.Row([
                                ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_color="blue",
                                              icon_size=18, tooltip="Edit",
                                              on_click=lambda e, iid=item[0]: toggle_edit(iid)),
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="red",
                                              icon_size=18, tooltip="Delete",
                                              on_click=lambda e, iid=item[0], n=item[3]:
                                                  delete_confirm(iid, n)),
                            ], spacing=0),
                        ]),
                    ))
                else:
                    buy_f  = ibox("Buy",   buy_price,  width=72)
                    sell_f = ibox("Sell",  sell_price, width=72)
                    disc_f = ibox("Disc%", disc_pct,   width=58)

                    if u_type == "alum":
                        in_p = ibox("Pcs", 0,               width=52)
                        in_f = ibox("Ft",  int(unit_in//12), width=44)
                        in_i = ibox("In",  int(unit_in%12),  width=44)

                        def save_d(e, i=item, b=buy_f, s=sell_f,
                                   p=in_p, f=in_f, inc=in_i, d=disc_f,
                                   bp=buy_price, sp=sell_price, dp=disc_pct):
                            try:
                                per_pc  = (float(f.value or 0)*12) + float(inc.value or 0)
                                added   = float(p.value or 0) * per_pc
                                old_stk = float(i[6] or 0.0)
                                new_stk = old_stk + added

                                if added > 0:
                                    add_audit_log(
                                        action_type  = "Stock Added",
                                        product_name = str(i[3]),
                                        details      = f"Added {float(p.value or 0):.0f} pcs",
                                        brand        = str(i[1]),
                                        die_code     = str(i[2]),
                                        color        = str(i[4]),
                                        unit_length  = per_pc if per_pc > 0 else float(i[7] or 120),
                                        old_stock    = old_stk,
                                        new_stock    = new_stk,
                                    )

                                update_inventory_item(
                                    i[0], i[1], i[2], i[3], i[4], i[5],
                                    float(b.value) if b.value else bp,
                                    float(s.value) if s.value else sp,
                                    new_stk if added > 0 else None,
                                    float(d.value) if d.value else dp,
                                )
                                nonlocal editing_id; editing_id=None; refresh_list()
                            except Exception as ex: print(f"Save error: {ex}")

                        qty_box = ft.Container(
                            content=ft.Column([
                                ft.Text("Add Stock", size=10, color="#1565C0", weight="bold"),
                                ft.Row([in_p, in_f, in_i], spacing=4),
                            ], spacing=2),
                            bgcolor="#F0F7FF", border=ft.border.all(1, "#1565C0"),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=6, vertical=4),
                            width=175,
                        )
                        save_fn = save_d

                    else:
                        in_qty = ibox("Add Qty", 0, width=90)

                        def save_pcs_d(e, i=item, b=buy_f, s=sell_f, q=in_qty, d=disc_f,
                                       bp=buy_price, sp=sell_price, dp=disc_pct):
                            try:
                                change_qty = float(q.value or 0)
                                old_stk    = float(i[6] or 0.0)
                                new_stk    = old_stk + change_qty

                                if change_qty > 0:
                                    add_audit_log(
                                        action_type  = "Stock Added",
                                        product_name = str(i[3]),
                                        details      = f"Added {change_qty:.0f} Pcs",
                                        brand        = str(i[1]),
                                        die_code     = str(i[2]),
                                        color        = str(i[4]),
                                        unit_length  = 1.0,
                                        old_stock    = old_stk,
                                        new_stock    = new_stk,
                                    )

                                update_inventory_item(
                                    i[0], i[1], i[2], i[3], i[4], i[5],
                                    float(b.value) if b.value else bp,
                                    float(s.value) if s.value else sp,
                                    new_stk if change_qty > 0 else None,
                                    float(d.value) if d.value else dp,
                                )
                                nonlocal editing_id; editing_id=None; refresh_list()
                            except Exception as ex: print(f"Save error: {ex}")

                        qty_box = ft.Container(
                            content=ft.Column([
                                ft.Text("Add Qty", size=10, color="#1565C0", weight="bold"),
                                in_qty,
                            ], spacing=2),
                            bgcolor="#F0F7FF", border=ft.border.all(1, "#1565C0"),
                            border_radius=8,
                            padding=ft.padding.symmetric(horizontal=6, vertical=4),
                            width=110,
                        )
                        save_fn = save_pcs_d

                    inventory_list.controls.append(ft.Container(
                        bgcolor="#F8F9FF",
                        border=ft.border.all(1.5, "#1565C0"), border_radius=10,
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        margin=ft.margin.symmetric(vertical=2),
                        content=ft.Row([
                            ft.Text(str(idx),           size=13, color="black", width=38),
                            ft.Text(str(item[2] or ""), size=13, color="black", width=85),
                            ft.Text(str(item[3] or ""), size=14, color="black",
                                    weight="bold", width=210),
                            qty_box,
                            buy_f, sell_f, disc_f,
                            ft.Row([
                                ft.IconButton(ft.Icons.CHECK_CIRCLE, icon_color="green",
                                              icon_size=22, tooltip="Save", on_click=save_fn),
                                ft.IconButton(ft.Icons.CANCEL, icon_color="red",
                                              icon_size=22, tooltip="Cancel",
                                              on_click=lambda _: toggle_edit(None)),
                            ], spacing=0),
                        ], spacing=6, scroll=ft.ScrollMode.AUTO),
                    ))

        page.update()

    # ── ADD NEW DIALOG ────────────────────────────────────────
    new_type_dd  = ft.Dropdown(
        label="Type", expand=True, color="black",
        label_style=ft.TextStyle(color="black"),
        options=[
            ft.dropdown.Option("alum",  "Aluminium (ft/pcs)"),
            ft.dropdown.Option("other", "PCS Item"),
        ],
        value="alum",
    )
    new_code     = ft.TextField(label="Die / Code",    expand=1, color="black", border_color="black")
    new_name     = ft.TextField(label="Product Name",  expand=2, color="black", border_color="black")
    new_spec_con = ft.Container(
        content=ft.TextField(label="Thickness (mm)", expand=1, color="black", border_color="black"),
        expand=1, visible=True,
    )
    new_buy      = ft.TextField(label="Buy Price",     expand=1, color="black",
                                border_color="black", input_filter=num_filter)
    new_sell     = ft.TextField(label="Sell Price",    expand=1, color="black",
                                border_color="black", input_filter=num_filter)
    new_discount = ft.TextField(label="Discount %",    expand=1, color="black",
                                border_color="black", input_filter=num_filter, hint_text="0")
    new_p = ft.TextField(label="Pcs", expand=1, color="black",
                         border_color="black", input_filter=num_filter)
    new_f = ft.TextField(label="Ft",  expand=1, color="black",
                         border_color="black", input_filter=num_filter)
    new_i = ft.TextField(label="In",  expand=1, color="black",
                         border_color="black", input_filter=num_filter)

    alum_row  = ft.Row([new_p, new_f, new_i], spacing=8)
    pcs_row   = ft.Row([new_p], spacing=8)
    stock_con = ft.Container(content=alum_row)

    def on_type_change(e):
        is_alum = new_type_dd.value == "alum"
        stock_con.content    = alum_row if is_alum else pcs_row
        new_spec_con.visible = is_alum
        page.update()
    new_type_dd.on_change = on_type_change

    def add_submit(e):
        if not new_name.value.strip():
            new_name.error_text = "Name দিন"; page.update(); return
        if not new_brand_dd.value:
            page.snack_bar = ft.SnackBar(ft.Text("Brand select করুন!", color="white"), bgcolor="red")
            page.snack_bar.open = True; page.update(); return
        if not new_color_dd.value:
            page.snack_bar = ft.SnackBar(ft.Text("Color select করুন!", color="white"), bgcolor="red")
            page.snack_bar.open = True; page.update(); return
        try:
            thick_val = new_spec_con.content.value.strip() if new_spec_con.visible else ""
            if new_type_dd.value == "alum":
                unit_in  = (float(new_f.value or 0)*12) + float(new_i.value or 0)
                total_in = float(new_p.value or 0) * unit_in
                u_type   = "alum"
            else:
                unit_in  = 1.0
                total_in = float(new_p.value or 0)
                u_type   = "other"

            disc_val = float(new_discount.value or 0)

            # DB insert — audit log নেই এখানে
            add_inventory_item(
                brand=new_brand_dd.value, die_no=new_code.value.strip(),
                name=new_name.value.strip(), color=new_color_dd.value,
                thick=thick_val, total_in=total_in, unit_in=unit_in,
                buy=float(new_buy.value or 0), sell=float(new_sell.value or 0),
                unit_type=u_type, discount=disc_val,
            )

            # ✅ Opening Stock log — একবারই এখানে
            add_audit_log(
                action_type  = "Opening Stock",
                product_name = new_name.value.strip(),
                details      = (f"Brand:{new_brand_dd.value} Die:{new_code.value.strip()} "
                                f"Color:{new_color_dd.value} Qty:{total_in} Discount:{disc_val}%"),
                brand        = new_brand_dd.value,
                die_code     = new_code.value.strip(),
                color        = new_color_dd.value,
                unit_length  = float(unit_in),
                old_stock    = 0.0,
                new_stock    = float(total_in),
            )

            for f in [new_code, new_name, new_buy, new_sell, new_discount, new_p, new_f, new_i]:
                f.value = ""; f.error_text = None
            new_spec_con.content.value = ""
            new_brand_dd.value = None; new_color_dd.value = None
            new_type_dd.value  = "alum"; stock_con.content = alum_row
            new_spec_con.visible = True
            page.close(add_dlg); refresh_list()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}", color="white"), bgcolor="red")
            page.snack_bar.open = True; page.update()

    add_dlg = ft.AlertDialog(
        bgcolor="white",
        title=ft.Text("Add New Product", weight="bold", color="blue"),
        content=ft.Container(
            width=560,
            content=ft.Column([
                ft.Row([new_brand_dd,
                        ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="blue", on_click=open_add_brand)]),
                ft.Row([new_color_dd,
                        ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="blue", on_click=open_add_color)]),
                new_type_dd,
                ft.Row([new_code, new_name], spacing=8),
                ft.Row([new_spec_con, new_buy, new_sell, new_discount], spacing=8),
                ft.Text("Opening Stock:", weight="bold", color="blue", size=13),
                stock_con,
            ], tight=True, spacing=12, scroll=ft.ScrollMode.AUTO),
        ),
        actions=[
            ft.TextButton("Cancel", style=ft.ButtonStyle(color="black"),
                          on_click=lambda _: page.close(add_dlg)),
            ft.ElevatedButton("Save", icon=ft.Icons.SAVE, on_click=add_submit,
                              bgcolor="blue", color="white"),
        ],
    )

    brand_filter_dd.on_change = refresh_list
    search_tf.on_change       = refresh_list
    load_dropdowns()
    refresh_list()

    def build_top_bar():
        if is_mobile():
            return ft.Row([
                ft.Text("Inventory", size=18, weight="bold", color="black"),
                ft.Container(expand=True),
                ft.ElevatedButton("Add New", icon=ft.Icons.ADD,
                                  on_click=lambda _: page.open(add_dlg),
                                  bgcolor="black", color="white", height=38),
            ])
        else:
            return ft.Row([
                ft.Text("Inventory Management", size=22, weight="bold", color="black"),
                ft.Row([
                    ft.Container(content=brand_filter_dd, width=155),
                    ft.Container(content=search_tf,       width=230),
                    ft.ElevatedButton("Add New", icon=ft.Icons.ADD,
                                      on_click=lambda _: page.open(add_dlg),
                                      bgcolor="black", color="white"),
                ], spacing=10),
            ], alignment="spaceBetween")

    return ft.Container(
        bgcolor="white", padding=12, expand=True,
        content=ft.Column([
            build_top_bar(),
            ft.Divider(height=8, color="black12"),
            ft.Container(
                content=inventory_list, expand=True,
                border=ft.border.all(1, "black12"), border_radius=8,
                padding=ft.padding.only(bottom=8),
            ),
        ], spacing=6),
    )
