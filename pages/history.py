import flet as ft
import re
from database import get_audit_logs


def history_page(page):

    def is_mobile():
        try:    return (page.width or 800) < 700
        except: return False

    ACTION_COLORS = {
        "Opening Stock":    "cyan",
        "Stock Added":      "green",
        "Stock Removed":    "red",
        "Price Changed":    "orange",
        "Discount Changed": "purple",
        "DELETE_ITEM":      "red400",
        "Sales (POS)":      "blue",          # 🌟 Added
        "Return Processed": "teal",          # 🌟 Added
        "STOCK_UPDATE":     "green",         # 🌟 For old migrated data
        "NEW_ITEM":         "cyan",          # 🌟 For old migrated data

    }
    ACTION_LABELS = {
        "Opening Stock":    "Opening Stock",
        "Stock Added":      "Stock Added",
        "Stock Removed":    "Stock Removed",
        "Price Changed":    "Price Changed",
        "Discount Changed": "Discount Changed",
        "DELETE_ITEM":      "Delete Item",
        "Sales (POS)":      "Sales (POS)",          # 🌟 Added
       "Return Processed": "Return Processed",      # 🌟 Added
       "STOCK_UPDATE":     "Stock Update",          # 🌟 Added
      "NEW_ITEM":         "New Item",              # 🌟 Added
    }

    def fmt_timestamp(ts):
        if not ts or ts == "—": return "—"
        ts = str(ts).strip()
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %b %Y, %I:%M %p",
            "%d %b %Y, %I:%M:%S %p",
        ]
        for fmt in formats:
            try:
                from datetime import datetime as _dt
                return _dt.strptime(ts.split('.')[0], fmt).strftime("%d %b %Y, %I:%M %p")
            except ValueError:
                continue
        return ts

    def convert_qty(total_val, unit_in, unit_type):
        try:
            total_val = float(total_val or 0)
            unit_in   = float(unit_in   or 120)
            u_type    = str(unit_type   or "alum").lower()

            if total_val <= 0:
                return "0 pcs"

            if u_type not in ("alum", "wool"):
                return f"{int(total_val)} pcs"

            pcs    = int(total_val // unit_in)
            remain = total_val % unit_in
            ft_val = int(remain // 12)
            in_val = round(remain % 12, 1)

            parts = []
            if pcs   > 0: parts.append(f"{pcs} pcs")
            if ft_val > 0: parts.append(f"{ft_val} ft")
            if in_val > 0: parts.append(f'{in_val:.0f} inc')
            return " ".join(parts) if parts else "0 pcs"
        except Exception as ex:
            print(f"convert_qty error: {ex}")
            return str(total_val)

    def fmt_details(text, unit_in, unit_type="alum"):
        if not text: return "—"
        try:
            clean_text = text.strip()
            if clean_text.replace('.', '', 1).isdigit():
                return f"Qty: {convert_qty(float(clean_text), unit_in, unit_type)}"

            def replace_qty(m):
                return f"Qty: {convert_qty(float(m.group(1)), unit_in, unit_type)}"

            def replace_qty_change(m):
                return f"Qty Change: {convert_qty(float(m.group(1)), unit_in, unit_type)}"

            result = re.sub(r"Qty Change[:\s]+([\d.]+)", replace_qty_change, text)
            result = re.sub(r"Qty[:\s]+([\d.]+)", replace_qty, result)
            return result
        except Exception as ex:
            return text

    list_view = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    filter_dd = ft.Dropdown(
    label="Filter by Action",
    expand=True,
    text_style=ft.TextStyle(color="white"),
    label_style=ft.TextStyle(color="white60"),
    border_color="white24",
    options=[
        ft.dropdown.Option("All",              "সব দেখুন"),
        ft.dropdown.Option("Opening Stock",    "Opening Stock"),
        ft.dropdown.Option("Stock Added",      "Stock Added"),
        ft.dropdown.Option("Stock Removed",    "Stock Removed"),
        ft.dropdown.Option("Price Changed",    "Price Changed"),
        ft.dropdown.Option("Discount Changed", "Discount Changed"),
        ft.dropdown.Option("DELETE_ITEM",      "Delete Item"),       # 🌟 Added
    ],
    value="All",
    on_change=lambda e: update_list(),
)

    def update_list():
        selected = filter_dd.value or "All"
        try:    logs = get_audit_logs(action_type=selected, limit=99999)
        except: logs = []

        mobile = is_mobile()
        list_view.controls.clear()

        if not logs:
            list_view.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.INBOX, color="white24", size=40),
                    ft.Text("কোনো ইতিহাস নেই", color="white54", size=14),
                ], horizontal_alignment="center", spacing=8),
                padding=30, alignment=ft.alignment.center,
            ))
            page.update()
            return

        # পারফরম্যান্স অপটিমাইজেশনের জন্য ইউনিট ম্যাপ ক্যাশ
        unit_type_cache = {}

        # 🌟 ১. ডুপ্লিকেট ট্র্যাকিংয়ের জন্য লুপের ওপরে একটি খালি সেট (Set) তৈরি করুন
        # ১. স্ক্রিনে ডুপ্লিকেট দেখানো বন্ধ করার জন্য সেট (Set)
        seen_logs = set()

        for log in logs:
            try:
                # সেফটি চেক: নতুন টেবিলে পর্যাপ্ত কলাম আছে কিনা
                if len(log) < 10: continue

                # 🌟 ডাটাবেজের নতুন ইনডেক্স টেবিল অনুযায়ী নিখুঁত ডেটা এক্সট্র্যাকশন
                raw_timestamp = str(log[0] or "—").strip()
                action_type   = str(log[1] or "—")
                product_name  = str(log[2] or "—")
                brand         = str(log[3] or "").strip()
                die_code      = str(log[4] or "").strip()
                color         = str(log[5] or "").strip()
                unit_length   = float(log[6]) if log[6] is not None else 120.0
                old_raw_stock = float(log[7]) if log[7] is not None else 0.0
                new_raw_stock = float(log[8]) if log[8] is not None else 0.0
                log_details   = str(log[9] or "")

                # 🌟 ২. ডুপ্লিকেট ফিল্টার লজিক 
                # (একই অ্যাকশন, প্রোডাক্ট, ডাই এবং স্টক চেঞ্জ হলে স্ক্রিনে একবারই দেখাবে)
                unique_key = (action_type, product_name, die_code, old_raw_stock, new_raw_stock)
                if unique_key in seen_logs:
                    continue
                seen_logs.add(unique_key)

                # 🌟 ৩. সুপাবেসের টাইমজোন (৬ ঘণ্টার জটলা) ফিক্সিং লজিক
                def fix_and_fmt_timestamp(ts):
                    if not ts or ts == "—": return "—"
                    from datetime import datetime as _dt, timedelta as _td
                    # যদি সুপাবেসের ISO ফরম্যাটে ডেটা আসে (যেমন: T বা Z থাকলে)
                    if "T" in ts or (("-" in ts or "/" in ts) and ":" in ts and ("AM" not in ts and "PM" not in ts)):
                        try:
                            clean_ts = ts.replace("T", " ").split(".")[0].replace("Z", "")
                            utc_dt = _dt.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                            local_dt = utc_dt + _td(hours=6) # ৬ ঘণ্টা যোগ করে বাংলাদেশ টাইম
                            return local_dt.strftime("%d %b %Y, %I:%M %p")
                        except Exception:
                            pass
                    return ts

                timestamp = fix_and_fmt_timestamp(raw_timestamp)

                # 🌟 ৪. ডাই কোড, ব্র্যান্ড এবং কালারসহ সুন্দর প্রোডাক্ট টাইটেল তৈরি
                display_parts = [product_name]
                if brand: display_parts.append(f"({brand})")
                if die_code: display_parts.append(f"[{die_code}]")
                if color: display_parts.append(f"- {color}")
                
                product_title = " ".join(display_parts)
                # বেশি লম্বা হয়ে গেলে স্ক্রিনের সৌন্দর্যের জন্য কেটে ছোট করা
                product_display = product_title

                # 🌟 ৫. ওল্ড স্টক এবং নিউ স্টক রিডেবল ফরম্যাটে কনভার্ট করা [Old ➔ New]
                snapshot_str = ""
                unit_type = "pcs" if unit_length <= 1.0 else "alum"
                
                # স্টক ট্র্যাকিং অ্যাকশনগুলোর জন্য ভিজ্যুয়াল ইন্ডিকেটর তৈরি
                if action_type in ["Opening Stock", "Stock Added", "Stock Removed", "Sales (POS)", "Return Processed"]:
                    try:
                        # আপনার প্রোজেক্টের কোয়ান্টিটি কনভার্টার ফাংশন (convert_qty) দিয়ে কনভার্ট
                        old_readable = convert_qty(old_raw_stock, unit_length, unit_type)
                        new_readable = convert_qty(new_raw_stock, unit_length, unit_type)
                        snapshot_str = f" [{old_readable} ➔ {new_readable}]"
                    except Exception:
                        # যদি কনভার্টার ফাংশনে কোনো সমস্যা হয়, সরাসরি সংখ্যা দেখাবে
                        snapshot_str = f" [{old_raw_stock:.0f} ➔ {new_raw_stock:.0f}]"

                # ডিটেইলস লেখার সাথে স্টক চেঞ্জের লেখাটা জুড়ে দেওয়া
                final_details = f"{log_details}{snapshot_str}"
                
                # আপনার হিস্ট্রি পেজের ডিফল্ট কালার ও লেবেল থিম ম্যাচিং
                color_theme = ACTION_COLORS.get(action_type, "white70")
                label = ACTION_LABELS.get(action_type, action_type)

                # 🌟 ৬. Flet UI-তে রো ডেটা পুশ করা
                if mobile:
                    list_view.controls.append(ft.Container(
                        bgcolor="#1e2b5e", border_radius=10, padding=12,
                        border=ft.Border(left=ft.BorderSide(4, color_theme), right=None, top=None, bottom=None),

                        content=ft.Column([
                            ft.Row([
                                ft.Text(label, size=13, weight="bold", color=color_theme, expand=True),
                                ft.Text(timestamp, size=11, color="white38"),
                            ]),
                            ft.Text(product_display, size=13, color="white", weight="bold"),
                            ft.Text(final_details, size=11, color="white60"),
                        ], spacing=4),
                    ))
                else:
                    list_view.controls.append(ft.Container(
                        #padding=ft.padding.symmetric(horizontal=10, vertical=9),
                        # ✅ এটা দাও
                        padding=ft.Padding(left=10, right=10, top=9, bottom=9),

                        border=ft.Border(left=None, right=None, top=None, bottom=ft.BorderSide(1, "white10")),

                        content=ft.Row([
                            ft.Text(timestamp, size=12, color="white60", width=185),
                            ft.Container(
                                content=ft.Text(label, size=13, weight="bold", color=color_theme),
                               padding=ft.Padding(left=6, right=0, top=0, bottom=0),
                                border=ft.Border(left=ft.BorderSide(3, color_theme), right=None, top=None, bottom=None),

                                width=155,
                            ),
                            ft.Text(product_display, size=13, color="white", weight="bold", expand=True),
                            ft.Text(final_details, size=12, color="white70", width=300),
                        ], spacing=10),
                    ))
            except Exception as ex:
                print(f"History row error: {ex}")
                continue

        page.update()

    update_list()

    return ft.Container(
       padding=ft.Padding(left=14, right=14, top=14, bottom=14), expand=True,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HISTORY, color="orange", size=26),
                ft.Text("Inventory & Price History", size=20, weight="bold"),
            ]),
            ft.Divider(height=10, color="white10"),
            ft.Row([
                filter_dd,
                ft.IconButton(ft.Icons.REFRESH, icon_color="white", tooltip="Refresh", on_click=lambda _: update_list()),
            ], spacing=8),
            ft.Container(height=6),
            ft.Container(
                content=list_view, expand=True,
                border=ft.border.all(1, "white10"),
                border_radius=10, padding=6,
            ),
        ]),
    )