import flet as ft
from database import (add_inventory_item, get_inventory_items, get_brands,
                      add_new_brand, update_inventory_item, delete_inventory_item,
                      get_colors, add_new_color)


def inventory_page(page):
    inventory_list = ft.Column(spacing=0, scroll="auto", expand=True)
    editing_id = None

    # brand filter dropdown — page level এ রাখা হয়েছে যাতে load_dropdowns() access করতে পারে
    brand_filter_dd = ft.Dropdown(
        label="Brand",
        width=150,
        value="All",
        color="black",
        text_size=13,
        content_padding=10,
    )
    search_tf = ft.TextField(
        label="Search",
        width=200,
        prefix_icon="search",
        color="black",
    )

    # =========================
    # LOAD DROPDOWNS
    # =========================

    def load_dropdowns():
        brand_names = get_brands()

        # FIX: filter dropdown এ "All" সহ
        brand_filter_dd.options = (
            [ft.dropdown.Option("All")] +
            [ft.dropdown.Option(b) for b in brand_names]
        )
        if not brand_filter_dd.value:
            brand_filter_dd.value = "All"

        # add dialog dropdown এ All ছাড়া
        new_brand_dropdown.options = [ft.dropdown.Option(b) for b in brand_names]

        color_names = get_colors()
        new_color_dropdown.options = [ft.dropdown.Option(c) for c in color_names]

        page.update()

    # =========================
    # ADD BRAND / COLOR
    # =========================

    def open_add_brand(e):
        brand_name_field = ft.TextField(
            label="Brand Name", autofocus=True,
            border_color="blue", color="black"
        )

        def save_b(e):
            if brand_name_field.value:
                add_new_brand(brand_name_field.value)
                load_dropdowns()
                page.close(brand_dlg)

        brand_dlg = ft.AlertDialog(
            bgcolor="white",
            title=ft.Text("Add New Brand", weight="bold", color="black"),
            content=brand_name_field,
            actions=[ft.ElevatedButton("Save", on_click=save_b, bgcolor="blue", color="white")]
        )
        page.open(brand_dlg)

    def open_add_color(e):
        color_field = ft.TextField(
            label="Color Name", autofocus=True,
            border_color="blue", color="black"
        )

        def save_c(e):
            if color_field.value:
                add_new_color(color_field.value)
                load_dropdowns()
                page.close(color_dlg)

        color_dlg = ft.AlertDialog(
            bgcolor="white",
            title=ft.Text("Add New Color", weight="bold", color="black"),
            content=color_field,
            actions=[ft.ElevatedButton("Save", on_click=save_c, bgcolor="blue", color="white")]
        )
        page.open(color_dlg)

    # =========================
    # REFRESH LIST
    # =========================

    def refresh_list(e=None):
        inventory_list.controls.clear()
        items = get_inventory_items()

        # Header row
        header = ft.Container(
            bgcolor="#f0f0f0",
            padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border=ft.border.only(bottom=ft.BorderSide(2, "black26")),
            content=ft.Row([
                ft.Text("SL",                   width=35,  weight="bold", color="black"),
                ft.Text("Code",                 width=80,  weight="bold", color="black"),
                ft.Text("Product Name (Brand)", width=220, weight="bold", color="black"),
                ft.Text("Spec",                 width=130, weight="bold", color="black"),
                ft.Text("Color",                width=80,  weight="bold", color="black"),
                ft.Text("Stock Status",         width=160, weight="bold", color="black"),
                ft.Text("Buy",                  width=70,  weight="bold", color="black"),
                ft.Text("Sell",                 width=70,  weight="bold", color="black"),
                ft.Text("Action",               width=90,  weight="bold", color="black"),
            ])
        )
        inventory_list.controls.append(header)

        b_filter = brand_filter_dd.value or "All"
        s_filter = search_tf.value.lower() if search_tf.value else ""

        for idx, item in enumerate(items, start=1):

            if b_filter != "All" and b_filter != str(item[1]).strip():
                continue
            if s_filter and s_filter not in str(item[3]).lower() and s_filter not in str(item[2]).lower():
                continue

            total_stock_inches = float(item[6] or 0)
            unit_len_inches    = float(item[7] or 1)
            u_type = str(item[10]).strip() if len(item) > 10 and item[10] else "alum"
            mm_val = str(item[5] or "").strip()

            # Spec display
            if u_type == "alum":
                u_ft  = int(unit_len_inches // 12)
                u_in  = int(unit_len_inches % 12)
                spec_display = f"{u_ft}' {u_in}\""
                if mm_val:
                    spec_display += f" ({mm_val}mm)"
            else:
                # PCS item — mm থাকলে দেখাবে, না থাকলে শুধু "PCS"
                spec_display = f"PCS ({mm_val}mm)" if mm_val else "PCS"

            # Stock display
            if u_type == "alum":
                pcs_count  = int(total_stock_inches // unit_len_inches)
                rem_inches = total_stock_inches % unit_len_inches
                stock_str  = f"{pcs_count} Pcs"
                if rem_inches > 0:
                    stock_str += f" (+{int(rem_inches // 12)}' {round(rem_inches % 12, 1)}\")"
            else:
                stock_str = f"{int(total_stock_inches)} Pcs"

            if editing_id != item[0]:

                row_content = ft.Row([
                    ft.Text(str(idx),                    width=35,  weight="w600", color="black"),
                    ft.Text(str(item[2]),                width=80,  weight="w600", color="black"),
                    ft.Text(f"{item[3]} ({item[1]})",    width=220, weight="w700", color="black"),
                    ft.Text(spec_display,                width=130, weight="bold", color="black"),
                    ft.Text(str(item[4]),                width=80,  color="black"),
                    ft.Text(stock_str,                   width=160, weight="bold", color="blue"),
                    ft.Text(str(item[8]),                width=70,  color="black"),
                    ft.Text(str(item[9]),                width=70,  color="black"),
                    ft.Row([
                        ft.IconButton("edit_outlined",   icon_color="blue",
                                      on_click=lambda e, id=item[0]: toggle_edit(id)),
                        ft.IconButton("delete_outline",  icon_color="red",
                                      on_click=lambda e, id=item[0], n=item[3]: delete_confirm(id, n))
                    ], spacing=0)
                ])

            else:

                buy_f  = ft.TextField(value=str(item[8]), width=65, border="underline",
                                      color="black", text_style=ft.TextStyle(color="black"))
                sell_f = ft.TextField(value=str(item[9]), width=65, border="underline",
                                      color="black", text_style=ft.TextStyle(color="black"))

                if u_type == "alum":
                    item_ft = int(unit_len_inches // 12)
                    item_in = int(unit_len_inches % 12)

                    in_p = ft.TextField(hint_text="Pcs", width=50, border="underline",
                                        text_style=ft.TextStyle(color="black"))
                    in_f = ft.TextField(value=str(item_ft), width=40, border="underline",
                                        text_style=ft.TextStyle(color="black"))
                    in_i = ft.TextField(value=str(item_in), width=40, border="underline",
                                        text_style=ft.TextStyle(color="black"))

                    qty_row = ft.Row([in_p, in_f, in_i], spacing=2, width=160)

                    def save_alum(e, i=item, b=buy_f, s=sell_f, p=in_p, f=in_f, inch=in_i):
                        try:
                            added = float(p.value or 0) * (
                                float(f.value or 0) * 12 + float(inch.value or 0)
                            )
                            update_inventory_item(
                                item_id=i[0], brand=i[1], die_no=i[2], name=i[3],
                                color=i[4], thick=i[5], buy=float(b.value),
                                sell=float(s.value), total_in=float(i[6]) + added
                            )
                            nonlocal editing_id
                            editing_id = None
                            refresh_list()
                        except Exception as ex:
                            print(f"Save error: {ex}")

                    save_fn = save_alum

                else:
                    in_qty = ft.TextField(hint_text="Add Qty", width=120, border="underline",
                                          text_style=ft.TextStyle(color="black"))
                    qty_row = ft.Row([in_qty], width=160)

                    def save_pcs(e, i=item, b=buy_f, s=sell_f, q=in_qty):
                        try:
                            added = float(q.value or 0)
                            update_inventory_item(
                                item_id=i[0], brand=i[1], die_no=i[2], name=i[3],
                                color=i[4], thick=i[5], buy=float(b.value),
                                sell=float(s.value), total_in=float(i[6]) + added
                            )
                            nonlocal editing_id
                            editing_id = None
                            refresh_list()
                        except Exception as ex:
                            print(f"Save error: {ex}")

                    save_fn = save_pcs

                row_content = ft.Row([
                    ft.Text(str(idx),         width=35,  color="black"),
                    ft.Text(str(item[2]),      width=80,  color="black"),
                    ft.Text(str(item[3]),      width=220, weight="bold", color="black"),
                    ft.Text(spec_display,      width=130, color="black"),
                    ft.Text(str(item[4]),      width=80,  color="black"),
                    qty_row,
                    buy_f,
                    sell_f,
                    ft.Row([
                        ft.IconButton("check_circle_outline", icon_color="green", on_click=save_fn),
                        ft.IconButton("cancel_outlined",      icon_color="grey",
                                      on_click=lambda _: toggle_edit(None))
                    ], spacing=0)
                ])

            inventory_list.controls.append(
                ft.Container(
                    content=row_content,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border=ft.border.only(bottom=ft.BorderSide(1, "black12"))
                )
            )

        page.update()

    def toggle_edit(item_id):
        nonlocal editing_id
        editing_id = item_id
        refresh_list()

    # =========================
    # ADD NEW DIALOG
    # =========================

    new_brand_dropdown = ft.Dropdown(
        label="Select Brand", expand=True, color="black"
    )
    new_color_dropdown = ft.Dropdown(
        label="Select Color", expand=True, color="black"
    )
    new_type_dropdown = ft.Dropdown(
        label="Type",
        expand=True,
        color="black",
        options=[
            ft.dropdown.Option("alum",  "Aluminium"),
            ft.dropdown.Option("other", "PCS Item"),
        ],
        value="alum"
    )

    new_code  = ft.TextField(hint_text="Code",         expand=1, color="black")
    new_name  = ft.TextField(hint_text="Product Name", expand=2, color="black")
    # FIX: value বাদ দিয়ে hint_text দেওয়া হয়েছে — placeholder হিসেবে দেখাবে, input দিলে চলে যাবে
    new_spec  = ft.TextField(hint_text="mm (e.g. 1.2)", expand=1, color="black")
    new_buy   = ft.TextField(hint_text="Buy Price",    expand=1, color="black")
    new_sell  = ft.TextField(hint_text="Sell Price",   expand=1, color="black")
    new_p     = ft.TextField(hint_text="Pcs",          width=80, color="black")
    # FIX: Ft field খালি — user দেবে
    new_f     = ft.TextField(hint_text="Ft",           width=80, color="black")
    new_i     = ft.TextField(hint_text="In",           width=80, color="black")

    alum_stock_row = ft.Row([new_p, new_f, new_i], spacing=10)
    pcs_stock_row  = ft.Row([new_p],               spacing=10)
    stock_container = ft.Container(content=alum_stock_row)

    def on_type_change(e):
        if new_type_dropdown.value == "alum":
            stock_container.content = alum_stock_row
        else:
            stock_container.content = pcs_stock_row
        page.update()

    new_type_dropdown.on_change = on_type_change

    def add_product_submit(e):
        if not new_name.value or not new_brand_dropdown.value or not new_color_dropdown.value:
            return

        if new_type_dropdown.value == "alum":
            unit_inches          = (float(new_f.value or 0) * 12) + float(new_i.value or 0)
            total_opening_inches = float(new_p.value or 0) * unit_inches
        else:
            unit_inches          = 1
            total_opening_inches = float(new_p.value or 0)

        add_inventory_item(
            new_brand_dropdown.value,
            new_code.value,
            new_name.value,
            new_color_dropdown.value,
            new_spec.value,
            total_opening_inches,
            unit_inches,
            float(new_buy.value or 0),
            float(new_sell.value or 0),
            new_type_dropdown.value
        )

        # fields clear করো
        for f in [new_code, new_name, new_spec, new_buy, new_sell, new_p, new_f, new_i]:
            f.value = ""
        new_brand_dropdown.value = None
        new_color_dropdown.value = None
        new_type_dropdown.value  = "alum"
        stock_container.content  = alum_stock_row

        page.close(add_dlg)
        refresh_list()

    add_dlg = ft.AlertDialog(
        bgcolor="white",
        title=ft.Text("Add New Product Entry", weight="bold", color="blue"),
        content=ft.Container(
            width=600,
            content=ft.Column([
                ft.Row([new_brand_dropdown, ft.IconButton("add_circle", on_click=open_add_brand, icon_color="blue")]),
                ft.Row([new_color_dropdown, ft.IconButton("add_circle", on_click=open_add_color, icon_color="blue")]),
                ft.Row([new_type_dropdown]),
                ft.Row([new_code, new_name]),
                ft.Row([new_spec, new_buy, new_sell]),
                ft.Text("Initial Stock:", weight="bold", color="blue"),
                stock_container,
            ], tight=True, spacing=15)
        ),
        actions=[
            ft.TextButton("Cancel", style=ft.ButtonStyle(color="black"),
                          on_click=lambda _: page.close(add_dlg)),
            ft.ElevatedButton("Save Product", on_click=add_product_submit,
                              bgcolor="blue", color="white")
        ]
    )

    # =========================
    # DELETE CONFIRM
    # =========================

    def delete_confirm(item_id, item_name):
        def final_delete(e):
            delete_inventory_item(item_id)
            page.close(conf_dlg)
            refresh_list()

        conf_dlg = ft.AlertDialog(
            bgcolor="white",
            title=ft.Text(f"Delete '{item_name}'?", color="black"),
            content=ft.Text("এই product টি permanently delete হয়ে যাবে।", color="black"),
            actions=[
                ft.TextButton("Cancel", style=ft.ButtonStyle(color="black"),
                              on_click=lambda _: page.close(conf_dlg)),
                ft.ElevatedButton("Confirm Delete", on_click=final_delete,
                                  bgcolor="red", color="white")
            ]
        )
        page.open(conf_dlg)

    # =========================
    # WIRE UP FILTER EVENTS
    # =========================

    brand_filter_dd.on_change = refresh_list
    search_tf.on_change       = refresh_list

    # =========================
    # INIT
    # =========================

    load_dropdowns()
    refresh_list()

    # =========================
    # RETURN UI
    # =========================

    return ft.Container(
        bgcolor="white",
        padding=20,
        expand=True,
        content=ft.Column([
            ft.Row([
                ft.Text("Inventory Management", size=26, weight="bold", color="black"),
                ft.Row([
                    brand_filter_dd,
                    search_tf,
                    # FIX: icon বাদ দিয়ে শুধু text — double plus চলে গেছে
                    ft.ElevatedButton(
                        "+ Add New",
                        on_click=lambda _: page.open(add_dlg),
                        bgcolor="black",
                        color="white"
                    )
                ])
            ], alignment="spaceBetween"),
            ft.Divider(height=20, color="black12"),
            inventory_list
        ])
    )