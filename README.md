# Retail Demand Forecasting & Inventory Optimization System

An end-to-end production-oriented analytics, demand forecasting, and inventory optimization platform built on Walmart's **M5 Forecasting Dataset**.

---

## 1. Project Title & Business Problem

### Business Problem
Retail supply chains suffer from inaccurate sales forecasts, leading to multi-million dollar stockout losses and excessive inventory holding costs. Traditional forecasting methods struggle with intermittent demand, pricing dynamics, store-level variations, and seasonal event impacts across diverse product categories.

### Project Objective
This system provides an end-to-end data architecture, automated ETL pipeline, dbt dimensional modeling layer, machine learning demand forecasting engines (Prophet & LightGBM), safety stock/reorder point inventory optimization, and an interactive executive Streamlit dashboard.

---

## 2. Dataset Overview

The system processes Walmart's official **M5 Forecasting Dataset** across 10 stores in 3 US states (California, Texas, Wisconsin):
- **`calendar.csv`**: Contains 1,969 days of calendar dates (`2011-01-29` to `2016-06-19`), weekly IDs (`wm_yr_wk`), event names/types (`Cultural`, `National`, `Religious`, `Sporting`), and SNAP food stamp binary entitlement indicators for CA, TX, and WI.
- **`sales_train_validation.csv`**: Contains daily sales volume across 30,490 items and 10 stores (wide format columns `d_1`...`d_1913`).
- **`sell_prices.csv`**: Contains weekly unit sell prices per item and store ($).

---

## 3. Technology Stack

- **Data Warehouse**: Google BigQuery (Production Data Warehouse) / DuckDB & SQLite (Local Offline Data Engine)
- **Data Pipeline & Preprocessing**: Python 3.13, Pandas, NumPy, PyArrow
- **Data Modeling & Transformation**: dbt (Data Build Tool - Week 2)
- **Forecasting Engines**: LightGBM, Facebook Prophet (Week 3)
- **Inventory Optimization**: Python SciPy / Custom Heuristics (Week 4)
- **Dashboard & Analytics**: Streamlit (Week 5)
- **Testing & Security**: Pytest, Python-dotenv, GCP IAM Role Delegation

---

## 4. End-to-End Week 1 Data Architecture

```
                                 [ M5 Raw Dataset ]
                                         │
                                         ▼
                      [ Google BigQuery / Local Warehouse ]
                  ┌──────────────────────┬───────────────────┐
                  │                      │                   │
           (raw_calendar)   (raw_sales_train_validation)  (raw_sell_prices)
                  │                      │                   │
                  └──────────────────────┼───────────────────┘
                                         ▼
                     [ Data Quality & Standardization Layer ]
                     - clean_calendar (ISO YYYY-MM-DD)
                     - clean_sales_train_validation (non-negative)
                     - clean_sell_prices (float validation)
                                         │
                                         ▼
                     [ Wide-to-Long Transformation Engine ]
                     - pd.melt(d_1 ... d_N -> long format)
                     - Date & Week Key Mapping
                     - Weekly Price Joining (wm_yr_wk)
                                         │
                                         ▼
                     [ Analytical Table: fact_daily_sales ]
                     - Standardized Granularity: date + item + store
                                         │
                                         ▼
                    [ Data Integrity & Hierarchy Validation ]
                    - M5 Dimension Hierarchy (1:1 checks)
                    - Temporal & Pricing Statistics
                                         │
                                         ▼
                    [ READY FOR DBT DIMENSIONAL MODELING ]
```

---

## 5. Google BigQuery Setup & Configuration

### 1. GCP Console Setup
1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create GCP Project: `m5-retail-analytics`.
3. Enable **BigQuery API** under **APIs & Services**.

### 2. Service Account & Credentials
1. Navigate to **IAM & Admin > Service Accounts**.
2. Create Service Account (e.g. `m5-ingestion-sa`).
3. Assign Roles:
   - `BigQuery Data Editor`
   - `BigQuery Job User`
4. Create & download JSON Service Account Key to `credentials/gcp-key.json`.

### 3. Local Environment Variables (`.env`)
Copy `.env.example` to `.env`:
```env
GCP_PROJECT_ID=m5-retail-analytics
BIGQUERY_DATASET=retail_m5_dw
GOOGLE_APPLICATION_CREDENTIALS=credentials/gcp-key.json
USE_LOCAL_DUCKDB=True
```
*(Note: Setting `USE_LOCAL_DUCKDB=True` or omitting GCP credentials triggers an automatic local DuckDB/SQLite fallback mode, allowing full offline execution without Cloud API keys).*

---

## 6. Warehouse Table Overview & Data Dictionary

Full documentation is available in [docs/data_dictionary.md](file:///c:/Users/HP/OneDrive/Desktop/retail-demand-forecasting/docs/data_dictionary.md).

### Summary Table List
- **Raw Layer**: `retail_m5_dw.raw_calendar`, `retail_m5_dw.raw_sales_train_validation`, `retail_m5_dw.raw_sell_prices`
- **Clean Layer**: `retail_m5_dw.clean_calendar`, `retail_m5_dw.clean_sales_train_validation`, `retail_m5_dw.clean_sell_prices`
- **Analytical Layer**: `retail_m5_dw.fact_daily_sales` (alias: `stg_sales_long`)

### Schema: `fact_daily_sales`
| Field | Data Type | Key | Description |
| :--- | :--- | :--- | :--- |
| `date` | `DATE` / `STRING` | PK | ISO-8601 sales date (`YYYY-MM-DD`) |
| `item_id` | `STRING` | PK | Product SKU identifier |
| `dept_id` | `STRING` | FK | Department identifier (`HOBBIES_1`, `FOODS_1`, etc.) |
| `cat_id` | `STRING` | FK | Category identifier (`FOODS`, `HOBBIES`, `HOUSEHOLD`) |
| `store_id` | `STRING` | PK | Store location identifier (`CA_1`, `TX_1`, etc.) |
| `state_id` | `STRING` | FK | US state abbreviation (`CA`, `TX`, `WI`) |
| `sales` | `INTEGER` | — | Daily unit sales volume ($\ge 0$) |
| `sell_price` | `FLOAT` | — | Unit sell price in USD ($) |

---

## 7. How to Run the Week 1 Pipeline

### Run Full Master ETL Pipeline
Executes Raw Ingestion $\rightarrow$ Data Quality $\rightarrow$ Transformation $\rightarrow$ Validation:

```bash
# Execute master ETL pipeline on active warehouse backend
python -m src.run_week1_pipeline

# Force local offline DuckDB/SQLite execution:
python -m src.run_week1_pipeline --local
```

### Run Individual Stage Modules
```bash
# 1. Raw Ingestion Stage
python -m src.data_ingestion.bigquery_ingestion

# 2. Data Quality & Standardization Stage
python -m src.preprocessing.run_day4_pipeline

# 3. Sales Transformation Stage
python -m src.preprocessing.run_day5_pipeline

# 4. Transformed Sales Validation Stage
python -m src.preprocessing.run_day6_pipeline
```

### Execute Test Suite
```bash
# Run all 36 automated unit & integration tests
pytest tests/ -v
```

---

## 8. Security & Secret Protection Notes

To prevent key leaks:
- The `.env` file, `credentials/` folder, `*.json` service account keys, and SQLite/DuckDB binary databases (`*.db`, `*.duckdb`) are strictly ignored via `.gitignore`.
- Credentials are fetched exclusively via environment variables (`os.getenv`). No hardcoded API keys or passwords exist anywhere in the source code.
- Automated security test (`test_security_credentials_not_tracked`) is included in the test suite.

---

## 9. Week 1 Completion Checklist

| Checklist Item | Status | Verification Note |
| :--- | :---: | :--- |
| M5 dataset available | **PASS** | `calendar.csv`, `sales_train_validation.csv`, `sell_prices.csv` mapped |
| BigQuery / Warehouse configured | **PASS** | Connection and schema creation verified |
| Raw tables created | **PASS** | `raw_calendar`, `raw_sales_train_validation`, `raw_sell_prices` loaded |
| Data quality checks implemented | **PASS** | Automated audit matrix (`data_quality.py`) active |
| Dates standardized | **PASS** | Converted to ISO `YYYY-MM-DD` |
| Sales volumes standardized | **PASS** | Non-negative integer enforcement ($sales \ge 0$) |
| Prices standardized | **PASS** | Floating-point precision ($sell\_price > 0$) |
| Wide-to-long transformation completed | **PASS** | `d_1...d_N` unpivoted to long structure |
| Product hierarchy preserved | **PASS** | 1:1 `item_id → dept_id → cat_id` verified |
| Store hierarchy preserved | **PASS** | 1:1 `store_id → state_id` verified |
| `fact_daily_sales` created | **PASS** | Primary table populated in warehouse |
| Final validation completed | **PASS** | All integrity & price checks passed (`[PASS]`) |
| Documentation completed | **PASS** | README.md & data_dictionary.md finalized |
| Credentials protected | **PASS** | Zero keys committed; `.gitignore` enforced |
| Project ready for dbt | **PASS** | Warehouse table schemas & grain ready for staging models |

---

## 10. Current Status & Week 2 Preview

### Current Status
**Week 1 (Data Architecture & ETL)** is 100% COMPLETE. The warehouse dataset `retail_m5_dw` and analytical fact table `fact_daily_sales` are fully loaded, sanitized, unpivoted, and verified.

### Ready for Week 2 (dbt Modeling)
In Week 2, we will start building our **dbt (Data Build Tool)** project:
- **Staging Models**: `stg_calendar`, `stg_sales`, `stg_prices`
- **Intermediate Models**: Aggregating weekly/monthly sales metrics and price movements
- **Mart Models**: `dim_items`, `dim_stores`, `dim_calendar`, `fct_daily_sales`
- **dbt Data Tests & Documentation**: Custom singular and generic tests
