# Retail Demand Forecasting & Inventory Optimization System

An end-to-end production-oriented analytics and forecasting engine built on Walmart's **M5 Forecasting Dataset**.

---

## Project Architecture

```
retail-demand-forecasting/
├── data/
│   ├── README.md
│   └── processed/
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── tests/
│   └── dbt_project.yml
├── src/
│   ├── config.py
│   ├── data_ingestion/
│   │   ├── config.py
│   │   ├── bq_client.py
│   │   ├── m5_loader.py
│   │   ├── load_calendar.py
│   │   ├── load_sales.py
│   │   ├── load_prices.py
│   │   └── bigquery_ingestion.py
│   ├── preprocessing/
│   │   └── clean_and_melt.py
│   ├── features/
│   ├── forecasting/
│   └── inventory/
├── models/
├── dashboard/
├── notebooks/
│   └── 01_exploratory_data_analysis.py
├── tests/
│   ├── test_phase1.py
│   └── test_ingestion.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Google BigQuery Setup & Configuration Guide

### 1. GCP Console Project Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new GCP Project (e.g. `m5-retail-analytics`).
3. Ensure BigQuery API is enabled under **APIs & Services > Enabled APIs**.

### 2. Service Account & Credentials
1. Navigate to **IAM & Admin > Service Accounts**.
2. Click **Create Service Account** (e.g., `m5-ingestion-sa`).
3. Grant the following IAM Roles:
   - **BigQuery Data Editor**
   - **BigQuery Job User**
4. Click on the created Service Account > **Keys** > **Add Key** > **Create new key (JSON)**.
5. Save the JSON key file safely on your machine (e.g., `credentials/gcp-key.json`).

### 3. Local `.env` Configuration
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Edit `.env` and fill in your GCP parameters:
```env
GCP_PROJECT_ID=your-gcp-project-id
BIGQUERY_DATASET=retail_m5_dw
GOOGLE_APPLICATION_CREDENTIALS=credentials/gcp-key.json
USE_LOCAL_DUCKDB=False
```
*(Note: If `GOOGLE_APPLICATION_CREDENTIALS` is omitted or `USE_LOCAL_DUCKDB=True` is set, the ingestion script automatically falls back to local storage).*

---

## Running Raw M5 Data Ingestion to Google BigQuery

### Individual Ingestion Scripts
You can load each dataset independently using its dedicated ingestion module:

```bash
# 1. Load raw calendar.csv -> BigQuery table raw_calendar
python -m src.data_ingestion.load_calendar

# 2. Load raw sales_train_validation.csv -> BigQuery table raw_sales_train_validation
python -m src.data_ingestion.load_sales

# 3. Load raw sell_prices.csv -> BigQuery table raw_sell_prices
python -m src.data_ingestion.load_prices
```

### Full Data Ingestion Pipeline
To execute end-to-end ingestion for all 3 datasets in a single command:
```bash
python -m src.data_ingestion.bigquery_ingestion
```

To force local offline fallback execution:
```bash
python -m src.data_ingestion.bigquery_ingestion --local
```

### Run Automated Ingestion Test Suite
```bash
pytest tests/test_ingestion.py -v
```

---

## Verifying BigQuery Tables

### 1. BigQuery Console Verification
1. Open [BigQuery Console](https://console.cloud.google.com/bigquery).
2. Expand your Project ID (`m5-retail-analytics`).
3. Expand Dataset (`retail_m5_dw`).
4. Verify the 3 raw tables exist:
   - `raw_calendar`
   - `raw_sales_train_validation`
   - `raw_sell_prices`

### 2. Run Verification Query in BigQuery SQL Workspace
```sql
SELECT 'raw_calendar' AS table_name, COUNT(*) AS row_count FROM `retail_m5_dw.raw_calendar`
UNION ALL
SELECT 'raw_sales_train_validation' AS table_name, COUNT(*) AS row_count FROM `retail_m5_dw.raw_sales_train_validation`
UNION ALL
SELECT 'raw_sell_prices' AS table_name, COUNT(*) AS row_count FROM `retail_m5_dw.raw_sell_prices`;
```

---

## Week 1 Day 4: Data Quality Checks & Data Standardization

### Architecture
Day 4 establishes the **Data Quality & Audit Layer** between raw warehouse tables and downstream dbt modeling:

```
Raw M5 Data  -->  BigQuery Raw Tables  -->  Data Quality Checks  -->  Clean/Validated Tables
                 (raw_calendar)            (data_quality.py)          (clean_calendar)
                 (raw_sales_train)                                   (clean_sales_train_validation)
                 (raw_sell_prices)                                   (clean_sell_prices)
```

### Data Quality Checks & Standardization Matrix

1. **Calendar Validation (`src/preprocessing/clean_calendar.py`)**:
   - Standardizes `date` to ISO format `YYYY-MM-DD`.
   - Validates continuity, year range (2011–2016), month (1–12), and weekday bounds.
   - Audits event coverage (`event_name_1`, `event_type_1`).
   - Generates `clean_calendar` table in BigQuery.

2. **Sales Validation (`src/preprocessing/clean_sales.py`)**:
   - Preserves wide format (`id`, `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id`, `d_1..d_N`).
   - Ensures non-negative numeric daily sales volumes.
   - Audits extreme sales outliers (>500 units/day) without auto-deletion.
   - Generates `clean_sales_train_validation` (and alias `clean_sales`) table in BigQuery.

3. **Pricing Validation (`src/preprocessing/clean_prices.py`)**:
   - Validates composite key `store_id` + `item_id` + `wm_yr_wk`.
   - Ensures numeric float type for `sell_price`.
   - Flags missing or zero prices (preserves raw price distribution without fabricating fake prices).
   - Generates `clean_sell_prices` table in BigQuery.

### Running Day 4 Pipeline & Tests

```bash
# 1. Execute Day 4 Data Quality & Standardization Pipeline
python -m src.preprocessing.run_day4_pipeline

# Force local DuckDB/SQLite offline execution:
python -m src.preprocessing.run_day4_pipeline --local

# 2. Run Automated Quality & Standardization Test Suite
pytest tests/test_data_quality.py -v
```

### Sample Data Quality Report Output

```text
==================================================
  DATA QUALITY REPORT: CALENDAR
==================================================
  Rows            : 1,969
  Columns         : 14
  Duplicate Rows  : 0
  Overall Status  : PASS
--------------------------------------------------
  CHECKS:
    [PASS]  Missing Dates: No missing date values
    [PASS]  Duplicate Dates: No duplicate dates found
    [PASS]  Valid Date Format: All dates follow ISO format YYYY-MM-DD
    [PASS]  Missing Weekday Values: No missing weekday values
    [PASS]  Valid Year/Week Ranges: Year and week values within valid bounds
    [PASS]  Unexpected Event Types: Event types match official M5 domain categories
    [PASS]  Event Coverage: Identified 162 holiday/special event occurrences
==================================================
```

---

## Common Errors & Troubleshooting

| Error | Cause | Solution |
| :--- | :--- | :--- |
| `DefaultCredentialsError` | `GOOGLE_APPLICATION_CREDENTIALS` path is incorrect or missing. | Ensure path in `.env` points to valid GCP service account JSON key file. |
| `Access Denied: 403` | Service account lacks permissions. | Grant **BigQuery Data Editor** & **BigQuery Job User** roles to the Service Account. |
| `NotFound: 404 Dataset` | Dataset does not exist. | The ingestion script auto-creates datasets, or run `CREATE SCHEMA retail_m5_dw` in GCP Console. |
| `ImportError: google-cloud-bigquery` | Package not installed. | Run `pip install google-cloud-bigquery db-dtypes pyarrow`. |

