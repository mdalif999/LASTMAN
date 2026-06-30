import flet as ft
import sqlite3
import os
import base64
from database import DB, update_app_password

# ডাটাবেজ পাথ
DB_PATH = DB

def settings_view(page):
    # ডাটাবেজ থেকে ডাটা আনা
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT owner_name, shop_name, address, phone, logo_path FROM business_profile WHERE id=1")
        profile = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"Error fetching profile: {e}")
        profile = None

    # ১. গোল লোগো কন্ট্রোল
    current_logo_data = profile[4] if profile and profile[4] else None
    
    def get_logo_content(data):
        if data and "base64," in data:
            try:
                base64_string = data.split(",")[1]
                return ft.Image(src_base64=base64_string, fit=ft.ImageFit.COVER, border_radius=60)
            except:
                return ft.Icon(ft.Icons.PERSON, size=60, color="orange")
        elif data and os.path.exists(data):
            return ft.Image(src=data, fit=ft.ImageFit.COVER, border_radius=60)
        else:
            return ft.Icon(ft.Icons.PERSON, size=60, color="orange")

    user_logo = ft.Container(
        width=120, height=120, bgcolor="orange100", border_radius=60,
        border=ft.Border(left=ft.BorderSide(2, "orange"), right=ft.BorderSide(2, "orange"), top=ft.BorderSide(2, "orange"), bottom=ft.BorderSide(2, "orange")), alignment=ft.alignment.Alignment(0, 0),

        content=get_logo_content(current_logo_data)
    )

    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            file = e.files[0]
            try:
                if file.path:
                    with open(file.path, "rb") as f:
                        image_bytes = f.read()
                else:
                    image_bytes = file.content if hasattr(file, 'content') else None

                if image_bytes:
                    encoded_string = base64.b64encode(image_bytes).decode("utf-8")
                    base64_data = f"data:image/png;base64,{encoded_string}"
                    
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE business_profile SET logo_path=? WHERE id=1", (base64_data,))
                    conn.commit()
                    conn.close()
                    
                    user_logo.content = ft.Image(src_base64=encoded_string, fit=ft.ImageFit.COVER, border_radius=60)
                    page.snack_bar = ft.SnackBar(ft.Text("লোগো আপডেট হয়েছে!"), bgcolor="green")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("ফাইল রিড করা সম্ভব হয়নি।"), bgcolor="red")
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_result)
    if file_picker not in page.overlay:
        page.overlay.append(file_picker)

    # ইনপুট ফিল্ডস
    owner_name = ft.TextField(label="মালিকের নাম", value=str(profile[0]) if profile else "", border_color="orange")
    shop_name = ft.TextField(label="দোকানের নাম", value=str(profile[1]) if profile else "", border_color="orange")
    address = ft.TextField(label="ঠিকানা", value=str(profile[2]) if profile else "", multiline=True, border_color="orange")
    phone = ft.TextField(label="মোবাইল নম্বর", value=str(profile[3]) if profile else "", border_color="orange")
    
    # 🚨 নতুন পাসওয়ার্ড ইনপুট ফিল্ড (আলাদা করে ডিফাইন করা হলো যাতে ভ্যালু ধরা যায়)
    new_password_field = ft.TextField(label="নতুন পাসওয়ার্ড", password=True, can_reveal_password=True, border_color="green")

    # ── Hardcoded Developer Info (Linkable) ──
    developer_info = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINED, color="cyan200", size=20),
                ft.Text("Contact Developer", size=20, weight="bold", color="cyan200"),
            ], alignment=ft.MainAxisAlignment.START),
            ft.Divider(color="white24"),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PERSON, color="white"),
                title=ft.Text("Alif (Developer)", color="white"),
                subtitle=ft.Text("Portfolio: CLICK HERE", color="blue300"),
                on_click=lambda e: page.launch_url(
                    "https://lumina-creative-portfolio-805565918113.asia-southeast1.run.app",
                    web_window_name="_blank"
                )
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PHONE, color="white"),
                title=ft.Text("Contact", color="white"),
                subtitle=ft.Text("+8801305232039", color="white70"),
                on_click=lambda _: page.launch_url("tel:+8801305232039")
            ),
            ft.ListTile(
                leading=ft.Icon(ft.Icons.EMAIL, color="white"),
                title=ft.Text("Email", color="white"),
                subtitle=ft.Text("mdalif1046@gmail.com", color="white70"),
                on_click=lambda _: page.launch_url("mailto:alif.dev@email.com")
            ),
        ], spacing=5),
        padding=15, bgcolor="#1e2b5e", border_radius=15, margin=ft.Margin(left=0, right=0, top=20, bottom=0)

    )

    # নেভিগেশন লজিক
    def show_section(section):
        settings_menu.visible = (section == "menu")
        profile_edit_area.visible = (section == "profile")
        backup_area.visible = (section == "backup")
        security_area.visible = (section == "security")
        page.update()

    def update_profile(e):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE business_profile SET owner_name=?, shop_name=?, address=?, phone=? WHERE id=1", 
                           (owner_name.value, shop_name.value, address.value, phone.value))
            conn.commit()
            conn.close()
            page.snack_bar = ft.SnackBar(ft.Text("তথ্য সেভ হয়েছে!"), bgcolor="green")
            page.snack_bar.open = True
            show_section("menu")
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red")
        page.update()

   # ============================================================
    # 🚨 নতুন পাসওয়ার্ড ইনপুট ফিল্ড (দুটি ঘর আলাদা করে ডিক্লেয়ার করা হলো)
    # ============================================================
    new_password_field = ft.TextField(label="নতুন পাসওয়ার্ড", password=True, can_reveal_password=True, border_color="green")
    confirm_password_field = ft.TextField(label="পাসওয়ার্ডটি আবার টাইপ করুন", password=True, can_reveal_password=True, border_color="green")
# ============================================================
    # SETTINGS PAGE PASSWORD UPDATE (INSTANT NO-YELLOW NAV FIX)
    # ============================================================
    def update_password(e):
        global APP_PASSWORD
        pwd_val = new_password_field.value.strip()
        conf_val = confirm_password_field.value.strip()
        
        # ১. খালি আছে কিনা চেক
        if not pwd_val or not conf_val:
            page.snack_bar = ft.SnackBar(ft.Text("পাসওয়ার্ডের দুটি ঘরই পূরণ করতে হবে!"), bgcolor="orange")
            page.snack_bar.open = True
            page.update()
            return
            
        # ২. দুইবারের পাসওয়ার্ড মিলল কিনা চেক
        if pwd_val != conf_val:
            confirm_password_field.error_text = "পাসওয়ার্ড দুটি মেলেনি! আবার চেক করুন।"
            page.update()
            return
        else:
            confirm_password_field.error_text = None
        
        try:
            # ৩. পাসওয়ার্ড চেঞ্জের মেইন মেমোরি ও ডাটাবেজ লজিক
            APP_PASSWORD = pwd_val
            page.client_storage.set("app_pin", pwd_val)
            
            update_app_password(pwd_val)
            
            # ৪. ইনপুট ফিল্ড খালি করা
            new_password_field.value = ""
            confirm_password_field.value = ""
            
            # 👑 ৫. সফলতার মেসেজ শো করা
            page.snack_bar = ft.SnackBar(
                content=ft.Text("পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে!", color="white", weight="bold"),
                bgcolor="green",
                duration=2000
            )
            page.snack_bar.open = True
            
            # 👑 ৬. কোনো টাইম ডিলে বা থ্রেড ছাড়া ইনস্ট্যান্টলি শো-সেকশন কল করা
            # এটি সরাসরি আপনার UI ভেরিয়েবলগুলোকে নিরাপদে আপডেট করবে
            show_section("menu")
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
    # মেনু
    settings_menu = ft.Column([
        ft.Text("Settings", size=30, weight="bold"),
        ft.Divider(),
        ft.ListTile(leading=ft.Icon(ft.Icons.PERSON, color="orange"), title=ft.Text("Business Profile"), subtitle=ft.Text("দোকানের তথ্য ও লোগো পরিবর্তন"), on_click=lambda _: show_section("profile")),
        ft.ListTile(leading=ft.Icon(ft.Icons.CLOUD_SYNC, color="blue"), title=ft.Text("Backup & Restore"), subtitle=ft.Text("ডাটা ক্লাউড ব্যাকআপ নিন"), on_click=lambda _: show_section("backup")),
        ft.ListTile(leading=ft.Icon(ft.Icons.SECURITY, color="green"), title=ft.Text("Security"), subtitle=ft.Text("পাসওয়ার্ড পরিবর্তন করুন"), on_click=lambda _: show_section("security")),
        developer_info
    ], visible=True)

    profile_edit_area = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_section("menu")), ft.Text("বিজনেস প্রোফাইল", size=20, weight="bold")]),
        ft.Container(content=ft.Column([user_logo, ft.TextButton("লোগো পরিবর্তন করুন", icon=ft.Icons.EDIT, on_click=lambda _: file_picker.pick_files(file_type=ft.FilePickerFileType.IMAGE))], horizontal_alignment="center"), alignment=ft.alignment.center),
        owner_name, shop_name, address, phone,
        ft.ElevatedButton("সেভ করুন", bgcolor="orange", color="white", on_click=update_profile, width=200)
    ], visible=False)

    backup_area = ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_section("menu")), ft.Text("Backup & Restore", size=20, weight="bold")]), ft.ElevatedButton("ব্যাকআপ নিন (লোকাল)", icon=ft.Icons.UPLOAD)], visible=False)
    
    # 🚨 সিকিউরিটি এরিয়া লেআউট (দুটি পাসওয়ার্ড ফিল্ড এবং অ্যালার্ট ইভেন্টসহ আপডেট করা) 🚨
    security_area = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_section("menu")), ft.Text("Security Settings", size=20, weight="bold")]), 
        ft.Text("নিরাপত্তার জন্য দুইবার নতুন পাসওয়ার্ডটি টাইপ করুন:", color="white70"),
        new_password_field, 
        confirm_password_field,
        ft.ElevatedButton("আপডেট করুন", bgcolor="green", color="white", on_click=update_password, width=200)
    ], visible=False, spacing=15)

    return ft.Container(
        content=ft.Column([settings_menu, profile_edit_area, backup_area, security_area], scroll=ft.ScrollMode.AUTO),
        padding=30, expand=True
    )