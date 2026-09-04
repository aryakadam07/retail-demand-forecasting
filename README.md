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

## 4. End-to-End System Data Architecture & Lineage

```
                                 M5 Raw Data
                                      ↓
                                  BigQuery
                                      ↓
                                 dbt Sources (`clean_calendar`, `clean_sales_train_validation`, `clean_sell_prices`, `fact_daily_sales`)
                                      ↓
                                 dbt Staging Models (`stg_calendar`, `stg_sales`, `stg_sell_prices`)
                                      ↓
                                 Daily Sales Model (`int_daily_sales`)
                                      ↓
                         ┌────────────┴────────────┐
                         ↓                         ↓
                 Weekly Sales Model        Monthly Sales Model
                (`int_weekly_sales`)      (`int_monthly_sales`)
                         │                         │
                         └────────────┬────────────┘
                                      ↓
                         Analytical Marts (`fct_daily_sales`, `fct_weekly_sales`, `fct_monthly_sales`)
                                      ↓
                         Demand Forecasting Models (Prophet & LightGBM)
```

---

## 5. dbt Transformation Pipeline & Analytical Marts Layer (Week 2 Day 9)

### Purpose of dbt Transformations
dbt (Data Build Tool) transforms raw and standardized warehouse data into clean, aggregated, analytics-ready datasets inside Google BigQuery / DuckDB warehouse. It enables modular SQL engineering, version-controlled transformations, automated lineage mapping with `ref()` and `source()`, and schema data testing.

### Data Lineage & DAG Dependencies
- **`sources.yml`**: Maps raw warehouse tables (`retail_m5_dw`).
- **Staging Layer (`models/staging/`)**: Normalized staging views (`stg_calendar`, `stg_sales`, `stg_sell_prices`).
- **Intermediate Layer (`models/intermediate/`)**:
  - `int_daily_sales`: Joins long daily sales with calendar dimensions.
  - `int_weekly_sales`: Aggregates daily sales to weekly temporal levels (`wm_yr_wk`).
  - `int_monthly_sales`: Aggregates daily sales to calendar monthly levels (`year`, `month`).
- **Marts Layer (`models/marts/`)**:
  - `fct_daily_sales`, `fct_weekly_sales`, `fct_monthly_sales`: Materialized persistent tables serving clean analytical datasets for downstream forecasting models.

---

### dbt Models & Data Quality Assertions

| Layer | Model Name | Materialization | Grain / Key Columns | Applied Schema & Singular Tests |
| :--- | :--- | :--- | :--- | :--- |
| **Staging** | `stg_calendar` | `view` | `sales_date` | `not_null`, `unique` on `sales_date` & `day_id` |
| **Staging** | `stg_sales` | `view` | `series_id` | `not_null`, `unique` on `series_id`, `accepted_values` on `cat_id` & `state_id` |
| **Staging** | `stg_sell_prices` | `view` | `store_id`, `item_id`, `wm_yr_wk` | `not_null` on primary columns |
| **Intermediate** | `int_daily_sales` | `view` | `sales_date + store_id + item_id` | `not_null`, `assert_daily_sales_unique_grain`, `assert_daily_sales_non_negative` |
| **Intermediate** | `int_weekly_sales` | `view` | `wm_yr_wk + store_id + item_id` | `not_null`, `assert_weekly_sales_unique_grain`, `assert_weekly_sales_matches_daily` |
| **Intermediate** | `int_monthly_sales` | `view` | `year + month + store_id + item_id` | `not_null`, `assert_monthly_sales_unique_grain`, `assert_monthly_sales_matches_daily` |
| **Marts** | `fct_daily_sales` | `table` | `sales_date + store_id + item_id` | `not_null` on primary columns |
| **Marts** | `fct_weekly_sales` | `table` | `wm_yr_wk + store_id + item_id` | `not_null` on primary columns |
| **Marts** | `fct_monthly_sales` | `table` | `year + month + store_id + item_id` | `not_null` on primary columns |

---

### How to Run dbt Commands & Verification

```bash
# 1. Test Warehouse Connection (DuckDB / BigQuery)
dbt debug --project-dir dbt --profiles-dir dbt --target local

# 2. Parse Project SQL & YAML Metadata
dbt parse --project-dir dbt --profiles-dir dbt --target local

# 3. Build Models & Execute Data Quality Tests (61/61 PASSED)
dbt build --project-dir dbt --profiles-dir dbt --target local

# Target production BigQuery:
dbt build --project-dir dbt --profiles-dir dbt --target dev
```
