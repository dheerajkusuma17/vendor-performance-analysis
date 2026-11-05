# Interview Prep — Vendor Performance Analysis

## 30-second pitch
> "I analysed a year of purchase and sales data for an 80-store wine and spirits retailer, about 15 million rows. I loaded the raw files into SQLite with a logged Python pipeline. Then I wrote a CTE-based SQL query that condenses everything into a 10.7K-row vendor-product KPI table, and analysed it in Python. The main findings: the top 10 vendors drive two-thirds of purchase spend, bulk orders cut unit cost by about 72%, and $2.7M is tied up in unsold stock. I validated a margin gap between high- and low-selling products with a t-test and built a Power BI dashboard so procurement can see it all on one page."

## STAR story
- **Situation:** Procurement had data split across six large tables (2.4M purchase lines and 12.8M sales lines) and no single view of vendor performance.
- **Task:** Build a repeatable workflow and find which vendors and products to act on.
- **Action:**
  - Ingested the CSVs into SQLite in chunks, with logging.
  - Designed a summary table using three CTEs (freight, purchases, sales) and LEFT JOINs.
  - Standardised KPIs: gross profit, margin, turnover, sales-to-purchase ratio and unsold value.
  - Cleaned the data: removed losses and zero-sales lines, stripped padded names and fixed a freight double-count.
  - Ran EDA, a Pareto analysis, quantile segmentation, confidence intervals and a Welch's t-test.
  - Built the Power BI dashboard.
- **Result:**
  - Showed that 65.69% of spend depends on 10 vendors and found 198 high-margin brands to promote.
  - Quantified $2.71M of locked capital and showed a ~72% unit-cost advantage for bulk orders.
  - Delivered one dashboard view in place of ad-hoc queries.

## Likely questions and answers

**1. Why build a summary table instead of querying raw tables?**
The raw joins touch about 15M rows and take time on every run. Pre-aggregating once gives a 10.7K-row table that Python and Power BI load instantly. The heavy logic also lives in one place, so every report uses the same KPI definitions.

**2. Walk me through the SQL.**
- FreightSummary sums freight per vendor from `vendor_invoice`.
- PurchaseSummary joins `purchases` to `purchase_prices` on Brand and sums quantity and dollars per vendor + brand + price. It drops zero-price lines.
- SalesSummary sums sales per vendor + brand.
- The final SELECT LEFT JOINs sales and freight onto purchases, so products that never sold are kept.

**3. Why LEFT JOIN and not INNER JOIN?**
An INNER JOIN would silently drop products we bought but never sold, and those are exactly the slow movers and locked capital we want to see.

**4. What data-quality issues did you find?**
- Padded vendor names.
- Products with zero sales, which made the margin infinite.
- Negative gross profit.
- Extreme outliers in price and freight.
- **A freight double-count:** freight is only known per vendor, but it was copied onto every product row. Summed, that gave $656.8M against the real $1.64M on invoices. I fixed it by allocating freight by each product's share of purchase dollars, using a window function.

**5. Why filter out rows with GrossProfit ≤ 0 or zero sales?**
For the profitability questions those rows distort averages; margins of −∞ or −500% swamp everything else. I kept them in the summary table and looked at them separately, because they are the loss-makers and unsold stock.

**6. How did you define "bulk"?**
I used `pd.qcut` on total purchase quantity, which makes three equal-size groups (Small / Medium / Large), then compared the mean unit cost of each. A caveat: small-quantity lines also include premium products, so part of the gap is product mix rather than discounts alone.

**7. Explain the confidence interval and t-test.**
- I took the top 25% and bottom 25% of vendor-product lines by sales.
- The 95% CI for low sellers' margin is 40.5–42.6%; for top sellers it is 30.7–31.6%. The intervals don't overlap.
- Welch's t-test (no equal-variance assumption) gave t = −17.67 and p < 0.001, so we reject "no difference".
- In business terms, high-volume products run on thinner margins.

**8. What is stock turnover here, and what does > 1 mean?**
Units sold ÷ units bought in the year. Above 1 means we sold more than we bought, so the extra came from opening stock. Below 1 means stock is piling up.

**9. What's in the dashboard?**
- KPI cards: sales, purchases, gross profit, margin and unsold capital.
- A purchase-contribution donut and top-10 vendor and brand bars.
- A low-turnover vendor funnel and a target-brand scatter.

**10. Any mistakes you'd fix in the dashboard?**
The margin card sums row-level percentages. It should be a DAX measure: `DIVIDE(SUM(GrossProfit), SUM(TotalSalesDollars))`, which gives about 30.4%.

**11. What recommendations did you make?**
- Diversify away from the top 10 vendors.
- Promote the 198 high-margin, low-volume brands.
- Clear slow stock to release the $2.71M.
- Buy in bulk only for products that turn over quickly.
- Review pricing and costs on high-volume lines.

**12. How would you scale this?**
- Move SQLite to Postgres or a cloud warehouse and schedule the pipeline (cron or Airflow).
- Add tests and data validation.
- Connect Power BI to the database with scheduled refresh.

**13. What would you add next?**
- Vendor lead time (receiving date − PO date).
- Price variance against the list price and payment-term analysis.
- A combined vendor scorecard.

**14. Why SQLite?**
It's file-based, needs no server and handles a few GB comfortably for analysis. The same SQL ports to Postgres or SQL Server.

**15. What was the hardest part?**
- Working out the table grain: invoices are per vendor and PO, sales per store, brand and day, and the price list per brand. That decides how to join without duplicating numbers.
- The freight bug is a concrete example of getting it wrong first and then fixing it.

## Do not claim
Lead-time, defect-rate or cost-variance tracking and "25% faster reports" are **not** in this project. Mention them only as next steps.
