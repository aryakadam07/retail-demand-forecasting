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

## Common Errors & Troubleshooting

| Error | Cause | Solution |
| :--- | :--- | :--- |
| `DefaultCredentialsError` | `GOOGLE_APPLICATION_CREDENTIALS` path is incorrect or missing. | Ensure path in `.env` points to valid GCP service account JSON key file. |
| `Access Denied: 403` | Service account lacks permissions. | Grant **BigQuery Data Editor** & **BigQuery Job User** roles to the Service Account. |
| `NotFound: 404 Dataset` | Dataset does not exist. | The ingestion script auto-creates datasets, or run `CREATE SCHEMA retail_m5_dw` in GCP Console. |
| `ImportError: google-cloud-bigquery` | Package not installed. | Run `pip install google-cloud-bigquery db-dtypes pyarrow`. |
