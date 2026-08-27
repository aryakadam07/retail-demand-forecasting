"""
Retail Demand Forecasting — Configuration & Environment Management
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Project Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if present
load_dotenv(BASE_DIR / ".env")

# Project Directory Paths
DATA_DIR = Path(os.getenv("RAW_DATA_DIR", BASE_DIR / "data"))
PROCESSED_DATA_DIR = Path(os.getenv("PROCESSED_DATA_DIR", BASE_DIR / "data" / "processed"))
MODELS_DIR = BASE_DIR / "models"
DBT_DIR = BASE_DIR / "dbt"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Google BigQuery Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "m5-retail-analytics")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "retail_m5_dw")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None)

# Execution Mode (Set USE_LOCAL_DUCKDB=True in .env for local testing without GCP keys)
USE_LOCAL_DUCKDB = os.getenv("USE_LOCAL_DUCKDB", "True").lower() in ("true", "1", "t", "yes")
LOCAL_DUCKDB_PATH = Path(os.getenv("LOCAL_DUCKDB_PATH", DATA_DIR / "m5_warehouse.duckdb"))

# Raw M5 Dataset Paths
CALENDAR_FILE = DATA_DIR / "calendar.csv"
SALES_TRAIN_FILE = DATA_DIR / "sales_train_validation.csv"
SELL_PRICES_FILE = DATA_DIR / "sell_prices.csv"


def validate_gcp_config() -> dict:
    """Validates GCP BigQuery credentials and environment configuration."""
    creds_path = GOOGLE_APPLICATION_CREDENTIALS
    creds_exist = False
    if creds_path:
        resolved_path = Path(creds_path)
        if not resolved_path.is_absolute():
            resolved_path = BASE_DIR / creds_path
        creds_exist = resolved_path.exists()

    return {
        "gcp_project_id": GCP_PROJECT_ID,
        "bigquery_dataset": BIGQUERY_DATASET,
        "credentials_path": creds_path,
        "credentials_valid": creds_exist,
        "use_local_fallback": USE_LOCAL_DUCKDB or not creds_exist,
    }


def get_config_summary() -> dict:
    """Returns a dictionary summarizing active project configuration."""
    summary = {
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "processed_dir": str(PROCESSED_DATA_DIR),
        "use_local_duckdb": USE_LOCAL_DUCKDB,
        "duckdb_path": str(LOCAL_DUCKDB_PATH),
    }
    summary.update(validate_gcp_config())
    return summary


if __name__ == "__main__":
    print("--- BigQuery Ingestion Configuration ---")
    for k, v in get_config_summary().items():
        print(f"  {k}: {v}")
