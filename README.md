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
                                 M5 Dataset
                                     ↓
                                  BigQuery
                                     ↓
                                dbt Sources (`clean_calendar`, `clean_sales_train_validation`, `clean_sell_prices`, `fact_daily_sales`)
                                     ↓
                                dbt Staging Models (`stg_calendar`, `stg_sales`, `stg_sell_prices`)
                                     ↓
                                Intermediate Models (Week 2 Day 9)
                                     ↓
                                Analytical Marts (Week 2 Day 10-12)
                                     ↓
                                Demand Forecasting (Prophet & LightGBM - Week 3)
                                     ↓
                                Inventory Optimization (Week 4)
                                     ↓
                                Streamlit Executive Dashboard (Week 5)
```

---

## 5. dbt Core Integration & BigQuery Staging Layer (Week 2 Day 8)

### Purpose of dbt
dbt (Data Build Tool) transforms raw and standardized warehouse data into analytics-ready data models inside Google BigQuery. It enables modular SQL engineering, version-controlled transformations, automated lineage mapping, and schema data testing.

### BigQuery + dbt Workflow
1. **Source Mapping**: Warehouse tables (`retail_m5_dw`) are referenced using dbt `{{ source() }}` macros in `sources.yml`.
2. **Staging Layer (`models/staging/`)**: Light transformation views that rename columns, cast data types, and normalize structures (`stg_calendar`, `stg_sales`, `stg_sell_prices`).
3. **Data Quality Tests (`schema.yml`)**: Automated schema assertions ensuring key integrity before downstream modeling.

---

### dbt Project Structure (`dbt/`)

```
dbt/
├── dbt_project.yml          # Project configuration & materialization settings
├── profiles.yml             # Connection profiles for BigQuery and local DuckDB
├── models/
│   ├── staging/
│   │   ├── sources.yml      # Source table declarations
│   │   ├── schema.yml       # Schema quality test declarations
│   │   ├── stg_calendar.sql # Staging view for calendar metadata
│   │   ├── stg_sales.sql    # Staging view for sales series
│   │   └── stg_sell_prices.sql # Staging view for unit prices
│   ├── intermediate/        # Intermediate transformations (Week 2)
│   └── marts/               # Dimensional star schema marts (Week 2)
├── tests/                   # Singular custom test assertions
├── macros/                  # Reusable SQL macros
├── seeds/                   # Static lookup CSV seeds
└── snapshots/               # Type-2 SCD dimension snapshots
```

---

### Staging Models & Data Quality Tests

| Model Name | Source Table | Materialization | Key Columns & Type Casts | Applied Schema Tests |
| :--- | :--- | :--- | :--- | :--- |
| `stg_calendar` | `clean_calendar` | `view` | `sales_date (date)`, `wm_yr_wk (bigint)`, `day_id (string)`, `snap_* (integer)` | `not_null`, `unique` on `sales_date` & `day_id` |
| `stg_sales` | `clean_sales_train_validation` | `view` | `series_id (string)`, `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id` | `not_null`, `unique` on `series_id`, `accepted_values` on `cat_id` & `state_id` |
| `stg_sell_prices` | `clean_sell_prices` | `view` | `store_id`, `item_id`, `wm_yr_wk (bigint)`, `sell_price (double)` | `not_null` on `store_id`, `item_id`, `wm_yr_wk`, `sell_price` |

*(Note: Naturally duplicated dimensional fields like `cat_id`, `state_id`, `store_id`, and `item_id` are not marked as unique, maintaining domain accuracy).*

---

### How to Run dbt Commands

```bash
# 1. Test BigQuery / Warehouse Connection
dbt debug --project-dir dbt --profiles-dir dbt --target local

# 2. Parse Project SQL & YAML Metadata
dbt parse --project-dir dbt --profiles-dir dbt --target local

# 3. Build Staging Views & Execute Data Quality Tests (20/20 PASSED)
dbt build --project-dir dbt --profiles-dir dbt --target local

# Target production BigQuery:
dbt build --project-dir dbt --profiles-dir dbt --target dev
```

