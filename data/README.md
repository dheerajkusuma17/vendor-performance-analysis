# Data

The raw CSVs (~2 GB) and the SQLite database (~2.2 GB) are **not stored in this repository** — GitHub rejects files over 100 MB.

## Source
Bibitor, LLC inventory case-study dataset: a fictional chain of 80 wine & spirits stores, one year of transactions (dated 2024 in this version).

## Files expected in this folder
| File | Rows | Size | Description |
|---|---|---|---|
| `begin_inventory.csv` | 206,529 | 17 MB | Stock on hand per store & brand on 2024-01-01 |
| `end_inventory.csv` | 224,489 | 19 MB | Stock on hand per store & brand on 2024-12-31 |
| `purchases.csv` | 2,372,474 | 362 MB | Purchase-order lines: vendor, brand, PO/receiving/invoice/pay dates, price, quantity, dollars |
| `purchase_prices.csv` | 12,261 | 1 MB | Price list per brand: selling price, purchase price, volume, vendor |
| `sales.csv` | 12,825,363 | 1.6 GB | Daily sales per store & brand: quantity, dollars, price, excise tax, vendor |
| `vendor_invoice.csv` | 5,543 | 0.5 MB | One invoice per vendor per PO: quantity, dollars, freight |

## Steps
1. Download the six CSVs and place them in this `data/` folder with the names above.
2. From the project root run `python src/ingestion_db.py` → creates `inventory.db` (~10 minutes).
3. Run `python src/get_vendor_summary.py` → creates the `vendor_sales_summary` table.
