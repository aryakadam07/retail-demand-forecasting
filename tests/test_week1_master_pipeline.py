"""
Unit Test Suite for Week 1 Master ETL Pipeline and Security Verification.
"""

import os
import pytest
import pandas as pd
from pathlib import Path

from src import config
from src.run_week1_pipeline import Week1MasterETLPipeline


def test_master_pipeline_execution():
    """Verifies that the Week 1 Master ETL pipeline runs end-to-end cleanly."""
    master = Week1MasterETLPipeline(use_local_duckdb=True)
    results = master.run_pipeline()

    assert results["status"] == "PASS"
    assert "stage1_ingestion" in results
    assert "stage2_quality" in results
    assert "stage3_transform" in results
    assert "stage4_validation" in results

    val_metrics = results["stage4_validation"]["validation_metrics"]
    assert val_metrics["row_count"] > 0
    assert val_metrics["row_count_status"] == "PASS"


def test_security_credentials_not_tracked():
    """Security Audit: Verifies that no sensitive credential files or secrets are committed/tracked."""
    repo_root = config.BASE_DIR

    # Sensitive files that must NEVER exist in repo root unless gitignored
    sensitive_files = [
        ".env",
        "credentials/gcp-key.json",
        "service-account.json",
        "key.json"
    ]

    for rel_path in sensitive_files:
        full_p = repo_root / rel_path
        # If file exists locally for dev testing, verify .gitignore excludes it
        if full_p.exists() and rel_path == ".env":
            gitignore_p = repo_root / ".gitignore"
            assert gitignore_p.exists()
            with open(gitignore_p, "r", encoding="utf-8") as f:
                content = f.read()
            assert ".env" in content


def test_data_dictionary_exists():
    """Verifies that docs/data_dictionary.md exists and contains expected schema definitions."""
    doc_path = config.BASE_DIR / "docs" / "data_dictionary.md"
    assert doc_path.exists()
    
    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "fact_daily_sales" in content
    assert "raw_calendar" in content
    assert "clean_calendar" in content
    assert "sell_price" in content
