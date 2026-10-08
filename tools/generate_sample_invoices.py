# Generates sample invoice ZIPs for Local/Test Mode
# Usage: python tools/generate_sample_invoices.py
import sys
import zipfile

from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from reportlab.pdfgen import canvas

OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent
    / "sample_data"
).resolve()

def draw_invoice(c, invoice_no, invoice_date, customer, country, line_items):
    """
    line_items: list of (category, product, qty, unit_price) tuples.
    Supports ONE or MORE rows in the line-items table (grand total is the
    sum of every row, like a real multi-product invoice).
    """
    y = 800
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(306, y, "INVOICE")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Invoice No: {invoice_no}"); y -= 20
    c.drawString(50, y, f"Invoice Date: {invoice_date}"); y -= 20
    c.drawString(50, y, f"Created Date: {invoice_date}"); y -= 20
    c.drawString(50, y, f"Bill To: {customer}"); y -= 20
    c.drawString(50, y, f"Country: {country}"); y -= 30

    headers = [
        "Category",
        "Product",
        "Quantity",
        "Unit Price",
        "Total Amount",
    ]

    table_data = [headers]

    grand_total = 0.0

    for category, product, qty, unit_price in line_items:

        line_total = qty * unit_price
        grand_total += line_total

        table_data.append(
            [
                category,
                product,
                qty,
                f"{unit_price:.2f}",
                f"{line_total:.2f}",
            ]
        )

    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    table = Table(
        table_data,
        colWidths=[100, 180, 80, 90, 100]
    )

    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    )

    table.wrapOn(c, 50, y)
    table.drawOn(c, 50, y - (20 * len(table_data)))

    y -= (20 * len(table_data)) + 30
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(
        550,
        y,
        f"Total Amount: {grand_total:,.2f}"
    )

    c.drawRightString(
        550,
        y - 20,
        "Thank you for your business."
    )

def build_zip(zip_name: str, invoices: list) -> Path:
    pdf_paths = []
    for inv in invoices:
        pdf_path = OUTPUT_DIR / f"{inv['invoice_no']}.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=(612, 792))
        draw_invoice(c, inv["invoice_no"], inv["invoice_date"], inv["customer"],
                     inv["country"], inv["line_items"])
        c.save()
        pdf_paths.append(pdf_path)

    zip_path = OUTPUT_DIR / zip_name
    with zipfile.ZipFile(zip_path, "w") as zf:
        for p in pdf_paths:
            zf.write(p, arcname=p.name)

    for p in pdf_paths:
        p.unlink()  # keep only the zip, not the loose PDFs

    print(f"Created {zip_path.name} with {len(invoices)} invoice(s)")
    return zip_path

if __name__ == "__main__":
    build_zip("Invoices_June.zip", [
        {
            "invoice_no": "INV-2026-101", "invoice_date": "2026-06-05",
            "customer": "Nile Trading Co", "country": "Spain",
            "line_items": [("Electronics", "Monitor 24-inch", 4, 950.00)],
        },
        {
            "invoice_no": "INV-2026-102", "invoice_date": "2026-06-18",
            "customer": "Delta Supplies", "country": "France",
            "line_items": [("Furniture", "Office Chair", 10, 60.00)],
        },
    ])

    build_zip("Invoices_March.zip", [
        {
            "invoice_no": "INV-2026-201", "invoice_date": "2026-03-10",
            "customer": "Red Sea Hardware", "country": "Japan",
            "line_items": [("Hardware", "Drill Machine", 6, 320.00)],
        },
        {
            "invoice_no": "INV-2026-202", "invoice_date": "2026-03-22",
            "customer": "Alex Foods Ltd", "country": "Egypt",
            "line_items": [("Food & Beverage", "Olive Oil 1L", 50, 12.50)],
        },
        {
            "invoice_no": "INV-2026-301", "invoice_date": "2026-03-15",
            "customer": "Giza Tech Solutions", "country": "Italy",
            "line_items": [
                ("Electronics", "Laptop", 3, 800.00),
                ("Electronics", "Wireless Mouse", 10, 15.00),
                ("Electronics", "Keyboard", 10, 20.00),
            ],
        },        
    ])

    build_zip("Invoices_August.zip", [
        {
            "invoice_no": "INV-2026-801","invoice_date": "2026-08-08",
            "customer": "Cairo Electronics","country": "Italy",
            "line_items": [
                ("Electronics", "Laptop", 4, 850.00),
                ("Electronics", "Wireless Mouse", 12, 18.50),
                ("Electronics", "Monitor", 5, 220.00),
            ],
        },
        {
            "invoice_no": "INV-2026-802","invoice_date": "2026-08-18",
            "customer": "Delta Office Supplies","country": "France",
            "line_items": [
                ("Office Supplies", "Printer Paper Box", 25, 8.00),
            ],
        },
        {
            "invoice_no": "INV-2026-803","invoice_date": "2026-08-25",
            "customer": "Nile Trading","country": "Spain",
            "line_items": [
                ("Electronics", "Desktop PC", 3, 1200.00),
                ("Electronics", "Keyboard", 6, 25.00),
            ],
        },
    ])

    build_zip("Invoices_September.zip", [
        {
            "invoice_no": "INV-2026-901","invoice_date": "2026-09-05",
            "customer": "Alex Distribution","country": "China",
            "line_items": [
                ("Networking", "Switch 24 Port", 4, 350.00),
                ("Networking", "Network Cable", 3, 3.50),
            ],
        },
        {
            "invoice_no": "INV-2026-902","invoice_date": "2026-09-14",
            "customer": "Tech Vision","country": "",
            "line_items": [
                ("Electronics", "Laptop", 5, 950.00),
                ("Electronics", "Docking Station", 5, 120.00),
                ("Electronics", "Monitor", 5, 180.00),
            ],
        },
        {
            "invoice_no": "INV-2026-903","invoice_date": "2026-09-27",
            "customer": "Smart Retail Group","country": "Saudi Arabia",
            "line_items": [
                ("POS Systems", "Barcode Scanner", 0, 65.00),
            ],
        },
    ])

    build_zip("Invoices_October.zip", [
        {
            "invoice_no": "INV-2026-1001","invoice_date": "2026-10-03",
            "customer": "Future Solutions","country": "India",
            "line_items": [
                ("Electronics", "Laptop", 2, 1000.00),
                ("Electronics", "Wireless Mouse", 5, 25.00),
                ("Electronics", "Mechanical Keyboard", 3, 75.00),
            ],
        },
        {
            "invoice_no": "INV-2026-1002","invoice_date": "2026-10-12",
            "customer": "Enterprise Corp","country": "Germany",
            "line_items": [
                ("Security", "IP Camera", 15, 90.00),
                ("Security", "NVR Recorder", 2, 600.00),
            ],
        },
        {
            "invoice_no": "INV-2026-1003","invoice_date": "2026-10-25",
            "customer": "Global Systems","country": "Canada",
            "line_items": [
                ("Servers", "Rack Server", 2, 4500.00),
                ("Servers", "UPS Unit", 2, 750.00),
                ("Networking", "Switch 48 Port", 4, 550.00),
            ],
        },

        {
            "invoice_no": "INV-2026-1004","invoice_date": "2026-10-28",
            "customer": "Test Customer","country": "England",
            "line_items": [
                ("Electronics", "Laptop", 1, 1000.00),
                ("Electronics", "Laptop", 1, 1000.00),
                ("Electronics", "Laptop", 5, 1000.00),
            ],
        }        
    ])