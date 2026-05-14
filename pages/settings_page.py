import flet as ft
import sqlite3
import os
import base64

# ডাটাবেজ পাথ
DB_PATH = "inventory.db"

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

    # ১. গোল লোগো কন্ট্রোল (Base64 ফ্রেন্ডলি)
    current_logo_data = profile[4] if profile and profile[4] else None
    
    # ইমেজ কন্ট্রোল তৈরি
    def get_logo_content(data):
        if data and "base64," in data:
            try:
                base64_string = data.split(",")[1]
                return ft.Image(
                    src_base64=base64_string,
                    fit=ft.ImageFit.COVER,
                    border_radius=60,
                )
            except:
                return ft.Icon(ft.Icons.PERSON, size=60, color="orange")
        elif data and os.path.exists(data):
            return ft.Image(src=data, fit=ft.ImageFit.COVER, border_radius=60)
        else:
            return ft.Icon(ft.Icons.PERSON, size=60, color="orange")

    user_logo = ft.Container(
        width=120, height=120,
        bgcolor="orange100",
        border_radius=60,
        border=ft.border.all(2, "orange"),
        alignment=ft.alignment.center,
        content=get_logo_content(current_logo_data)
    )

    # লোগো সেভ করার লজিক (Base64 মেথড - ওয়েবের জন্য সেরা)
    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            file = e.files[0]
            try:
                # ওয়েবে file.path থাকলে সরাসরি রিড হবে, না হলে bytes চেক করবে
                if file.path:
                    with open(file.path, "rb") as f:
                        image_bytes = f.read()
                else:
                    # কিছু ব্রাউজারে bytes সরাসরি পাওয়া যায়
                    image_bytes = file.content if hasattr(file, 'content') else None

                if image_bytes:
                    encoded_string = base64.b64encode(image_bytes).decode("utf-8")
                    base64_data = f"data:image/png;base64,{encoded_string}"
                    
                    # ডাটাবেজে সেভ
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE business_profile SET logo_path=? WHERE id=1", (base64_data,))
                    conn.commit()
                    conn.close()
                    
                    # UI আপডেট
                    user_logo.content = ft.Image(
                        src_base64=encoded_string,
                        fit=ft.ImageFit.COVER,
                        border_radius=60
                    )
                    page.snack_bar = ft.SnackBar(ft.Text("লোগো আপডেট হয়েছে!"), bgcolor="green")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("ফাইল রিড করা সম্ভব হয়নি।"), bgcolor="red")
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

    # সেকশন কন্ট্রোল
    def show_section(section):
        settings_menu.visible = (section == "menu")
        profile_edit_area.visible = (section == "profile")
        backup_area.visible = (section == "backup")
        security_area.visible = (section == "security")
        page.update()

    # ডাটা আপডেট ফাংশন
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
            page.snack_bar.open = True
        page.update()

    # --- UI Components ---
    settings_menu = ft.Column([
        ft.Text("Settings", size=30, weight="bold"),
        ft.Divider(),
        ft.ListTile(
            leading=ft.Icon(ft.Icons.PERSON, color="orange"),
            title=ft.Text("Business Profile"),
            subtitle=ft.Text("দোকানের তথ্য ও লোগো পরিবর্তন"),
            on_click=lambda _: show_section("profile")
        ),
        ft.ListTile(
            leading=ft.Icon(ft.Icons.CLOUD_SYNC, color="blue"),
            title=ft.Text("Backup & Restore"),
            subtitle=ft.Text("ডাটা ক্লাউড ব্যাকআপ নিন"),
            on_click=lambda _: show_section("backup")
        ),
        ft.ListTile(
            leading=ft.Icon(ft.Icons.SECURITY, color="green"),
            title=ft.Text("Security"),
            subtitle=ft.Text("পাসওয়ার্ড পরিবর্তন করুন"),
            on_click=lambda _: show_section("security")
        )
    ], visible=True)

    profile_edit_area = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_section("menu")), ft.Text("বিজনেস প্রোফাইল", size=20, weight="bold")]),
        ft.Container(
            content=ft.Column([
                user_logo,
                ft.TextButton("লোগো পরিবর্তন করুন", icon=ft.Icons.EDIT, 
                             on_click=lambda _: file_picker.pick_files(file_type=ft.FilePickerFileType.IMAGE))
            ], horizontal_alignment="center"),
            alignment=ft.alignment.center
        ),
        owner_name, shop_name, address, phone,
        ft.ElevatedButton("সেভ করুন", bgcolor="orange", color="white", on_click=update_profile, width=200)
    ], visible=False)

    backup_area = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_section("menu")), ft.Text("Backup & Restore", size=20, weight="bold")]),
        ft.ElevatedButton("ব্যাকআপ নিন (লোকাল)", icon=ft.Icons.UPLOAD)
    ], visible=False)

    security_area = ft.Column([
        ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: show_section("menu")), ft.Text("Security Settings", size=20, weight="bold")]),
        ft.TextField(label="নতুন পাসওয়ার্ড", password=True, can_reveal_password=True),
        ft.ElevatedButton("আপডেট করুন", bgcolor="green", color="white")
    ], visible=False)

    return ft.Container(
        content=ft.Column([settings_menu, profile_edit_area, backup_area, security_area], scroll=ft.ScrollMode.AUTO),
        padding=30, expand=True
    )