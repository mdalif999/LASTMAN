import flet as ft
from database import (
    add_inventory_item, get_inventory_items, get_inventory_total_count,
    get_brands, add_new_brand, update_inventory_item, delete_inventory_item,
    get_colors, add_new_color, add_audit_log, DB,
)

PAGE_SIZE = 50  # একবারে কতটা load হবে


def inventory_page(page):
    editing_id     = None
    current_offset = [0]   # pagination offset
    total_count    = [0]   # মোট item count

    inventory_list = ft.Column(spacing=0, scroll="auto")

    def is_mobile():
        try:    return (page.width or 800) < 700
        except: return False

    num_filter = ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string="")

    def ibox(label, value="", width=None, expand=None):
      _orig = str(value)
      tf = ft.TextField(
        label=label, value=_orig,
        width=width, expand=expand,
        input_filter=ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string=""),
        text_align=ft.TextAlign.CENTER,
        border_color="#1565C0", border_width=2, border_radius=8,
        bgcolor="#EEF4FF", color="black",
        label_style=ft.TextStyle(color="#1565C0", size=11, weight="bold"),
        text_style=ft.TextStyle(color="black", weight="bold", size=14),
        content_padding=ft.Padding(left=6, right=6, top=8, bottom=8),
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

    # pagination label
    page_info_txt = ft.Text("", size=12, color="black54")

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
            if f.value.strip():
                add_new_brand(f.value.strip())
                load_dropdowns()
                page.close(d)
        d = ft.AlertDialog(bgcolor="white",
            title=ft.Text("Add Brand", weight="bold", color="black"), content=f,
            actions=[ft.ElevatedButton("Save", on_click=save, bgcolor="blue", color="white")])
        page.open(d)

    def open_add_color(e):
        f = ft.TextField(label="Color Name", autofocus=True, border_color="blue", color="black")
        def save(ev):
            if f.value.strip():
                add_new_color(f.value.strip())
                load_dropdowns()
                page.close(d)
        d = ft.AlertDialog(bgcolor="white",
            title=ft.Text("Add Color", weight="bold", color="black"), content=f,
            actions=[ft.ElevatedButton("Save", on_click=save, bgcolor="blue", color="white")])
        page.open(d)

    def delete_confirm(item_id, item_name):
        def do_delete(e):
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

    # ── PAGINATION HELPERS ──────────────────────────────────
    def go_prev(e):
        if current_offset[0] >= PAGE_SIZE:
            current_offset[0] -= PAGE_SIZE
            refresh_list()

    def go_next(e):
        if current_offset[0] + PAGE_SIZE < total_count[0]:
            current_offset[0] += PAGE_SIZE
            refresh_list()

    def on_filter_change(e):
     nonlocal editing_id
     editing_id = None  # ← এটা add করো
     current_offset[0] = 0
     refresh_list()

    def force_sync_from_supabase():
     try:
        import main as m
        if m.supabase:
            result = m.supabase.table("inventory").select("*").execute()
            rows = result.data or []
            import sqlite3
            conn = sqlite3.connect(DB)
            cur = conn.cursor()

            # ✅ Supabase থেকে আসা সব ID
            supabase_ids = [r.get("id") for r in rows if r.get("id")]

            for r in rows:
                cur.execute("""
                    INSERT OR REPLACE INTO inventory 
                    (id, brand, die_no, name, color, thick, total_in,
                     unit_in, buy_price, sell_price, unit_type, current_stock,
                     discount_percent, is_synced)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)
                """, (
                    r.get("id"), r.get("brand"), r.get("die_no"),
                    r.get("name"), r.get("color"), r.get("thick"),
                    r.get("total_in"), r.get("unit_in"), r.get("buy_price"),
                    r.get("sell_price"), r.get("unit_type"), r.get("current_stock"),
                    r.get("discount_percent"),
                ))

            # ✅ Supabase এ নেই এমন local item delete করো
            if supabase_ids:
                placeholders = ",".join("?" * len(supabase_ids))
                cur.execute(
                    f"DELETE FROM inventory WHERE id NOT IN ({placeholders})",
                    supabase_ids
                )
                deleted = cur.rowcount
            else:
                deleted = 0

            conn.commit()
            conn.close()
            current_offset[0] = 0
            refresh_list()
            load_dropdowns()
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✅ {len(rows)} synced, {deleted} removed!", color="white"),
                bgcolor="green"
            )
            page.snack_bar.open = True
            page.update()
     except Exception as ex:
        print(f"Force sync error: {ex}")
        page.snack_bar = ft.SnackBar(
            ft.Text(f"❌ Sync failed: {ex}", color="white"), bgcolor="red"
        )
        page.snack_bar.open = True
        page.update()
    
    
    # ================================================================
    # REFRESH LIST
    # ================================================================
    def refresh_list(e=None):
        nonlocal editing_id
        
        inventory_list.controls.clear()
  
       

        mobile   = is_mobile()
        if mobile:
            inventory_list.width = None
        else:
            inventory_list.width = 1120

        b_filter = brand_filter_dd.value or "All"
        s_filter = (search_tf.value or "").lower().strip()

        # search/filter থাকলে সব load করো, না থাকলে pagination
        if s_filter or b_filter != "All":
            # সব data এনে filter করো
            all_items = get_inventory_items(limit=99999, offset=0)
            filtered  = []
            for item in all_items:
                if b_filter != "All" and b_filter != str(item[1]).strip(): continue
                if s_filter and (
                    s_filter not in str(item[3] or "").lower() and
                    s_filter not in str(item[2] or "").lower() and
                    s_filter not in str(item[1] or "").lower()
                ): continue
                filtered.append(item)
            total_count[0]    = len(filtered)
            page_info_txt.value = f"Showing {len(filtered)} results"
        else:
            total_count[0]  = get_inventory_total_count()
            filtered        = get_inventory_items(limit=PAGE_SIZE, offset=current_offset[0])
            showing_from    = current_offset[0] + 1
            showing_to      = min(current_offset[0] + PAGE_SIZE, total_count[0])
            page_info_txt.value = (
                f"Showing {showing_from}–{showing_to} of {total_count[0]}"
                if total_count[0] > 0 else "No items"
            )

        if not mobile:
            # ── DESKTOP HEADER (Sell column নেই) ──
            inventory_list.controls.append(ft.Container(
                bgcolor="#e8eaf6",
                padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                border=ft.Border(bottom=ft.BorderSide(2, "black26")),
                content=ft.Row([
                    ft.Text("SL",                   width=38,  weight="bold", color="black", size=13),
                    ft.Text("Code",                 width=85,  weight="bold", color="black", size=13),
                    ft.Text("Product Name (Brand)", width=300, weight="bold", color="black", size=13),
                    ft.Text("Spec",                 width=130, weight="bold", color="black", size=13),
                    ft.Text("Color",                width=90,  weight="bold", color="black", size=13),
                    ft.Text("Stock",                width=115, weight="bold", color="black", size=13),
                    ft.Text("Price",                width=90,  weight="bold", color="black", size=13),
                    ft.Text("Disc%",                width=65,  weight="bold", color="red",   size=13),
                    ft.Text("Action",               width=90,  weight="bold", color="black", size=13),
                ]),
            ))

        for idx, item in enumerate(filtered, current_offset[0] + 1):
            total_in   = float(item[6]  or 0)
            unit_in    = float(item[7]  or 120)
            u_type     = str(item[10]   or "alum").strip().lower()
            mm_val     = str(item[5]    or "").strip()
            buy_price  = float(item[9]  or 0)
            try:    disc_pct = float(item[11] or 0)
            except: disc_pct = 0.0

            # effective sell = buy - disc%
            effective_sell = round(buy_price * (1 - disc_pct / 100), 2)

            if u_type == "alum":
                u_ft = int(unit_in//12); u_in = int(unit_in%12)
                spec_display = f"{u_ft}' {u_in}\""
                if mm_val: spec_display += f" ({mm_val}mm)"
            else:
                spec_display = "PCS"

            if u_type == "alum":
                pcs_c = int(total_in//unit_in); rem = total_in % unit_in
                stock_str = f"{pcs_c} Pcs"
                if rem > 0: stock_str += f" +{int(rem//12)}' {round(rem%12,1)}\""
            else:
                stock_str = f"{int(total_in)} Pcs"

            s_color = ("red"    if total_in <= 0
                       else "orange" if (u_type == "alum" and total_in < unit_in)
                                        or (u_type != "alum" and total_in < 10)
                       else "blue")

            # ── MOBILE CARD ──────────────────────────────────────
            if mobile:
                if editing_id == item[0]:
                    buy_f  = ibox("Price",  buy_price,  expand=1)
                    disc_f = ibox("Disc%",  disc_pct,   expand=1)

                    if u_type == "alum":
                        in_p = ibox("Pcs", 0,                expand=1)
                        in_f = ibox("Ft",  int(unit_in//12), expand=1)
                        in_i = ibox("In",  int(unit_in%12),  expand=1)

                        def save_m(e, i=item, b=buy_f,
                                   p=in_p, f=in_f, inc=in_i, d=disc_f,
                                   bp=buy_price, dp=disc_pct):
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
                                    float(b.value or bp),
                                    new_stk if added > 0 else None,
                                    float(d.value or dp),
                                )
                                nonlocal editing_id; editing_id = None; refresh_list()
                            except Exception as ex: print(ex)

                        qty_row = ft.Row([in_p, in_f, in_i], spacing=6)
                        save_fn = save_m

                    else:
                        in_qty = ibox("Add Qty", 0, expand=1)

                        def save_pcs_m(e, i=item, b=buy_f, q=in_qty, d=disc_f,
                                       bp=buy_price, dp=disc_pct):
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
                                    float(b.value or bp),
                                    new_stk if change_qty > 0 else None,
                                    float(d.value or dp),
                                )
                                nonlocal editing_id; editing_id = None; refresh_list()
                            except Exception as ex: print(ex)

                        qty_row = in_qty
                        save_fn = save_pcs_m

                    card = ft.Container(
                        bgcolor="white", border_radius=12, padding=14,
                        border=ft.border.all(2, "#1565C0"),
                        margin=ft.Margin(left=0, right=0, top=0, bottom=10),
                        content=ft.Column([
                            ft.Text(f"{item[3]}  ({item[1]})", weight="bold", color="black", size=15),
                            ft.Text(f"Code: {item[2]}  •  Color: {item[4]}  •  {spec_display}",
                                    size=12, color="black54"),
                            ft.Divider(color="black12"),
                            ft.Text("Add Stock:", size=12, color="#1565C0", weight="bold"),
                            qty_row,
                            ft.Divider(color="black12"),
                            ft.Row([buy_f, disc_f], spacing=8),
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
                        margin=ft.Margin(left=0, right=0, top=0, bottom=8),
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
                                    ft.Text(f"Price: {buy_price:,.0f}",  size=13, color="black", weight="bold"),
                                    ft.Text(f"Disc: {disc_pct}%",        size=12, color="red"),
                                    ft.Text(f"Net: {effective_sell:,.0f}", size=12, color="green700"),
                                ], horizontal_alignment="end", spacing=2),
                            ]),
                        ], spacing=6),
                    )
                inventory_list.controls.append(card)

            # ── DESKTOP ROW (Sell column নেই) ─────────────────────
            else:
                if editing_id != item[0]:
                    inventory_list.controls.append(ft.Container(
                        padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                        border=ft.Border(bottom=ft.BorderSide(1, "black12")),
                        content=ft.Row([
                            ft.Text(str(idx),                  width=38,  color="black",  size=13),
                            ft.Text(str(item[2] or ""),        width=85,  color="black",  size=13),
                            ft.Text(f"{item[3]}  ({item[1]})", width=300, color="black",
                                    weight="bold", size=14),
                            ft.Text(spec_display,               width=130, color="black",  size=13),
                            ft.Text(str(item[4] or ""),         width=90,  color="black",  size=13),
                            ft.Text(stock_str,                  width=115, color=s_color,
                                    weight="bold", size=13),
                            ft.Text(f"{buy_price:,.0f}",        width=90,  color="black",  size=13),
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
                    buy_f  = ibox("Price", buy_price,  width=80)
                    disc_f = ibox("Disc%", disc_pct,   width=65)

                    if u_type == "alum":
                        in_p = ibox("Pcs", 0,                width=52)
                        in_f = ibox("Ft",  int(unit_in//12), width=44)
                        in_i = ibox("In",  int(unit_in%12),  width=44)

                        def save_d(e, i=item, b=buy_f,
                                   p=in_p, f=in_f, inc=in_i, d=disc_f,
                                   bp=buy_price, dp=disc_pct):
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
                                    new_stk if added > 0 else None,
                                    float(d.value) if d.value else dp,
                                )
                                nonlocal editing_id; editing_id = None; refresh_list()
                            except Exception as ex: print(f"Save error: {ex}")

                        qty_box = ft.Container(
                            content=ft.Column([
                                ft.Text("Add Stock", size=10, color="#1565C0", weight="bold"),
                                ft.Row([in_p, in_f, in_i], spacing=4),
                            ], spacing=2),
                            bgcolor="#F0F7FF", border=ft.border.all(1, "#1565C0"),
                            border_radius=8,
                            padding=ft.Padding(left=6, right=6, top=4, bottom=4),
                            width=175,
                        )
                        save_fn = save_d

                    else:
                        in_qty = ibox("Add Qty", 0, width=90)

                        def save_pcs_d(e, i=item, b=buy_f, q=in_qty, d=disc_f,
                                       bp=buy_price, dp=disc_pct):
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
                                    new_stk if change_qty > 0 else None,
                                    float(d.value) if d.value else dp,
                                )
                                nonlocal editing_id; editing_id = None; refresh_list()
                            except Exception as ex: print(f"Save error: {ex}")

                        qty_box = ft.Container(
                            content=ft.Column([
                                ft.Text("Add Qty", size=10, color="#1565C0", weight="bold"),
                                in_qty,
                            ], spacing=2),
                            bgcolor="#F0F7FF", border=ft.border.all(1, "#1565C0"),
                            border_radius=8,
                            padding=ft.Padding(left=6, right=6, top=4, bottom=4),
                            width=110,
                        )
                        save_fn = save_pcs_d

                    inventory_list.controls.append(ft.Container(
                        bgcolor="#F8F9FF",
                        border=ft.border.all(1.5, "#1565C0"), border_radius=10,
                        padding=ft.Padding(left=12, right=12, top=10, bottom=10),
                        margin=ft.Margin(left=0, right=0, top=2, bottom=2),
                        content=ft.Row([
                            ft.Text(str(idx),           size=13, color="black", width=38),
                            ft.Text(str(item[2] or ""), size=13, color="black", width=85),
                            ft.Text(str(item[3] or ""), size=14, color="black",
                                    weight="bold", width=270),
                            qty_box,
                            buy_f, disc_f,
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
    # Sell field সরানো হয়েছে — শুধু Buy (Price) আর Discount আছে
    new_buy      = ft.TextField(label="Price (Buy)",   expand=1, color="black",
                            border_color="black",
                            input_filter=ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string=""))
    new_discount = ft.TextField(label="Discount %",    expand=1, color="black",
                            border_color="black", hint_text="0",
                            input_filter=ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string=""))
    new_p = ft.TextField(label="Pcs", expand=1, color="black",
                     border_color="black",
                     input_filter=ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string=""))
    new_f = ft.TextField(label="Ft",  expand=1, color="black",
                     border_color="black",
                     input_filter=ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string=""))
    new_i = ft.TextField(label="In",  expand=1, color="black",
                     border_color="black",
                     input_filter=ft.InputFilter(allow=True, regex_string=r"^\d*\.?\d*$", replacement_string=""))

    alum_row  = ft.Row([new_p, new_f, new_i], spacing=8)
    pcs_row   = ft.Row([new_p], spacing=8)
    stock_con = ft.Container(content=alum_row)

    def on_type_change(e):
        is_alum = new_type_dd.value == "alum"
        stock_con.content = ft.Row([new_p, new_f, new_i], spacing=8) if is_alum else ft.Row([new_p], spacing=8)
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

            add_inventory_item(
                brand=new_brand_dd.value, die_no=new_code.value.strip(),
                name=new_name.value.strip(), color=new_color_dd.value,
                thick=thick_val, total_in=total_in, unit_in=unit_in,
                buy=float(new_buy.value or 0),
                unit_type=u_type, discount=disc_val,
            )

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

            for f in [new_code, new_name, new_buy, new_discount, new_p, new_f, new_i]:
                f.value = ""; f.error_text = None
            new_spec_con.content.value = ""
            new_brand_dd.value = None; new_color_dd.value = None
            new_type_dd.value  = "alum"; stock_con.content = ft.Row([new_p, new_f, new_i], spacing=8)
            new_spec_con.visible = True
            page.close(add_dlg)
            current_offset[0] = 0
            refresh_list()
            load_dropdowns()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}", color="white"), bgcolor="red")
            page.snack_bar.open = True; page.update()

    add_dlg = ft.AlertDialog(
        bgcolor="white",
        title=ft.Text("Add New Product", weight="bold", color="blue"),
        content=ft.Container(
            width=520,
            content=ft.Column([
                ft.Row([new_brand_dd,
                        ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="blue", on_click=open_add_brand)]),
                ft.Row([new_color_dd,
                        ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="blue", on_click=open_add_color)]),
                new_type_dd,
                ft.Row([new_code, new_name], spacing=8),
                # Sell field নেই — শুধু Price + Discount
                ft.Row([new_spec_con, new_buy, new_discount], spacing=8),
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

    brand_filter_dd.on_change = on_filter_change
    search_tf.on_change       = on_filter_change
    load_dropdowns()
    refresh_list()

    # ── PAGINATION BUTTONS ──────────────────────────────────
    prev_btn = ft.IconButton(ft.Icons.ARROW_BACK_IOS, on_click=go_prev,
                             icon_color="black", tooltip="Previous page")
    next_btn = ft.IconButton(ft.Icons.ARROW_FORWARD_IOS, on_click=go_next,
                             icon_color="black", tooltip="Next page")

    pagination_row = ft.Row(
        [prev_btn, page_info_txt, next_btn],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    def build_top_bar():
     if is_mobile():
        return ft.Row([
            ft.Text("Inventory", size=18, weight="bold", color="black"),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Sync",
                icon=ft.Icons.CLOUD_DOWNLOAD,
                bgcolor="blue", color="white", height=38,
                on_click=lambda _: force_sync_from_supabase()
            ),
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
                ft.ElevatedButton(
                    "Sync",
                    icon=ft.Icons.CLOUD_DOWNLOAD,
                    bgcolor="blue", color="white",
                    on_click=lambda _: force_sync_from_supabase()
                ),
                ft.ElevatedButton("Add New", icon=ft.Icons.ADD,
                                  on_click=lambda _: page.open(add_dlg),
                                  bgcolor="black", color="white"),
            ], spacing=10, wrap=True),
        ], alignment="spaceBetween", wrap=True, width=1120)

    return ft.Container(
        bgcolor="white", padding=12, expand=True,
        content=ft.Column([
            build_top_bar(),
            ft.Divider(height=8, color="black12"),
            ft.Container(
                content=ft.Row(
                    [inventory_list],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                expand=True,
                border=ft.border.all(1, "black12"), border_radius=8,
                padding=ft.Padding(left=0, right=0, top=0, bottom=8),
            ),
            pagination_row,
        ], spacing=6),
    )