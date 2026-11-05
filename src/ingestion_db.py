"""Step 1 of the pipeline: load every raw CSV in data/ into the SQLite database.

Each CSV becomes one table with the same name (purchases.csv -> purchases).
Large files (sales.csv is ~1.6 GB) are read in chunks so memory use stays low.

Usage:
    python src/ingestion_db.py                  # uses data/ and inventory.db
    python src/ingestion_db.py --data-dir path/to/csvs --db path/to/file.db
"""
import argparse
import logging
import sqlite3
import time
from pathlib import Path

import pandas as pd

from config import DATA_DIR, DB_PATH, LOG_DIR

CHUNK_SIZE = 500_000

logging.basicConfig(
    filename=LOG_DIR / "ingestion_db.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)


def ingest_db(df: pd.DataFrame, table_name: str, conn, if_exists: str = "replace") -> None:
    """Write a DataFrame into a database table."""
    df.to_sql(table_name, con=conn, if_exists=if_exists, index=False)


def ingest_csv(csv_path: Path, conn) -> int:
    """Load one CSV into a table of the same name, chunk by chunk. Returns rows loaded."""
    table = csv_path.stem
    rows = 0
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=CHUNK_SIZE)):
        ingest_db(chunk, table, conn, if_exists="replace" if i == 0 else "append")
        rows += len(chunk)
    return rows


def load_raw_data(data_dir: Path = DATA_DIR, db_path: Path = DB_PATH) -> None:
    """Ingest every CSV in data_dir into db_path and log timings."""
    start = time.time()
    csv_files = sorted(Path(data_dir).glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}. See data/README.md.")

    with sqlite3.connect(db_path) as conn:
        for csv_path in csv_files:
            t0 = time.time()
            logging.info(f"Ingesting {csv_path.name} ...")
            rows = ingest_csv(csv_path, conn)
            logging.info(f"Loaded {rows:,} rows into '{csv_path.stem}' in {time.time() - t0:.1f}s")
            print(f"{csv_path.name:<22} {rows:>12,} rows")

    total_min = (time.time() - start) / 60
    logging.info(f"--------------- Ingestion complete in {total_min:.2f} minutes ---------------")
    print(f"Done in {total_min:.2f} minutes -> {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load raw CSVs into SQLite.")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    load_raw_data(args.data_dir, args.db)
