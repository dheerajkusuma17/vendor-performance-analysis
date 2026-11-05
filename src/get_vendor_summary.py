"""Step 2 of the pipeline: build the vendor_sales_summary table.

1. Run sql/vendor_sales_summary.sql (joins purchases, prices, sales, freight).
2. Clean it (types, missing values, stray spaces).
3. Add KPI columns (gross profit, margin, stock turnover, sales-to-purchase ratio).
4. Save it back into the database for analysis and Power BI.

Usage:
    python src/get_vendor_summary.py
"""
import logging
import sqlite3
import time

import numpy as np
import pandas as pd

from config import DB_PATH, LOG_DIR, SQL_DIR, SUMMARY_TABLE
from ingestion_db import ingest_db

logging.basicConfig(
    filename=LOG_DIR / "get_vendor_summary.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)


def create_vendor_summary(conn) -> pd.DataFrame:
    """Merge the raw tables into one vendor + brand level summary."""
    query = (SQL_DIR / "vendor_sales_summary.sql").read_text(encoding="utf-8")
    return pd.read_sql_query(query, conn)


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide, but return NaN (not inf) where the denominator is 0."""
    return numerator / denominator.replace(0, np.nan)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Fix types, fill gaps and add KPI columns."""
    df = df.copy()
    df["Volume"] = df["Volume"].astype("float")

    # products bought but never sold have no sales row -> treat as 0 sales
    df = df.fillna(0)

    # vendor names in the raw files are padded with spaces
    df["VendorName"] = df["VendorName"].str.strip()
    df["Description"] = df["Description"].str.strip()

    # KPIs
    # round to cents so float noise (e.g. 2.8e-14) doesn't turn break-even rows into "profit"
    df["GrossProfit"] = (df["TotalSalesDollars"] - df["TotalPurchaseDollars"]).round(2)
    df["ProfitMargin"] = safe_divide(df["GrossProfit"], df["TotalSalesDollars"]) * 100
    df["StockTurnover"] = safe_divide(df["TotalSalesQuantity"], df["TotalPurchaseQuantity"])
    df["SalesToPurchaseRatio"] = safe_divide(df["TotalSalesDollars"], df["TotalPurchaseDollars"])
    return df


def main() -> None:
    start = time.time()
    with sqlite3.connect(DB_PATH) as conn:
        logging.info("Creating vendor summary table ...")
        summary_df = create_vendor_summary(conn)

        logging.info("Cleaning data ...")
        clean_df = clean_data(summary_df)

        logging.info("Writing table to database ...")
        ingest_db(clean_df, SUMMARY_TABLE, conn)

    msg = f"{SUMMARY_TABLE}: {len(clean_df):,} rows, {clean_df.shape[1]} columns ({time.time() - start:.1f}s)"
    logging.info(msg)
    print(msg)


if __name__ == "__main__":
    main()
