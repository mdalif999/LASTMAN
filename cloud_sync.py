"""
cloud_sync.py
─────────────────────────────────────────────────────────────
প্রথমবার app চালু হলে (local DB খালি থাকলে), Supabase থেকে
সব ডেটা (inventory, sales, audit_logs) নামিয়ে local SQLite এ
সেভ করে রাখে — যাতে app পরে অফলাইনেও কাজ করে।

main.py তে এভাবে ব্যবহার করুন:

    from cloud_sync import first_run_download
    first_run_download(supabase)   # app শুরু হওয়ার আগে, init_db() এর পরে

এটা চালানোর পর local DB তে data থাকবে, এবং inventory page
50 টা করে (pagination) load করবে।
─────────────────────────────────────────────────────────────
"""

from database import (
    is_inventory_empty,
    bulk_insert_inventory_from_cloud,
    bulk_insert_sales_from_cloud,
    bulk_insert_audit_logs_from_cloud,
)

FETCH_BATCH = 1000  # Supabase থেকে একসাথে কত row আনবে (Supabase max ~1000)


def _fetch_all_rows(supabase, table_name):
    """একটা টেবিলের সব row Supabase থেকে batch করে নামায়।"""
    all_rows = []
    start = 0
    while True:
        try:
            res = (
                supabase.table(table_name)
                .select("*")
                .range(start, start + FETCH_BATCH - 1)
                .execute()
            )
            rows = res.data or []
        except Exception as e:
            print(f"cloud_sync: error fetching {table_name}: {e}")
            break

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < FETCH_BATCH:
            break  # last page
        start += FETCH_BATCH

    return all_rows


def first_run_download(supabase, force=False):
    """
    Local inventory টেবিল খালি থাকলে (প্রথমবার app চালু হলে),
    Supabase থেকে inventory, sales, audit_logs নামিয়ে local এ insert করে।

    force=True দিলে — খালি না থাকলেও জোর করে আবার download করবে
    (যেমন: Settings পেজে 'Re-download from Cloud' বাটনের জন্য)।

    Returns: dict সহ কতগুলো row নামানো হলো।
    """
    if not force and not is_inventory_empty():
        print("cloud_sync: local DB already has data — skipping first-run download.")
        return {"inventory": 0, "sales": 0, "audit_logs": 0, "skipped": True}

    print("cloud_sync: local DB is empty. Downloading data from Supabase...")

    summary = {"inventory": 0, "sales": 0, "audit_logs": 0, "skipped": False}

    try:
        inv_rows = _fetch_all_rows(supabase, "inventory")
        summary["inventory"] = bulk_insert_inventory_from_cloud(inv_rows)
        print(f"cloud_sync: imported {summary['inventory']} inventory items.")
    except Exception as e:
        print(f"cloud_sync: inventory download failed: {e}")

    try:
        sales_rows = _fetch_all_rows(supabase, "sales")
        summary["sales"] = bulk_insert_sales_from_cloud(sales_rows)
        print(f"cloud_sync: imported {summary['sales']} sales records.")
    except Exception as e:
        print(f"cloud_sync: sales download failed: {e}")

    try:
        log_rows = _fetch_all_rows(supabase, "audit_logs")
        summary["audit_logs"] = bulk_insert_audit_logs_from_cloud(log_rows)
        print(f"cloud_sync: imported {summary['audit_logs']} audit logs.")
    except Exception as e:
        print(f"cloud_sync: audit_logs download failed: {e}")

    print("cloud_sync: first-run download complete.")
    return summary