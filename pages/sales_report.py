import flet as ft
from database import (
    get_filtered_sales_report,
    get_invoice_items
)


def sales_report_page(page):

    # =========================
    # SHOW INVOICE DETAILS
    # =========================

    def show_invoice_details(order_id):

        items = get_invoice_items(order_id)

        if not items:
            return

        product_rows = []
        grand_total = 0

        for i, item in enumerate(items):

            total = float(item["total"] or 0)
            grand_total += total

            product_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(i + 1))),
                        ft.DataCell(ft.Text(str(item["die_no"]))),
                        ft.DataCell(ft.Text(str(item["profile_name"]))),
                        ft.DataCell(ft.Text(str(item["color"]))),
                        ft.DataCell(ft.Text(str(item["spec"]))),
                        ft.DataCell(ft.Text(str(item["quantity"]))),
                        ft.DataCell(
                            ft.Text(f"{float(item['price']):,.2f}")
                        ),
                        ft.DataCell(
                            ft.Text(f"{total:,.2f}")
                        ),
                    ]
                )
            )

        invoice_dialog = ft.AlertDialog(
            modal=True,

            title=ft.Text(
                f"Invoice #{order_id}",
                weight="bold"
            ),

            content=ft.Container(
                width=950,

                content=ft.Column([

                    ft.DataTable(

                        border=ft.border.all(1, "black12"),

                        columns=[
                            ft.DataColumn(ft.Text("SL")),
                            ft.DataColumn(ft.Text("Die No")),
                            ft.DataColumn(ft.Text("Profile")),
                            ft.DataColumn(ft.Text("Color")),
                            ft.DataColumn(ft.Text("Spec")),
                            ft.DataColumn(ft.Text("Qty")),
                            ft.DataColumn(ft.Text("Price")),
                            ft.DataColumn(ft.Text("Total")),
                        ],

                        rows=product_rows
                    ),

                    ft.Divider(),

                    ft.Row(
                        [
                            ft.Text(
                                f"Grand Total: {grand_total:,.2f} TK",
                                size=18,
                                weight="bold",
                                color="green"
                            )
                        ],
                        alignment="end"
                    )

                ],
                scroll=ft.ScrollMode.AUTO)

            ),

            actions=[
                ft.TextButton(
                    "Close",
                    on_click=lambda _: page.close(invoice_dialog)
                )
            ]
        )

        page.open(invoice_dialog)

    # =========================
    # LOAD REPORT DATA
    # =========================
    all_sales_data = [] # ডাটাবেস থেকে আসা সব ডাটা এখানে জমা থাকবে

    def load_report_data(filter_type="today"):

        try:

            data = get_filtered_sales_report(filter_type)

            report_table.rows.clear()

            t_sales = 0
            t_due = 0

            for index, row in enumerate(data):

                try:
                    r = dict(row)

                    # আপনার ডাটাবেজ কুয়েরির কলাম নামের সাথে মিলিয়ে পরিবর্তন:
                    net_total = float(r.get("net_total") or 0)
                    paid = float(r.get("paid_amount") or 0)
                    due = float(r.get("due_amount") or 0)

                    t_sales += net_total
                    t_due += due

                    report_table.rows.append(

                        ft.DataRow(

                            on_select_changed=lambda e,
                            oid=r.get("order_id"):
                            show_invoice_details(oid),

                            cells=[

                                ft.DataCell(
                                    ft.Text(str(index + 1))
                                ),

                                ft.DataCell(
                                    ft.Text(
                                        f"#{r.get('order_id')}",
                                        weight="bold"
                                    )
                                ),

                                ft.DataCell(
                                    ft.Text(
                                        f"{r.get('sale_date')} | {r.get('sale_time')}"
                                    )
                                ),

                                ft.DataCell(
                                    ft.Text(
                                        str(
                                            r.get("customer_name")
                                            or "Cash"
                                        )
                                    )
                                ),

                                ft.DataCell(
                                    ft.Text(
                                        str(
                                            r.get("customer_phone")
                                            or "N/A"
                                        )
                                    )
                                ),

                                ft.DataCell(
                                    ft.Text(
                                        f"{net_total:,.2f}",
                                        weight="bold"
                                    )
                                ),

                                ft.DataCell(
                                    ft.Text(
                                        f"{paid:,.2f}",
                                        color="green"
                                    )
                                ),

                                ft.DataCell(
                                    ft.Text(
                                        f"{due:,.2f}",
                                        color="red"
                                    )
                                ),
                            ]
                        )
                    )

                except Exception as row_err:
                    print(f"Row Error: {row_err}")

            sales_card_text.value = f"{t_sales:,.2f} TK"
            due_card_text.value = f"{t_due:,.2f} TK"

            page.update()

        except Exception as e:
            print(f"Loading Error: {e}")

    # =========================
    # TABLE
    # =========================

    report_table = ft.DataTable(

        show_checkbox_column=False,

        border=ft.border.all(1, "black12"),

        columns=[
            ft.DataColumn(ft.Text("SN")),
            ft.DataColumn(ft.Text("Invoice")),
            ft.DataColumn(ft.Text("Date & Time")),
            ft.DataColumn(ft.Text("Customer")),
            ft.DataColumn(ft.Text("Phone")),
            ft.DataColumn(ft.Text("Net")),
            ft.DataColumn(ft.Text("Paid")),
            ft.DataColumn(ft.Text("Due")),
        ]
    )

    # =========================
    # SUMMARY
    # =========================

    sales_card_text = ft.Text(
        "0 TK",
        size=25,
        weight="bold",
        color="green"
    )

    due_card_text = ft.Text(
        "0 TK",
        size=25,
        weight="bold",
        color="red"
    )

    # INITIAL LOAD
    load_report_data()

    # =========================
    # RETURN UI
    # =========================

    return ft.Container(

        padding=20,
        expand=True,

        content=ft.Column([

            ft.Row([
                ft.Text(
                    "Sales Report",
                    size=25,
                    weight="bold"
                )
            ]),

            ft.Row([

                ft.Container(
                    expand=1,
                    bgcolor="#1a237e",
                    padding=15,
                    border_radius=10,

                    content=ft.Column([
                        ft.Text("Sales", color="white"),
                        sales_card_text
                    ])
                ),

                ft.Container(
                    expand=1,
                    bgcolor="#1a237e",
                    padding=15,
                    border_radius=10,

                    content=ft.Column([
                        ft.Text("Due", color="white"),
                        due_card_text
                    ])
                ),

            ]),

            ft.Divider(),

            ft.Container(
                expand=True,

                content=ft.ListView([
                    ft.Row(
                        [report_table],
                        scroll="always"
                    )
                ])
            )

        ])
    )