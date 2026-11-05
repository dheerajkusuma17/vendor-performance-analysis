# Project Guide — Vendor Performance Analysis (in simple words)

A study guide so you can explain every part of this project.

## 1. The story
A company runs **80 wine & spirits stores** (the fictional "Bibitor, LLC" dataset, year 2024). It buys products from about **120 vendors** (suppliers such as Diageo, Jim Beam, Bacardi) and sells them to customers.

Management asked: **"Which vendors and products make us money, which ones waste our money, and where is our cash stuck?"**

The data was spread across 6 big CSV files (~15 million rows, 2 GB). The work went in 5 steps:
1. **Load:** put all 6 CSVs into one SQLite database (`src/ingestion_db.py`). It logs each step to `logs/`.
2. **Explore:** use SQL to see how the tables connect (`analysis/01_data_exploration.py`).
3. **Summarise:** one SQL query with 3 CTEs merges everything into **one row per vendor + product**, giving the `vendor_sales_summary` table (10,692 rows). Python adds KPI columns and saves it (`src/get_vendor_summary.py`).
4. **Analyse:** clean the data, draw charts, answer 8 business questions and run statistics (`analysis/02_vendor_performance_analysis.py`).
5. **Present:** a one-page Power BI dashboard for procurement.

## 2. Why this project matters
- Buying stock is a retailer's biggest cost. Choosing vendors badly means cash stuck on shelves, low margins and dependence on a few suppliers.
- It shows the **full analyst workflow**: raw data → SQL → Python → statistics → dashboard → recommendations.
- The data is big and messy (millions of rows, padded names, zero sales, a freight join bug), not a tiny clean CSV.

## 3. The data
| Table | One row means | Key columns |
|---|---|---|
| `purchases` | one product line on a purchase order | VendorNumber, Brand, PODate, ReceivingDate, PurchasePrice, Quantity, Dollars |
| `purchase_prices` | price list entry for one product | Brand, Price (selling), PurchasePrice, Volume |
| `vendor_invoice` | one invoice per vendor per PO | Quantity, Dollars, **Freight** |
| `sales` | one product sold in one store on one day | SalesQuantity, SalesDollars, SalesPrice, ExciseTax, VendorNo |
| `begin_inventory` / `end_inventory` | stock on hand on 1 Jan / 31 Dec | Store, Brand, onHand, Price |

**How they connect:** `purchases` + `purchase_prices` join on **Brand**; `sales` joins on **VendorNo + Brand**; `vendor_invoice` joins on **VendorNumber** (freight).

## 4. The questions and answers
| # | Question | Answer |
|---|---|---|
| 1 | Which brands sell little but have high margins? | 198 brands → promotion / pricing candidates |
| 2 | Top vendors and brands? | Diageo $67.99M; Jack Daniel's No 7 $7.96M |
| 3 | Who takes most purchase spend? | Diageo 16.3% (Pareto chart) |
| 4 | How dependent are we on top vendors? | Top 10 = 65.69% of purchases |
| 5 | Does bulk buying lower unit cost? | Yes: $39.07 → $10.78 per unit (~72% less) |
| 6 | Which vendors' stock moves slowly? | e.g. Alisa Carr Beverages, turnover 0.62 |
| 7 | How much cash is locked in unsold stock? | $2.71M; Diageo $722K is the largest |
| 8 | Do high and low sellers have different margins? | Yes: 31.2% vs 41.6%, t-test p < 0.001 |

## 5. Concepts to know

### SQL
- **JOIN / LEFT JOIN** – glue tables on a shared column. A LEFT JOIN keeps every purchase row even when no sales match (products never sold).
- **GROUP BY + SUM** – collapse millions of rows into totals per vendor/product.
- **CTE (`WITH name AS (...)`)** – a named temporary result that makes a long query readable. Here there are three: FreightSummary, PurchaseSummary and SalesSummary.
- **Window function (`SUM(...) OVER (PARTITION BY VendorNumber)`)** – a total per vendor without collapsing rows. Used to share freight fairly across products.
- **Summary (pre-aggregated) table** – do the heavy joins once and save the result, so dashboards load fast.

### Python
- pandas: `read_csv(chunksize=...)`, `read_sql_query`, `to_sql`, `groupby().agg()`, `quantile`, `qcut` (splits into equal-size groups: Small/Medium/Large), `cumsum`.
- `sqlite3` / SQLAlchemy – Python talking to a database.
- `logging` – the script writes what it did, and any errors, to a log file.
- **Scripts vs notebooks** – scripts (`src/`) are the repeatable pipeline. The `# %%` analysis scripts can run cell-by-cell in VS Code like a notebook.

### Business KPIs
- **Gross Profit** = Sales $ − Purchase $
- **Profit Margin %** = Gross Profit ÷ Sales $ × 100
- **Stock Turnover** = Units sold ÷ Units bought. Below 1 means stock is piling up.
- **Sales-to-Purchase Ratio** = Sales $ ÷ Purchase $
- **Unsold Inventory Value** = (Units bought − Units sold) × Purchase price: the cash sitting on shelves.
- **Pareto / 80-20 rule** – a few vendors make up most of the spend, which is a concentration risk.
- **Volume discount** – bigger orders get a lower price per unit.

### Statistics
- **describe(), histogram, boxplot** – show the spread of values and the outliers.
- **Correlation (−1 to +1)** – do two columns move together? Purchase qty vs sales qty = 0.999.
- **Percentile / quantile** – the 85th percentile is the value above 85% of rows.
- **95% confidence interval** – the range where the true average most likely lies.
- **Welch's t-test** – checks whether two group averages really differ. H0 says "no difference". If p < 0.05 we reject H0, so the difference is real and not luck. "Welch" means we don't assume both groups have equal variance.

### Power BI
- Import from a database, then build cards, donut, bar, funnel and scatter visuals, plus slicers.
- **DAX measure** – a formula such as `DIVIDE(SUM(GrossProfit), SUM(TotalSalesDollars))`. A ratio should be a measure, never a "Sum of" a percentage column.

## 6. Problems found and fixed during restoration
1. `clean_data()` used a variable that only existed inside the notebook (`vendor_sales_summary` instead of `df`), so the script crashed when run on its own. **Fixed.**
2. **Freight over-count:** vendor freight was copied onto every product row. Summed, that gave $656.8M instead of the real $1.64M. It is now allocated by share of purchase dollars. **Fixed.**
3. Profit margin was `-inf` when sales = 0. It is now blank. **Fixed.**
4. A hard-coded `C:\Users\...` path meant nobody else could run the code. It now uses relative paths. **Fixed.**
5. The 1.6 GB sales file was loaded into memory in one go. It is now read in 500K-row chunks. **Fixed.**
6. The confidence-interval test was labelled "vendors", but each row is a vendor + product. **Relabelled.**
7. **Dashboard issues (documented, not changed):**
   - The Profit Margin (%) card shows 38.7, the plain average of row margins. The true weighted margin is 30.4%; the fix is a DAX measure.
   - The "Profit Margin ($)" card is really Gross Profit.
   - The donut percentages are shares of the top 10 vendors only.

## 7. Roles this project fits
- **Data Analyst / Business Analyst** (best fit): SQL, Python, Power BI and business recommendations.
- **BI Analyst / Power BI Developer**: summary-table design, KPIs and the dashboard.
- **Supply Chain / Procurement / Inventory Analyst**: vendor dependence, bulk pricing and locked capital.
- **Financial / FP&A Analyst**: margins, profitability and working capital tied up in stock.
- **Junior Data Engineer** (secondary): ingestion pipeline, logging and the SQL aggregation layer.

## 8. Ideas to extend later
- **Lead time** per vendor = ReceivingDate − PODate (the data exists in `purchases`).
- **Price variance** = paid PurchasePrice vs list price in `purchase_prices`.
- **Payment terms** = PayDate − InvoiceDate.
- A vendor scorecard that ranks vendors on all KPIs, plus a Streamlit web dashboard and pytest tests.
