"""
Retail Demand Forecasting — Data Ingestion Module Configuration
Re-exports and defines dataset table names and ingestion parameters.
"""

from src import config

# Data Directories & Files
DATA_DIR = config.DATA_DIR
CALENDAR_FILE = config.CALENDAR_FILE
SALES_TRAIN_FILE = config.SALES_TRAIN_FILE
SELL_PRICES_FILE = config.SELL_PRICES_FILE

# Google BigQuery Configuration
GCP_PROJECT_ID = config.GCP_PROJECT_ID
BIGQUERY_DATASET = config.BIGQUERY_DATASET
GOOGLE_APPLICATION_CREDENTIALS = config.GOOGLE_APPLICATION_CREDENTIALS
USE_LOCAL_DUCKDB = config.USE_LOCAL_DUCKDB

# Raw Table Names in BigQuery
RAW_CALENDAR_TABLE = "raw_calendar"
RAW_SALES_TABLE = "raw_sales_train_validation"
RAW_PRICES_TABLE = "raw_sell_prices"

# Data Types / Dtypes for safe CSV loading
CALENDAR_DTYPES = {
    "date": "str",
    "wm_yr_wk": "int64",
    "weekday": "str",
    "wday": "int64",
    "month": "int64",
    "year": "int64",
    "d": "str",
    "event_name_1": "str",
    "event_type_1": "str",
    "event_name_2": "str",
    "event_type_2": "str",
    "snap_CA": "int64",
    "snap_TX": "int64",
    "snap_WI": "int64",
}

SALES_BASE_DTYPES = {
    "id": "str",
    "item_id": "str",
    "dept_id": "str",
    "cat_id": "str",
    "store_id": "str",
    "state_id": "str",
}

PRICES_DTYPES = {
    "store_id": "str",
    "item_id": "str",
    "wm_yr_wk": "int64",
    "sell_price": "float64",
}
