"""
Retail Demand Forecasting — Ingestion Engine Automated Tests
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import pandas as pd
from src import config
from src.data_ingestion.bigquery_ingestion import BigQueryIngestionEngine


@pytest.fixture
def ingestion_engine():
    """Initializes BigQuery Ingestion Engine with local warehouse fallback for testing."""
    return BigQueryIngestionEngine(use_local_duckdb=True)


def test_gcp_config_validation():
    """Verifies GCP configuration validation helper."""
    cfg = config.validate_gcp_config()
    assert "gcp_project_id" in cfg
    assert "bigquery_dataset" in cfg
    assert "credentials_valid" in cfg


def test_ingestion_prerequisites(ingestion_engine):
    """Verifies prerequisite checking method."""
    assert ingestion_engine.check_prerequisites() is True


def test_single_table_ingestion(ingestion_engine):
    """Verifies loading a test table into the warehouse engine."""
    sample_df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["val1", "val2", "val3"]})
    success, rows, elapsed = ingestion_engine.ingest_table(sample_df, "raw_test_table")
    
    assert success is True
    assert rows == 3
    assert elapsed >= 0.0


def test_full_ingestion_run(ingestion_engine):
    """Verifies end-to-end raw data ingestion execution."""
    summary = ingestion_engine.run_full_ingestion()
    
    assert "raw_calendar" in summary
    assert "raw_sales_train" in summary
    assert "raw_sell_prices" in summary

    assert summary["raw_calendar"]["success"] is True
    assert summary["raw_sales_train"]["success"] is True
    assert summary["raw_sell_prices"]["success"] is True

    assert summary["raw_calendar"]["rows"] > 0
    assert summary["raw_sales_train"]["rows"] > 0
    assert summary["raw_sell_prices"]["rows"] > 0
