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
- **Data Modeling & Transformation**: dbt (Data Build Tool - Week 2 Analytical Layer)
- **Forecasting Engines**: LightGBM, Facebook Prophet (Week 3)
- **Inventory Optimization**: Python SciPy / Custom Heuristics (Week 4)
- **Dashboard & Analytics**: Streamlit (Week 5)
- **Testing & Security**: Pytest, dbt-tests, Python-dotenv, GCP IAM Role Delegation

---

## 4. End-to-End System Data Architecture & Lineage

```
                                      M5 Raw Data
                                           ↓
                                    BigQuery / DuckDB
                                           ↓
                                      dbt Sources 
           (`clean_calendar`, `clean_sales_train_validation`, `clean_sell_prices`, `fact_daily_sales`)
                                           ↓
                                   dbt Staging Layer 
                       (`stg_calendar`, `stg_sales`, `stg_sell_prices`)
                                           ↓
                                  Intermediate Layer 
                                  (`int_daily_sales`)
                                           │
                     ┌─────────────────────┼─────────────────────┐
                     ↓                     ↓                     ↓
             Weekly Sales Model    Monthly Sales Model    Analytical Mart
            (`int_weekly_sales`)  (`int_monthly_sales`) (`mart_sales_forecasting`)
                     │                     │                     │
                     ↓                     ↓                     ↓
             `fct_weekly_sales`   `fct_monthly_sales`   Downstream Forecasting
                                                        (Prophet & LightGBM)
                                                                 │
                                                                 ↓
                                                      Inventory Optimization
                                                                 │
                                                                 ↓
                                                        Streamlit Dashboard
```

---

## 5. dbt Analytical Modeling & Transformation Layer (Week 2 Complete)

### Purpose of dbt Transformations
dbt (Data Build Tool) transforms raw and standardized warehouse tables into clean, aggregated, analytics-ready datasets inside Google BigQuery / DuckDB. It enables modular SQL software engineering, version-controlled transformations, automated lineage mapping with `ref()` and `source()`, and comprehensive data quality schema & singular testing.

### Retail Hierarchy Preservation
The analytical data layer strictly preserves Walmart's **M5 Retail Hierarchy**:
```
State (CA, TX, WI)
  ↓
Store (CA_1, CA_2, TX_1, WI_1)
  ↓
Category (FOODS, HOBBIES, HOUSEHOLD)
  ↓
Department (FOODS_1, FOODS_2, HOBBIES_1...)
  ↓
Item (FOODS_1_001, HOBBIES_1_001...)
```
No granular item-store dimensions are aggregated away in the primary forecasting mart, allowing downstream ML models to train and forecast at the item-store level or aggregate upward dynamically.

---

### Data Lineage & Model Breakdown

| Layer | Model Name | Materialization | Grain / Key Columns | Purpose & Business Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Staging** | `stg_calendar` | `view` | `sales_date` | Normalizes calendar dates, event classifications, SNAP entitlement flags, and Walmart week IDs (`wm_yr_wk`). |
| **Staging** | `stg_sales` | `view` | `series_id` | Cleans series identifiers and maps product hierarchy (`item_id`, `dept_id`, `cat_id`, `store_id`, `state_id`). |
| **Staging** | `stg_sell_prices` | `view` | `store_id + item_id + wm_yr_wk` | Casts and validates weekly unit selling prices in USD. |
| **Intermediate** | `int_daily_sales` | `view` | `sales_date + store_id + item_id` | Denormalizes fact daily sales with calendar attributes, SNAP flags, and event indicators. |
| **Intermediate** | `int_weekly_sales` | `view` | `wm_yr_wk + store_id + item_id` | Aggregates daily sales to weekly temporal levels (`wm_yr_wk`) with pricing min/max/avg stats. |
| **Intermediate** | `int_monthly_sales` | `view` | `year + month + store_id + item_id` | Aggregates daily sales to calendar monthly levels (`year`, `month`) with pricing stats. |
| **Marts** | `mart_sales_forecasting` | `table` | `date + store_id + item_id` | **Primary analytical mart** for Prophet & LightGBM forecasting. Contains sales, prices, hierarchy, and calendar features. |
| **Marts** | `fct_daily_sales` | `table` | `sales_date + store_id + item_id` | Materialized daily sales fact table serving operational daily reporting. |
| **Marts** | `fct_weekly_sales` | `table` | `wm_yr_wk + store_id + item_id` | Materialized weekly sales fact table serving tactical weekly reporting. |
| **Marts** | `fct_monthly_sales` | `table` | `year + month + store_id + item_id` | Materialized monthly sales fact table serving strategic executive reporting. |

---

### dbt Data Quality & Testing Framework (74/74 Tests Passing)

The dbt project enforces rigorous quality controls using standard schema tests (`not_null`, `unique`, `accepted_values`) and custom singular SQL tests:

1. **Schema Assertions**:
   - `not_null`: Applied across mandatory primary keys, dates, product IDs, store IDs, state IDs, categories, departments, and sales volume fields.
   - `accepted_values`: Enforces valid categories (`FOODS`, `HOBBIES`, `HOUSEHOLD`) and states (`CA`, `TX`, `WI`).
2. **Singular Custom Tests**:
   - `assert_daily_sales_unique_grain.sql`: Asserts uniqueness of `(sales_date, store_id, item_id)` grain.
   - `assert_daily_sales_non_negative.sql`: Asserts daily `sales >= 0`.
   - `assert_weekly_sales_unique_grain.sql`: Asserts uniqueness of `(wm_yr_wk, store_id, item_id)` grain.
   - `assert_monthly_sales_unique_grain.sql`: Asserts uniqueness of `(year, month, store_id, item_id)` grain.
   - `assert_weekly_sales_matches_daily.sql`: Asserts exact total sales conservation between daily and weekly layers.
   - `assert_monthly_sales_matches_daily.sql`: Asserts exact total sales conservation between daily and monthly layers.
   - `assert_mart_sales_forecasting_unique_grain.sql`: Asserts uniqueness of `(date, store_id, item_id)` in the final analytical forecasting mart.
   - `assert_mart_sales_forecasting_non_negative.sql`: Asserts non-negative sales and sell prices in the forecasting mart.

---

### Warehouse Validation Audit Results (`mart_sales_forecasting`)

Automated warehouse verification was executed against the compiled `mart_sales_forecasting` table:

- **Total Row Count**: 2,000 records
- **Date Range**: `2011-01-29` to `2011-05-08`
- **Retail Hierarchy Coverage**:
  - **States**: 3 (`CA`, `TX`, `WI`)
  - **Stores**: 4 (`CA_1`, `CA_2`, `TX_1`, `WI_1`)
  - **Categories**: 3 (`FOODS`, `HOBBIES`, `HOUSEHOLD`)
  - **Departments**: 6
  - **Items**: 20 distinct SKUs
- **Total Sales Volume**: 10,029 units
- **Data Quality Audit**:
  - **Null Values**: 0 nulls across date, item, store, state, category, department, sales.
  - **Duplicate Grain Records**: 0 duplicates at `(item_id + store_id + date)`.
  - **Negative Sales / Prices**: 0 negative values.
- **Sales Conservation Check**:
  - `int_daily_sales`: 10,029
  - `int_weekly_sales`: 10,029
  - `int_monthly_sales`: 10,029
  - `fct_daily_sales`: 10,029
  - `mart_sales_forecasting`: 10,029
  - **Result**: **100% Perfect Sales Alignment** across all transformation layers.

---

## 6. How to Run dbt Execution & Documentation Commands

```bash
# 1. Test Warehouse Connection (DuckDB / BigQuery)
dbt debug --profiles-dir dbt --target local

# 2. Parse Project SQL & YAML Metadata
dbt parse --profiles-dir dbt --target local

# 3. Build Models & Execute Data Quality Tests (74/74 PASSED)
dbt build --profiles-dir dbt --target local

# 4. Generate Interactive dbt Documentation & Lineage Catalog
dbt docs generate --profiles-dir dbt --target local

# Target production BigQuery:
dbt build --profiles-dir dbt --target dev
```
