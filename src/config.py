"""Central place for project paths, so no script has a hard-coded C:\\ path."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"          # raw CSVs go here (not committed to git)
DB_PATH = PROJECT_ROOT / "inventory.db"   # SQLite database built by ingestion_db.py
LOG_DIR = PROJECT_ROOT / "logs"
SQL_DIR = PROJECT_ROOT / "sql"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

SUMMARY_TABLE = "vendor_sales_summary"

LOG_DIR.mkdir(exist_ok=True)
