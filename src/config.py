"""
Retail Demand Forecasting & Inventory Optimization
Configuration & Environment Management
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if present
load_dotenv(BASE_DIR / ".env")

# Project Directory Paths
DATA_DIR = Path(os.getenv("RAW_DATA_DIR", BASE_DIR / "data"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", BASE_DIR / "data" / "processed"))
MODELS_DIR = BASE_DIR / "models"
DBT_DIR = BASE_DIR / "dbt"

# Create directories if they do not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Google BigQuery Settings
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "m5-retail-analytics")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "retail_m5_dw")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None)

# Execution Mode (Fallback to local DuckDB if GCP keys are absent)
USE_LOCAL_DUCKDB = os.getenv("USE_LOCAL_DUCKDB", "True").lower() in ("true", "1", "t", "yes")
LOCAL_DUCKDB_PATH = Path(os.getenv("LOCAL_DUCKDB_PATH", DATA_DIR / "m5_warehouse.duckdb"))

# Raw M5 File Names
CALENDAR_FILE = DATA_DIR / "calendar.csv"
SALES_TRAIN_FILE = DATA_DIR / "sales_train_validation.csv"
SELL_PRICES_FILE = DATA_DIR / "sell_prices.csv"

def get_config_summary() -> dict:
    """Returns a dictionary summarizing the active project configuration."""
    return {
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "processed_dir": str(PROCESSED_DATA_DIR),
        "gcp_project": GCP_PROJECT_ID,
        "bq_dataset": BIGQUERY_DATASET,
        "use_local_duckdb": USE_LOCAL_DUCKDB,
        "duckdb_path": str(LOCAL_DUCKDB_PATH),
    }

if __name__ == "__main__":
    print("--- Retail Demand Forecasting Config ---")
    for k, v in get_config_summary().items():
        print(f"  {k}: {v}")
