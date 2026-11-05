# %% [markdown]
# # 01 · Data Exploration — understanding the raw tables
#
# **Goal:** look at how the data sits in `inventory.db` and decide whether we need an
# aggregated table that helps with:
# 1. Vendor selection for profitability
# 2. Product pricing optimization
#
# Run cell-by-cell in VS Code (click **Run Cell** above each `# %%`) or the whole file with
# `python analysis/01_data_exploration.py`. Requires `inventory.db` (see `data/README.md`).

# %%
import sqlite3
import sys
from pathlib import Path

import pandas as pd
from IPython.display import display

# works from the repo root, from analysis/, or from notebooks/
ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
sys.path.append(str(ROOT / "src"))
from get_vendor_summary import clean_data, create_vendor_summary  # noqa: E402

conn = sqlite3.connect(ROOT / "inventory.db")

# %% [markdown]
# ## Which tables are in the database and how big are they?

# %%
tables = pd.read_sql_query(
    "SELECT name FROM sqlite_master WHERE type='table' AND name != 'vendor_sales_summary'", conn
)
for table in tables["name"]:
    count = pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", conn)["n"].iloc[0]
    print("-" * 40, table, f"({count:,} rows)", "-" * 40)
    display(pd.read_sql(f"SELECT * FROM {table} LIMIT 5", conn))

# %% [markdown]
# ## Drill into one vendor (4466 — American Vintage Beverage) to see how tables relate

# %%
purchases = pd.read_sql_query("SELECT * FROM purchases WHERE VendorNumber = 4466", conn)
purchase_prices = pd.read_sql_query("SELECT * FROM purchase_prices WHERE VendorNumber = 4466", conn)
vendor_invoice = pd.read_sql_query("SELECT * FROM vendor_invoice WHERE VendorNumber = 4466", conn)
sales = pd.read_sql_query("SELECT * FROM sales WHERE VendorNo = 4466", conn)

print("purchases:", purchases.shape, "| purchase_prices:", purchase_prices.shape,
      "| vendor_invoice:", vendor_invoice.shape, "| sales:", sales.shape)

# %%
display(purchases.groupby(["Brand", "PurchasePrice"])[["Quantity", "Dollars"]].sum())

# %%
display(sales.groupby("Brand")[["SalesDollars", "SalesPrice", "SalesQuantity"]].sum())

# %% [markdown]
# ### What we learned
# 1. **purchases** — actual purchase lines: PO date, receiving date, brand bought from each vendor,
#    dollars paid and quantity.
# 2. **purchase_prices** — the price list: selling price and purchase price per product
#    (one row per brand).
# 3. **vendor_invoice** — one row per vendor per PO; it summarises purchases (quantity, dollars)
#    and adds **freight**.
# 4. **sales** — every sale: brand, quantity sold, selling price, revenue, excise tax.
#
# The numbers we need are spread across four tables, so we build **one summary table** with:
# purchases by vendor, sales, freight per vendor and actual product prices.

# %% [markdown]
# ## Building blocks of the summary query

# %%
freight_summary = pd.read_sql_query(
    """SELECT VendorNumber, SUM(Freight) AS FreightCost
       FROM vendor_invoice
       GROUP BY VendorNumber""",
    conn,
)
display(freight_summary.head())

# %%
purchase_summary = pd.read_sql_query(
    """SELECT p.VendorNumber, p.VendorName, p.Brand, p.PurchasePrice,
              pp.Volume, pp.Price AS ActualPrice,
              SUM(p.Quantity) AS TotalPurchaseQuantity,
              SUM(p.Dollars)  AS TotalPurchaseDollars
       FROM purchases p
       JOIN purchase_prices pp ON p.Brand = pp.Brand
       WHERE p.PurchasePrice > 0
       GROUP BY p.VendorNumber, p.VendorName, p.Brand
       ORDER BY TotalPurchaseDollars DESC""",
    conn,
)
display(purchase_summary.head())

# %%
sales_summary = pd.read_sql_query(
    """SELECT VendorNo, Brand,
              SUM(SalesDollars)  AS TotalSalesDollars,
              SUM(SalesPrice)    AS TotalSalesPrice,
              SUM(SalesQuantity) AS TotalSalesQuantity,
              SUM(ExciseTax)     AS TotalExciseTax
       FROM sales
       GROUP BY VendorNo, Brand
       ORDER BY TotalSalesDollars DESC""",
    conn,
)
display(sales_summary.head())

# %% [markdown]
# ## The full summary query
# The three pieces above are combined with CTEs in `sql/vendor_sales_summary.sql`.
#
# **Freight fix:** freight is only known per vendor. The first version copied each vendor's
# total freight onto every one of its products, so summing freight over-counted it ~400×.
# The query now splits a vendor's freight across its products by share of purchase dollars.

# %%
vendor_sales_summary = create_vendor_summary(conn)
print(vendor_sales_summary.shape)
display(vendor_sales_summary.head())

# %%
true_freight = pd.read_sql("SELECT SUM(Freight) AS f FROM vendor_invoice", conn)["f"].iloc[0]
print(f"Freight in summary: {vendor_sales_summary['FreightCost'].sum():,.2f} | "
      f"freight on invoices: {true_freight:,.2f}")

# %% [markdown]
# ## Data quality checks before cleaning

# %%
display(vendor_sales_summary.dtypes)
display(vendor_sales_summary.isnull().sum())

# %%
# vendor names in the raw files carry trailing spaces
print(vendor_sales_summary["VendorName"].unique()[:10])

# %% [markdown]
# ## Cleaning + new KPI columns
# `clean_data()` in `src/get_vendor_summary.py`:
# - `Volume` → float; missing sales (products never sold) → 0; strip spaces from names
# - **GrossProfit** = sales $ − purchase $
# - **ProfitMargin %** = gross profit ÷ sales $ × 100 (blank when sales are 0)
# - **StockTurnover** = units sold ÷ units bought
# - **SalesToPurchaseRatio** = sales $ ÷ purchase $

# %%
clean_df = clean_data(vendor_sales_summary)
display(clean_df.head())

# %% [markdown]
# ## Why save this as a table?
# - The query joins ~2.4M purchase rows and ~12.8M sales rows — expensive to repeat.
# - Saving the result (`python src/get_vendor_summary.py`) gives a ~10.7K-row table that the
#   analysis and the Power BI dashboard can load instantly.

# %%
display(pd.read_sql("PRAGMA table_info(vendor_sales_summary);", conn))
conn.close()
