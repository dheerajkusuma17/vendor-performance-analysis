-- vendor_sales_summary
-- One row per (vendor, product/brand, purchase price) combining purchases, prices, sales and freight.
-- Turns ~15M raw rows (2.37M purchases + 12.8M sales) into ~10.7K rows that dashboards can load instantly.

WITH FreightSummary AS (
    -- total freight paid to each vendor (vendor_invoice has one row per vendor per PO)
    SELECT
        VendorNumber,
        SUM(Freight) AS VendorFreight
    FROM vendor_invoice
    GROUP BY VendorNumber
),

PurchaseSummary AS (
    -- what we bought: quantity and dollars per vendor + brand, plus list price & bottle size
    SELECT
        p.VendorNumber,
        p.VendorName,
        p.Brand,
        p.Description,
        p.PurchasePrice,
        pp.Price  AS ActualPrice,      -- shelf (selling) price from the price list
        pp.Volume,                     -- bottle size in mL
        SUM(p.Quantity) AS TotalPurchaseQuantity,
        SUM(p.Dollars)  AS TotalPurchaseDollars
    FROM purchases p
    JOIN purchase_prices pp
        ON p.Brand = pp.Brand          -- Brand is unique in purchase_prices
    WHERE p.PurchasePrice > 0          -- drop free / zero-cost lines
    GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description,
             p.PurchasePrice, pp.Price, pp.Volume
),

SalesSummary AS (
    -- what we sold: totals per vendor + brand
    SELECT
        VendorNo,
        Brand,
        SUM(SalesQuantity) AS TotalSalesQuantity,
        SUM(SalesDollars)  AS TotalSalesDollars,
        SUM(SalesPrice)    AS TotalSalesPrice,
        SUM(ExciseTax)     AS TotalExciseTax
    FROM sales
    GROUP BY VendorNo, Brand
)

SELECT
    ps.VendorNumber,
    ps.VendorName,
    ps.Brand,
    ps.Description,
    ps.PurchasePrice,
    ps.ActualPrice,
    ps.Volume,
    ps.TotalPurchaseQuantity,
    ps.TotalPurchaseDollars,
    ss.TotalSalesQuantity,
    ss.TotalSalesDollars,
    ss.TotalSalesPrice,
    ss.TotalExciseTax,
    -- Freight is known per vendor, not per product. Share it across the vendor's products
    -- by their share of purchase dollars, so SUM(FreightCost) equals the real freight bill.
    fs.VendorFreight * ps.TotalPurchaseDollars
        / SUM(ps.TotalPurchaseDollars) OVER (PARTITION BY ps.VendorNumber) AS FreightCost
FROM PurchaseSummary ps
LEFT JOIN SalesSummary ss
    ON ps.VendorNumber = ss.VendorNo
   AND ps.Brand = ss.Brand
LEFT JOIN FreightSummary fs
    ON ps.VendorNumber = fs.VendorNumber
ORDER BY ps.TotalPurchaseDollars DESC;
